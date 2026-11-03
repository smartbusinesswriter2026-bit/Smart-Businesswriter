"""Spreadsheet exports from a stored case bundle (product layer, standard library only).

Three formats, all written from the **stored values** so nothing is re-typed,
re-rounded or recomputed:

* CSV - the artifact table (`artifact, metric, unit, precision, value, derivation`);
* SpreadsheetML 2003 XML - a workbook with three worksheets: `Case` (identity),
  `Artifacts` (the table) and `Report` (the delivered report, one line per row);
* .xlsx (Office Open XML) - the primary spreadsheet download: `Case`, one sheet
  per requested statement, the working papers and the notes when the case carries
  them, the recorded values and the report.

A spreadsheet carries **no hash and no internal marker**: the spec hash, the code
hash, the entry hashes and the file digest are the system's own identifiers, they
belong to the record behind the artefact, and they are never printed in a student's
workbook (B-199).  The file's SHA-256 is returned to the caller beside the download,
not written into a cell.

**The statements are typed cells.**  A statement sheet writes its label in column A
and its amount in column B as a *number*, so Excel and LibreOffice can total and
sort the column; the amount format carries the record's decimal places, a thousands
separator and parentheses for a negative, exactly as the record's own text renders
them.  The case sheets (the artifact table, the report) keep the stored strings,
because those values are not all numbers and re-typing them would change them.

The files open in Excel and LibreOffice; no third-party library is used.
"""

import csv
import hashlib
import io
import os
import tempfile
import zipfile
from decimal import Decimal as D, InvalidOperation
from pathlib import Path
from xml.sax.saxutils import escape

from . import export as case_export

CSV_HEADER = ("artifact", "metric", "unit", "precision", "value", "derivation")
#: The stored row key for each CSV column (the artifact table calls the id "id").
ROW_KEYS = ("id", "metric", "unit", "precision", "value", "derivation")


def artifact_rows(bundle):
    """The stored artifact rows (re-exported for callers of this module)."""
    return case_export.artifact_rows(bundle)


