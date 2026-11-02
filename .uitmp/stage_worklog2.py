"""Stage our WORKLOG entry only.

The other session has an uncommitted WORKLOG entry in the working tree.  This
builds the staged blob from HEAD's file with *our* entry (already updated in
the working tree) substituted in, so the commit carries our increment and
their entry stays uncommitted for them.
"""

import io
import os
import subprocess

REPO = r"D:\SMART BUSINESSWRITER"
REL = "business_pipeline_v0.12/business_pipeline/docs/WORKLOG.md"
WORK = os.path.join(REPO, REL.replace("/", os.sep))

MINE = "## 2026-11-02 \u2014 [design] The logo loses its white card, the favicon comes back, and the mark grows"
NEXT = "## 2026-11-02 \u2014 [design] Subject-by-subject paper validation"

work = io.open(WORK, "rb").read().decode("utf-8")
start = work.index(MINE)
end = work.index(NEXT)
mine_block = work[start:end]

head = subprocess.run(["git", "show", "HEAD:" + REL], cwd=REPO,
                      capture_output=True, check=True).stdout.decode("utf-8")
hstart = head.index(MINE)
hend = head.index(NEXT)
staged = head[:hstart] + mine_block + head[hend:]

staged_path = os.path.join(REPO, ".uitmp", "worklog_staged2.md")
io.open(staged_path, "wb").write(staged.encode("utf-8"))

sha = subprocess.run(["git", "hash-object", "-w", staged_path], cwd=REPO,
                     capture_output=True, check=True).stdout.decode("ascii").strip()
result = subprocess.run(
    ["git", "update-index", "--add", "--cacheinfo", "100644," + sha + "," + REL],
    cwd=REPO, capture_output=True)
if result.returncode != 0:
    raise SystemExit(result.stderr.decode("utf-8", "replace"))

print("staged blob: %s" % sha)
print(subprocess.run(["git", "diff", "--cached", "--stat", "--", REL], cwd=REPO,
                     capture_output=True, check=True).stdout.decode("utf-8").strip())
print("left unstaged in the working tree:")
print(subprocess.run(["git", "diff", "--", REL], cwd=REPO,
                     capture_output=True, check=True).stdout.decode("utf-8").strip()[:400])
