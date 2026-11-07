"""Regenerate the committed input-schema slice used by the calculator router.

Run from `business_pipeline/`:

    PYTHONPATH=src python scripts/generate_calc_inputs.py

The product package may not import the frozen core, so the router reads a
committed slice of the method input schemas instead of importing
`bp.methods`. This helper is the only thing that regenerates it: it imports
the core (a scripts-side privilege), writes deterministic sorted JSON, and
`tests/test_product_calc_router.py` fails if the slice drifts from
`bp.methods.list_methods()`.

The slice carries names, types, one-line descriptions and the declared required
flag only - no numbers, no formula and nothing the router could compute with.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "src" / "bp" / "product" / "data" / "calc_inputs_v0_1.json"


def build():
    sys.path.insert(0, str(ROOT / "src"))
    from bp import methods
    from bp import finance_methods  # noqa: F401 - registers the additional methods, as the server does

    rows = {}
    for method in methods.list_methods():
        schema = method.get("input_schema") or {}
        rows[method["method_id"]] = {
            "tier": method.get("tier"),
            "version": method.get("version"),
            "inputs": {
                name: {"type": (spec or {}).get("type"),
                       "desc": (spec or {}).get("desc") or "",
                       "required": (spec or {}).get("required", True) is not False}
                for name, spec in sorted(schema.items())
            },
        }
    return {
        "format": "bp-calc-inputs/1",
        "note": ("Generated from bp.methods.list_methods() by "
                 "scripts/generate_calc_inputs.py. Names, types and descriptions only; "
                 "the calculator router computes nothing."),
        "methods": dict(sorted(rows.items())),
    }


def main():
    payload = build()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote %s (%d methods)" % (TARGET, len(payload["methods"])))


if __name__ == "__main__":
    main()
