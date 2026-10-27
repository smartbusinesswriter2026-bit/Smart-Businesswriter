"""Economics shelf audit and frozen-contract regeneration.

Usage:
    python scripts/econ_shelf.py --check
    python scripts/econ_shelf.py --fixture

`--check` reports the method, preset and Economics-tool counts, the level split,
missing student notes and the glossary size. It exits non-zero if a tool is
missing notes, so it can be used as a release gate.

`--fixture` regenerates `tests/fixtures/frozen_contract.json` from the code. Use
it only after an owner-approved unfreeze and a matching B-decision; the frozen
contract is deliberately guarded by `tests/test_frozen_contract.py`.
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import server  # noqa: E402
from bp.methods import LIBRARY  # noqa: E402
from bp.product import subjects  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "frozen_contract.json")


def check():
    page = subjects.detail("economics")
    print("methods: %d" % len(LIBRARY))
    print("presets: %d" % len(server.PRESETS))
    print("economics tools: %d" % len(page["tools"]))
    for level in ("intro", "intermediate", "advanced"):
        keys = [tool["key"] for tool in page["tools"] if tool["level"] == level]
        print("  %-12s %d" % (level, len(keys)))
    missing = [tool["key"] for tool in page["tools"]
               if not (tool["formula"] and tool["steps"] and tool["common_mistakes"])]
    print("missing student notes: %s" % (", ".join(missing) if missing else "none"))
    print("glossary terms: %d" % len(page["glossary"]))
    return 1 if missing else 0


def fixture():
    with open(FIXTURE, encoding="utf-8") as stream:
        old = json.load(stream)
    methods = {}
    for method_id in sorted(LIBRARY):
        method = LIBRARY[method_id]
        methods[method_id] = {
            "tier": method.tier,
            "metric": method.metric,
            "unit": method.unit,
            "test_names": list(method.test_names),
            "claim_ceiling": method.claim_ceiling,
            "category": method.category,
            "inputs": sorted(method.input_schema),
        }
    payload = {"note": old["note"], "methods": methods,
               "presets": sorted(server.PRESETS), "routes": old["routes"]}
    with open(FIXTURE, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print("wrote %s: %d methods, %d presets" % (FIXTURE, len(methods), len(payload["presets"])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="audit the Economics shelf")
    parser.add_argument("--fixture", action="store_true", help="regenerate the frozen contract fixture")
    args = parser.parse_args()
    if args.fixture:
        fixture()
    if args.check or not args.fixture:
        sys.exit(check())
