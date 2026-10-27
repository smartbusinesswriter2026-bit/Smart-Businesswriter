"""Print-ready HTML for a deliverable (product layer, standard library only).

HTML is the honest route to PDF: the browser prints exactly what is on the page, so no PDF writer is
needed and nothing can drift between what the student sees and what the marker receives. The stylesheet is
inlined and declares an A4 page with margins, so "Print to PDF" produces a sane document without the
student touching settings.

Content is escaped, and the statements stay in a monospaced face for the same reason as in the Word
renderer: the alignment *is* part of the meaning.
"""

import html
import os
from hashlib import sha256

_STYLE = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: Georgia, 'Times New Roman', serif; color: #1b1b1b; line-height: 1.45; }
h1 { font-size: 18pt; border-bottom: 1px solid #d8d4c8; padding-bottom: 6px; }
h2 { font-size: 12pt; margin: 20px 0 6px; letter-spacing: .02em; }
pre { white-space: pre-wrap; word-wrap: break-word; font-family: Consolas, ui-monospace, monospace;
      font-size: 9.5pt; background: #f7f6f1; border: 1px solid #e2ded2; padding: 8px; margin: 0; }
footer { margin-top: 26px; font-size: 8pt; color: #6b6b6b; }
"""


def render(title, sections, footer="Produced by Smart Business Writer from a stored case bundle."):
    parts = ['<!doctype html><html><head><meta charset="utf-8">',
             "<title>%s</title>" % html.escape(title or "Case export"),
             "<style>%s</style></head><body>" % _STYLE,
             "<h1>%s</h1>" % html.escape(title or "Case export")]
    for heading, lines in sections:
        parts.append("<h2>%s</h2>" % html.escape(heading))
        parts.append("<pre>%s</pre>" % html.escape("\n".join(lines)))
    parts.append("<footer>%s</footer>" % html.escape(footer))
    parts.append("</body></html>")
    return "".join(parts)


def render_file(title, sections, path):
    text = render(title, sections)
    data = text.encode("utf-8")
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return {"path": path, "sha256": sha256(data).hexdigest(), "bytes": len(data),
            "note": "open and print to PDF for a fixed copy"}
