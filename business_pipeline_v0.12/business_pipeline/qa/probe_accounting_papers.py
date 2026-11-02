"""Run every accounting capability through its paper formatter with a real result.

For each capability whose method belongs to the accounting shelf, this probe:
  * finds the capability key,
  * computes the method from the shipped preset's inputs,
  * calls the paper formatter the draft uses,
  * reports raw long decimals, "could not be read" fallbacks and missing keys.

Read-only: it writes nothing and computes nothing beyond the frozen method itself.

Usage:  PYTHONPATH=src python qa/probe_accounting_papers.py
"""
import copy
import json
import re
import sys
from decimal import Decimal

sys.path.insert(0, "src")

from bp import methods  # noqa: E402
from bp.product import capabilities, chat  # noqa: E402
from bp.server import PRESETS  # noqa: E402

ACCOUNTING_METHODS = [
    "management_accounts", "trial_balance_check", "ratio_analysis", "standard_cost_variances",
    "abc_costing", "sales_variances", "breakeven", "multi_product_breakeven",
    "working_capital", "loan_amortization", "trend_analysis", "tax_declared",
]

LONG_DECIMAL = re.compile(r"\d+\.\d{6,}")


def preset_for(method_id):
    for name, preset in PRESETS.items():
        if preset.get("method") == method_id:
            return name, preset
    return None, None


def main():
    rows = capabilities.catalogue()
    by_method = {}
    for row in rows:
        by_method.setdefault(row.get("method"), []).append(row)
    for method_id in ACCOUNTING_METHODS:
        method = methods.LIBRARY[method_id]
        preset_name, preset = preset_for(method_id)
        print("=" * 78)
        print("%s  (preset %s)" % (method_id, preset_name))
        matches = by_method.get(method_id) or []
        if not matches:
            print("   no capability row carries this method")
            continue
        try:
            result = method.impl(copy.deepcopy(preset["inputs"]))
        except Exception as error:                          # pragma: no cover - probe only
            print("   method refused the preset inputs: %s" % error)
            continue
        for row in matches:
            formatter = chat.CAPABILITY_LINES.get(row["key"])
            print("   capability %-26s formatter=%s" % (row["key"], getattr(formatter, "__name__", formatter)))
            try:
                lines = chat._capability_lines(row, {"ok": True, "inputs": preset["inputs"],
                                                     "result": result})
            except Exception as error:                      # pragma: no cover - probe only
                print("      FORMATTER RAISED: %s" % error)
                continue
            for line in lines:
                flag = ""
                if LONG_DECIMAL.search(line):
                    flag = "   <-- raw long decimal"
                if "could not be read" in line:
                    flag += "   <-- fallback"
                print("      " + line + flag)


if __name__ == "__main__":
    main()
