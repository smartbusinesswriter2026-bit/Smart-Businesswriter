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

#: The amount styles a working paper adds.  Ids 0-16 are the styles that were always there, so a
#: statements workbook's bytes never move; the working paper's own ids come after them.
#:
#: One style per declared precision, plain and as a percentage, because the record declares each
#: figure's own precision and a working paper shows every figure at the precision the record
#: declares - the paper's own convention (`product/session_paper.py` reads the same
#: declaration).  A workbook that showed every figure at one precision would print a count as
#: "12.00" and a p-value as "0.00", and the reader would take both for the record's figures.
ST_AMOUNT_PLAIN = 17        # ids 17..23: 0 to 6 decimal places
ST_AMOUNT_PERCENT = 24      # ids 24..30: 0 to 6 decimal places
ST_AMOUNT_SUBTOTAL_PLAIN = 31    # ids 31..37: the same, ruled as a subtotal
ST_AMOUNT_SUBTOTAL_PERCENT = 38  # ids 38..44: the same, as a percentage

#: The decimal places a working paper can show.  The core declares 0, 2, 3 and 4 today; the range
#: is the one the statements writer already allowed for `places`.
PRECISIONS = (0, 1, 2, 3, 4, 5, 6)

#: The unit the core itself renders as a percentage (`quantity.Quantity.display`): a rate is a
#: proportion, and the brief asks for a rate to read as a percentage.
PERCENT_UNITS = ("rate",)

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


def _styles_xml(places=2, working_paper=False):
    """The workbook's styles: the case sheets' four, and the statement sheets' own.

    The amount format carries the record's decimal places, a thousands separator and
    parentheses for a negative - the same convention the record's own text uses.

    A working paper adds one amount style per declared precision, plain and as a percentage,
    so that every figure is shown at the precision the record declares.  A statements workbook
    does not ask for them, and its bytes never move.
    """
    digits = places if isinstance(places, int) and 0 <= places <= 6 else 2
    plain = "#,##0" + ("." + "0" * digits if digits else "")
    amount_format = "%s;(%s)" % (plain, plain)
    num_fmts = ['<numFmt numFmtId="164" formatCode="%s"/>' % escape(amount_format)]
    extra = ""
    extra_count = 0
    if working_paper:
        plain_ids, percent_ids = [], []
        for index, precision in enumerate(PRECISIONS):
            plain_p = "#,##0" + ("." + "0" * precision if precision else "")
            num_fmts.append('<numFmt numFmtId="%d" formatCode="%s"/>'
                            % (165 + index, escape("%s;(%s)" % (plain_p, plain_p))))
            percent_p = "0" + ("." + "0" * precision if precision else "") + "%"
            num_fmts.append('<numFmt numFmtId="%d" formatCode="%s"/>'
                            % (172 + index, escape("%s;(%s)" % (percent_p, percent_p))))
            plain_ids.append(165 + index)
            percent_ids.append(172 + index)
        # the ids run plain, percentage, then the same two ruled as a subtotal
        styles = ([(num_fmt, 0) for num_fmt in plain_ids]
                  + [(num_fmt, 0) for num_fmt in percent_ids]
                  + [(num_fmt, 1) for num_fmt in plain_ids]
                  + [(num_fmt, 1) for num_fmt in percent_ids])
        extra = "".join(
            '<xf numFmtId="%d" fontId="%d" fillId="0" borderId="%d" xfId="0" applyNumberFormat="1"'
            ' applyFont="1" applyBorder="1" applyAlignment="1">'
            '<alignment horizontal="right"/></xf>' % (num_fmt, 1 if border else 0, border)
            for num_fmt, border in styles)
        extra_count = len(styles)
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<numFmts count="%d">%s</numFmts>'
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
            '<cellXfs count="%d">'
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
            '%s'
            '</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            '</styleSheet>') % (len(num_fmts), "".join(num_fmts), 17 + extra_count, extra)

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


def _dimension(rows):
    """The sheet's own dimension: the range the sheet actually uses, as `A1:D12`."""
    width = 0
    for row in rows:
        width = max(width, len(row))
    return "A1:%s%d" % (_column(max(width - 1, 0)), max(len(rows), 1))


#: The signature every PNG starts with, and EMU per pixel at 96 dpi.
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_EMU_PER_PIXEL = 9525
#: The widest a chart may be on a sheet: six inches.
_MAX_IMAGE_EMU = 5486400


def _png_size(data):
    """(width, height) in pixels from a PNG's IHDR, or None."""
    if not isinstance(data, (bytes, bytearray)) or len(data) < 24:
        return None
    if bytes(data[:8]) != _PNG_SIGNATURE or bytes(data[12:16]) != b"IHDR":
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return (width, height) if width and height else None


def _drawing_ext(png):
    """The picture's size in EMU, capped to the sheet's width and keeping its aspect."""
    size = _png_size(png)
    width, height = size if size else (720, 300)
    scale = min(1.0, _MAX_IMAGE_EMU / float(width * _EMU_PER_PIXEL))
    return int(width * _EMU_PER_PIXEL * scale), int(height * _EMU_PER_PIXEL * scale)


