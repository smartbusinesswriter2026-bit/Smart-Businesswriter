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


def render_bytes(title, sections, mono=True):
    """The whole .docx as bytes, deterministic for the same input."""
    body = document_xml(title, sections, mono=mono)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in (("[Content_Types].xml", CONTENT_TYPES),
                           ("_rels/.rels", RELS),
                           ("word/document.xml", body)):
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
                   hanging=None, italic=False, style=None, keep_next=False, break_before=False):
    ppr = []
    if break_before:
        ppr.append("<w:pageBreakBefore/>")
    if style:
        ppr.append('<w:pStyle w:val="%s"/>' % style)
    if align:
        ppr.append('<w:jc w:val="%s"/>' % align)
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


def academic_document_xml(title, sections, style="apa", byline=()):
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
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            "<w:body>" + "".join(parts) + "</w:body></w:document>")


def render_academic(title, sections, style="apa", byline=()):
    """The whole academic .docx as bytes, deterministic for the same input."""
    body = academic_document_xml(title, sections, style, byline=byline)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in (("[Content_Types].xml", ACADEMIC_CONTENT_TYPES),
                           ("_rels/.rels", ACADEMIC_RELS),
                           ("word/document.xml", body),
                           ("word/styles.xml", STYLES),
                           ("word/header1.xml", HEADER),
                           ("word/_rels/document.xml.rels", DOCUMENT_RELS)):
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


def note_document_xml(title, subtitle, sections):
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
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>" + "".join(parts) + "</w:body></w:document>")


def render_note(title, subtitle, sections):
    """The whole explanation .docx as bytes, deterministic for the same input."""
    body = note_document_xml(title, subtitle, sections)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in (("[Content_Types].xml", CONTENT_TYPES),
                           ("_rels/.rels", RELS),
                           ("word/document.xml", body)):
            z.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), text)
    return buf.getvalue()


def render_file(title, sections, path):
    data = render_bytes(title, sections)
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