def to_csv(bundle):
    """The artifact table as deterministic CSV text (stored strings, LF endings)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for row in artifact_rows(bundle):
        writer.writerow(["" if row.get(key) is None else str(row.get(key)) for key in ROW_KEYS])
    return buffer.getvalue()


SCHEDULE_HEADER = ("Activity", "Early start", "Early finish", "Late start", "Late finish", "Float", "Critical")


def _schedule_values(bundle):
    values = {}
    for row in artifact_rows(bundle):
        metric = row.get("metric")
        if not isinstance(metric, str):
            continue
        for prefix in ("es_", "ef_", "ls_", "lf_", "float_", "critical_"):
            if metric.startswith(prefix):
                values.setdefault(metric[len(prefix):], {})[prefix[:-1]] = row.get("value")
                break
    # `critical_count` and similar totals are not activities: a schedule row
    # needs an early start and an early finish.
    return {name: found for name, found in values.items() if "es" in found and "ef" in found}


def _schedule_rows(bundle):
    """A schedule sheet from stored CPM artifacts, or [] when the case has none."""
    values = _schedule_values(bundle)
    if not values:
        return []
    rows = [SCHEDULE_HEADER]
    for activity in sorted(values):
        found = values[activity]
        rows.append((activity,) + tuple("" if found.get(key) is None else str(found.get(key))
                                        for key in ("es", "ef", "ls", "lf", "float", "critical")))
    return rows


def _schedule_xlsx_rows(bundle):
    """The schedule with a coloured bar strip, when every date is a whole period."""
    values = _schedule_values(bundle)
    if not values:
        return []
    try:
        periods = {}
        for activity, found in values.items():
            start, finish = int(D(str(found["es"]))), int(D(str(found["ef"])))
            if D(str(found["es"])) != start or D(str(found["ef"])) != finish:
                return []
            periods[activity] = (start, finish, str(found.get("critical")) == "1")
    except (KeyError, InvalidOperation, ValueError):
        return []
    horizon = max(finish for _start, finish, _critical in periods.values())
    header = list(SCHEDULE_HEADER) + [str(period) for period in range(horizon + 1)]
    rows = [[(cell, True) for cell in header]]
    for activity in sorted(values):
        found = values[activity]
        base = [activity] + ["" if found.get(key) is None else str(found.get(key))
                             for key in ("es", "ef", "ls", "lf", "float", "critical")]
        start, finish, critical = periods[activity]
        strip = [("", 3 if critical else 2) if start <= period < finish else ""
                 for period in range(horizon + 1)]
        rows.append(base + strip)
    return rows


def _sheet(name, rows):
    """One SpreadsheetML worksheet from a list of string rows."""
    body = []
    for cells in rows:
        body.append("<Row>%s</Row>" % "".join(
            '<Cell><Data ss:Type="String">%s</Data></Cell>' % escape(str(cell)) for cell in cells))
    return '<Worksheet ss:Name="%s"><Table>%s</Table></Worksheet>' % (escape(str(name)), "".join(body))


def to_spreadsheetml(bundle):
    """The workbook as deterministic SpreadsheetML 2003 XML text."""
    identity = [
        ("Case id", str(bundle.get("id") or "not recorded")),
        ("Title", str(bundle.get("title") or "not recorded")),
        ("Method", str(bundle.get("method") or "not recorded")),
        ("Tier", str(bundle.get("tier") or "not recorded")),
        ("Created at", str(bundle.get("created_at") or "not recorded")),
    ]
    artifacts = [CSV_HEADER] + [
        tuple("" if row.get(key) is None else str(row.get(key)) for key in ROW_KEYS)
        for row in artifact_rows(bundle)]
    schedule = _schedule_rows(bundle)
    delivery = bundle.get("delivery")
    report = delivery.get("report") if isinstance(delivery, dict) and isinstance(delivery.get("report"), str) else ""
    report_rows = [("Line", "Text")] + [("", line) for line in report.splitlines()] or [("not recorded", "")]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
            'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
            + _sheet("Case", identity) + _sheet("Artifacts", artifacts)
            + (_sheet("Schedule", schedule) if schedule else "")
            + _sheet("Report", report_rows)
            + "</Workbook>\n")


def _write(path, text, suffix):
    target = Path(path)
    if str(target.parent) not in ("", "."):
        target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(target.parent or "."), prefix=".tmp-%s-" % suffix, suffix="." + suffix)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return str(target)


def export_csv(bundle, path):
    """Write the artifact CSV. Returns the path."""
    return _write(path, to_csv(bundle), "csv")


def export_spreadsheetml(bundle, path, sha=False):
    """Write the SpreadsheetML workbook. Returns the path (or a path/sha dict when `sha`)."""
    text = to_spreadsheetml(bundle)
    written = _write(path, text, "xml")
    if sha:
        return {"path": written, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    return written


# -- .xlsx (Office Open XML), written with the standard library ---------------
#: Style ids in `xl/styles.xml`.  0-3 are the case sheets' own (plain, bold, and the two bar
#: fills the CPM schedule uses); the rest belong to the statement sheets.
ST_TEXT = 0
ST_BOLD = 1
ST_HEADER = 2
ST_HEADER_ALT = 3
ST_TITLE = 4
ST_SUBTITLE = 5
ST_GROUP = 6
ST_DETAIL = 7
ST_SUBTOTAL = 8
ST_TOTAL = 9
ST_AMOUNT = 10
ST_AMOUNT_SUBTOTAL = 11
ST_AMOUNT_TOTAL = 12
ST_NOTE = 13
ST_TABLE_HEAD = 14
ST_PASS = 15
ST_FAIL = 16

_XLSX_CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                       '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                       '<Default Extension="xml" ContentType="application/xml"/>'
                       '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                       '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                       "%s</Types>")
_XLSX_ROOT_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')


def _styles_xml(places=2):
    """The workbook's styles: the case sheets' four, and the statement sheets' own.

    The amount format carries the record's decimal places, a thousands separator and
    parentheses for a negative - the same convention the record's own text uses.
    """
    digits = places if isinstance(places, int) and 0 <= places <= 6 else 2
    plain = "#,##0" + ("." + "0" * digits if digits else "")
    amount_format = "%s;(%s)" % (plain, plain)
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<numFmts count="1"><numFmt numFmtId="164" formatCode="%s"/></numFmts>'
            '<fonts count="5"><font><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="14"/><name val="Calibri"/></font>'
            '<font><i/><sz val="11"/><name val="Calibri"/><color rgb="FF595959"/></font>'
            '<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFC00000"/></font></fonts>'
            '<fills count="4"><fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FF4E79A7"/><bgColor indexed="64"/></patternFill></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FFE15759"/><bgColor indexed="64"/></patternFill></fill></fills>'
            '<borders count="4"><border/>'
            '<border><left/><right/><top style="thin"><color rgb="FF000000"/></top><bottom/><diagonal/></border>'
            '<border><left/><right/><top/><bottom style="double"><color rgb="FF000000"/></bottom><diagonal/></border>'
            '<border><left/><right/><top/><bottom style="thin"><color rgb="FF000000"/></bottom><diagonal/></border>'
            '</borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="17">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
            '<xf numFmtId="0" fontId="0" fillId="2" borderId="0" xfId="0" applyFill="1"/>'
            '<xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1"/>'
            '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
            '<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1">'
            '<alignment indent="1"/></xf>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="2" xfId="0" applyFont="1" applyBorder="1"/>'
            '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1">'
            '<alignment horizontal="right"/></xf>'
            '<xf numFmtId="164" fontId="1" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1"'
            ' applyBorder="1" applyAlignment="1"><alignment horizontal="right"/></xf>'
            '<xf numFmtId="164" fontId="1" fillId="0" borderId="2" xfId="0" applyNumberFormat="1" applyFont="1"'
            ' applyBorder="1" applyAlignment="1"><alignment horizontal="right"/></xf>'
            '<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="3" xfId="0" applyFont="1" applyBorder="1"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
            '<xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
            '</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            '</styleSheet>') % escape(amount_format)

_SHEET_BAD = set('[]:*?/\\')


def _column(index):
    """"A", "B", ... "AA" for a zero-based column index."""
    name = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def _text(value):
    """XML-safe cell text with the characters a spreadsheet cannot hold removed."""
    text = "" if value is None else str(value)
    cleaned = "".join(ch for ch in text if ch in "\t\n\r" or ord(ch) >= 32)
    return escape(cleaned)


def _number_text(value):
    """A number as the cell's own text: the record's value, never re-quantised."""
    return format(value, "f")


def _xlsx_sheet(rows, widths=None, freeze=None):
    """One worksheet part.

    A row is a list of cells; a cell is text, a number, or a (value, style) pair.  A number is
    written as a number, so the column can be totalled and sorted; the amount format in
    `xl/styles.xml` gives it the record's decimal places and a thousands separator.
    """
    body = []
    for r, cells in enumerate(rows, start=1):
        out = []
        for c, cell in enumerate(cells):
            marker = cell[1] if isinstance(cell, tuple) and len(cell) == 2 else None
            value = cell[0] if isinstance(cell, tuple) else cell
            if marker is True:
                style_id = 1
            elif isinstance(marker, int):
                style_id = marker
            else:
                style_id = 0
            style = ' s="%d"' % style_id if style_id else ""
            if isinstance(value, D):
                out.append('<c r="%s%d"%s><v>%s</v></c>'
                           % (_column(c), r, style, _number_text(value)))
            elif value is None or str(value) == "":
                # an empty cell, so a long label beside it can overflow into it
                out.append('<c r="%s%d"%s/>' % (_column(c), r, style))
            else:
                out.append('<c r="%s%d" t="inlineStr"%s><is><t xml:space="preserve">%s</t></is></c>'
                           % (_column(c), r, style, _text(value)))
        body.append('<row r="%d">%s</row>' % (r, "".join(out)))
    views = ""
    if freeze:
        views = ('<sheetViews><sheetView workbookViewId="0">'
                 '<pane ySplit="%d" topLeftCell="A%d" activePane="bottomLeft" state="frozen"/>'
                 '<selection pane="bottomLeft" activeCell="A%d" sqref="A%d"/>'
                 '</sheetView></sheetViews>' % (freeze, freeze + 1, freeze + 1, freeze + 1))
    columns = ""
    if widths:
        columns = ("<cols>" + "".join(
            '<col min="%d" max="%d" width="%s" customWidth="1"/>' % (i + 1, i + 1, width)
            for i, width in enumerate(widths)) + "</cols>")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            + views + columns + "<sheetData>" + "".join(body) + "</sheetData></worksheet>")


def _sheet_name(name, used):
    clean = "".join(ch for ch in str(name) if ch not in _SHEET_BAD)[:31] or "Sheet"
    candidate, n = clean, 2
    while candidate.lower() in used:
        suffix = " (%d)" % n
        candidate = clean[:31 - len(suffix)] + suffix
        n += 1
    used.add(candidate.lower())
    return candidate


# -- the statements, as typed cells --------------------------------------------
#
# A statement sheet is a walk over the record's own typed blocks: the chart's statement line is
# the label, the record's figure is the number, and nothing is summed here.  A subtotal is the
# record's subtotal, not the sum of the cells above it; a figure the record does not carry is
# named as missing rather than filled in.

#: The statement each code means, and the sheet it is written on.
STATEMENT_SHEETS = (("IS", "Income statement"), ("RE", "Changes in equity"),
                    ("BS", "Balance sheet"), ("CF", "Cash flow"))

#: The working sheet's columns: date, description, account, debit, credit.
WORKING_WIDTHS = (12, 46, 28, 18, 18)

#: The record's wording for each balance-sheet section and its subtotal.
BS_SECTIONS = (("current_assets", "Current assets", "Total current assets"),
               ("non_current_assets", "Non-current assets", "Total non-current assets"),
               ("unclassified_assets", "Assets (no section declared)", "Total unclassified assets"))
BS_LIABILITIES = (("current_liabilities", "Current liabilities", "Total current liabilities"),
                  ("non_current_liabilities", "Non-current liabilities", "Total non-current liabilities"),
                  ("unclassified_liabilities", "Liabilities (no section declared)", "Total unclassified liabilities"))


def _number(value):
    """The record's own figure as a number, exactly as it is stored.

    `None` when the record does not carry the figure as a number: a gap is named, never filled.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, D):
        return value if value.is_finite() else None
    text = str(value).strip()
    if not text:
        return None
    try:
        found = D(text)
    except InvalidOperation:
        return None
    return found if found.is_finite() else None