def _drawing_xml(items, media_ids):
    """One `xdr:wsDr` part: each picture anchored to a cell, sized from its own pixels."""
    anchors = []
    for index, (item, media_id) in enumerate(zip(items, media_ids), start=1):
        cx, cy = _drawing_ext(item["png"])
        row = max(0, int(item.get("row") or 0))
        column = max(0, int(item.get("col") or 0))
        anchors.append(
            '<xdr:oneCellAnchor>'
            '<xdr:from><xdr:col>%d</xdr:col><xdr:colOff>0</xdr:colOff>'
            '<xdr:row>%d</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>'
            '<xdr:ext cx="%d" cy="%d"/>'
            '<xdr:pic><xdr:nvPicPr><xdr:cNvPr id="%d" name="Figure %d"/>'
            '<xdr:cNvPicPr><a:picLocks noChangeAspect="1"/></xdr:cNvPicPr></xdr:nvPicPr>'
            '<xdr:blipFill><a:blip r:embed="rId%d"/>'
            '<a:stretch><a:fillRect/></a:stretch></xdr:blipFill>'
            '<xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr></xdr:pic>'
            '<xdr:clientData/></xdr:oneCellAnchor>'
            % (column, row, cx, cy, index, index, index, cx, cy))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            + "".join(anchors) + "</xdr:wsDr>")


def _drawing_rels(media_ids):
    """The drawing's relationships: one picture per anchor."""
    parts = ['<Relationship Id="rId%d" '
             'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
             'Target="../media/image%d.png"/>' % (index, media_id)
             for index, media_id in enumerate(media_ids, start=1)]
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(parts) + "</Relationships>")


def _sheet_drawing_rels(order):
    """A worksheet's relationship to the drawing anchored on it."""
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" '
            'Target="../drawings/drawing%d.xml"/></Relationships>' % order)


def _xlsx_sheet(rows, options=None):
    """One worksheet part.

    A row is a list of cells; a cell is text, a number, or a (value, style) pair.  A number is
    written as a number, so the column can be totalled and sorted; the amount format in
    `xl/styles.xml` gives it the record's decimal places and a thousands separator.

    **The optional parts are written only when the sheet asks for them.**  The sheet's own
    properties, the dimension, the merged title row, the print setup and the footer are the
    working paper's furniture; a workbook that asks for none of them keeps the bytes it had, so
    the statements tile's workbook is untouched by the working paper's arrival.  The children are
    written in the order `CT_Worksheet` requires, because Excel rejects the file otherwise even
    though every part of it is valid XML.
    """
    options = options or {}
    widths = options.get("widths")
    freeze = options.get("freeze")
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
    if freeze or options.get("gridlines") is False:
        attributes = ' showGridLines="0"' if options.get("gridlines") is False else ""
        pane = ""
        if freeze:
            pane = ('<pane ySplit="%d" topLeftCell="A%d" activePane="bottomLeft" state="frozen"/>'
                    '<selection pane="bottomLeft" activeCell="A%d" sqref="A%d"/>'
                    % (freeze, freeze + 1, freeze + 1, freeze + 1))
        views = ('<sheetViews><sheetView%s workbookViewId="0">%s</sheetView></sheetViews>'
                 % (attributes, pane))
    columns = ""
    if widths:
        columns = ("<cols>" + "".join(
            '<col min="%d" max="%d" width="%s" customWidth="1"/>' % (i + 1, i + 1, width)
            for i, width in enumerate(widths)) + "</cols>")
    properties = ""
    dimension = ""
    if options.get("print"):
        properties = '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>'
    if options.get("dimension"):
        dimension = '<dimension ref="%s"/>' % _dimension(rows)
    merges = ""
    if options.get("merge"):
        merges = '<mergeCells count="1"><mergeCell ref="%s"/></mergeCells>' % options["merge"]
    printing = ""
    if options.get("print"):
        printing = ('<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6"'
                    ' header="0.3" footer="0.3"/>'
                    '<pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/>')
    footer = ""
    if options.get("footer"):
        footer = ('<headerFooter><oddFooter>&amp;L%s&amp;RPage &amp;P of &amp;N</oddFooter>'
                  '</headerFooter>' % _text(options["footer"]))
    drawing = ""
    if any(item.get("png") for item in (options.get("figures") or [])):
        # `drawing` is a child of CT_Worksheet and comes after headerFooter
        drawing = '<drawing r:id="rId1"/>'
    root = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            + (' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
               if drawing else "")
            + ">")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            + root
            + properties + dimension + views + columns
            + "<sheetData>" + "".join(body) + "</sheetData>"
            + merges + printing + footer + drawing + "</worksheet>")


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

#: The appendix key that carries each statement's typed figures.  A record without it
#: does not hold that statement's figures as values, and a renderer cannot invent them.
STATEMENT_SOURCES = {"IS": "income_groups", "RE": "equity_statement",
                     "BS": "balance_sheet_groups", "CF": "cash_flow"}


def holds_statement(accounts, code):
    """Whether the appendix carries this statement's typed figures.

    The balance sheet is carried either by its groups or by the record's flat
    projection, so both count.
    """
    source = STATEMENT_SOURCES.get(code)
    if source and accounts.get(source):
        return True
    return code == "BS" and bool(accounts.get("statements"))

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


