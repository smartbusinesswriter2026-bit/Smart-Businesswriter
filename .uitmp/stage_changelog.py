"""Stage only our CHANGELOG bullet (the other session has an entry of its own).

The committed blob stores LF line endings, so the swap is written with "\\n".
"""

import io
import os
import subprocess

REPO = r"D:\SMART BUSINESSWRITER"
REL = "business_pipeline_v0.12/business_pipeline/docs/CHANGELOG.md"
TMP = os.path.join(REPO, ".uitmp")

OLD = (
    "- **The Home mark is 20% larger and sits closer to the wordmark.** `.hero img` height goes\n"
    "  78px -> 94px (56px -> 67px under 900px), the mark sits 6px lower, and the gap to\n"
    '  "Smart Business Writer" is 6px instead of 16px, so the two read as one lockup. The\n'
    "  topbar mark and the chat button keep their sizes.\n"
)
NEW = (
    "- **The Home mark is larger, and the wordmark sits in the middle of it.** `.hero img` height\n"
    "  goes 78px -> 103px (56px -> 74px under 900px), and the space between the mark and\n"
    '  "Smart Business Writer" is now the same as the space between that wordmark and "Your\n'
    '  reliable business writing assistant" - 25px on each side, measured on the rendered\n'
    "  pixels, not on the boxes. The topbar mark and the chat button keep their sizes.\n"
)

data = subprocess.run(["git", "show", "HEAD:" + REL], cwd=REPO,
                      capture_output=True, check=True).stdout
old = OLD.encode("utf-8")
if data.count(old) != 1:
    raise SystemExit("old bullet count %d" % data.count(old))
data = data.replace(old, NEW.encode("utf-8"))

path = os.path.join(TMP, "staged_changelog.md")
io.open(path, "wb").write(data)
sha = subprocess.run(["git", "hash-object", "-w", path], cwd=REPO,
                     capture_output=True, check=True).stdout.decode("ascii").strip()
result = subprocess.run(
    ["git", "update-index", "--add", "--cacheinfo", "100644," + sha + "," + REL],
    cwd=REPO, capture_output=True)
if result.returncode != 0:
    raise SystemExit(result.stderr.decode("utf-8", "replace"))
print("staged changelog blob: %s" % sha)
print(subprocess.run(["git", "diff", "--cached", "--stat"], cwd=REPO,
                     capture_output=True, check=True).stdout.decode("utf-8").strip())
