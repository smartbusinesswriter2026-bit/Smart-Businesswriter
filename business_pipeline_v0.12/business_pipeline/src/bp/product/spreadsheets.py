"""Spreadsheet exports from a stored case bundle (product layer, standard library only).

Three formats, all written from the **stored values** so nothing is re-typed,
re-rounded or recomputed:

* CSV - the artifact table (`artifact, metric, unit, precision, value, derivation`);
* SpreadsheetML 2003 XML - a workbook with three worksheets: `Case` (identity
  and hashes), `Artifacts` (the table) and `Report` (the delivered report, one
  line per row);
* .xlsx (Office Open XML) - the primary spreadsheet download: `Case`, the
  statements, trial balance, journal and checks when the case carries them,
  the recorded values and the report.

Every cell is written as a string, so `50.00` stays `50.00` and never becomes a
numeric cell that Excel might re-format.

The files open in Excel and LibreOffice; no third-party library is used.
"""

import csv
import hashlib
import io
import os
import tempfile
import zipfile
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
        ("Spec hash", str(bundle.get("spec_hash") or "not recorded")),
        ("Outputs hash", str(bundle.get("outputs_hash") or "not recorded")),
        ("Created at", str(bundle.get("created_at") or "not recorded")),
    ]
    artifacts = [CSV_HEADER] + [
        tuple("" if row.get(key) is None else str(row.get(key)) for key in ROW_KEYS)
        for row in artifact_rows(bundle)]
    delivery = bundle.get("delivery")
    report = delivery.get("report") if isinstance(delivery, dict) and isinstance(delivery.get("report"), str) else ""
    report_rows = [("Line", "Text")] + [("", line) for line in report.splitlines()] or [("not recorded", "")]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
            'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
            + _sheet("Case", identity) + _sheet("Artifacts", artifacts) + _sheet("Report", report_rows)
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
#: Every cell is an inline string, as in the SpreadsheetML writer: a stored
#: "6,650.00" stays that text and is never re-typed as a number Excel may re-format.

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
_XLSX_STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
                '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
                '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
                '<borders count="1"><border/></borders>'
                '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
                '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
                '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
                '</styleSheet>')

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


def _xlsx_sheet(rows):
    """One worksheet part. A row is a list of cells; a cell is text or a (text, bold) pair."""
    body = []
    for r, cells in enumerate(rows, start=1):
        out = []
        for c, cell in enumerate(cells):
            bold = isinstance(cell, tuple) and len(cell) == 2 and cell[1] is True
            value = cell[0] if isinstance(cell, tuple) else cell
            style = ' s="1"' if bold else ""
            out.append('<c r="%s%d" t="inlineStr"%s><is><t xml:space="preserve">%s</t></is></c>'
                       % (_column(c), r, style, _text(value)))
        body.append('<row r="%d">%s</row>' % (r, "".join(out)))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>" + "".join(body) + "</sheetData></worksheet>")


def _sheet_name(name, used):
    clean = "".join(ch for ch in str(name) if ch not in _SHEET_BAD)[:31] or "Sheet"
    candidate, n = clean, 2
    while candidate.lower() in used:
        suffix = " (%d)" % n
        candidate = clean[:31 - len(suffix)] + suffix
        n += 1
    used.add(candidate.lower())
    return candidate


