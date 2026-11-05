"""Excel (.xlsx) export of a stored statements record (product layer, stdlib only).

Produces a real .xlsx workbook with one sheet per rendered statement, plus Key Figures,
Verification Checks, Working, and Notes sheets.  Every figure is read from the stored
record — nothing is recomputed.  Amounts are written as typed numbers so Excel can
total and sort them.  No third-party dependency (zipfile + XML).

Follows the Minimax statement render design (docs/MINIMAX_STATEMENT_RENDER.md).
"""
import io
import re
import zipfile
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

from . import export as case_export

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
{sheets}
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>
{sheets}
</sheets>
</workbook>"""

SHEET_REL = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{rels}
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1">
<numFmt numFmtId="164" formatCode="#,##0.00"/>
</numFmts>
<fonts count="3">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="14"/><name val="Calibri"/></font>
</fonts>
<fills count="2">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/></border>
<border><left/><right/><top/><bottom style="thin"><color rgb="BFBFBF"/></bottom></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""

NUM_FMT = '#,##0.00'


def _money(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    text = str(v).strip().replace(",", "").strip("()")
    try:
        d = Decimal(text)
        if str(v).strip().startswith("("):
            d = -d
        return float(d)
    except (InvalidOperation, ValueError):
        return None


def _line_value(line):
    """(label, Decimal) for a rendered line ending in an amount, else (line, None)."""
    text = str(line or "").rstrip()
    m = re.match(r"^(.*?)\s{2,}(\S+)$", text)
    if not m:
        return text.strip(), None
    try:
        val = Decimal(m.group(2).replace(",", "").strip("()"))
        if m.group(2).startswith("("):
            val = -val
    except (InvalidOperation, ValueError):
        return text.strip(), None
    return m.group(1).strip(), val


def _parse_statement(text):
    rows = []
    for line in str(text or "").splitlines():
        if not line.strip():
            rows.append(("", None))
            continue
        label, val = _line_value(line)
        rows.append((label, val))
    return rows


def _is_heading(label):
    if not label:
        return False
    if label.isupper() and len(label) < 60:
        return True
    return False


_SHEET_NAMES = {
    "income_statement": "Income Statement",
    "balance_sheet": "Balance Sheet",
    "equity": "Changes in Equity",
    "cash_flow": "Cash Flow Statement",
    "trial_balance": "Trial Balance",
    "notes": "Notes",
}

COLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _cell_ref(col, row):
    return "%s%d" % (col, row)


def _sheet_xml(rows_data):
    """Build a worksheet XML from a list of (label, value_or_None, is_heading, is_total) rows."""
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
             '<sheetData>']
    r = 1
    for item in rows_data:
        if item is None:
            r += 1
            continue
        label, val, style = item
        lines.append('<row r="%d">' % r)
        # Column A: label
        if label:
            lines.append('<c r="A%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (r, escape(str(label))))
        # Column B: value
        if val is not None:
            lines.append('<c r="B%d" s="%d"><v>%s</v></c>' % (r, style, val))
        lines.append('</row>')
        r += 1
    lines.append('</sheetData>')
    # Column widths
    lines.append('<cols><col min="1" max="1" width="44" customWidth="1"/><col min="2" max="2" width="16" customWidth="1"/></cols>')
    lines.append('</worksheet>')
    return "\n".join(lines)


def _make_sheet_rows(text, title, period, currency):
    """Parse statement text into sheet rows: (label, value, style)."""
    parsed = _parse_statement(text)
    rows = []
    rows.append((title, None, 2))  # title style
    rows.append(("Period: %s to %s" % (period.get("start", ""), period.get("end", "")), None, 0))
    rows.append(("Currency: " + currency, None, 0))
    rows.append(None)  # blank
    for label, val in parsed:
        if not label and val is None:
            rows.append(None)
            continue
        if _is_heading(label) and val is None:
            rows.append((label, None, 1))  # section heading (bold)
            continue
        # Detect total/subtotal lines
        style = 0
        low = label.lower()
        if low.startswith("total") or low.startswith("net ") or "total " in low:
            style = 3  # total with border
        elif "subtotal" in low or low.startswith("less:") is False and ("total" in low):
            style = 1
        v = float(val) if val is not None else None
        rows.append((label, v, style))
    return rows


def render_bytes(record):
    """The whole .xlsx as bytes, built from the stored record (zipfile + XML)."""
    statements = record.get("statements") or {}
    statements_only = record.get("statements_only") or ""
    period = (record.get("reading") or {}).get("period") or {}
    currency = (record.get("reading") or {}).get("currency", "USD")

    # Build sheet list
    sheet_defs = []  # (name, xml_content)
    sheet_names = []

    for key, title in _SHEET_NAMES.items():
        text = statements.get(key)
        if not text:
            continue
        rows = _make_sheet_rows(text, title, period, currency)
        if not any(r is not None and (r[0] or r[1] is not None) for r in rows):
            continue
        xml = _sheet_xml(rows)
        sheet_names.append(title)
        sheet_defs.append((title, xml))

    # Fallback: if no structured sheets, use statements_only
    if not sheet_defs and statements_only:
        rows = [(line, None, 0) for line in statements_only.splitlines()]
        xml = _sheet_xml(rows)
        sheet_names.append("Statements")
        sheet_defs.append(("Statements", xml))

    # Key Figures sheet
    scalars = (record.get("core") or {}).get("scalars") or {}
    if scalars:
        rows = [("Key Figures", None, 2), ("Period: %s to %s" % (period.get("start", ""), period.get("end", "")), None, 0),
                ("Currency: " + currency, None, 0), None,
                ("Figure", None, 1), ("Value", None, 1)]
        # fix: need label/value in same row
        rows = [("Key Figures", None, 2), (None, None, 0)]
        # rebuild properly
        rows = []
        rows.append(("Key Figures", None, 2))
        rows.append(("Period: %s to %s" % (period.get("start", ""), period.get("end", "")), None, 0))
        rows.append(("Currency: " + currency, None, 0))
        rows.append(None)
        rows.append(("Figure", None, 1))
        # We'll put value in col B via a special marker — use tuples (label, value, style)
        # Rebuild as (label, value, style) triples
        rows = [("Key Figures", None, 2)]
        rows.append(("Period: %s to %s" % (period.get("start", ""), period.get("end", "")), None, 0))
        rows.append(("Currency: " + currency, None, 0))
        rows.append(None)
        rows.append(("Figure", None, 1))  # header placeholder
        # Actually use a two-column approach: store (label, value, style)
        rows = []
        rows.append(("Key Figures", None, 2))
        rows.append(("Period: %s to %s" % (period.get("start", ""), period.get("end", "")), None, 0))
        rows.append(("Currency: " + currency, None, 0))
        rows.append(None)
        # header row: label in A, "Value" in B
        rows.append(("Figure", "Value", 1))  # special: value is a string header
        for key, val in scalars.items():
            v = _money(val)
            rows.append((key.replace("_", " ").title(), v, 0))
        sheet_names.append("Key Figures")
        sheet_defs.append(("Key Figures", _sheet_xml_kv(rows)))

    # Verification Checks sheet
    checks = record.get("checks") or []
    if checks:
        rows = [("Verification Checks", None, 2)]
        rows.append(("Period: %s to %s" % (period.get("start", ""), period.get("end", "")), None, 0))
        rows.append(None)
        rows.append(("Check", "Result", 1))
        for ch in checks:
            if isinstance(ch, dict):
                name = ch.get("name", "")
                result_str = "PASS" if ch.get("ok") else "FAIL"
                detail = str(ch.get("detail", ""))[:200]
                rows.append((name, result_str + "  " + detail, 0))
            elif isinstance(ch, (list, tuple)) and len(ch) >= 2:
                name = str(ch[0])
                result_str = "PASS" if ch[1] else "FAIL"
                detail = str(ch[2])[:200] if len(ch) > 2 else ""
                rows.append((name, result_str + "  " + detail, 0))
        sheet_names.append("Verification Checks")
        sheet_defs.append(("Verification Checks", _sheet_xml_kv(rows, col_b_width=80)))

    # Working sheet (journal + trial balance + checks)
    working = record.get("working") or {}
    journal = working.get("journal", "")
    trial_balance = working.get("trial_balance", "")
    if journal or trial_balance:
        rows = [("Working Papers", None, 2)]
        rows.append(None)
        if journal:
            rows.append(("Journal", None, 1))
            for line in journal.splitlines():
                if line.strip():
                    rows.append((line.strip(), None, 0))
            rows.append(None)
        if trial_balance:
            rows.append(("Trial Balance", None, 1))
            for line in trial_balance.splitlines():
                if line.strip():
                    rows.append((line.strip(), None, 0))
        sheet_names.append("Working")
        sheet_defs.append(("Working", _sheet_xml_text(rows)))

    # Notes sheet is already created from _SHEET_NAMES above (key="notes").
    # Do not create a duplicate.

    if not sheet_defs:
        sheet_defs.append(("Statements", _sheet_xml_text([("No statements available", None, 0)])))
        sheet_names.append("Statements")

    # Build the zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _content_types(sheet_names))
        z.writestr("_rels/.rels", RELS)
        # workbook.xml
        sheet_entries = []
        rel_entries = []
        for i, name in enumerate(sheet_names, 1):
            sheet_entries.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name), i, i))
            rel_entries.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i))
        wb_xml = WORKBOOK.replace("{sheets}", "\n".join(sheet_entries))
        z.writestr("xl/workbook.xml", wb_xml)
        z.writestr("xl/_rels/workbook.xml.rels", SHEET_REL.replace("{rels}", "\n".join(rel_entries)))
        z.writestr("xl/styles.xml", STYLES)
        for i, (name, xml) in enumerate(sheet_defs, 1):
            z.writestr("xl/worksheets/sheet%d.xml" % i, xml)
    return buf.getvalue()


def _content_types(sheet_names):
    overrides = ""
    for i in range(len(sheet_names)):
        overrides += '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n' % (i + 1)
    return CONTENT_TYPES.replace("{sheets}", overrides)


def _sheet_xml(rows_data):
    """Build worksheet XML from (label, value, style) tuples. value can be float or None."""
    # First pass: build rows and count
    row_lines = []
    r = 1
    for item in rows_data:
        if item is None:
            r += 1
            continue
        if isinstance(item, str):
            item = (item, None, 0)
        label, val, style = item if len(item) == 3 else (item[0], item[1] if len(item) > 1 else None, 0)
        row_lines.append('<row r="%d">' % r)
        if label is not None and str(label).strip():
            row_lines.append('<c r="A%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (r, escape(str(label))))
        if val is not None:
            if isinstance(val, str):
                row_lines.append('<c r="B%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (r, escape(val)))
            else:
                row_lines.append('<c r="B%d" s="%d"><v>%s</v></c>' % (r, style, val))
        row_lines.append('</row>')
        r += 1
    max_row = r - 1
    if max_row < 1:
        max_row = 1
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
             '<dimension ref="A1:B%d"/>' % max_row,
             '<sheetData>']
    lines.extend(row_lines)
    lines.append('</sheetData>')
    lines.append('<cols><col min="1" max="1" width="44" customWidth="1"/><col min="2" max="2" width="18" customWidth="1"/></cols>')
    lines.append('</worksheet>')
    return "\n".join(lines)


def _sheet_xml_kv(rows_data, col_b_width=18):
    """Build worksheet XML from (label, value, style) tuples where value can be str or float."""
    return _sheet_xml(rows_data)


def _sheet_xml_text(rows_data):
    """Build worksheet XML from text-only rows."""
    return _sheet_xml(rows_data)