def label_width(rows):
    """Column A is as wide as the longest label it holds, within a readable bound."""
    longest = 0
    for row in rows:
        for cell in row:
            value = cell[0] if isinstance(cell, tuple) else cell
            if isinstance(value, str):
                longest = max(longest, len(value))
    return min(60, max(24, longest + 2))


def statement_sheets(accounts, bundle=None):
    """The sheets a statements record becomes: one per requested statement, then the working, then the notes."""
    sheets = []
    requested = _requested(accounts, bundle)
    for code, name in STATEMENT_SHEETS:
        if code not in requested:
            continue
        rows = _statement_rows(code, accounts)
        if not rows:
            continue
        widths = [label_width(rows), 18]
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


# -- the working paper (the Finance tiles' workbook) --------------------------------
#
# A case bundle that is not a statements engagement becomes a working paper: a cover, a
# summary, the inputs, the working, the results, the checks, the notes and the record's own
# provenance.  One generic renderer serves every tile.  It is driven by the record's method id
# and its artifact rows, never by the tile key, so a new tile needs no branch here - only a
# section label.
#
# Every cell is a value the record holds.  The renderer never computes, sums, rounds or
# re-derives one; a section the record cannot fill is dropped rather than shown empty, and a
# field the record does not carry is named "not recorded" rather than guessed.

WORKING_PAPER_SHEETS = ("Cover", "Summary", "Inputs", "Working", "Results", "Checks", "Notes", "Record")

#: A statement-style sheet: label, amount, unit, note.
PAPER_WIDTHS = (24, 18, 10, 52)

#: The artifact table as the record holds it: metric, unit, precision, value, derivation.
RESULT_WIDTHS = (28, 10, 10, 18, 52)

#: The notes sheet: the section, and the record's own text.
NOTE_WIDTHS = (34, 96)


def _appendix_of(bundle):
    """The delivery's appendix, or an empty one."""
    delivery = bundle.get("delivery") if isinstance(bundle, dict) else None
    appendix = delivery.get("appendix") if isinstance(delivery, dict) else None
    return appendix if isinstance(appendix, dict) else {}


def _spec_of(bundle):
    """The frozen problem spec the session recorded, or an empty one."""
    session = bundle.get("session") if isinstance(bundle, dict) else None
    spec = session.get("spec") if isinstance(session, dict) else None
    return spec if isinstance(spec, dict) else {}


def _reperform_of(bundle):
    """The re-perform bundle: the inputs that were run and the outputs they produced."""
    reperform = bundle.get("reperform") if isinstance(bundle, dict) else None
    return reperform if isinstance(reperform, dict) else {}


def _verification_event(bundle):
    """The session's verification event: what the checks did, as the record holds it."""
    session = bundle.get("session") if isinstance(bundle, dict) else None
    events = session.get("events") if isinstance(session, dict) else None
    for event in events or []:
        if isinstance(event, dict) and event.get("stage") == "verification":
            return event
    return None


def _declared_inputs(bundle):
    """The inputs the case declares, in the order the record declares them.

    The frozen spec carries each input with its value and its provenance; the re-perform bundle
    carries the values that were actually run.  A spec input wins - it is the declaration - and
    an input only the re-perform bundle carries is added, because the record ran it.
    """
    run = _reperform_of(bundle).get("inputs")
    run = run if isinstance(run, dict) else {}
    declared = {}
    spec_inputs = _spec_of(bundle).get("inputs")
    if isinstance(spec_inputs, dict):
        for name, entry in spec_inputs.items():
            value = entry.get("value") if isinstance(entry, dict) else entry
            provenance = entry.get("provenance") if isinstance(entry, dict) else None
            declared[str(name)] = {"value": value if value is not None else run.get(name),
                                   "provenance": provenance or "not recorded"}
    for name, value in run.items():
        declared.setdefault(str(name), {"value": value, "provenance": "not recorded"})
    return declared


def _human(name):
    """A recorded name as a label.

    The record's own word is never replaced by another one; only its shape changes.  A name of
    several words reads as `Breakeven Units`; a single word is left as the record writes it,
    because `npv` and `irr` are the metric names the case itself uses.
    """
    text = str(name or "").replace("_", " ").strip()
    if not text or " " not in text:
        return text
    return " ".join(word[:1].upper() + word[1:] for word in text.split())


def _text_or_missing(value):
    """A recorded field as text; a field the record does not carry is named, not guessed."""
    if value is None:
        return "not recorded"
    text = str(value)
    return text if text.strip() else "not recorded"


def _figure(value, precision=None, percent=False, subtotal=False):
    """A recorded figure as a cell: the record's own value, at the record's own precision.

    The value is never re-quantised - the cell holds the figure the record holds - and the
    number format shows it at the precision the record declares, which is how the paper shows
    it too.  A figure the record does not declare a precision for keeps the workbook's own
    format.
    """
    number = _number(value)
    if number is None:
        return ("" if value is None else str(value), ST_TEXT)
    return (number, _amount_style(precision, percent, subtotal))


