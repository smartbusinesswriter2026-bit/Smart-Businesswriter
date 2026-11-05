"""Excel (.xlsx) export of a stored statements record (product layer, stdlib only).

Produces a real .xlsx workbook following the Minimax statement render design.
Every figure is read from the stored record — nothing is recomputed.
Amounts are written as typed numbers.  No third-party dependency (zipfile + XML).
"""
import io
import re
import zipfile
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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

THEME_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">
<a:themeElements>
<a:clrScheme name="Office">
<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
<a:dk2><a:srgbClr val="44546A"/></a:dk2>
<a:lt2><a:srgbClr val="E7E6E6"/></a:lt2>
<a:accent1><a:srgbClr val="4472C4"/></a:accent1>
<a:accent2><a:srgbClr val="ED7D31"/></a:accent2>
<a:accent3><a:srgbClr val="A5A5A5"/></a:accent3>
<a:accent4><a:srgbClr val="FFC000"/></a:accent4>
<a:accent5><a:srgbClr val="5B9BD5"/></a:accent5>
<a:accent6><a:srgbClr val="70AD47"/></a:accent6>
<a:hlink><a:srgbClr val="0563C1"/></a:hlink>
<a:folHlink><a:srgbClr val="954F72"/></a:folHlink>
</a:clrScheme>
<a:fontScheme name="Office">
<a:majorFont><a:latin typeface="Calibri Light"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
<a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>
</a:fontScheme>
<a:fmtScheme name="Office">
<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>
<a:lnStyleLst><a:ln w="6350" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln></a:lnStyleLst>
<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>
<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>
</a:fmtScheme>
</a:themeElements>
<a:objectDefaults/>
<a:extraClrSchemeLst/>
</a:theme>"""

CORE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>Financial Statements</dc:title>
<dc:creator>Smart Business Writer</dc:creator>
<cp:lastModifiedBy>Smart Business Writer</cp:lastModifiedBy>
<dcterms:created xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:created>
<dcterms:modified xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:modified>
</cp:coreProperties>"""

APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<Application>Smart Business Writer</Application>
</Properties>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
<Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
{sheets}
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<workbookPr/><bookViews><workbookView/></bookViews><sheets>
{sheets}
</sheets><calcPr calcId="124519" fullCalcOnLoad="1"/></workbook>"""

_SHEET_NAMES = {
    "income_statement": "Income Statement",
    "balance_sheet": "Balance Sheet",
    "equity": "Changes in Equity",
    "cash_flow": "Cash Flow Statement",
    "trial_balance": "Trial Balance",
    "notes": "Notes",
}


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


def _sheet_xml(rows_data):
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
                fmt_id = "164" if style == 3 else "0"
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


def _make_sheet_rows(text, title, period, currency):
    parsed = _parse_statement(text)
    rows = []
    rows.append((title, None, 2))
    rows.append(("Period: %s to %s" % (period.get("start", ""), period.get("end", "")), None, 0))
    rows.append(("Currency: " + currency, None, 0))
    rows.append(None)
    for label, val in parsed:
        if not label and val is None:
            rows.append(None)
            continue
        if _is_heading(label) and val is None:
            rows.append((label, None, 1))
            continue
        style = 0
        low = label.lower()
        if low.startswith("total") or low.startswith("net ") or "total " in low:
            style = 3
        v = float(val) if val is not None else None
        rows.append((label, v, style))
    return rows


def render_bytes(record):
    statements = record.get("statements") or {}
    statements_only = record.get("statements_only") or ""
    period = (record.get("reading") or {}).get("period") or {}
    currency = (record.get("reading") or {}).get("currency", "USD")

    sheet_defs = []
    sheet_names = []

    for key, title in [("income_statement", "Income Statement"),
                       ("balance_sheet", "Balance Sheet"),
                       ("equity", "Changes in Equity"),
                       ("cash_flow", "Cash Flow Statement"),
                       ("trial_balance", "Trial Balance"),
                       ("notes", "Notes")]:
        text = statements.get(key)
        if not text:
            continue
        rows = _make_sheet_rows(text, title, period, currency)
        if not any(r is not None and (r[0] or (len(r) > 1 and r[1] is not None)) for r in rows):
            continue
        xml = _sheet_xml(rows)
        sheet_names.append(title)
        sheet_defs.append((title, xml))

    if not sheet_defs and statements_only:
        rows = [(line, None, 0) for line in statements_only.splitlines()]
        xml = _sheet_xml(rows)
        sheet_names.append("Statements")
        sheet_defs.append(("Statements", xml))

    # Key Figures sheet
    scalars = (record.get("core") or {}).get("scalars") or {}
    if scalars:
        rows = [("Key Figures", None, 2),
                ("Period: %s to %s" % (period.get("start", ""), period.get("end", "")), None, 0),
                ("Currency: " + currency, None, 0), None,
                ("Figure", "Value", 1)]
        for key, val in scalars.items():
            v = _money(val)
            rows.append((key.replace("_", " ").title(), v, 0))
        sheet_names.append("Key Figures")
        sheet_defs.append(("Key Figures", _sheet_xml(rows)))

    # Verification Checks sheet
    checks = record.get("checks") or []
    if checks:
        rows = [("Verification Checks", None, 2),
                ("Period: %s to %s" % (period.get("start", ""), period.get("end", "")), None, 0), None,
                ("Check", "Result", 1)]
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
        sheet_defs.append(("Verification Checks", _sheet_xml(rows)))

    # Working sheet
    working = record.get("working") or {}
    journal = working.get("journal", "")
    trial_balance = working.get("trial_balance", "")
    if journal or trial_balance:
        rows = [("Working Papers", None, 2), None]
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
        sheet_defs.append(("Working", _sheet_xml(rows)))

    # Notes sheet
    notes_text = (record.get("statements") or {}).get("notes", "")
    if notes_text:
        rows = [("Notes", None, 2), None]
        for line in notes_text.splitlines():
            rows.append((line, None, 0))
        sheet_names.append("Notes")
        sheet_defs.append(("Notes", _sheet_xml(rows)))

    if not sheet_defs:
        sheet_defs.append(("Statements", _sheet_xml([("No statements available", None, 0)])))
        sheet_names.append("Statements")

    # Build the zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # [Content_Types].xml
        overrides = ""
        for i in range(len(sheet_names)):
            overrides += '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n' % (i + 1)
        overrides += '<Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>\n'
        overrides += '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\n'
        overrides += '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\n'
        ct = CONTENT_TYPES.replace("{sheets}", overrides)
        z.writestr("[Content_Types].xml", ct)

        z.writestr("_rels/.rels", RELS)
        z.writestr("docProps/core.xml", CORE_XML)
        z.writestr("docProps/app.xml", APP_XML)
        z.writestr("xl/theme/theme1.xml", THEME_XML)

        # workbook.xml
        sheet_entries = []
        rel_entries = []
        for i, name in enumerate(sheet_names, 1):
            sheet_entries.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name), i, i))
            rel_entries.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i))
        # styles relationship
        styles_rid = len(sheet_names) + 1
        rel_entries.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % styles_rid)
        # theme relationship
        theme_rid = len(sheet_names) + 2
        rel_entries.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>' % theme_rid)
        wb_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<workbookPr/><bookViews><workbookView/></bookViews><sheets>
""" + "\n".join(sheet_entries) + """
</sheets><calcPr calcId="124519" fullCalcOnLoad="1"/></workbook>"""
        z.writestr("xl/workbook.xml", wb_xml)

        rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        rels_xml += '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        rels_xml += "\n".join(rel_entries)
        rels_xml += "\n</Relationships>"
        z.writestr("xl/_rels/workbook.xml.rels", rels_xml)

        z.writestr("xl/styles.xml", STYLES_XML)
        for i, (name, xml) in enumerate(sheet_defs, 1):
            z.writestr("xl/worksheets/sheet%d.xml" % i, xml)

    return buf.getvalue()
