"""One-off, self-checking patch: give every `typing` hook its own name (B-179).

Six hooks were defined twice under three names (`_risk_typing`, `_tax_typing`,
`_social_typing`).  Python keeps the last definition, so every method's `Method(...)`
construction captured whichever block came last in the file, and three methods were
given another method's units and precision:

    risk_metrics     -> the schedule-risk hook   (returns in "periods")
    tax_incidence    -> the tax_declared hook    (units in "currency")
    social_welfare   -> the social-engagement hook (a headcount in "rate")

The patch renames all six blocks and re-points the six constructions.  Every target
line is asserted against its expected content first, so a drifted file fails closed
instead of being edited in the wrong place.

Run once:  python qa/patch_typing_hooks.py      (then delete nothing: it is the record)
"""
import sys

PATH = "src/bp/methods.py"

# (1-based line, expected text, replacement)
EDITS = [
    (4616, "def _risk_typing(metric):", "def _risk_metrics_typing(metric):"),
    (5164, "def _tax_typing(metric):", "def _tax_incidence_typing(metric):"),
    (6441, "def _social_typing(metric):", "def _social_welfare_typing(metric):"),
    (10066, "def _social_typing(metric):", "def _social_engagement_typing(metric):"),
    (12616, "def _risk_typing(metric):", "def _schedule_risk_typing(metric):"),
    (13953, "def _tax_typing(metric):", "def _tax_declared_typing(metric):"),
    (15468, "typing=_risk_typing),", "typing=_risk_metrics_typing),"),
    (15588, "typing=_tax_typing),", "typing=_tax_incidence_typing),"),
    (15874, "typing=_social_typing),", "typing=_social_welfare_typing),"),
    (16623, "typing=_social_typing),", "typing=_social_engagement_typing),"),
    (16918, "typing=_risk_typing),", "typing=_schedule_risk_typing),"),
    (17124, "typing=_tax_typing),", "typing=_tax_declared_typing),"),
]


def main():
    with open(PATH, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    problems = []
    for number, expected, _ in EDITS:
        line = lines[number - 1]
        if expected not in line:
            problems.append("line %d: expected %r, found %r" % (number, expected, line.strip()))
    if problems:
        for problem in problems:
            print("REFUSED: " + problem)
        return 1
    for number, expected, replacement in EDITS:
        lines[number - 1] = lines[number - 1].replace(expected, replacement)
    with open(PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    print("patched %d lines in %s" % (len(EDITS), PATH))
    return 0


if __name__ == "__main__":
    sys.exit(main())
