"""Check how a malformed records field reaches a student: refusal, or unhandled error?

Usage:  PYTHONPATH=src python qa/probe_refusal_path.py
"""
import copy
import sys

sys.path.insert(0, "src")

from bp import methods  # noqa: E402
from bp.orchestrator import Pipeline  # noqa: E402
from bp.server import PRESETS  # noqa: E402

BAD = [
    ("multi_product_breakeven: 'variable' instead of 'variable_cost'",
     "multi_product_breakeven",
     {"fixed_costs": "6000",
      "products": [{"name": "coffee", "price": "5", "variable": "2", "mix_units": "3"},
                   {"name": "cake", "price": "6", "variable": "3", "mix_units": "1"}]}),
    ("abc_costing: allocation missing driver_quantity", "abc_costing",
     {"activities": [{"name": "setup", "pool_cost": "1000"}],
      "products": [{"name": "x", "units": "100"}],
      "allocations": [{"activity": "setup", "product": "x"}]}),
    ("sales_variances: product missing actual_price", "sales_variances",
     {"products": [{"name": "x", "budget_units": "10", "budget_price": "5", "actual_units": "12"},
                   {"name": "y", "budget_units": "10", "budget_price": "8", "actual_units": "8",
                    "actual_price": "7"}]}),
    ("unknown input name on a delivered tool", "breakeven",
     {"fixed": "1000", "price": "20", "variable": "10", "nonsense": "1"}),
    ("binary float input", "breakeven", {"fixed": 1000.0, "price": "20", "variable": "10"}),
]

for title, method_id, inputs in BAD:
    print("=" * 72)
    print(title)
    request = {"objective": "acceptance probe", "method": method_id, "inputs": inputs}
    try:
        delivery = Pipeline().run(request, lambda stage: True)
        print("   status: %s" % delivery.status)
        print("   reason: %s" % (getattr(delivery, "blocked_reason", None),))
    except Exception as error:
        print("   UNHANDLED %s: %s" % (type(error).__name__, error))

print("=" * 72)
print("the shipped multibreakeven preset, as a control")
delivery = Pipeline().run(copy.deepcopy(PRESETS["multibreakeven"]), lambda stage: True)
print("   status: %s" % delivery.status)
