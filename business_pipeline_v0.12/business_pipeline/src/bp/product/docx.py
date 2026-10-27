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


def document_xml(title, sections):
    """The `word/document.xml` body: a title, then each (heading, lines) section."""
    parts = [_para(title, bold=True, size=32)]
    for heading, lines in sections:
        parts.append(_para(""))
        parts.append(_para(heading, bold=True, size=24))
        for line in lines:
            parts.append(_para(line, mono=True, size=17))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>" + "".join(parts) + "</w:body></w:document>")


def render_bytes(title, sections):
    """The whole .docx as bytes, deterministic for the same input."""
    body = document_xml(title, sections)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in (("[Content_Types].xml", CONTENT_TYPES),
                           ("_rels/.rels", RELS),
                           ("word/document.xml", body)):
            # a fixed timestamp keeps two exports of the same content byte-identical
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