def _accounting_rows(accounts):
    """Sheets copied from the stored accounts appendix: statements, the trial balance, the journal, the checks."""
    sheets = []
    statements = accounts.get("statements_export")
    if isinstance(statements, dict):
        rows = []
        for key in ("trial_balance", "income_statement", "balance_sheet", "cash_flow", "reconciliation", "notes"):
            part = statements.get(key)
            if isinstance(part, str) and part.strip():
                if rows:
                    rows.append([])
                rows.extend([[line] for line in part.splitlines()])
        if rows:
            sheets.append(("Statements", rows))
    trial = accounts.get("trial_balance")
    if isinstance(trial, dict) and isinstance(trial.get("rows"), list):
        rows = [[("Code", True), ("Account", True), ("Debit", True), ("Credit", True)]]
        for row in trial["rows"]:
            if isinstance(row, dict):
                rows.append([row.get("code"), row.get("name"), row.get("debit"), row.get("credit")])
            else:
                rows.append(list(row)[:4])
        rows.append([("", True), ("Total", True), trial.get("total_debits"), trial.get("total_credits")])
        sheets.append(("Trial balance", rows))
    journal = accounts.get("journal")
    if isinstance(journal, list) and journal:
        rows = [[("Date", True), ("Description", True), ("Account", True), ("Name", True),
                 ("Debit", True), ("Credit", True), ("Entry hash", True)]]
        for entry in journal:
            for line in entry.get("lines") or []:
                rows.append([entry.get("date"), entry.get("description"), line.get("account"), line.get("name"),
                             line.get("debit"), line.get("credit"), entry.get("hash")])
        sheets.append(("Journal", rows))
    checks = accounts.get("checks")
    if isinstance(checks, list) and checks:
        rows = [[("Check", True), ("Result", True), ("Detail", True)]]
        for check in checks:
            rows.append([check[0], "PASS" if len(check) > 1 and check[1] else "FAIL",
                         check[2] if len(check) > 2 else ""])
        sheets.append(("Checks", rows))
    return sheets


def to_xlsx(bundle):
    """The workbook as .xlsx bytes: identity, the recorded values, and the accounting work when present.

    Every cell is copied from the stored bundle; nothing is recomputed.
    """
    identity = [
        [("Case id", True), str(bundle.get("id") or "not recorded")],
        [("Title", True), str(bundle.get("title") or "not recorded")],
        [("Method", True), str(bundle.get("method") or "not recorded")],
        [("Tier", True), str(bundle.get("tier") or "not recorded")],
        [("Spec hash", True), str(bundle.get("spec_hash") or "not recorded")],
        [("Outputs hash", True), str(bundle.get("outputs_hash") or "not recorded")],
        [("Created at", True), str(bundle.get("created_at") or "not recorded")],
    ]
    sheets = [("Case", identity)]
    delivery = bundle.get("delivery") if isinstance(bundle, dict) else None
    appendix = delivery.get("appendix") if isinstance(delivery, dict) else None
    accounts = appendix.get("accounts") if isinstance(appendix, dict) else None
    if isinstance(accounts, dict):
        sheets.extend(_accounting_rows(accounts))
    artifacts = [[(label, True) for label in CSV_HEADER]] + [
        ["" if row.get(key) is None else str(row.get(key)) for key in ROW_KEYS]
        for row in artifact_rows(bundle)]
    sheets.append(("Recorded values", artifacts))
    report = delivery.get("report") if isinstance(delivery, dict) and isinstance(delivery.get("report"), str) else ""
    if report.strip():
        sheets.append(("Report", [[line] for line in report.splitlines()]))

    used = set()
    named = [(_sheet_name(name, used), rows) for name, rows in sheets]
    overrides = "".join(
        '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % i
        for i in range(1, len(named) + 1))
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                + "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name, {'"': "&quot;"}), i, i)
                          for i, (name, _) in enumerate(named, start=1))
                + "</sheets></workbook>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i)
                      for i in range(1, len(named) + 1))
            + '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (len(named) + 1)
            + "</Relationships>")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        parts = [("[Content_Types].xml", _XLSX_CONTENT_TYPES % overrides),
                 ("_rels/.rels", _XLSX_ROOT_RELS),
                 ("xl/workbook.xml", workbook),
                 ("xl/_rels/workbook.xml.rels", rels),
                 ("xl/styles.xml", _XLSX_STYLES)]
        parts.extend(("xl/worksheets/sheet%d.xml" % i, _xlsx_sheet(rows))
                     for i, (_, rows) in enumerate(named, start=1))
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