def _amount_style(precision, percent=False, subtotal=False):
    """The style that shows a figure at the precision the record declares."""
    if precision is None:
        return ST_AMOUNT
    try:
        index = PRECISIONS.index(int(precision))
    except (TypeError, ValueError):
        return ST_AMOUNT
    if percent:
        return (ST_AMOUNT_SUBTOTAL_PERCENT if subtotal else ST_AMOUNT_PERCENT) + index
    return (ST_AMOUNT_SUBTOTAL_PLAIN if subtotal else ST_AMOUNT_PLAIN) + index


def _is_percent(unit):
    """True for the unit the core itself renders as a percentage."""
    return str(unit or "").strip().lower() in PERCENT_UNITS


def _typing(bundle):
    """A lookup for the record's declared unit and precision: `typing(key) -> (unit, precision)`.

    The core's method contract declares the unit and the decimal places of every figure it
    emits, and the paper reads that declaration - `product/session_paper.py` reads the same one
    - so that a workbook and a paper print the same figure the same way.  A template's derived
    keys are in no method's contract, so the core records those in
    `appendix["analysis"]["artifacts"]`; they are read from there.

    This is a declaration, not a computation: nothing here calculates a figure.  A key no
    source declares keeps the workbook's own format and reads "not recorded" for its unit,
    because a gap is named and never filled.
    """
    hook = None
    method_id = _method_of(bundle).get("id")
    if method_id:
        try:
            from ..methods import LIBRARY
            hook = getattr(LIBRARY.get(method_id), "typing", None)
        except Exception:                                   # noqa: BLE001
            hook = None
    recorded = {}
    analysis = _appendix_of(bundle).get("analysis")
    for entry in (analysis.get("artifacts") or []) if isinstance(analysis, dict) else []:
        if not isinstance(entry, dict) or entry.get("precision") is None:
            continue
        try:
            pair = (entry.get("unit"), int(entry["precision"]))
        except (TypeError, ValueError):
            continue
        for key in (entry.get("id"), entry.get("metric")):
            if key:
                recorded.setdefault(str(key), pair)

    def declared(*keys):
        """The unit and precision the record declares for a figure, by any of its keys."""
        for key in keys:
            if not key:
                continue
            name = str(key)
            if hook is not None:
                try:
                    unit, precision = hook(name)
                except Exception:                           # noqa: BLE001
                    unit, precision = None, None
                if precision is not None:
                    return (unit, precision)
            if name in recorded:
                return recorded[name]
        return (None, None)

    return declared


def _method_of(bundle):
    """The record's method, as the appendix holds it, or as the bundle names it."""
    method = _appendix_of(bundle).get("method")
    if isinstance(method, dict) and method.get("id"):
        return method
    return {"id": bundle.get("method") if isinstance(bundle, dict) else None}


def _period(bundle):
    """The period the record's artifacts carry, if they carry one."""
    for artifact in _appendix_of(bundle).get("artifacts") or []:
        labels = artifact[1] if isinstance(artifact, (list, tuple)) and len(artifact) > 1 else None
        if isinstance(labels, (list, tuple)) and len(labels) > 1 and labels[1]:
            return str(labels[1])
    return ""


def _currency(bundle):
    """The currency the record carries, if it carries one."""
    engagement = _appendix_of(bundle).get("engagement")
    if isinstance(engagement, dict) and engagement.get("currency"):
        return str(engagement["currency"])
    return ""


def _subtitle(bundle):
    """The sheet's subtitle: the record's method, its tier and its case id."""
    method = _method_of(bundle).get("id")
    tier = bundle.get("tier") if isinstance(bundle, dict) else None
    case_id = bundle.get("id") if isinstance(bundle, dict) else None
    parts = [str(part) for part in (method, tier, case_id) if part]
    return " — ".join(parts)


def _period_note(bundle):
    """The period and currency the record carries, in one line."""
    parts = []
    period = _period(bundle)
    if period:
        parts.append("Period: %s" % period)
    currency = _currency(bundle)
    if currency:
        parts.append("Currency: %s" % currency)
    return " · ".join(parts)


def _paper_header(title, subtitle, note, header):
    """The opening of a working-paper sheet: title, subtitle, period line, spacer, header band."""
    return [[(title, ST_TITLE)],
            [(subtitle, ST_SUBTITLE)],
            [(note, ST_NOTE)] if note else [],
            [],
            [(label, ST_TABLE_HEAD) for label in header]]


def _paper_options(bundle, widths):
    """The furniture every working-paper sheet carries.

    The title row is the only merged row and the merge never reaches past the used width; the
    header band repeats on every printed page; the gridlines stay off; the footer carries the
    case id and the page number.
    """
    case_id = str(bundle.get("id") or "") if isinstance(bundle, dict) else ""
    options = {"widths": widths, "freeze": 5, "gridlines": False, "print": True,
               "dimension": True, "repeat": 5,
               "merge": "A1:%s1" % _column(len(widths) - 1)}
    if case_id:
        options["footer"] = case_id
    return options


def _band(label, width):
    """A section band across the sheet's width."""
    return [(label, ST_GROUP)] + [("", ST_GROUP) for _ in range(width - 1)]