def _amount(value, style=ST_AMOUNT):
    """A cell holding the record's figure as a number."""
    number = _number(value)
    if number is None:
        return ("not in the record", ST_NOTE)
    return (number, style)


def _side(value, style=ST_AMOUNT):
    """One side of an entry: the amount, or nothing when that side has none.

    The record's own text leaves a side blank when it carries no amount, and a column of
    zeros is not what a trial balance looks like.
    """
    number = _number(value)
    if number is None or number == 0:
        return ("", ST_TEXT)
    return (number, style)


def _title_row(accounts, key, fallback):
    """The statement's own title: the wording the record uses for it."""
    text = (accounts.get("statements_export") or {}).get(key) or ""
    for line in text.splitlines():
        if line.strip():
            return [(line.strip(), ST_TITLE)]
    return [(fallback, ST_TITLE)]


def _period_line(accounts, as_at=False):
    """The period line under the title, from the record's engagement."""
    engagement = accounts.get("engagement") or {}
    period = engagement.get("period") or {}
    currency = engagement.get("currency") or ""
    start, end = period.get("start"), period.get("end")
    if as_at:
        return "As at %s   %s" % (end, currency) if end else ""
    return "%s to %s   %s" % (start, end, currency) if start and end else ""


def _headings(accounts, key, fallback, as_at=False):
    """The title row and the period line."""
    rows = [_title_row(accounts, key, fallback)]
    period = _period_line(accounts, as_at=as_at)
    if period:
        rows.append([(period, ST_SUBTITLE)])
    return rows


