"""Report which calculator tools the explainer can teach today.

Run from `business_pipeline/`:

    PYTHONPATH=src python scripts/explain_coverage.py
    PYTHONPATH=src python scripts/explain_coverage.py --check

The explainer is registry-driven: a new tool gets a generic document from its
method contract immediately, and its catalogue formula/steps lift it to the
full teachable version.  This report makes the difference visible as the
catalogue grows.  `--check` exits non-zero if a tool has no notes and is not in
the declared gap set, so a new method cannot silently ship without a reason.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import explain, subjects  # noqa: E402


def main(argv):
    report = explain.coverage()
    undeclared = sorted(set(report["partial"]) - set(report["declared_gaps"]))
    report["undeclared"] = undeclared
    report["counts"] = {"tools": len(subjects.TOOL_INFO),
                        "ready": len(report["ready"]),
                        "partial": len(report["partial"]),
                        "missing": len(report["missing"])}
    if "--check" in argv:
        if undeclared:
            print("undeclared explanation gaps: " + ", ".join(undeclared))
            return 1
        print("ok: %d tools, %d ready, %d contract-only, %d declared gaps"
              % (report["counts"]["tools"], report["counts"]["ready"],
                 report["counts"]["partial"], len(report["declared_gaps"])))
        return 0
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
