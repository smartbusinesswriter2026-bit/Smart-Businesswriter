"""Spreadsheet exports from a stored case bundle (product layer, standard library only).

Two formats, both written from the **stored strings** so nothing is re-typed,
re-rounded or recomputed:

* CSV - the artifact table (`artifact, metric, unit, precision, value, derivation`);
* SpreadsheetML 2003 XML - a workbook with three worksheets: `Case` (identity
  and hashes), `Artifacts` (the table) and `Report` (the delivered report, one
  line per row).  Every cell is written as a string, so `50.00` stays `50.00`
  and never becomes a numeric cell that Excel might re-format.

The files open in Excel and LibreOffice; no third-party library is used.
"""

import csv
import hashlib
import io
import os
import tempfile
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
