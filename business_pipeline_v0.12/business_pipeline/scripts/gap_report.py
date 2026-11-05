"""Print the statements library's gap report — the review step the manual requires.

The library never changes code. This script is how the owner reads it: what the pipeline could not
place, which gaps repeat across distinct problems, which gates fail, and which refusals cluster.

    $env:PYTHONPATH="src"; python scripts/gap_report.py
    $env:PYTHONPATH="src"; python scripts/gap_report.py --json > report.json

Every number is counted twice: by problem (distinct text) and by row. A fixture solved a hundred
times is one problem, not a hundred observations — but it is also not deleted, because a repeated
problem is itself a finding.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from bp.product import statement_library as library  # noqa: E402


def render(report):
    lines = []
    lines.append("STATEMENTS LIBRARY — GAP REPORT")
    lines.append("=" * 78)
    lines.append("store:              " + str(library._STORE_DIR))
    lines.append("rows:               {total}".format(**report))
    lines.append("distinct problems:  {distinct_problems}".format(**report))
    lines.append("solved (rows):      {solved}  ({:.1%})".format(report["solve_rate"], **report))
    lines.append("solved (problems):  {:.1%}".format(report["distinct_solve_rate"]))
    for title, key in (("by kind", "by_kind"), ("by reader", "by_source"), ("by origin", "by_origin")):
        if report.get(key):
            lines.append(title + ": " + ", ".join("{} {}".format(k, v)
                                                  for k, v in report[key].items()))
    if report.get("most_repeated"):
        lines.append("")
        lines.append("MOST REPEATED PROBLEMS (evidence, not garbage)")
        for item in report["most_repeated"]:
            lines.append("  {:>4} x  {}".format(item["rows"], item["text"].replace("\n", " ")))
    lines.append("")
    lines.append("PROPOSALS (each needs the owner's approval before any code changes)")
    if not report.get("proposals"):
        lines.append("  none: no gap repeats across two or more distinct problems.")
    for number, proposal in enumerate(report["proposals"], 1):
        lines.append("")
        lines.append("  {}. [{}] {}".format(number, proposal["type"], proposal["item"]))
        lines.append("     problems: {}   rows: {}   last seen: {}".format(
            proposal["problems"], proposal["rows"], proposal.get("last_seen") or "unknown"))
        if proposal.get("why"):
            lines.append("     why: " + proposal["why"])
        lines.append("     -> " + proposal["suggestion"])
    if report.get("singles"):
        lines.append("")
        lines.append("SEEN ONCE (kept, not proposed: one occurrence is not a pattern)")
        for item in report["singles"]:
            lines.append("  - [{}] {}".format(item["type"], item["item"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--top", type=int, default=15, help="how many proposals per category")
    args = parser.parse_args(argv)
    report = library.gap_report(top=args.top)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
