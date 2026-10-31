"""Diff the script that is inside the served page against the current app.js."""
import difflib
import io
import os

REPO = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
PAGE = os.path.join(REPO, "web", "index.html")
APP = r"D:\SMART BUSINESSWRITER\.uitmp\app.js"

page = io.open(PAGE, encoding="utf-8", newline="").read()
start = page.index("<script>") + len("<script>")
end = page.rindex("</script>")
inline = page[start:end].replace("\r\n", "\n")
app = io.open(APP, encoding="utf-8", newline="").read().replace("\r\n", "\n")

print("inline lines: %d | app.js lines: %d" % (inline.count("\n"), app.count("\n")))
if inline.strip() == app.strip():
    print("IDENTICAL")
else:
    diff = list(difflib.unified_diff(inline.splitlines(), app.splitlines(),
                                     "served index.html", "app.js", n=2, lineterm=""))
    print("diff hunks: %d lines" % len(diff))
    for line in diff[:160]:
        print(line)
