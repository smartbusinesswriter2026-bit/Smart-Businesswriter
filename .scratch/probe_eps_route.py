"""Does the EPS detector hijack a trial balance that mentions preference dividends?"""
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

WITH_PREF = """The following trial balance was extracted at 31 December 2026.
Cash 30,000
Trade receivables 10,000
Inventory 12,000
Trade payables 8,000
Preference dividends 2,000
Capital 40,000
Retained earnings 4,000
Sales 60,000"""

PLAIN = """The following trial balance was extracted at 31 December 2026.
Cash 32,000
Trade receivables 10,000
Inventory 12,000
Trade payables 8,000
Capital 40,000
Retained earnings 4,000
Sales 60,000"""

for label, text in (("plain trial balance", PLAIN), ("with preference dividends", WITH_PREF)):
    print("=" * 70)
    print(label)
    print("=" * 70)
    try:
        record = statements.solve(text)
        print("  problem_type:", record.get("problem_type"))
        print("  computed:", record.get("computed"), " hidden:", record.get("hidden"))
        print("  checks:", len(record.get("checks") or []))
        print("  net income:", (record.get("core") or {}).get("scalars", {}).get("net_income"))
    except Exception as error:
        print("  RAISED:", type(error).__name__, str(error)[:200])
