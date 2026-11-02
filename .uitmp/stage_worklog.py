"""Put the new WORKLOG entry at the top of the dated entries, and build the
blob that will be staged for the commit.

Another session is mid-increment in the same tree and has an uncommitted
WORKLOG entry of its own.  This script therefore:

1. moves our entry above that one in the working tree (newest first), and
2. writes a staged blob that holds *our* entry only, so the commit carries
   our increment and the other session's entry stays uncommitted in the
   working tree for them to commit themselves.
"""

import io
import os
import subprocess

REPO = r"D:\SMART BUSINESSWRITER"
REL = "business_pipeline_v0.12/business_pipeline/docs/WORKLOG.md"
WORK = os.path.join(REPO, REL.replace("/", os.sep))

MINE = "## 2026-11-02 \u2014 [design] The logo loses its white card, the favicon comes back, and the mark grows"
THEIRS = "## 2026-11-02 \u2014 [design] The market-data panels are split by consumer"
NEXT = "## 2026-11-02 \u2014 [design] Subject-by-subject paper validation"

data = io.open(WORK, "rb").read().decode("utf-8")

start = data.index(MINE)
end = data.index(NEXT)
mine_block = data[start:end]
rest = data[:start] + data[end:]

# Put our entry first, above the other session's entry.
anchor = rest.index(THEIRS)
reordered = rest[:anchor] + mine_block + rest[anchor:]
io.open(WORK, "wb").write(reordered.encode("utf-8"))
print("working tree: our entry now sits above the other session's entry")

# The staged blob: HEAD's file plus our entry, and nothing else.
head = subprocess.run(["git", "show", "HEAD:" + REL], cwd=REPO,
                      capture_output=True, check=True).stdout.decode("utf-8")
anchor = head.index(NEXT)
staged = head[:anchor] + mine_block + head[anchor:]
staged_path = os.path.join(REPO, ".uitmp", "worklog_staged.md")
io.open(staged_path, "wb").write(staged.encode("utf-8"))

sha = subprocess.run(["git", "hash-object", "-w", staged_path], cwd=REPO,
                     capture_output=True, check=True).stdout.decode("ascii").strip()
print("staged blob: %s" % sha)

result = subprocess.run(
    ["git", "update-index", "--add", "--cacheinfo", "100644," + sha + "," + REL],
    cwd=REPO, capture_output=True)
if result.returncode != 0:
    raise SystemExit(result.stderr.decode("utf-8", "replace"))
print("index updated for %s" % REL)

check = subprocess.run(["git", "diff", "--cached", "--stat", "--", REL], cwd=REPO,
                       capture_output=True, check=True).stdout.decode("utf-8")
print(check.strip())
