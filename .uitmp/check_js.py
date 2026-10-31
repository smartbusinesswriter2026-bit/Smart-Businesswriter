"""Extract the inline script from the workbench page and syntax-check it with node."""
import re
import subprocess
import sys
import tempfile
import os

PATH = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html"
html = open(PATH, encoding="utf-8").read()

blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
print("inline script blocks:", len(blocks), "sizes:", [len(b) for b in blocks])

ok = True
for index, body in enumerate(blocks):
    handle, path = tempfile.mkstemp(suffix=".js")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(body)
    result = subprocess.run(["node", "--check", path], capture_output=True, text=True)
    print("block %d: node --check -> %s" % (index, "OK" if result.returncode == 0 else "FAILED"))
    if result.returncode != 0:
        ok = False
        print(result.stderr[:1200])
    os.unlink(path)

# also check the html has balanced section tags for the panels
opens = re.findall(r'<section[^>]*id="panel-([a-z]+)"', html)
closes = len(re.findall(r"</section>", html))
print("panel sections:", len(opens), opens)
print("</section> count:", closes)
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
