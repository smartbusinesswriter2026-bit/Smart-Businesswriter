"""Print what the calculator router does with finance phrases.

Usage:  PYTHONPATH=src python qa/probe_router.py [out.txt]
"""
import json
import sys

sys.path.insert(0, "src")

from bp.product import calc_router  # noqa: E402

PHRASES = [
    "net present value of this project",
    "what is the wacc",
    "break even units",
    "price this bond",
    "bond price",
    "coupon rate and yield to maturity",
    "what is the duration of my bond",
    "internal rate of return",
    "value at risk of my portfolio",
    "future value of a lump sum",
]


def main():
    lines = []
    for phrase in PHRASES:
        outcome = calc_router.plan(phrase)
        keys = sorted(outcome.keys())
        lines.append("%-42s keys=%s" % (phrase, keys))
        lines.append("    %s" % json.dumps({key: outcome[key] for key in keys
                                            if key in ("tool", "method", "status", "reason",
                                                       "missing", "inputs", "kind")},
                                           default=str))
    text = "\n".join(lines) + "\n"
    if len(sys.argv) > 1:
        open(sys.argv[1], "w", encoding="utf-8").write(text)
        print("wrote %s" % sys.argv[1])
    else:
        print(text)


if __name__ == "__main__":
    main()
