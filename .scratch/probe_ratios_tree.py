"""The ratios for the Ashgrove trial balance, on whichever tree BP_SRC names."""
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
record = statements.solve(TRIAL_BALANCE + "\nAlso compute the liquidity ratios.")
print("problem_type:", record.get("problem_type"))
print("computed:", record.get("computed"), "hidden:", record.get("hidden"))
ratios = record.get("ratios") or {}
print("ratio keys:", list(ratios))
for row in (ratios.get("computed") or []):
    print("   %-22s %-36s %s" % (row.get("ratio"), row.get("value"), row.get("definition")))
print("--- named unsupported ---")
for row in (ratios.get("named_unsupported") or []):
    print("   ", row)
print("--- core scalars ---")
for key, value in sorted((record.get("core") or {}).get("scalars", {}).items()):
    print("   %-24s %s" % (key, value))
