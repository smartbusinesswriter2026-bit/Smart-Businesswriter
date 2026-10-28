"""Print-ready HTML for a computation explanation (product layer, stdlib only).

The same document model as the Word note.  HTML is the honest route to PDF: the
browser prints exactly what is on the page, so no PDF writer or third-party
dependency is needed.  All strings are escaped before they reach the page.
"""

import html

_STYLE = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: Georgia, 'Times New Roman', serif; color: #1b1b1b; line-height: 1.45;
       max-width: 190mm; margin: 0 auto; }
h1 { font-size: 20pt; margin: 0 0 4px; }
.sub { color: #5b6470; font-style: italic; margin: 0 0 22px; }
h2 { font-size: 13pt; margin: 24px 0 8px; border-bottom: 1px solid #d8d4c8; padding-bottom: 4px; }
h3 { font-size: 11.5pt; margin: 18px 0 6px; }
p { margin: 0 0 9px; }
ul { margin: 0 0 10px 20px; padding: 0; }
li { margin: 0 0 5px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 14px; font-size: 9.5pt; }
th, td { border: 1px solid #c9d0d8; padding: 5px 7px; text-align: left; vertical-align: top; }
th { background: #f1f4f8; font-weight: bold; }
footer { margin-top: 28px; padding-top: 8px; border-top: 1px solid #d8d4c8;
         font-size: 8pt; color: #6b6b6b; }
"""


def _e(value):
    return html.escape(str(value if value is not None else ""), quote=False)


def render(document):
    title = document.get("title") or "Computation explanation"
    parts = ['<!doctype html><html><head><meta charset="utf-8">',
             "<title>%s</title>" % _e(title),
             "<style>%s</style></head><body>" % _STYLE,
             "<h1>%s</h1>" % _e(title)]
    if document.get("subtitle"):
        parts.append('<p class="sub">%s</p>' % _e(document["subtitle"]))
    for section in document.get("sections") or []:
        heading = section.get("heading") or ""
        level = int(section.get("level") or 2)
        if heading:
            parts.append("<h%d>%s</h%d>" % (3 if level > 1 else 2, _e(heading),
                                            3 if level > 1 else 2))
        for paragraph in section.get("paragraphs") or []:
            parts.append("<p>%s</p>" % _e(paragraph))
        if section.get("bullets"):
            parts.append("<ul>" + "".join("<li>%s</li>" % _e(item)
                                          for item in section["bullets"]) + "</ul>")
        table = section.get("table")
        if isinstance(table, dict) and table.get("columns"):
            parts.append("<table><thead><tr>")
            parts.extend("<th>%s</th>" % _e(column) for column in table["columns"])
            parts.append("</tr></thead><tbody>")
            for row in table.get("rows") or []:
                parts.append("<tr>" + "".join(
                    "<td>%s</td>" % _e(row[index] if index < len(row) else "")
                    for index in range(len(table["columns"]))) + "</tr>")
            parts.append("</tbody></table>")
    parts.append("<footer>Produced from the recorded run. This companion explains the numbers; "
                 "it does not recalculate them. Print this page to PDF for a fixed copy.</footer>")
    parts.append("</body></html>")
    return "".join(parts)