def _income_statement_rows(accounts):
    """The income statement: revenue lines, expense lines, and the record's net income.

    The lines are the chart's statement lines, so the accounts of one line are one row, and the
    record's own order is kept (the record prints its expense lines alphabetically).
    """
    groups = accounts.get("income_groups") or {}
    income = groups.get("income") or {}
    expenses = groups.get("expenses") or {}
    comprehensive = accounts.get("comprehensive_income") or {}
    rows = _headings(accounts, "income_statement", "INCOME STATEMENT")
    rows.append([("Revenue", ST_GROUP)])
    for label in sorted(income):
        rows.append([(label, ST_DETAIL), _amount(income[label])])
    rows.append([("Total revenue", ST_SUBTOTAL), _amount(groups.get("total_revenue"), ST_AMOUNT_SUBTOTAL)])
    rows.append([])
    rows.append([("Expenses", ST_GROUP)])
    for label in sorted(expenses):
        rows.append([(label, ST_DETAIL), _amount(expenses[label])])
    rows.append([("Total expenses", ST_SUBTOTAL), _amount(groups.get("total_expenses"), ST_AMOUNT_SUBTOTAL)])
    rows.append([("Net income", ST_TOTAL), _amount(comprehensive.get("profit_for_period"), ST_AMOUNT_TOTAL)])
    oci = groups.get("oci") or {}
    if oci:
        rows.append([])
        rows.append([("Other comprehensive income", ST_GROUP)])
        for label in sorted(oci):
            rows.append([(label, ST_DETAIL), _amount(oci[label])])
        rows.append([("Total other comprehensive income", ST_SUBTOTAL),
                     _amount(groups.get("total_oci"), ST_AMOUNT_SUBTOTAL)])
        rows.append([("Total comprehensive income", ST_TOTAL),
                     _amount(groups.get("total_comprehensive_income"), ST_AMOUNT_TOTAL)])
    return rows