def _cover_sheet(bundle, contents):
    """The cover: the case's own identity, and the sheets that follow it."""
    rows = _paper_header(_text_or_missing(bundle.get("title")), _subtitle(bundle),
                         _period_note(bundle), ("Field", "Value"))
    method = _method_of(bundle)
    rows.append([("Method", ST_DETAIL),
                 (_text_or_missing(method.get("id")), ST_TEXT)])
    if method.get("version"):
        rows.append([("Method version", ST_DETAIL), (str(method["version"]), ST_TEXT)])
    if method.get("category"):
        rows.append([("Method category", ST_DETAIL), (str(method["category"]), ST_TEXT)])
    if method.get("review_status"):
        rows.append([("Review status", ST_DETAIL), (str(method["review_status"]), ST_TEXT)])
    rows.append([("Tier", ST_DETAIL), (_text_or_missing(bundle.get("tier")), ST_TEXT)])
    rows.append([("Case id", ST_DETAIL), (_text_or_missing(bundle.get("id")), ST_TEXT)])
    period = _period(bundle)
    if period:
        rows.append([("Period", ST_DETAIL), (period, ST_TEXT)])
    currency = _currency(bundle)
    if currency:
        rows.append([("Currency", ST_DETAIL), (currency, ST_TEXT)])
    rows.append([("Prepared", ST_DETAIL), (_text_or_missing(bundle.get("created_at")), ST_TEXT)])
    if contents:
        rows.append([])
        rows.append(_band("Contents", 2))
        for name in contents:
            rows.append([(name, ST_DETAIL), ("", ST_TEXT)])
    return ("Cover", rows, _paper_options(bundle, (34, 96)))


def _check_rows(bundle):
    """The record's checks, with the outcome the record holds for each."""
    names = _appendix_of(bundle).get("tests")
    if not isinstance(names, list):
        return []
    event = _verification_event(bundle)
    outcome = event.get("status") if isinstance(event, dict) else None
    failed = event.get("failed") if isinstance(event, dict) else None
    failed = failed if isinstance(failed, list) else []
    rows = []
    for name in names:
        text = str(name)
        if outcome is None:
            result = "not recorded"
        elif text in failed:
            result = "FAIL"
        else:
            result = "PASS"
        detail = event.get("detail") if isinstance(event, dict) else None
        rows.append({"check": text, "result": result, "detail": str(detail) if detail else ""})
    return rows


def _checks_summary(checks):
    """The checks summary, in the record's own counts: `n passed / n total`."""
    outcomes = [check["result"] for check in checks if check["result"] in ("PASS", "FAIL")]
    if not outcomes:
        return "not recorded"
    failed = outcomes.count("FAIL")
    return "%d passed / %d total" % (len(outcomes) - failed, len(checks))


def _summary_sheet(bundle):
    """The summary: the record's result, and the record's checks."""
    results = artifact_rows(bundle)
    checks = _check_rows(bundle)
    if not results and not checks:
        return None
    typing = _typing(bundle)
    rows = _paper_header("Summary", _subtitle(bundle), _period_note(bundle),
                         ("Item", "Value", "Unit", "Note"))
    if results:
        rows.append(_band("Result", 4))
        for row in results:
            unit, precision = typing(row.get("metric"), row.get("id"))
            amount, style = _figure(row.get("value"), precision, _is_percent(unit))
            rows.append([(_human(row.get("metric") or row.get("id")), ST_DETAIL),
                         (amount, style),
                         (_text_or_missing(unit or row.get("unit")), ST_TEXT),
                         (str(row.get("derivation") or ""), ST_TEXT)])
    if checks:
        rows.append(_band("Checks", 4))
        rows.append([("Checks recorded", ST_DETAIL),
                     (_checks_summary(checks), ST_TEXT), ("checks", ST_TEXT), ("", ST_TEXT)])
        rows.append([("Checks not applicable", ST_DETAIL),
                     ("not recorded", ST_TEXT), ("checks", ST_TEXT), ("", ST_TEXT)])
    return ("Summary", rows, _paper_options(bundle, PAPER_WIDTHS))


def _inputs_sheet(bundle):
    """The inputs the case declares: each one's value, its unit and its provenance."""
    declared = _declared_inputs(bundle)
    if not declared:
        return None
    typing = _typing(bundle)
    rows = _paper_header("Inputs", _subtitle(bundle), _period_note(bundle),
                         ("Input", "Value", "Unit", "Provenance"))
    for name, entry in declared.items():
        value = entry["value"]
        provenance = _text_or_missing(entry.get("provenance"))
        unit, precision = typing(name)
        if isinstance(value, (list, tuple)):
            rows.append(_band(_human(name), 4))
            for index, item in enumerate(value, start=1):
                amount, style = _figure(item, precision, _is_percent(unit))
                rows.append([("Item %d" % index, ST_DETAIL), (amount, style),
                             (_text_or_missing(unit), ST_TEXT), (provenance, ST_TEXT)])
        else:
            amount, style = _figure(value, precision, _is_percent(unit))
            rows.append([(_human(name), ST_DETAIL), (amount, style),
                         (_text_or_missing(unit), ST_TEXT), (provenance, ST_TEXT)])
    return ("Inputs", rows, _paper_options(bundle, PAPER_WIDTHS))


