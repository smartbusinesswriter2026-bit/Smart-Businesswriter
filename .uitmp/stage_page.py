"""Stage only our changes to the two files the other session also edited.

`web/index.html` and `docs/CHANGELOG.md` carry another session's work in the
working tree.  This builds the staged blob from HEAD's file with our own
edits substituted in, so the commit carries our increment and their work stays
uncommitted in the working tree.
"""

import io
import os
import subprocess

REPO = r"D:\SMART BUSINESSWRITER"
TMP = os.path.join(REPO, ".uitmp")

PAGE_REL = "business_pipeline_v0.12/business_pipeline/web/index.html"
CHANGELOG_REL = "business_pipeline_v0.12/business_pipeline/docs/CHANGELOG.md"


def head_bytes(rel):
    return subprocess.run(["git", "show", "HEAD:" + rel], cwd=REPO,
                          capture_output=True, check=True).stdout


def stage(rel, payload):
    path = os.path.join(TMP, "staged_" + os.path.basename(rel))
    io.open(path, "wb").write(payload)
    sha = subprocess.run(["git", "hash-object", "-w", path], cwd=REPO,
                         capture_output=True, check=True).stdout.decode("ascii").strip()
    result = subprocess.run(
        ["git", "update-index", "--add", "--cacheinfo", "100644," + sha + "," + rel],
        cwd=REPO, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr.decode("utf-8", "replace"))
    print("staged %s (%s)" % (rel, sha[:10]))


# --- the page: two CSS rules, three lines -------------------------------
page = head_bytes(PAGE_REL)
swaps = [
    (b".hero img{height:94px;width:auto;margin-top:6px;",
     b".hero img{height:103px;width:auto;margin-top:6px;"),
    (b".hero h1{font-size:45px;line-height:1.08;margin:6px 0 10px;",
     b".hero h1{font-size:45px;line-height:1.08;margin:8px 0 10px;"),
    (b"  .hero img{height:67px;margin-top:4px}",
     b"  .hero img{height:74px;margin-top:4px}"),
]
for old, new in swaps:
    if page.count(old) != 1:
        raise SystemExit("expected exactly one %r in HEAD's page" % old[:40])
    page = page.replace(old, new)
stage(PAGE_REL, page)

# --- the changelog: one bullet ------------------------------------------
changelog = head_bytes(CHANGELOG_REL)
old_bullet = (b"- **The Home mark is 20% larger and sits closer to the wordmark.** `.hero img` height goes\r\n"
              b"  78px -> 94px (56px -> 67px under 900px), the mark sits 6px lower, and the gap to\r\n"
              b"  \"Smart Business Writer\" is 6px instead of 16px, so the two read as one lockup. The\r\n"
              b"  topbar mark and the chat button keep their sizes.\r\n")
new_bullet = (b"- **The Home mark is larger, and the wordmark sits in the middle of it.** `.hero img` height\r\n"
              b"  goes 78px -> 103px (56px -> 74px under 900px), and the space between the mark and\r\n"
              b"  \"Smart Business Writer\" is now the same as the space between that wordmark and \"Your\r\n"
              b"  reliable business writing assistant\" - 25px on each side, measured on the rendered\r\n"
              b"  pixels, not on the boxes. The topbar mark and the chat button keep their sizes.\r\n")
if changelog.count(old_bullet) != 1:
    raise SystemExit("expected exactly one old bullet in HEAD's changelog")
changelog = changelog.replace(old_bullet, new_bullet)
stage(CHANGELOG_REL, changelog)

print("")
print(subprocess.run(["git", "diff", "--cached", "--stat"], cwd=REPO,
                     capture_output=True, check=True).stdout.decode("utf-8").strip())
