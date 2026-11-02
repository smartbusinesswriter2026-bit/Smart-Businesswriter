"""Dump the frozen method contract for a list of method ids.

Read-only probe for the QA manual (source-of-truth rank 1: `bp.methods.LIBRARY`).

Usage:  PYTHONPATH=src python qa/probe_methods.py <out.json> <method_id> [...]
"""
import json
import sys

sys.path.insert(0, "src")

from bp import methods  # noqa: E402

FIELDS = ("name", "tier", "metric", "unit", "claim_ceiling", "category", "status",
          "version", "default_period", "intended_use", "unsupported_use",
          "assumptions", "limitations", "test_names", "input_schema", "output_precision",
          "output_units", "defaults", "review_status", "fallbacks", "default_thresholds")


def describe(method_id):
    method = methods.LIBRARY[method_id]
    row = {"method_id": method_id}
    for name in FIELDS:
        value = getattr(method, name, None)
        if isinstance(value, tuple):
            value = list(value)
        row[name] = value
    row["input_keys"] = sorted((method.input_schema or {}).keys())
    return row


def main(argv):
    out_path = argv[1]
    ids = argv[2:]
    rows = [describe(method_id) for method_id in ids]
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=1, default=str)
    print("wrote %s (%d methods)" % (out_path, len(rows)))


if __name__ == "__main__":
    main(sys.argv)
