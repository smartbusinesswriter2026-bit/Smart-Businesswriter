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


def document_xml(title, report_text, artifacts):
    """The `word/document.xml` body: a title, the stored report, then the stored artifacts."""
    parts = [_para(title, bold=True, size=32)]
    for line in (report_text or "").splitlines():
        parts.append(_para(line, mono=True, size=17))
    if artifacts:
        parts.append(_para(""))
        parts.append(_para("Artifacts as recorded", bold=True, size=24))
        for row in artifacts:
            value = row.get("value")
            unit = row.get("unit") or ""
            line = "%s  %s%s  [%s]" % (row.get("id"), "" if value is None else value,
                                       (" " + unit) if unit else "", row.get("derivation") or "")
            parts.append(_para(line, mono=True, size=17))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>" + "".join(parts) + "</w:body></w:document>")


def to_bytes(bundle):
    """The whole .docx as bytes, deterministic for the same bundle."""
    title = case_export._title(bundle)
    report = case_export._report_text(bundle)
    rows = case_export.artifact_rows(bundle)
    body = document_xml(title, report, rows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # a fixed timestamp keeps two exports of the same bundle byte-identical
        info = zipfile.ZipInfo("[Content_Types].xml", date_time=(1980, 1, 1, 0, 0, 0))
        z.writestr(info, CONTENT_TYPES)
        info = zipfile.ZipInfo("_rels/.rels", date_time=(1980, 1, 1, 0, 0, 0))
        z.writestr(info, RELS)
        info = zipfile.ZipInfo("word/document.xml", date_time=(1980, 1, 1, 0, 0, 0))
        z.writestr(info, body)
    return buf.getvalue()


def export_docx(bundle, path):
    """Write the .docx and return its path and SHA-256, like the other exporters."""
    data = to_bytes(bundle)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return {"path": path, "sha256": sha256(data).hexdigest(), "bytes": len(data)}
