"""Assemble the new case-first workbench UI into web/index.html.

The logo (an inline base64 PNG) and the MARK constant are carried over from the
file that is already there, so the two large images are not re-encoded.  The
line endings of the original file (CRLF) are kept.
"""

import io
import os
import re
import sys

REPO = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
PAGE = os.path.join(REPO, "web", "index.html")
BODY = r"D:\SMART BUSINESSWRITER\.uitmp\body.html"
APP = r"D:\SMART BUSINESSWRITER\.uitmp\app.js"

EXTRA_CSS = """
/* --- case-first workbench additions ------------------------------------ */
.check{display:flex;align-items:flex-start;gap:8px;margin:8px 0 0;font-size:14px;line-height:1.45}
.check input{margin-top:2px}
.check span{color:var(--ink-2)}
tr.row-warn td{background:var(--warn-soft,rgba(196,138,32,.12))}
figure.chart{margin:14px 0;padding:12px;border:1px solid var(--border-2);border-radius:10px;background:var(--surface-2,transparent)}
figure.chart svg{max-width:100%;height:auto}
figure.chart figcaption{margin-top:8px;font-size:13px;color:var(--ink-3)}
.casegrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.badge.warn{background:var(--warn-soft,rgba(196,138,32,.18));border-color:var(--warn,#c48a20)}
"""

text = io.open(PAGE, encoding="utf-8", newline="").read()

style_end = text.index("</style>")
head = text[:style_end]
if EXTRA_CSS in head:          # the script may be run again: do not stack the CSS
    head = head.replace(EXTRA_CSS, "")

body_start = text.index("<body>")
script_start = text.index("<script>", body_start)
body_old = text[body_start:script_start]
script_old = text[script_start:]

logo_match = re.search(r'data:image/png;base64,[^"]+', body_old)
if not logo_match:
    sys.exit("the logo image was not found in the old body")
logo = logo_match.group(0)

mark_match = re.search(r'data:image/png;base64,[^"]+', script_old)
if not mark_match:
    sys.exit("the MARK constant was not found in the old script")
mark = mark_match.group(0)

body_new = io.open(BODY, encoding="utf-8", newline="").read()
app_new = io.open(APP, encoding="utf-8", newline="").read()

if body_new.count("__LOGO__") != 2:
    sys.exit("expected two logo placeholders, found %d" % body_new.count("__LOGO__"))
if app_new.count("__MARK__") != 1:
    sys.exit("expected one MARK placeholder, found %d" % app_new.count("__MARK__"))

body_new = body_new.replace("__LOGO__", logo)
app_new = app_new.replace("__MARK__", mark)

out = head + EXTRA_CSS + "</style>\n" + body_new + "<script>\n" + app_new + "\n</script>\n</body>\n</html>\n"

# the file that is there now uses CRLF; keep it that way
out = out.replace("\r\n", "\n").replace("\n", "\r\n")

io.open(PAGE, "w", encoding="utf-8", newline="").write(out)
print("written: %d bytes" % len(out.encode("utf-8")))