def _balance_sheet_rows(accounts):
    """The balance sheet, in the sections the record's own grouping uses."""
    grouped = accounts.get("balance_sheet_groups") or {}
    if not grouped.get("classified"):
        return _balance_sheet_flat_rows(accounts)
    groups = grouped.get("groups") or {}
    totals = grouped.get("totals") or {}
    statements = accounts.get("statements") or {}
    rows = _headings(accounts, "balance_sheet", "BALANCE SHEET", as_at=True)
    for key, title, total_label in BS_SECTIONS:
        group = groups.get(key) or {}
        if not group:
            continue
        rows.append([(title, ST_GROUP)])
        for label, value in group.items():
            rows.append([(label, ST_DETAIL), _amount(value)])
        rows.append([(total_label, ST_SUBTOTAL), _amount(totals.get(key), ST_AMOUNT_SUBTOTAL)])
    rows.append([("Total assets", ST_TOTAL), _amount(statements.get("total_assets"), ST_AMOUNT_TOTAL)])
    rows.append([])
    for key, title, total_label in BS_LIABILITIES:
        group = groups.get(key) or {}
        if not group:
            continue
        rows.append([(title, ST_GROUP)])
        for label, value in group.items():
            rows.append([(label, ST_DETAIL), _amount(value)])
        rows.append([(total_label, ST_SUBTOTAL), _amount(totals.get(key), ST_AMOUNT_SUBTOTAL)])
    rows.append([("Total liabilities", ST_TOTAL), _amount(statements.get("total_liabilities"), ST_AMOUNT_TOTAL)])
    rows.append([])
    rows.append([("Equity", ST_GROUP)])
    for label, value in (groups.get("equity") or {}).items():
        rows.append([(label, ST_DETAIL), _amount(value)])
    rows.append([("Total equity", ST_SUBTOTAL), _amount(totals.get("equity"), ST_AMOUNT_SUBTOTAL)])
    rows.append([("Total liabilities and equity", ST_TOTAL),
                 _amount(statements.get("total_assets"), ST_AMOUNT_TOTAL)])
    return rows


def _balance_sheet_flat_rows(accounts):
    """The balance sheet of a chart that declares no section: one row per statement line.

    The record's own projection carries the lines and their totals, so no account is listed
    twice and no total is worked out here.
    """
    statements = accounts.get("statements") or {}
    rows = _headings(accounts, "balance_sheet", "BALANCE SHEET", as_at=True)
    for key, title, total_label, total in (
            ("assets", "Assets", "Total assets", statements.get("total_assets")),
            ("liabilities", "Liabilities", "Total liabilities", statements.get("total_liabilities")),
            ("equity", "Equity", "Total equity", statements.get("equity_with_current_earnings"))):
        group = statements.get(key) or {}
        if not group:
            continue
        rows.append([(title, ST_GROUP)])
        for label, value in group.items():
            rows.append([(label, ST_DETAIL), _amount(value)])
        rows.append([(total_label, ST_SUBTOTAL), _amount(total, ST_AMOUNT_SUBTOTAL)])
        if key != "equity":
            rows.append([])
    rows.append([("Total liabilities and equity", ST_TOTAL),
                 _amount(statements.get("total_assets"), ST_AMOUNT_TOTAL)])
    return rows


def _cash_flow_rows(accounts):
    """The cash flow statement: the record's dated movements under each activity, then its totals."""
    cash = accounts.get("cash_flow") or {}
    rows = _headings(accounts, "cash_flow", "CASH FLOW STATEMENT")
    detail = cash.get("detail") or []
    for key, title in (("operating", "Operating activities"), ("investing", "Investing activities"),
                       ("financing", "Financing activities")):
        rows.append([(title, ST_GROUP)])
        for entry in detail:
            if entry.get("activity") != key:
                continue
            label = "%s  %s" % (entry.get("date"), entry.get("description"))
            rows.append([(label, ST_DETAIL), _amount(entry.get("amount"))])
        rows.append([("Total %s" % title.lower(), ST_SUBTOTAL), _amount(cash.get(key), ST_AMOUNT_SUBTOTAL)])
        if key != "financing":
            rows.append([])
    rows.append([("Net change in cash", ST_TOTAL), _amount(cash.get("net_direct"), ST_AMOUNT_TOTAL)])
    rows.append([("Cash at start of period", ST_TOTAL), _amount(cash.get("opening_cash"), ST_AMOUNT_TOTAL)])
    rows.append([("Cash at end of period", ST_TOTAL), _amount(cash.get("closing_cash"), ST_AMOUNT_TOTAL)])
    return rows


