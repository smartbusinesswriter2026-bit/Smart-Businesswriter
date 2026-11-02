"""Regenerate the committed registry slice inside `bp.product.subjects`.

Run from `business_pipeline/`:

    $env:PYTHONPATH="src"; python scripts/generate_subjects.py

The product package may not import the frozen core, so `subjects.py` carries a
static `CATALOGUE` slice of `src/bp/data/registry_v0_2.json`.  This helper is
the *only* thing that regenerates it.  It imports the registry (a scripts-side
privilege), writes deterministic sorted Python, and refuses to run if the
hand-written subject definitions refer to a tool or worksheet that does not
exist in `subjects.py`.  `tests/test_product_subjects.py` is the guard that
fails when the committed slice drifts from the registry or the frozen fixture.
"""

import pprint
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


FORM_SHORT = {"computed": "Computed", "worksheet": "Worksheet",
              "read_only": "No worksheet yet", "theory": "Reading lens"}


def _status_short(record):
    """A quantitative method with no linked method is a build gap, not a worksheet gap."""
    if record["form"] == "read_only" and record["type"] == "Q":
        return "Method not built"
    return FORM_SHORT[record["form"]]


def build_catalogue():
    sys.path.insert(0, str(ROOT / "src"))
    from bp import registry

    data = {}
    for record in registry.load()["records"]:
        data[record["id"]] = {
            "id": record["id"],
            "name": record["name"],
            "type": record["type"],
            "form": record["form"],
            "summary": record.get("summary", ""),
            "evidence_needs": record.get("evidence_needs", ""),
            "status_short": _status_short(record),
            "status_note": record.get("implementation_status", ""),
            "implementation_status": record.get("implementation_status", ""),
            "template": record.get("template"),
            "linked_methods": [{"method_id": item["method_id"], "coverage": item.get("coverage")}
                               for item in record.get("linked_methods") or []],
            "disciplines": list(record.get("disciplines") or []),
        }
    return data


def main():
    target = ROOT / "src" / "bp" / "product" / "subjects.py"
    source = target.read_text(encoding="utf-8")
    start = source.index("CATALOGUE = ")
    end = source.index("\n\n\ndef _fill_catalogue_ids", start)
    catalogue = build_catalogue()
    rendered = "CATALOGUE = " + pprint.pformat(catalogue, width=132, sort_dicts=True)
    target.write_text(source[:start] + rendered + source[end:], encoding="utf-8")

    # Import the written module to prove the hand-written definitions resolve.
    sys.path.insert(0, str(ROOT / "src"))
    from bp.product import subjects

    unknown = []
    for definition in subjects.SUBJECT_DEFS:
        unknown.extend(key for key in definition["tools"] if key not in subjects.TOOL_INFO)
        unknown.extend(key for key in definition["worksheets"] if key not in subjects.WORKSHEETS)
    if unknown:
        raise SystemExit("unknown subject tool/worksheet keys: %s" % ", ".join(sorted(set(unknown))))
    print("wrote %d catalogue records; %d subjects; %d compute tools"
          % (len(catalogue), len(subjects.SUBJECT_DEFS), len(subjects.compute_tools())))


if __name__ == "__main__":
    main()
