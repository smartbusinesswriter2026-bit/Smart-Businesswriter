"""Word (.docx) export of a stored case bundle (product layer, standard library only).

A .docx is a zip of XML parts. This writes the minimum a Word-compatible reader needs:

    [Content_Types].xml
    _rels/.rels
    word/document.xml

The content is the **stored** report text, verbatim, plus the stored artifacts table - nothing is
re-typed, re-rounded or recomputed. The report is set in a monospaced face because the statements are
fixed-width columns; a proportional font would destroy their alignment and therefore their meaning.

XML escaping is done explicitly: a report containing `&` or `<` must render, not corrupt the file.
"""

import io
import os
import zipfile
from hashlib import sha256
from xml.sax.saxutils import escape

from . import export as case_export

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" \
ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" \
Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" \
Target="word/document.xml"/>
</Relationships>"""


def _simple_content_types(media):
    """The plain report's content types, plus image defaults when pictures are present."""
    extra = ""
    if media:
        exts = {os.path.splitext(name)[1].lower().lstrip(".") for name, _ in media}
        if "png" in exts:
            extra += '<Default Extension="png" ContentType="image/png"/>'
        if "jpg" in exts or "jpeg" in exts:
            extra += '<Default Extension="jpg" ContentType="image/jpeg"/>'
            extra += '<Default Extension="jpeg" ContentType="image/jpeg"/>'
    return CONTENT_TYPES.replace("</Types>", extra + "</Types>")


def _simple_document_rels(media):
    """The plain report's document relationships: one image per figure, from rId1."""
    extra = "".join(
        '<Relationship Id="rId%d" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        'Target="media/%s"/>' % (index + 1, name)
        for index, (name, _) in enumerate(media))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + extra + "</Relationships>")


def _para(text, bold=False, mono=False, size=None):
    """One paragraph. `xml:space="preserve"` keeps the fixed-width padding of the statements."""
    props = []
    if mono:
        props.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>')
    if bold:
        props.append("<w:b/>")
    if size:
        props.append('<w:sz w:val="%d"/>' % size)
    rpr = "<w:rPr>" + "".join(props) + "</w:rPr>" if props else ""
    body = escape(text or "")
    return ('<w:p><w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (rpr, body))


def document_xml(title, sections, mono=True):
    """The `word/document.xml` body: a title, then each (heading, lines) section.

    `mono` is kept for the accounting statements, whose fixed-width columns carry
    meaning.  A written report passes `mono=False` so Word uses its normal face.
    """
    parts = [_para(title, bold=True, size=32)]
    for heading, lines in sections:
        parts.append(_para(""))
        parts.append(_para(heading, bold=True, size=24))
        for line in lines:
            parts.append(_para(line, mono=mono, size=17))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>" + "".join(parts) + "</w:body></w:document>")


def render_bytes(title, sections, mono=True, figures=None):
    """The whole .docx as bytes, deterministic for the same input.

    `figures` is a list of rendered figure records; each one is appended after the
    report with its APA label and its picture (or, with no rasterizer, its stored
    values).  A workbook that asks for none keeps the bytes it had.
    """
    media = []
    body = document_xml(title, sections, mono=mono)
    if figures:
        extra = "".join(_figure_xml(figure, index, media)
                        for index, figure in enumerate(figures, 1))
        body = body.replace("<w:body>", "<w:body>" + extra, 1)
        body = body.replace(
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">', 1)
    parts = [("[Content_Types].xml", _simple_content_types(media)),
             ("_rels/.rels", RELS),
             ("word/document.xml", body)]
    if media:
        parts.append(("word/_rels/document.xml.rels", _simple_document_rels(media)))
    parts.extend(("word/media/" + name, data) for name, data in media)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in parts:
            # a fixed timestamp keeps two exports of the same content byte-identical
            z.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), text)
    return buf.getvalue()


