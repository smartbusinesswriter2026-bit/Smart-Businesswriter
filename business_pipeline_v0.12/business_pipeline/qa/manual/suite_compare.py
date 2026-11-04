"""Separate the pre-existing suite failures from the new ones.

    python qa/manual/suite_compare.py [out-file]

Reads the three runs taken by `qa/manual/suite_measure.ps1`:

    qa/baseline/seam-pre-suite-err.txt   the pre-increment baseline (commit d938095)
    qa/baseline/seam-head-suite-err.txt  the current HEAD            (commit f1bb0c5)
    qa/baseline/seam-wt-suite-err.txt    the working tree (snapshot)

and writes the separation twice: once against the pre-increment baseline
(what the increment changed) and once against the current HEAD (what the last
commit changed).

The test id is the parenthesised full id unittest prints, e.g.

    FAIL: test_a_write_off (test_bad_debt.WriteOff.test_a_write_off)

which names the module, the class and the method - that is the id.
"""

import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
BASELINE = os.path.join(PROJECT, "qa", "baseline")

RUNS = (
    ("pre", "seam-pre-suite-err.txt", "the pre-increment baseline", "d938095 (build 1.98)"),
    ("head", "seam-head-suite-err.txt", "the current HEAD", "f1bb0c5"),
    ("wt", "seam-wt-suite-err.txt", "the working tree", "a snapshot of it"),
)

LINE = re.compile(r"^(FAIL|ERROR):\s+\S+\s+\(([^)]+)\)")
SUMMARY = re.compile(r"^Ran (\d+) tests in ([\d.]+)s", re.M)
VERDICT = re.compile(r"^(OK|FAILED \([^)]*\))", re.M)


def read_run(path):
    """The failing test ids of one run, and its summary line."""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    ids = set()
    for line in text.splitlines():
        match = LINE.match(line.strip())
        if match:
            ids.add("%s %s" % (match.group(1), match.group(2)))
    ran = SUMMARY.search(text)
    verdict = VERDICT.search(text)
    return {
        "ids": ids,
        "tests": ran.group(1) if ran else "?",
        "secs": ran.group(2) if ran else "?",
        "verdict": verdict.group(1) if verdict else "?",
    }


def kinds(ids):
    return dict(Counter(item.split(" ", 1)[0] for item in ids))


def section(title, left, right, left_label, right_label):
    lines = ["=" * 78, title, "-" * 78]
    lines.append("   %s: %d" % (left_label, len(left)))
    lines.append("   %s: %d" % (right_label, len(right)))
    lines.append("")
    for name, items in (
        ("PRE-EXISTING (fail on both)", left & right),
        ("NEW (fail on the %s only)" % right_label.lower(), right - left),
        ("GONE (fail on the %s only)" % left_label.lower(), left - right),
    ):
        lines.append("=" * 78)
        lines.append("%s: %d" % (name, len(items)))
        lines.append("-" * 78)
        for item in sorted(items):
            lines.append("   " + item)
        lines.append("")
    return lines


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    runs = {}
    for key, filename, label, which in RUNS:
        path = os.path.join(BASELINE, filename)
        if not os.path.exists(path):
            raise SystemExit("missing run: %s (run qa/manual/suite_measure.ps1 first)" % path)
        data = read_run(path)
        data["label"] = label
        data["which"] = which
        runs[key] = data

    lines = ["HEAD vs WORKING TREE - the full suite, measured on 2026-11-05", "=" * 78, ""]
    lines.append("What was measured")
    lines.append("-" * 78)
    lines.append("  pre-increment   a byte-exact copy of commit d938095 (\"build 1.98: detector/runtime")
    lines.append("                  layer wired\"), built with `git archive` and proven byte-exact by")
    lines.append("                  comparing the copy's git tree hash with the commit's own tree hash")
    lines.append("                  (qa/manual/suite_treehash.py).")
    lines.append("  current HEAD    the same, for commit f1bb0c5, minus the `.baseline_head/` tree that")
    lines.append("                  HEAD carries (a committed archive of an older commit, not product).")
    lines.append("  working tree    a snapshot of the working tree, copied to `.snapshot_wt/` and measured")
    lines.append("                  there, so a second session working in the same tree cannot move the")
    lines.append("                  numbers underneath the measurement. The snapshot is taken when the")
    lines.append("                  measurement starts; edits made to the working tree after that are")
    lines.append("                  another lane's work and are not in it.")
    lines.append("  command         python -m unittest discover -s tests -v")
    lines.append("")
    for key in ("pre", "head", "wt"):
        data = runs[key]
        lines.append("  %-14s : %s tests in %ss  -> %s"
                     % (data["label"], data["tests"], data["secs"], data["verdict"]))
    lines.append("")
    lines.append("  problems        : pre-increment %d, current HEAD %d, working tree %d"
                 % (len(runs["pre"]["ids"]), len(runs["head"]["ids"]), len(runs["wt"]["ids"])))
    lines.append("")
    lines.append("  by kind:")
    for key in ("pre", "head", "wt"):
        lines.append("     %-14s %s" % (key, kinds(runs[key]["ids"])))
    lines.append("")
    lines.extend(section(
        "AGAINST THE PRE-INCREMENT BASELINE (d938095) - what the increment changed",
        runs["pre"]["ids"], runs["wt"]["ids"], "baseline", "working tree"))
    lines.extend(section(
        "AGAINST THE CURRENT HEAD (f1bb0c5) - what the last commit changed",
        runs["head"]["ids"], runs["wt"]["ids"], "HEAD", "working tree"))

    text = "\n".join(lines)
    print(text)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print("written to %s" % out_path)


if __name__ == "__main__":
    main()