def _equity_rows(accounts):
    """The statement of changes in equity, from the record's own roll.

    Per account: the opening balance, each movement with its kind and what it was, and the
    closing balance - so a reader can check opening + movements = closing line by line.
    """
    equity = accounts.get("equity_statement") or {}
    rows = _headings(accounts, "equity_statement_export", "STATEMENT OF CHANGES IN EQUITY")
    for account in equity.get("accounts") or []:
        rows.append([(str(account.get("name") or ""), ST_GROUP)])
        rows.append([("Opening balance", ST_DETAIL), _amount(account.get("opening"))])
        movements = account.get("movements") or []
        if not movements:
            rows.append([("no movement in the period", ST_DETAIL), ("", ST_TEXT)])
        for movement in movements:
            label = "%s  %s" % (movement.get("date"), movement.get("kind"))
            note = str(movement.get("description") or "")
            if movement.get("closing_entry"):
                note += " (closing)"
            row = [(label, ST_DETAIL), _amount(movement.get("amount"))]
            if note:
                row.append((note, ST_NOTE))
            rows.append(row)
        rows.append([("Closing balance", ST_DETAIL), _amount(account.get("closing"))])
        rows.append([])
    rows.append([("Total opening", ST_SUBTOTAL), _amount(equity.get("total_opening"), ST_AMOUNT_SUBTOTAL)])
    rows.append([("Total movement", ST_SUBTOTAL), _amount(equity.get("total_movement"), ST_AMOUNT_SUBTOTAL)])
    rows.append([("Total closing", ST_TOTAL), _amount(equity.get("total_closing"), ST_AMOUNT_TOTAL)])
    return rows


def _requested(accounts, bundle=None):
    """The statements the record was asked to render.

    The request travels with the appendix (`requested`), because the workbook is built from the
    appendix alone.  A statement that was computed but not asked for is not a sheet.
    """
    for source in (accounts, (bundle or {}).get("delivery") or {}, bundle or {}):
        wanted = source.get("requested") if isinstance(source, dict) else None
        if isinstance(wanted, list) and wanted:
            return [str(code).strip().upper() for code in wanted]
    return [code for code, _name in STATEMENT_SHEETS]


def _statement_rows(code, accounts):
    """The rows of one statement, or [] when the record does not carry that statement."""
    if code == "IS":
        return _income_statement_rows(accounts)
    if code == "RE":
        return _equity_rows(accounts)
    if code == "BS":
        return _balance_sheet_rows(accounts)
    if code == "CF":
        if accounts.get("cash_flow_withheld_because") or not accounts.get("cash_flow"):
            return []
        return _cash_flow_rows(accounts)
    return []


