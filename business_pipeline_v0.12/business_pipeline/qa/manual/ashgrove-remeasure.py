"""Re-measure the owner's case study after the reader's seams were closed.

The trial balance is the one in `qa/manual/statements-case-study.md`, unchanged.  What the
reader now prints is what this script prints.
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp.product import statements  # noqa: E402

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


def main():
    statements.attach_core(
        solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
        diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
            {"journal": None, "trial_balance": rows, "places": places}),
        ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
        dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs))
    record = statements.solve(ASHGROVE)
    print("solved:", record.get("solved"))
    print("refusal:", record.get("refusal"))
    print("reading source:", (record.get("reading") or {}).get("source"))
    print()
    for name, statement in (record.get("statements") or {}).items():
        print("=" * 70)
        print(name)
        print("=" * 70)
        print(statement)
        print()


if __name__ == "__main__":
    main()