def _working_sheet(bundle):
    """The working: one block per step the record holds - label, formula, substitution, result.

    The record does not say which declared input feeds which step, so the declared inputs are
    shown under each step rather than guessed at; the derivation is the record's own.
    """
    results = artifact_rows(bundle)
    if not results:
        return None
    declared = _declared_inputs(bundle)
    typing = _typing(bundle)
    rows = _paper_header("Working", _subtitle(bundle), _period_note(bundle),
                         ("Step", "Result", "Unit", "Formula"))
    for row in results:
        metric = row.get("metric") or row.get("id")
        unit, precision = typing(metric, row.get("id"))
        rows.append(_band(_human(metric), 4))
        derivation = row.get("derivation")
        rows.append([("Formula", ST_DETAIL), ("", ST_TEXT), ("", ST_TEXT),
                     (str(derivation) if derivation else "not recorded", ST_TEXT)])
        for name, entry in declared.items():
            value = entry["value"]
            in_unit, in_precision = typing(name)
            if isinstance(value, (list, tuple)):
                for index, item in enumerate(value, start=1):
                    amount, style = _figure(item, in_precision, _is_percent(in_unit))
                    rows.append([("%s - item %d" % (_human(name), index), ST_DETAIL),
                                 (amount, style), (_text_or_missing(in_unit), ST_TEXT),
                                 ("", ST_TEXT)])
            else:
                amount, style = _figure(value, in_precision, _is_percent(in_unit))
                rows.append([(_human(name), ST_DETAIL), (amount, style),
                             (_text_or_missing(in_unit), ST_TEXT), ("", ST_TEXT)])
        amount, style = _figure(row.get("value"), precision, _is_percent(unit), subtotal=True)
        rows.append([("Result", ST_SUBTOTAL), (amount, style),
                     (_text_or_missing(unit), ST_TEXT), ("", ST_TEXT)])
    return ("Working", rows, _paper_options(bundle, PAPER_WIDTHS))


def _results_sheet(bundle):
    """The artifact table: the record's own rows, typed."""
    results = artifact_rows(bundle)
    if not results:
        return None
    typing = _typing(bundle)
    rows = _paper_header("Results", _subtitle(bundle), _period_note(bundle),
                         ("Metric", "Unit", "Precision", "Value", "Derivation"))
    for row in results:
        metric = row.get("metric") or row.get("id")
        unit, precision = typing(metric, row.get("id"))
        amount, style = _figure(row.get("value"), precision, _is_percent(unit))
        rows.append([(_human(metric), ST_DETAIL),
                     (_text_or_missing(unit or row.get("unit")), ST_TEXT),
                     (_text_or_missing(precision if precision is not None
                                       else row.get("precision")), ST_TEXT),
                     (amount, style),
                     (str(row.get("derivation") or ""), ST_TEXT)])
    return ("Results", rows, _paper_options(bundle, RESULT_WIDTHS))


def _checks_sheet(bundle):
    """The checks the record ran, and the outcome it holds for each."""
    checks = _check_rows(bundle)
    if not checks:
        return None
    rows = _paper_header("Checks", _subtitle(bundle), _period_note(bundle),
                         ("Check", "Result", "Detail"))
    for check in checks:
        style = ST_PASS if check["result"] == "PASS" else (
            ST_FAIL if check["result"] == "FAIL" else ST_TEXT)
        rows.append([(check["check"], ST_DETAIL), (check["result"], style),
                     (check["detail"], ST_TEXT)])
    return ("Checks", rows, _paper_options(bundle, (44, 12, 64)))


def _gaps(bundle):
    """The gaps the record leaves open, named rather than filled."""
    gaps = []
    if not _currency(bundle):
        gaps.append("The record carries no currency for this case.")
    results = artifact_rows(bundle)
    if results and not _declared_inputs(bundle):
        gaps.append("The record carries no declared input for the recorded result.")
    for row in results:
        if not row.get("derivation"):
            gaps.append("The record carries no derivation for %s."
                        % _human(row.get("metric") or row.get("id")))
    return gaps


def _notes_sheet(bundle):
    """The record's own notes: the delivered report, its assumptions, its limits, its gaps."""
    appendix = _appendix_of(bundle)
    delivery = bundle.get("delivery") if isinstance(bundle, dict) else None
    report = delivery.get("report") if isinstance(delivery, dict) else None
    sections = []
    if isinstance(report, str) and report.strip():
        sections.append(("Delivered report", [line for line in report.splitlines() if line.strip()]))
    assumptions = appendix.get("assumptions")
    if isinstance(assumptions, list) and assumptions:
        sections.append(("Assumptions", [str(item) for item in assumptions]))
    limitations = appendix.get("limitations")
    if isinstance(limitations, list) and limitations:
        sections.append(("Limitations", [str(item) for item in limitations]))
    ambiguities = appendix.get("ambiguities")
    if isinstance(ambiguities, list) and ambiguities:
        lines = []
        for entry in ambiguities:
            if isinstance(entry, dict):
                for key in ("question", "default_chosen", "impact"):
                    if entry.get(key):
                        lines.append("%s: %s" % (key, entry[key]))
            else:
                lines.append(str(entry))
        if lines:
            sections.append(("Ambiguities", lines))
    honesty = appendix.get("honesty")
    if isinstance(honesty, dict) and honesty:
        sections.append(("What was not done",
                         ["%s: %s" % (key, value) for key, value in honesty.items()]))
    gaps = _gaps(bundle)
    if gaps:
        sections.append(("Gaps", gaps))
    if not sections:
        return None
    rows = _paper_header("Notes", _subtitle(bundle), _period_note(bundle), ("Note", "Text"))
    for name, lines in sections:
        rows.append(_band(name, 2))
        for line in lines:
            rows.append([("", ST_DETAIL), (line, ST_TEXT)])
    return ("Notes", rows, _paper_options(bundle, NOTE_WIDTHS))