def _working_rows(accounts, requested=None):
    """The working papers: the journal, the trial balance, the checks and the cash flow's reconciliations.

    Everything here is the record's own figure.  The journal's hashes and the entry markers are
    the system's, not the student's, and are not written.
    """
    rows = [[("WORKING PAPERS", ST_TITLE)]]
    period = _period_line(accounts)
    if period:
        rows.append([(period, ST_SUBTITLE)])
    rows.append([])
    rows.append([("Journal", ST_GROUP)])
    rows.append([("Date", ST_TABLE_HEAD), ("Description", ST_TABLE_HEAD), ("Account", ST_TABLE_HEAD),
                 ("Debit", ST_TABLE_HEAD), ("Credit", ST_TABLE_HEAD)])
    for entry in accounts.get("journal") or []:
        description = str(entry.get("description") or "")
        if entry.get("opening"):            # the record marks an opening entry as one
            description = "(opening) " + description
        for line in entry.get("lines") or []:
            rows.append([(str(entry.get("date") or ""), ST_TEXT), (description, ST_TEXT),
                         (str(line.get("name") or ""), ST_TEXT), _side(line.get("debit")),
                         _side(line.get("credit"))])
    rows.append([])
    rows.append([("Trial balance", ST_GROUP)])
    rows.append([("Account", ST_TABLE_HEAD), ("", ST_TABLE_HEAD), ("", ST_TABLE_HEAD),
                 ("Debit", ST_TABLE_HEAD), ("Credit", ST_TABLE_HEAD)])
    trial = accounts.get("trial_balance") or {}
    for row in trial.get("rows") or []:
        cells = list(row) if isinstance(row, (list, tuple)) else []
        name = cells[1] if len(cells) > 1 else (row.get("name") if isinstance(row, dict) else "")
        debit = cells[2] if len(cells) > 2 else (row.get("debit") if isinstance(row, dict) else "")
        credit = cells[3] if len(cells) > 3 else (row.get("credit") if isinstance(row, dict) else "")
        rows.append([(str(name or ""), ST_TEXT), ("", ST_TEXT), ("", ST_TEXT), _side(debit), _side(credit)])
    rows.append([("Total", ST_TOTAL), ("", ST_TOTAL), ("", ST_TOTAL),
                 _amount(trial.get("total_debits"), ST_AMOUNT_TOTAL),
                 _amount(trial.get("total_credits"), ST_AMOUNT_TOTAL)])
    rows.append([])
    rows.append([("Checks", ST_GROUP)])
    rows.append([("Check", ST_TABLE_HEAD), ("", ST_TABLE_HEAD), ("", ST_TABLE_HEAD),
                 ("Result", ST_TABLE_HEAD), ("Detail", ST_TABLE_HEAD)])
    for check in accounts.get("checks") or []:
        cells = list(check) if isinstance(check, (list, tuple)) else []
        name = cells[0] if cells else ""
        ok = bool(cells[1]) if len(cells) > 1 else False
        detail = cells[2] if len(cells) > 2 else ""
        rows.append([(str(name), ST_TEXT), ("", ST_TEXT), ("", ST_TEXT),
                     ("PASS" if ok else "FAIL", ST_PASS if ok else ST_FAIL), (str(detail), ST_TEXT)])
    cash = accounts.get("cash_flow") or {}
    if cash:
        rows.append([])
        rows.append([("Cash flow reconciliation", ST_GROUP)])
        for label, value in (("Operating activities", cash.get("operating")),
                             ("Investing activities", cash.get("investing")),
                             ("Financing activities", cash.get("financing")),
                             ("Net change in cash, direct route", cash.get("net_direct")),
                             ("Net change in cash, indirect route", cash.get("net_indirect")),
                             ("Cash at start of period", cash.get("opening_cash")),
                             ("Cash at end of period", cash.get("closing_cash"))):
            rows.append([(label, ST_DETAIL), ("", ST_TEXT), ("", ST_TEXT), _amount(value), ("", ST_TEXT)])
    reconciliation = accounts.get("reconciliation")
    if isinstance(reconciliation, dict) and reconciliation:
        rows.append([])
        who = reconciliation.get("account_name") or "the cash account"
        rows.append([("Reconciliation (%s)" % who, ST_GROUP)])
        for label, value in (("Balance per statement", reconciliation.get("statement_closing")),
                             ("Add: receipts in transit", reconciliation.get("receipts_in_transit")),
                             ("Less: outstanding payments", reconciliation.get("payments_outstanding")),
                             ("Adjusted statement balance", reconciliation.get("adjusted_statement")),
                             ("Balance per ledger", reconciliation.get("ledger_balance")),
                             ("Add: unrecorded receipts", reconciliation.get("unrecorded_receipts")),
                             ("Less: unrecorded payments", reconciliation.get("unrecorded_payments")),
                             ("Adjusted ledger balance", reconciliation.get("adjusted_ledger")),
                             ("Difference", reconciliation.get("difference"))):
            rows.append([(label, ST_DETAIL), ("", ST_TEXT), ("", ST_TEXT), _amount(value), ("", ST_TEXT)])
    withheld = accounts.get("cash_flow_withheld_because")
    if withheld:
        rows.append([])
        rows.append([("Cash flow statement", ST_GROUP)])
        rows.append([("Withheld", ST_DETAIL), ("", ST_TEXT), ("", ST_TEXT), ("", ST_TEXT),
                     (str(withheld), ST_NOTE)])
    elif "CF" in (requested or []) and not cash:
        rows.append([])
        rows.append([("Cash flow statement", ST_GROUP)])
        rows.append([("Withheld", ST_DETAIL), ("", ST_TEXT), ("", ST_TEXT), ("", ST_TEXT),
                     ("the record does not carry a cash flow statement", ST_NOTE)])
    return rows


def _notes_rows(accounts):
    """The record's notes, verbatim: one line per row."""
    text = (accounts.get("statements_export") or {}).get("notes") or ""
    rows = []
    for line in text.splitlines():
        rows.append([(line, ST_TITLE if not rows else ST_TEXT)])
    return rows


