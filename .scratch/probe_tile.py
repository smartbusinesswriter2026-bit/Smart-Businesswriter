"""Measure the statements tile's current behaviour for the case study and the notebook.

- the Ashgrove trial balance: statements, checks, ratios, named gaps
- a transaction narrative with NO model configured
- a transaction narrative read through the deterministic detector layer
"""
import os
import sys

ROOT = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp import statement_plan  # noqa: E402
from bp.product import statements  # noqa: E402


def attach():
    statements.attach_core(
        solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
        diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
            {"journal": None, "trial_balance": rows, "places": places}),
        ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
        dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
        build=lambda plan: statement_plan.build(plan))


ASHGROVE = """The following trial balance was extracted at 31 December 2026.
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

NARRATIVE = ("Alder Trading opened on 1 January 2025. The owner invested 50,000 cash in the business "
             "for shares on 1 January 2025. The business purchased a delivery van for 30,000 cash on "
             "2 January 2025. It paid 6,000 cash rent on 3 March 2025. It paid 8,000 cash salaries on "
             "31 March 2025.")


def main():
    attach()

    print("=" * 72)
    print("ASHGROVE: the trial balance")
    print("=" * 72)
    record = statements.solve(ASHGROVE)
    print("solved:", record.get("solved"), "type:", record.get("problem_type"))
    print("reading source:", (record.get("reading") or {}).get("source"))
    print("reading why:", (record.get("reading") or {}).get("why"))
    print("reading missing:", (record.get("reading") or {}).get("missing"))
    print("working missing:", (record.get("working") or {}).get("missing"))
    print("checks:")
    for check in record.get("checks") or []:
        print("   [%s] %s" % ("ok" if check.get("ok") else "!!", check.get("name")))
    for name in ("balance_sheet", "cash_flow", "statement_of_changes_in_equity"):
        text = (record.get("statements") or {}).get(name)
        if not text:
            print("--- %s: NOT PRESENT ---" % name)
            continue
        print("--- %s ---" % name)
        print(text)
    print("ratios:")
    for key, value in sorted(((record.get("ratios") or {}).get("computed") or {}).items()):
        print("   %-22s %s" % (key, value))
    print("ratios not computed:")
    for key, value in sorted(((record.get("ratios") or {}).get("missing") or {}).items()):
        print("   %-22s %s" % (key, value))

    print()
    print("=" * 72)
    print("NARRATIVE with no model configured")
    print("=" * 72)
    record = statements.solve(NARRATIVE)
    print("solved:", record.get("solved"), "type:", record.get("problem_type"))
    print("reading source:", (record.get("reading") or {}).get("source"))
    print("refusal:", record.get("refusal"))
    print("checks:", [(c.get("name"), c.get("ok")) for c in (record.get("checks") or [])])
    for name, text in (record.get("statements") or {}).items():
        print("--- %s ---" % name)
        print(text)


if __name__ == "__main__":
    main()
