"""Compare two unittest runs: which failures are pre-existing and which are new.

Usage:  python compare_suites.py <head.err> <wt.err> <out.txt>
"""
import re
import sys
from collections import Counter

LINE = re.compile(r"^(FAIL|ERROR):\s+(\S+)\s+\(([^)]+)\)")


def read_failures(path):
    """Every failing test id in a run, as 'module.Class.test'."""
    found = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = LINE.match(line.strip())
            if match:
                kind, test, where = match.groups()
                found.append("%s %s.%s" % (kind, where, test))
    return found


def summary(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    ran = re.search(r"Ran (\d+) tests in ([\d.]+)s", text)
    verdict = re.search(r"^(OK|FAILED \([^)]*\))", text, re.M)
    return (ran.group(1) if ran else "?"), (ran.group(2) if ran else "?"), \
           (verdict.group(1) if verdict else "?")


head_path, wt_path = sys.argv[1], sys.argv[2]
out_path = sys.argv[3] if len(sys.argv) > 3 else None

head = read_failures(head_path)
wt = read_failures(wt_path)
head_ids = set(head)
wt_ids = set(wt)

lines = []
head_tests, head_secs, head_verdict = summary(head_path)
wt_tests, wt_secs, wt_verdict = summary(wt_path)

lines.append("HEAD vs WORKING TREE - the full suite, measured on 2026-11-04")
lines.append("=" * 78)
lines.append("")
lines.append("How this was measured")
lines.append("-" * 78)
lines.append("  HEAD          a byte-exact copy of HEAD: `git archive HEAD` into")
lines.append("                .baseline_head/x, then every one of the 5775 tracked files")
lines.append("                hash-compared against the HEAD blob (one generated file,")
lines.append("                documents/index.json, restored byte-exactly).")
lines.append("  working tree  the tree this increment ships, run in place.")
lines.append("  command       python -m unittest discover -s tests -v")
lines.append("")
lines.append("HEAD baseline   : %s tests in %ss  -> %s" % (head_tests, head_secs, head_verdict))
lines.append("working tree    : %s tests in %ss  -> %s" % (wt_tests, wt_secs, wt_verdict))
lines.append("")
lines.append("HEAD problems      : %d" % len(head_ids))
lines.append("working-tree probs : %d" % len(wt_ids))
lines.append("")
lines.append("=" * 78)
lines.append("PRE-EXISTING (fail on HEAD and on the working tree): %d" % len(head_ids & wt_ids))
lines.append("-" * 78)
for item in sorted(head_ids & wt_ids):
    lines.append("   " + item)
lines.append("")
lines.append("=" * 78)
lines.append("NEW (fail on the working tree only): %d" % len(wt_ids - head_ids))
lines.append("-" * 78)
for item in sorted(wt_ids - head_ids):
    lines.append("   " + item)
lines.append("")
lines.append("=" * 78)
lines.append("GONE (fail on HEAD only, fixed in the working tree): %d" % len(head_ids - wt_ids))
lines.append("-" * 78)
for item in sorted(head_ids - wt_ids):
    lines.append("   " + item)
lines.append("")
lines.append("by kind:")
for label, ids in (("HEAD", head_ids), ("working tree", wt_ids)):
    kinds = Counter(item.split(" ", 1)[0] for item in ids)
    lines.append("   %-14s %s" % (label, dict(kinds)))

text = "\n".join(lines)
print(text)
if out_path:
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
