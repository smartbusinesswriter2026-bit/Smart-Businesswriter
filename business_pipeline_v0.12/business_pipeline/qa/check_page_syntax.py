"""Run the CI's own page-syntax gate on web/index.html (QA tool, mirrors scripts/ci.py).

**Every inline block is checked, not just the last one.**

The gate this mirrors used to look for `<script>` tags with no attributes and to check
only the final match.  The page's two tagged blocks - `<script id="tile-close-shim">`
and `<script id="statements-tile">` - did not match that pattern at all, so neither
was ever parsed.  A stray `}` in the statements-tile block sat in the served page and
the gate stayed green, which is how a dead tile shipped.  A gate that cannot see a
block is not a gate.

The tagged blocks are the design lane's page code, so this file is where the hole is
closed.  `scripts/ci.py` carries the same hole and belongs to the computation lane:
it is recorded as a `[design]` request in `docs/WORKLOG.md` for the owner to instruct.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
    html = stream.read()

# Every inline block, tagged or not, with its id when it carries one.
blocks = re.findall(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", html, re.S)
if not blocks:
    print("no inline script found")
    sys.exit(1)

directory = tempfile.mkdtemp(prefix="bp-page-")
failed = []
try:
    for index, (attrs, body) in enumerate(blocks, 1):
        found = re.search(r'id="([^"]*)"', attrs)
        name = found.group(1) if found else "anonymous"
        path = os.path.join(directory, "block-%d.js" % index)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(body)
        result = subprocess.run(["node", "--check", path], capture_output=True, text=True)
        if result.returncode:
            failed.append(name)
            print("page syntax [%s]: FAILED" % name)
            print(result.stderr[:2000])
        else:
            print("page syntax [%s]: OK" % name)
finally:
    shutil.rmtree(directory, ignore_errors=True)

print("page syntax: %d of %d blocks parsed" % (len(blocks) - len(failed), len(blocks)))
if failed:
    print("page syntax: FAILED in %s" % ", ".join(failed))
    sys.exit(1)
print("page syntax: OK")
