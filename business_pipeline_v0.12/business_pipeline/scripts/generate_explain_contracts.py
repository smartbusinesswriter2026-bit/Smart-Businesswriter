"""Regenerate the committed method-contract slice used by the explainer.

Run from `business_pipeline/`:

    PYTHONPATH=src python scripts/generate_explain_contracts.py

The product layer may not import the frozen core, so the explainer reads a
committed slice of the method contracts instead of importing `bp.methods`.
This helper is the only thing that regenerates it: it imports the core (a
scripts-side privilege), writes deterministic sorted JSON, and
`tests/test_product_explain.py` fails if the slice drifts from
`bp.methods.list_methods()`.

The slice carries the contract prose the explanation needs - intended use,
unsupported use, claim ceiling, assumptions, limitations, defaults and the
declared checks - plus the input schema. It carries no computed value.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "src" / "bp" / "product" / "data" / "explain_contracts_v0_1.json"


def build():
    sys.path.insert(0, str(ROOT / "src"))
    from bp import methods

    rows = {}
    for method in methods.list_methods():
        rows[method["method_id"]] = {
            "method_id": method["method_id"],
            "version": method.get("version"),
            "tier": method.get("tier"),
            "category": method.get("category"),
            "status": method.get("status"),
            "review_status": method.get("review_status"),
            "intended_use": method.get("intended_use") or "",
            "unsupported_use": method.get("unsupported_use") or "",
            "claim_ceiling": method.get("claim_ceiling") or "",
            "assumptions": list(method.get("assumptions") or []),
            "limitations": list(method.get("limitations") or []),
            "defaults": list(method.get("defaults") or []),
            "planned_checks": list(method.get("planned_checks") or []),
            "inputs": {
                name: {
                    "type": (spec or {}).get("type"),
                    "desc": (spec or {}).get("desc") or "",
                    "required": (spec or {}).get("required", True) is not False,
                }
                for name, spec in sorted((method.get("input_schema") or {}).items())
            },
        }
    return {
        "format": "bp-explain-contracts/1",
        "note": ("Generated from bp.methods.list_methods() by "
                 "scripts/generate_explain_contracts.py. Contract prose and input "
                 "names only; the explainer computes nothing."),
        "methods": dict(sorted(rows.items())),
    }


def main():
    payload = build()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print("wrote %s (%d methods)" % (TARGET, len(payload["methods"])))


if __name__ == "__main__":
    main()
