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
<Override PartName="/word/footer1.xml" \
ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
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
Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" \
Target="footer1.xml"/>
</Relationships>"""

FOOTER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" \
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<w:p><w:pPr><w:jc w:val="right"/></w:pPr>
<w:r><w:fldChar w:fldCharType="begin"/></w:r>
<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>
<w:r><w:fldChar w:fldCharType="end"/></w:r>
</w:p></w:ftr>"""


def _academic_para(text, bold=False, align=None, size=24, after=0, indent=None, hanging=None):
    ppr = []
    if align:
        ppr.append('<w:jc w:val="%s"/>' % align)
    ppr.append('<w:spacing w:line="480" w:lineRule="auto" w:after="%d"/>' % after)
    if hanging:
        ppr.append('<w:ind w:left="%d" w:hanging="%d"/>' % (hanging, hanging))
    elif indent:
        ppr.append('<w:ind w:firstLine="%d"/>' % indent)
    props = ('<w:pPr>' + "".join(ppr) + '</w:pPr>') if ppr else ""
    rpr = ('<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
           + ("<w:b/>" if bold else "") + '<w:sz w:val="%d"/></w:rPr>' % size)
    return ('<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>'
            % (props, rpr, escape(text or "")))


def academic_document_xml(title, sections, style="apa"):
    """An APA/Harvard-style student paper: title page, double spacing, hanging references."""
    import datetime
    parts = [
        _academic_para("", after=0),
        _academic_para(title, bold=True, align="center", after=240),
        _academic_para("Author: [your name]", align="center"),
        _academic_para("Institution: [your institution]", align="center"),
        _academic_para(datetime.datetime.now(datetime.timezone.utc).strftime("%d %B %Y"), align="center"),
        '<w:p><w:r><w:br w:type="page"/></w:r></w:p>',
    ]
    for heading, lines in sections:
        is_reference = heading in ("References", "Bibliography")
        parts.append(_academic_para(heading, bold=True, align="center", after=120))
        for line in lines:
            if line.startswith("•") or line.startswith("-"):
                parts.append(_academic_para(line, indent=None))
            elif is_reference:
                parts.append(_academic_para(line, indent=None, hanging=720))
            else:
                parts.append(_academic_para(line, indent=720))
    parts.append(
        '<w:sectPr><w:footerReference w:type="default" r:id="rId1"/>'
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
        'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            "<w:body>" + "".join(parts) + "</w:body></w:document>")


def render_academic(title, sections, style="apa"):
    """The whole academic .docx as bytes, deterministic for the same input."""
    body = academic_document_xml(title, sections, style)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in (("[Content_Types].xml", ACADEMIC_CONTENT_TYPES),
                           ("_rels/.rels", ACADEMIC_RELS),
                           ("word/document.xml", body),
                           ("word/_rels/document.xml.rels", DOCUMENT_RELS),
                           ("word/footer1.xml", FOOTER)):
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