def _label_width(rows):
    """Column A is as wide as the longest label it holds, within a readable bound."""
    longest = 0
    for row in rows:
        for cell in row:
            value = cell[0] if isinstance(cell, tuple) else cell
            if isinstance(value, str):
                longest = max(longest, len(value))
    return min(60, max(24, longest + 2))


def _accounting_rows(accounts, bundle=None):
    """The sheets a statements record becomes: one per requested statement, then the working, then the notes."""
    sheets = []
    requested = _requested(accounts, bundle)
    for code, name in STATEMENT_SHEETS:
        if code not in requested:
            continue
        rows = _statement_rows(code, accounts)
        if not rows:
            continue
        widths = [_label_width(rows), 18]
        if any(len(row) > 2 for row in rows):
            widths.append(52)
        sheets.append((name, rows, {"widths": widths, "freeze": 2}))
    working = _working_rows(accounts, requested)
    if working:
        sheets.append(("Working", working, {"widths": WORKING_WIDTHS, "freeze": 2}))
    notes = _notes_rows(accounts)
    if notes:
        sheets.append(("Notes", notes, {"widths": (110,), "freeze": 1}))
    return sheets


def to_xlsx(bundle):
    """The workbook as .xlsx bytes: identity, the statements, the working papers, the notes.

    Every cell is copied from the stored bundle; nothing is recomputed.  A statement's amounts
    are written as numbers, in the record's decimal places.
    """
    identity = [
        [("Case id", True), str(bundle.get("id") or "not recorded")],
        [("Title", True), str(bundle.get("title") or "not recorded")],
        [("Method", True), str(bundle.get("method") or "not recorded")],
        [("Tier", True), str(bundle.get("tier") or "not recorded")],
        [("Created at", True), str(bundle.get("created_at") or "not recorded")],
    ]
    sheets = [("Case", identity, {})]
    delivery = bundle.get("delivery") if isinstance(bundle, dict) else None
    appendix = delivery.get("appendix") if isinstance(delivery, dict) else None
    accounts = appendix.get("accounts") if isinstance(appendix, dict) else None
    if isinstance(accounts, dict):
        sheets.extend(_accounting_rows(accounts, bundle))
    artifacts = [[(label, True) for label in CSV_HEADER]] + [
        ["" if row.get(key) is None else str(row.get(key)) for key in ROW_KEYS]
        for row in artifact_rows(bundle)]
    schedule = _schedule_xlsx_rows(bundle)
    if schedule:
        sheets.append(("Schedule", schedule, {}))
    sheets.append(("Recorded values", artifacts, {}))
    report = delivery.get("report") if isinstance(delivery, dict) and isinstance(delivery.get("report"), str) else ""
    if report.strip():
        sheets.append(("Report", [[line] for line in report.splitlines()], {}))

    used = set()
    named = [(_sheet_name(name, used), rows, options) for name, rows, options in sheets]
    overrides = "".join(
        '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % i
        for i in range(1, len(named) + 1))
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                + "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name, {'"': "&quot;"}), i, i)
                          for i, (name, _rows, _options) in enumerate(named, start=1))
                + "</sheets></workbook>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i)
                      for i in range(1, len(named) + 1))
            + '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (len(named) + 1)
            + "</Relationships>")
    places = ((accounts or {}).get("engagement") or {}).get("places", 2)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        parts = [("[Content_Types].xml", _XLSX_CONTENT_TYPES % overrides),
                 ("_rels/.rels", _XLSX_ROOT_RELS),
                 ("xl/workbook.xml", workbook),
                 ("xl/_rels/workbook.xml.rels", rels),
                 ("xl/styles.xml", _styles_xml(places))]
        parts.extend(("xl/worksheets/sheet%d.xml" % i,
                      _xlsx_sheet(rows, options.get("widths"), options.get("freeze")))
                     for i, (_name, rows, options) in enumerate(named, start=1))
        for name, text in parts:
            # a fixed timestamp keeps two exports of the same content byte-identical
            archive.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), text)
    return buffer.getvalue()


def export_xlsx(bundle, path):
    """Write the .xlsx workbook and return its path, SHA-256 and size."""
    data = to_xlsx(bundle)
    target = Path(path)
    if str(target.parent) not in ("", "."):
        target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(target.parent or "."), prefix=".tmp-xlsx-", suffix=".xlsx")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return {"path": str(target), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