ACADEMIC_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" \
ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" \
ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/header1.xml" \
ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
</Types>"""

ACADEMIC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" \
Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" \
Target="word/document.xml"/>
</Relationships>"""

DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" \
Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" \
Target="header1.xml"/>
<Relationship Id="rId2" \
Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" \
Target="styles.xml"/>
</Relationships>"""

HEADER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" \
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<w:p><w:pPr><w:jc w:val="right"/><w:spacing w:line="240" w:lineRule="auto" w:after="0"/></w:pPr>
<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr>
<w:fldChar w:fldCharType="begin"/></w:r>
<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr>
<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>
<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr>
<w:fldChar w:fldCharType="end"/></w:r>
</w:p></w:hdr>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
<w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:line="480" w:lineRule="auto" w:after="0"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>
<w:pPr><w:spacing w:line="480" w:lineRule="auto" w:after="0"/><w:jc w:val="left"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>
<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/>
<w:spacing w:before="240" w:after="120" w:line="480" w:lineRule="auto"/><w:jc w:val="center"/>
<w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/>
<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/>
<w:spacing w:before="180" w:after="0" w:line="480" w:lineRule="auto"/><w:outlineLvl w:val="1"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/>
<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/>
<w:spacing w:before="120" w:after="0" w:line="480" w:lineRule="auto"/><w:outlineLvl w:val="2"/></w:pPr>
<w:rPr><w:b/><w:i/><w:sz w:val="24"/></w:rPr></w:style>
</w:styles>"""


def _academic_para(text, bold=False, align=None, size=24, after=0, indent=None,
                   hanging=None, italic=False, style=None, keep_next=False, break_before=False,
                   shade=None):
    ppr = []
    if break_before:
        ppr.append("<w:pageBreakBefore/>")
    if style:
        ppr.append('<w:pStyle w:val="%s"/>' % style)
    if align:
        ppr.append('<w:jc w:val="%s"/>' % align)
    if shade:
        ppr.append('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade)
    ppr.append('<w:spacing w:line="480" w:lineRule="auto" w:after="%d"/>' % after)
    if keep_next:
        ppr.append("<w:keepNext/>")
    if hanging:
        ppr.append('<w:ind w:left="%d" w:hanging="%d"/>' % (hanging, hanging))
    elif indent:
        ppr.append('<w:ind w:firstLine="%d"/>' % indent)
    props = ('<w:pPr>' + "".join(ppr) + '</w:pPr>') if ppr else ""
    rpr = ('<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
           + ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "")
           + '<w:sz w:val="%d"/></w:rPr>' % size)
    return ('<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>'
            % (props, rpr, escape(text or "")))


def _page_break():
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


#: Word's text column is 9360 twips wide between the 1-inch margins.
FIGURE_WIDTH = 9360
#: The tint behind a figure's cell label.
LABEL_FILL = "E8EDF4"
#: The tint behind a cell that carries the shared core of a model.
HUB_FILL = "DCE6F1"


