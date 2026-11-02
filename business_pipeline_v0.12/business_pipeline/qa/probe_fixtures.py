"""Print the shape of each golden fixture, so the acceptance suite can read it.

Usage:  python qa/probe_fixtures.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(os.path.dirname(HERE), "tests", "fixtures")


def main():
    for name in sorted(os.listdir(FIX)):
        if not name.endswith("_golden.json"):
            continue
        data = json.load(open(os.path.join(FIX, name), encoding="utf-8-sig"))
        print("=" * 70)
        print(name, "|", type(data).__name__)
        if isinstance(data, dict):
            print("  top keys:", sorted(data.keys()))
            cases = data.get("cases") or []
        else:
            cases = data
        print("  n cases:", len(cases))
        if cases:
            first = cases[0]
            print("  case keys:", sorted(first.keys()))
            for key in ("name", "method", "inputs", "tolerance"):
                if key in first:
                    value = first[key]
                    if isinstance(value, dict):
                        print("   %s: %s" % (key, sorted(value.keys())))
                    elif isinstance(value, list):
                        print("   %s: [list of %d]" % (key, len(value)))
                    else:
                        print("   %s: %r" % (key, value))
            expected = first.get("expected") or first.get("outputs") or {}
            if isinstance(expected, dict):
                print("   expected keys:", sorted(expected.keys()))


if __name__ == "__main__":
    main()