def _record_sheet(bundle):
    """The record's own provenance: what it is, when it was made, and what it is called.

    The record's hashes are not printed.  B-199 is the owner's rule: a hash is the system's own
    marker, never a student's cell.  They stay where they belong - the stored bundle, the
    appendix, the replay record - and the exporter returns the SHA-256 of the file beside the
    download, which is a fact about the file and not a cell in it.
    """
    method = _method_of(bundle)
    rows = _paper_header("Record", _subtitle(bundle), _period_note(bundle), ("Field", "Value"))
    rows.append([("Case id", ST_DETAIL), (_text_or_missing(bundle.get("id")), ST_TEXT)])
    value = _text_or_missing(method.get("id"))
    if method.get("version"):
        value = "%s (version %s)" % (value, method["version"])
    rows.append([("Method", ST_DETAIL), (value, ST_TEXT)])
    rows.append([("Tier", ST_DETAIL), (_text_or_missing(bundle.get("tier")), ST_TEXT)])
    rows.append([("Created at", ST_DETAIL), (_text_or_missing(bundle.get("created_at")), ST_TEXT)])
    return ("Record", rows, _paper_options(bundle, (34, 96)))


def working_paper_sheets(bundle):
    """The sheets a case bundle becomes when it is not a statements engagement.

    The order is the working paper's: cover, summary, inputs, working, results, checks, notes,
    record.  A section the record cannot fill is dropped rather than shown empty, so a case with
    no declared inputs has no Inputs sheet and a case with no checks has no Checks sheet.
    """
    builders = (_summary_sheet, _inputs_sheet, _working_sheet, _results_sheet,
                _checks_sheet, _notes_sheet, _record_sheet)
    sheets = []
    for builder in builders:
        sheet = builder(bundle)
        if sheet is not None:
            sheets.append(sheet)
    schedule = _schedule_xlsx_rows(bundle)
    if schedule:
        sheets.append(("Schedule", schedule, {}))
    contents = [name for name, _rows, _options in sheets]
    sheets.insert(0, _cover_sheet(bundle, contents))
    return sheets


def _case_sheets(bundle, accounts):
    """The sheets a statements case becomes: its identity, the statements, the working papers."""
    identity = [
        [("Case id", True), str(bundle.get("id") or "not recorded")],
        [("Title", True), str(bundle.get("title") or "not recorded")],
        [("Method", True), str(bundle.get("method") or "not recorded")],
        [("Tier", True), str(bundle.get("tier") or "not recorded")],
        [("Created at", True), str(bundle.get("created_at") or "not recorded")],
    ]
    sheets = [("Case", identity, {})]
    sheets.extend(statement_sheets(accounts, bundle))
    artifacts = [[(label, True) for label in CSV_HEADER]] + [
        ["" if row.get(key) is None else str(row.get(key)) for key in ROW_KEYS]
        for row in artifact_rows(bundle)]
    schedule = _schedule_xlsx_rows(bundle)
    if schedule:
        sheets.append(("Schedule", schedule, {}))
    sheets.append(("Recorded values", artifacts, {}))
    delivery = bundle.get("delivery") if isinstance(bundle, dict) else None
    report = delivery.get("report") if isinstance(delivery, dict) and isinstance(delivery.get("report"), str) else ""
    if report.strip():
        sheets.append(("Report", [[line] for line in report.splitlines()], {}))
    return sheets


def _statements_engagement(bundle):
    """The record's accounts block, when the record is a statements engagement.

    Not every record's appendix carries an account mapping: several methods publish their own
    analysis parameters under `accounts` - a power analysis publishes its design and its
    effect, a missing-data bound publishes its convention.  Those records are not statements
    engagements, and a workbook built as if they were would carry empty statement sheets and
    no results at all.  A statements engagement is the one that carries the statements
    themselves, which is the product's own rule for this (`product/explain.py` reads the same
    key).
    """
    accounts = _appendix_of(bundle).get("accounts")
    if not isinstance(accounts, dict):
        return None
    return accounts if accounts.get("statements") else None


def _with_figures(sheets, figures):
    """Attach each rendered figure to the sheet it names, below that sheet's data.

    A figure with no PNG is skipped: the workbook never carries a picture it
    cannot show.  A figure that names no sheet, or names one this workbook does
    not carry, is placed on the last sheet rather than dropped.
    """
    out = [(name, rows, dict(options or {})) for name, rows, options in sheets]
    if not out:
        return out
    by_name = {str(entry[0]).strip().lower(): entry for entry in out}
    for figure in figures or []:
        picture = (figure.get("asset") or {}).get("png")
        if not picture:
            continue
        entry = by_name.get(str(figure.get("place") or "").strip().lower()) or out[-1]
        entry[2].setdefault("figures", []).append(
            {"png": picture, "row": len(entry[1]) + 2})
    return out