def _figure_cell(paragraphs, width, fill=None, span=None, vmerge=None):
    props = ['<w:tcW w:w="%d" w:type="dxa"/>' % width]
    if span and span > 1:
        props.append('<w:gridSpan w:val="%d"/>' % span)
    if vmerge == "restart":
        props.append('<w:vMerge w:val="restart"/>')
    elif vmerge == "continue":
        props.append('<w:vMerge/>')
    if fill:
        props.append('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % fill)
    props.append('<w:tcBorders><w:top w:val="single" w:sz="4" w:color="BFC8D6"/>'
                 '<w:left w:val="single" w:sz="4" w:color="BFC8D6"/>'
                 '<w:bottom w:val="single" w:sz="4" w:color="BFC8D6"/>'
                 '<w:right w:val="single" w:sz="4" w:color="BFC8D6"/></w:tcBorders>')
    return ("<w:tc><w:tcPr>%s</w:tcPr>%s</w:tc>" % ("".join(props), "".join(paragraphs)))


def _cell_paragraphs(cell):
    """The paragraphs of one figure cell: its label, its bullets, its gap.

    The label sits on its own tinted line, so a reader can find a cell by its
    name.  A cell with nothing in it still prints its gap, so it is never an
    empty box.
    """
    parts = []
    label = str(cell.get("label") or "")
    if label:
        parts.append(_academic_para(label, bold=True, size=19, after=30, shade=LABEL_FILL))
    for bullet in cell.get("bullets") or []:
        parts.append(_academic_para("\u2022  " + str(bullet), size=19, after=20))
    gap = cell.get("gap")
    if gap:
        parts.append(_academic_para(str(gap), italic=True, size=17, after=20))
    if not parts:
        parts.append(_academic_para("", size=19, after=20))
    return parts


def _axis_labels(labels, count, vertical=False):
    """Place a two-value axis across `count` slots.

    A horizontal axis reads low-to-high left to right; a vertical axis reads
    high at the top and low at the bottom.  When there are more cells than
    labels the ends carry the labels and the middle stays blank; when the
    counts match, every slot is labelled.
    """
    labels = [str(label) for label in (labels or [])]
    if not labels or count <= 0:
        return [""] * count
    if len(labels) == count:
        return list(reversed(labels)) if vertical else list(labels)
    out = [""] * count
    if vertical:
        out[0] = labels[-1]
        out[-1] = labels[0]
    else:
        out[0] = labels[0]
        out[-1] = labels[-1]
    return out


def _figure_grid_xml(grid):
    """One Word table for one grid of a figure, axes included."""
    rows = grid.get("rows") or []
    if not rows:
        return ""
    columns = max(len(row) for row in rows)
    fractions = list(grid.get("col_widths") or [])
    if len(fractions) != columns:
        fractions = [1.0 / columns] * columns
    axis_y = grid.get("axis_y")
    axis_x = grid.get("axis_x")
    # a vertical axis gets its own narrow column down the left-hand side, and
    # the content columns share what is left of the text width
    axis_width = 0.13 if axis_y else 0.0
    if axis_y:
        total = sum(fractions) or 1.0
        fractions = [fraction / total * (1.0 - axis_width) for fraction in fractions]
        fractions = [axis_width] + fractions
    scale = [int(FIGURE_WIDTH * float(fraction)) for fraction in fractions]
    scale[-1] += FIGURE_WIDTH - sum(scale)
    offset = 1 if axis_y else 0
    parts = ['<w:tbl><w:tblPr><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>']
    parts.extend('<w:gridCol w:w="%d"/>' % width for width in scale)
    parts.append("</w:tblGrid>")
    y_labels = _axis_labels(axis_y, len(rows), vertical=True) if axis_y else [""] * len(rows)
    for index, row in enumerate(rows):
        cells = []
        if axis_y:
            cells.append(_figure_cell(
                [_academic_para(y_labels[index], italic=True, size=17, align="right", after=20)],
                scale[0]))
        column = 0
        while column < columns:
            cell = row[column] if column < len(row) else {"label": "", "bullets": []}
            span = max(1, min(int(cell.get("span") or 1), columns - column))
            width = sum(scale[offset + column:offset + column + span])
            fill = HUB_FILL if cell.get("role") == "hub" else None
            cells.append(_figure_cell(_cell_paragraphs(cell), width, fill=fill, span=span))
            column += span
        parts.append("<w:tr>" + "".join(cells) + "</w:tr>")
    if axis_x:
        # the horizontal axis is a row of labels under the columns
        cells = []
        if axis_y:
            cells.append(_figure_cell([_academic_para("", size=17, after=20)], scale[0]))
        x_labels = _axis_labels(axis_x, columns, vertical=False)
        content = scale[offset:]
        for column, width in enumerate(content):
            cells.append(_figure_cell(
                [_academic_para(x_labels[column], italic=True, size=17, align="center", after=20)],
                width))
        parts.append("<w:tr>" + "".join(cells) + "</w:tr>")
    parts.append("</w:tbl>")
    return "".join(parts)


#: The text column is 6.5 in between the 1-inch margins; 914400 EMU per inch.
FIGURE_WIDTH_EMU = 5943600
#: The signature every PNG starts with.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_size(data):
    """(width, height) in pixels from a PNG's IHDR, or None."""
    if not isinstance(data, (bytes, bytearray)) or len(data) < 24:
        return None
    if bytes(data[:8]) != PNG_SIGNATURE or bytes(data[12:16]) != b"IHDR":
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return (width, height) if width and height else None


def _attr(text):
    return escape(str(text or ""), {'"': "&quot;"})


def _image_xml(rel_id, number, name, width, height, alt):
    """One inline picture, sized to the text column."""
    return (
        '<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="%d" cy="%d"/>'
        '<wp:docPr id="%d" name="Figure %d" descr="%s"/>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic>'
        '<pic:nvPicPr><pic:cNvPr id="%d" name="%s"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
        % (width, height, number, number, _attr(alt), number, _attr(name),
           rel_id, width, height))


def _figure_values_xml(rows):
    """The stored values of a chart, as a small table.

    This is the honest fallback when no rasterizer is installed: the reader
    still sees every stored string, and nothing is drawn that cannot be checked.
    """
    parts = ['<w:tbl><w:tblPr><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>'
             '<w:gridCol w:w="4680"/><w:gridCol w:w="4680"/></w:tblGrid>']
    for label, value in rows:
        parts.append("<w:tr>"
                     + _figure_cell([_academic_para(str(label), size=19, after=20)], 4680)
                     + _figure_cell([_academic_para(str(value), size=19, after=20)], 4680)
                     + "</w:tr>")
    parts.append("</w:tbl>")
    return "".join(parts)


def _figure_table_xml(table):
    """A business table as a Word table: the declared columns, then every row."""
    columns = [str(column) for column in table.get("columns") or []]
    rows = table.get("rows") or []
    if not columns:
        return ""
    width = int(FIGURE_WIDTH / len(columns))
    parts = ['<w:tbl><w:tblPr><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>']
    parts.extend('<w:gridCol w:w="%d"/>' % width for _ in columns)
    parts.append("</w:tblGrid>")
    parts.append("<w:tr>" + "".join(
        _figure_cell([_academic_para(column, bold=True, size=19, after=20, shade=LABEL_FILL)], width)
        for column in columns) + "</w:tr>")
    for row in rows:
        parts.append("<w:tr>" + "".join(
            _figure_cell([_academic_para(str(cell), size=19, after=20)], width)
            for cell in row) + "</w:tr>")
    parts.append("</w:tbl>")
    return "".join(parts)


def _figure_xml(figure, number, media=None, first_rel=3):
    """The Word XML for one figure: its APA label, its picture or grid, its note."""
    parts = [_academic_para("Figure %d. %s" % (number, figure.get("caption") or ""),
                            bold=False, size=22, after=60, keep_next=True)]
    asset = figure.get("asset") or {}
    picture = asset.get("png")
    if picture and media is not None:
        size = _png_size(picture)
        width = FIGURE_WIDTH_EMU
        height = int(width * size[1] / size[0]) if size else int(width * 0.42)
        name = "figure%d.png" % number
        rel_id = "rId%d" % (len(media) + first_rel)
        media.append((name, picture))
        parts.append(_image_xml(rel_id, number, name, width, height, figure.get("caption")))
    elif figure.get("rows"):
        parts.append(_figure_values_xml(figure["rows"]))
        parts.append(_academic_para("Values as recorded.", italic=True, size=17, after=60))
    if figure.get("table"):
        parts.append(_figure_table_xml(figure["table"]))
    for grid in figure.get("grids") or []:
        if grid.get("title"):
            parts.append(_academic_para(str(grid["title"]), bold=True, size=20,
                                        after=40, keep_next=True))
        parts.append(_figure_grid_xml(grid))
    if figure.get("note"):
        parts.append(_academic_para("Note. " + str(figure["note"]), italic=True,
                                    size=18, after=120))
    return "".join(parts)



def academic_document_xml(title, sections, style="apa", byline=(), media=None):
    """An APA/Harvard-style student paper: title page, double spacing, hanging references.

    `byline` is the student's own title-page lines (name, institution, course,
    instructor).  Empty lines are dropped, and nothing is invented: a paper never
    carries a placeholder such as "[your name]".

    The title page is its own section, vertically centred as APA 7 asks; the body
    is a second section, so it starts on a new page and is not centred. The
    reference list starts on its own page.
    """
    import datetime
    lines = [str(line).strip() for line in (byline or []) if str(line or "").strip()]
    title = str(title or "").strip()
    section = ('<w:headerReference w:type="default" r:id="rId1"/>'
               '<w:pgSz w:w="12240" w:h="15840"/>'
               '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
               'w:header="720" w:footer="720" w:gutter="0"/>')
    parts = [_academic_para(title, bold=True, align="center", after=0, keep_next=True)]
    if lines:
        parts.append(_academic_para("", after=0))
        parts.extend(_academic_para(line, align="center") for line in lines)
    parts.append(_academic_para(
        datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y"), align="center"))
    # end the title-page section: centred vertically, page numbered like the rest
    parts.append('<w:p><w:pPr><w:sectPr><w:vAlign w:val="center"/>' + section + '</w:sectPr>'
                 '</w:pPr></w:p>')
    # the title is repeated at the top of the first page of text (APA 7)
    parts.append(_academic_para(title, bold=True, align="center", after=240, keep_next=True))
    figure_number = 0
    for item in sections:
        if isinstance(item, dict):
            heading = item.get("heading", "")
            level = int(item.get("level", 1))
            lines = item.get("lines") or []
        else:
            heading, lines = item
            level = 1
        is_reference = heading in ("References", "Bibliography")
        if level >= 3:
            parts.append(_academic_para(heading, bold=True, italic=True, after=60,
                                        style="Heading3", keep_next=True))
        elif level == 2:
            parts.append(_academic_para(heading, bold=True, after=60,
                                        style="Heading2", keep_next=True))
        else:
            parts.append(_academic_para(heading, bold=True, align="center", after=120,
                                        style="Heading1", break_before=is_reference))
        figure = item.get("figure") if isinstance(item, dict) else None
        if figure:
            figure_number += 1
            parts.append(_figure_xml(figure, figure_number, media))
        table = item.get("table") if isinstance(item, dict) else None
        if isinstance(table, dict) and table.get("columns"):
            columns = [str(column) for column in table["columns"]]
            width = max(900, int(9360 / max(1, len(columns))))
            parts.append(_note_table(columns, table.get("rows") or [],
                                     widths=[width] * len(columns)))
            if table.get("note"):
                parts.append(_academic_para("Note. " + str(table["note"]), italic=True,
                                            size=18, after=120))
        for line in lines:
            text = line if isinstance(line, str) else str(line)
            if text.startswith("\u2022") or text.startswith("-"):
                parts.append(_academic_para(text, indent=None))
            elif is_reference:
                parts.append(_academic_para(text, indent=None, hanging=720))
            else:
                parts.append(_academic_para(text, indent=720))
    parts.append('<w:sectPr>' + section + '</w:sectPr>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            "<w:body>" + "".join(parts) + "</w:body></w:document>")


def _content_types(media):
    """The academic content types, plus a PNG default when pictures are present."""
    extra = '<Default Extension="png" ContentType="image/png"/>' if media else ""
    return ACADEMIC_CONTENT_TYPES.replace("</Types>", extra + "</Types>")


def _document_rels(media):
    """The document relationships: header, styles, then one image per figure."""
    extra = "".join(
        '<Relationship Id="rId%d" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        'Target="media/%s"/>' % (index + 3, name)
        for index, (name, _) in enumerate(media))
    return DOCUMENT_RELS.replace("</Relationships>", extra + "</Relationships>")


def render_academic(title, sections, style="apa", byline=(), bundle=None, plan=None, scale=3):
    """The whole academic .docx as bytes, deterministic for the same input.

    A figure that carries a rendered PNG is embedded as an inline picture; a
    figure with no rasterizer falls back to a table of its stored values, so the
    document is never broken by a missing optional package.

    When `bundle` is supplied, every figure the plan's recorded data earns is
    proposed, drawn and placed before the document is written.  Without a
    bundle the sections are rendered exactly as given.
    """
    if bundle is not None:
        from . import figure_plan
        sections, _ = figure_plan.build(bundle, sections, plan, scale=scale)
    media = []
    body = academic_document_xml(title, sections, style, byline=byline, media=media)
    parts = [("[Content_Types].xml", _content_types(media)),
             ("_rels/.rels", ACADEMIC_RELS),
             ("word/document.xml", body),
             ("word/styles.xml", STYLES),
             ("word/header1.xml", HEADER),
             ("word/_rels/document.xml.rels", _document_rels(media))]
    parts.extend(("word/media/" + name, data) for name, data in media)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in parts:
            # a fixed timestamp keeps two exports of the same content byte-identical
            z.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), text)
    return buf.getvalue()


# --- the teachable note -----------------------------------------------------
#
# A computation explanation is read, not marked: single spacing, 11pt Times New
# Roman, real tables for the declared figures and the recorded results.  It is a
# different document from the academic paper, so it has its own renderer.

def _note_para(text, bold=False, italic=False, size=22, align=None, indent=None,
               hanging=None, after=120, before=0):
    ppr = []
    if align:
        ppr.append('<w:jc w:val="%s"/>' % align)
    ppr.append('<w:spacing w:before="%d" w:after="%d" w:line="264" w:lineRule="auto"/>'
               % (before, after))
    if hanging:
        ppr.append('<w:ind w:left="%d" w:hanging="%d"/>' % (hanging, hanging))
    elif indent:
        ppr.append('<w:ind w:left="%d"/>' % indent)
    rpr = ('<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
           + ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "")
           + '<w:sz w:val="%d"/></w:rPr>' % size)
    return ('<w:p><w:pPr>%s</w:pPr><w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>'
            % ("".join(ppr), rpr, escape(text or "")))


def _note_cell(text, bold=False, width=2400):
    shade = '<w:shd w:val="clear" w:color="auto" w:fill="F1F4F8"/>' if bold else ""
    return ('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>'
            '<w:tcBorders><w:top w:val="single" w:sz="4" w:color="BFC8D6"/>'
            '<w:left w:val="single" w:sz="4" w:color="BFC8D6"/>'
            '<w:bottom w:val="single" w:sz="4" w:color="BFC8D6"/>'
            '<w:right w:val="single" w:sz="4" w:color="BFC8D6"/></w:tcBorders>%s'
            '</w:tcPr>%s</w:tc>' % (width, shade, _note_para(text, bold=bold, size=19, after=40)))


def _note_table(columns, rows, widths=None):
    widths = widths or [2400] * len(columns)
    parts = ['<w:tbl><w:tblPr><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>']
    parts.extend('<w:gridCol w:w="%d"/>' % width for width in widths)
    parts.append("</w:tblGrid>")
    parts.append("<w:tr>" + "".join(_note_cell(column, bold=True, width=widths[index])
                                    for index, column in enumerate(columns)) + "</w:tr>")
    for row in rows:
        parts.append("<w:tr>" + "".join(
            _note_cell(row[index] if index < len(row) else "", width=widths[index])
            for index in range(len(columns))) + "</w:tr>")
    parts.append("</w:tbl>")
    parts.append(_note_para(""))
    return "".join(parts)


def note_document_xml(title, subtitle, sections, images=None, media=None):
    if media is None:
        media = []
    images = images or []
    parts = [_note_para(title, bold=True, size=32, after=60)]
    if subtitle:
        parts.append(_note_para(subtitle, italic=True, size=20, after=200))
    for section in sections or []:
        heading = section.get("heading") or ""
        level = int(section.get("level") or 1)
        if heading:
            parts.append(_note_para(heading, bold=True, size=26 if level == 1 else 23,
                                    before=180, after=60))
        for paragraph in section.get("paragraphs") or []:
            parts.append(_note_para(paragraph))
        for bullet in section.get("bullets") or []:
            parts.append(_note_para("\u2022  " + str(bullet), indent=360, hanging=180))
        table = section.get("table")
        if isinstance(table, dict) and table.get("columns"):
            columns = table.get("columns") or []
            width = max(1200, int(9360 / max(1, len(columns))))
            parts.append(_note_table(columns, table.get("rows") or [],
                                     widths=[width] * len(columns)))
    if images:
        for index, (name, data) in enumerate(images, 1):
            size = _png_size(data) if str(name).lower().endswith(".png") else None
            img_width = FIGURE_WIDTH_EMU
            if size:
                img_height = int(img_width * size[1] / size[0])
            else:
                img_height = int(img_width * 0.42)
            rel_id = "rId%d" % (len(media) + 1)
            media.append((name, data))
            parts.append(_note_para("Evidence: " + str(name), bold=True, size=20, after=40))
            parts.append(_image_xml(rel_id, index + 1000, name, img_width, img_height, name))
    if images:
        root = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">')
    else:
        root = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">')
    return root + "<w:body>" + "".join(parts) + "</w:body></w:document>"


def render_note(title, subtitle, sections, images=None):
    """The whole explanation .docx as bytes, deterministic for the same input."""
    images = images or []
    media = []
    body = note_document_xml(title, subtitle, sections, images=images, media=media)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("[Content_Types].xml", date_time=(1980, 1, 1, 0, 0, 0)),
                   _simple_content_types(media))
        z.writestr(zipfile.ZipInfo("_rels/.rels", date_time=(1980, 1, 1, 0, 0, 0)), RELS)
        z.writestr(zipfile.ZipInfo("word/document.xml", date_time=(1980, 1, 1, 0, 0, 0)), body)
        if media:
            z.writestr(zipfile.ZipInfo("word/_rels/document.xml.rels", date_time=(1980, 1, 1, 0, 0, 0)),
                       _simple_document_rels(media))
        for name, data in media:
            z.writestr(zipfile.ZipInfo("word/media/" + name, date_time=(1980, 1, 1, 0, 0, 0)), data)
    return buf.getvalue()


def render_file(title, sections, path, figures=None):
    data = render_bytes(title, sections, figures=figures)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return {"path": path, "sha256": sha256(data).hexdigest(), "bytes": len(data)}


def to_bytes(bundle):
    """Back-compatible entry point: the stored report and artifacts, as one document."""
    title = case_export._title(bundle)
    report = case_export._report_text(bundle)
    rows = case_export.artifact_rows(bundle)
    sections = [("Report", (report or "").splitlines())]
    if rows:
        sections.append(("Artifacts as recorded",
                         ["%s  %s%s  [%s]" % (r.get("id"), "" if r.get("value") is None else r.get("value"),
                                              (" " + r["unit"]) if r.get("unit") else "",
                                              r.get("derivation") or "") for r in rows]))
    return render_bytes(title, sections)


def export_docx(bundle, path):
    """Write the .docx and return its path and SHA-256, like the other exporters."""
    data = to_bytes(bundle)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return {"path": path, "sha256": sha256(data).hexdigest(), "bytes": len(data)}
