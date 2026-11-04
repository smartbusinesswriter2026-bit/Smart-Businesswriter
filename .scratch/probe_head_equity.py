"""Print the equity statement and the ratios for the Ashgrove trial balance.

BP_SRC selects the tree: the working tree, or the HEAD baseline copy.
"""
import os
import sys

SRC = os.environ.get("BP_SRC") or os.path.join(
    r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline", "src")
sys.path.insert(0, SRC)

from bp import methods  # noqa: E402
from bp import statement_plan  # noqa: E402
from bp.product import statements  # noqa: E402

statements.attach_core(
    solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
    diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
        {"journal": None, "trial_balance": rows, "places": places}),
    ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
    dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
    build=lambda plan: statement_plan.build(plan))

TRIAL_BALANCE = """The following trial balance was extracted at 31 December 2026.
Equipment 30,000
Cash 15,900
Trade receivables 18,400
Inventory 22,600
Cost of sales 84,000
Wages 19,000
Rent 8,000
Utilities 3,200
Depreciation 3,000
Interest expense 1,200
Trade payables 14,800 Cr
Loan 12,000 Cr
Capital 20,000 Cr
Retained earnings 8,000 Cr
Sales 140,000 Cr
Other income 1,500 Cr
Accumulated depreciation 9,000 Cr"""

print("tree:", SRC)
record = statements.solve(TRIAL_BALANCE)
print("=" * 78)
print("EQUITY")
print("=" * 78)
print((record.get("statements") or {}).get("equity"))
print("=" * 78)
print("RATIOS with the instruction asking for them")
print("=" * 78)
with_ratios = statements.solve(TRIAL_BALANCE + "\nAlso compute the liquidity ratios.")
print("problem_type:", with_ratios.get("problem_type"))
ratios = with_ratios.get("ratios") or {}
for key, value in sorted((ratios.get("computed") or {}).items()):
    print("   %-24s %s" % (key, value))
for key, value in sorted((ratios.get("missing") or {}).items()):
    print("   MISSING %-18s %s" % (key, value))