def to_xlsx(bundle, figures=None):
    """The workbook as .xlsx bytes.

    A statements engagement keeps the workbook it has always had - the case sheet, the
    statements, the working papers and the notes.  Any other case becomes a working paper: a
    cover, a summary, the inputs, the working, the results, the checks, the notes and the
    record's own provenance.

    Every cell is copied from the stored bundle; nothing is recomputed.  A statement's amounts
    are written as numbers, in the record's decimal places.

    `figures` is a list of rendered figure records; each one is anchored below the data of
    the sheet it names.  A figure with no PNG is skipped, so a workbook never carries a
    picture it cannot show.
    """
    accounts = _statements_engagement(bundle)
    if accounts is not None:
        sheets = _case_sheets(bundle, accounts)
        places = (accounts.get("engagement") or {}).get("places", 2)
    else:
        sheets = working_paper_sheets(bundle)
        places = 2
    used = set()
    named = [(_sheet_name(name, used), rows, options) for name, rows, options in sheets]
    if figures:
        named = _with_figures(named, figures)
    return write_xlsx(named, places, working_paper=accounts is None)


def write_xlsx(sheets, places=2, working_paper=False):
    """The workbook as .xlsx bytes, from the sheets it is to carry.

    `sheets` is a list of `(name, rows, options)`: the name, the rows of the sheet
    (a cell is a value, or a `(value, style)` pair) and the sheet's own options
    (`widths`, `freeze`).

    `working_paper` asks for the styles a working paper needs: one amount style per declared
    precision, so that every figure is shown at the precision the record declares.  A
    statements workbook does not ask for them, and its bytes never move.

    **The OOXML facts live here.**  One writer, so there is one package structure to
    get right: a part declared once, a relationship that resolves, a sheet name that
    is unique, the children of a worksheet in the order `CT_Worksheet` requires, and
    a fixed timestamp so two exports of the same content are byte-identical.  Excel
    enforces all of that and refuses the workbook otherwise, even though every part
    of it is valid XML; `to_xlsx` (a case bundle) and `bp.product.xlsx` (the
    statements tile) are the two callers.
    """
    drawings = []
    for index, (_name, _rows, options) in enumerate(sheets, start=1):
        items = [item for item in ((options or {}).get("figures") or []) if item.get("png")]
        if items:
            drawings.append((index, items))
    overrides = "".join(
        '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % i
        for i in range(1, len(sheets) + 1))
    if drawings:
        overrides = ('<Default Extension="png" ContentType="image/png"/>' + overrides
                     + "".join(
                         '<Override PartName="/xl/drawings/drawing%d.xml" '
                         'ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>' % order
                         for order, _entry in enumerate(drawings, start=1)))
    # the header band repeats on every printed page; the name is workbook-level, so it names the
    # sheet by its position.  A workbook that asks for no repeat carries no defined name.
    defined = "".join(
        '<definedName name="_xlnm.Print_Titles" localSheetId="%d">\'%s\'!$%d:$%d</definedName>'
        % (index, str(name).replace("'", "''"), repeat, repeat)
        for index, (name, _rows, options) in enumerate(sheets)
        for repeat in [options.get("repeat")] if repeat)
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                + "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name, {'"': "&quot;"}), i, i)
                          for i, (name, _rows, _options) in enumerate(sheets, start=1))
                + "</sheets>"
                + ("<definedNames>%s</definedNames>" % defined if defined else "")
                + "</workbook>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i)
                      for i in range(1, len(sheets) + 1))
            + '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (len(sheets) + 1)
            + "</Relationships>")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        parts = [("[Content_Types].xml", _XLSX_CONTENT_TYPES % overrides),
                 ("_rels/.rels", _XLSX_ROOT_RELS),
                 ("xl/workbook.xml", workbook),
                 ("xl/_rels/workbook.xml.rels", rels),
                 ("xl/styles.xml", _styles_xml(places, working_paper))]
        parts.extend(("xl/worksheets/sheet%d.xml" % i,
                      _xlsx_sheet(rows, options))
                     for i, (_name, rows, options) in enumerate(sheets, start=1))
        media = 0
        for order, (sheet_index, items) in enumerate(drawings, start=1):
            media_ids = []
            for item in items:
                media += 1
                media_ids.append(media)
            parts.append(("xl/drawings/drawing%d.xml" % order,
                          _drawing_xml(items, media_ids)))
            parts.append(("xl/drawings/_rels/drawing%d.xml.rels" % order,
                          _drawing_rels(media_ids)))
            parts.append(("xl/worksheets/_rels/sheet%d.xml.rels" % sheet_index,
                          _sheet_drawing_rels(order)))
            for item, media_id in zip(items, media_ids):
                parts.append(("xl/media/image%d.png" % media_id, item["png"]))
        for name, text in parts:
            # a fixed timestamp keeps two exports of the same content byte-identical
            archive.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), text)
    return buffer.getvalue()


def export_xlsx(bundle, path, figures=None):
    """Write the .xlsx workbook and return its path, SHA-256 and size."""
    data = to_xlsx(bundle, figures)
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
