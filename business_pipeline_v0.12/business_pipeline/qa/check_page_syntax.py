"""Run the CI's own page-syntax gate on web/index.html (QA tool, mirrors scripts/ci.py)."""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
    html = stream.read()
scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
if not scripts:
    print("no inline script found")
    sys.exit(1)
directory = tempfile.mkdtemp(prefix="bp-page-")
path = os.path.join(directory, "page.js")
with open(path, "w", encoding="utf-8") as stream:
    stream.write(scripts[-1])
result = subprocess.run(["node", "--check", path], capture_output=True, text=True)
print("page syntax:", "OK" if result.returncode == 0 else "FAILED")
if result.returncode:
    print(result.stderr[:2000])
sys.exit(result.returncode)
