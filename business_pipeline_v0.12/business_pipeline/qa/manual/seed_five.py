"""Feed the five acceptance problems into the learning library, then read the gap report.

These are solved through the same HTTP handler the workbench uses, so every outcome — solved,
unsolved, or refused — is recorded the way a student's problem would be. `origin="manual"` marks
them as acceptance evidence rather than fixtures.

    $env:PYTHONPATH="src"; python qa/manual/seed_five.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods, schedule_math, statement_plan  # noqa: E402
from bp.product import statements as S  # noqa: E402
from bp.product import statement_library as library  # noqa: E402

S.attach_core(
    solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
    diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
        {"journal": None, "trial_balance": rows, "places": places}),
    ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
    dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
    build=statement_plan.build,
    schedules=schedule_math.compute,
)

CASES = {
    "cogm": "Data: Direct materials used 50,000; direct labor 40,000; manufacturing overhead 30,000; "
            "beginning WIP 10,000; ending WIP 12,000; beginning finished goods 15,000; ending "
            "finished goods 18,000; sales 200,000; selling and administrative expenses 35,000.\n"
            "Required: Create a cost of goods manufactured schedule and an income statement.",
    "cash_flow": "Data: Net income 50,000; depreciation 10,000; gain on sale of equipment 3,000; "
                 "increase in AR 8,000; decrease in inventory 5,000; increase in AP 4,000; purchase "
                 "of equipment 25,000; proceeds from sale of equipment 7,000; issue common stock "
                 "20,000; dividends paid 12,000; beginning cash 15,000.\n"
                 "Required: Create a statement of cash flows using the indirect method.",
    "equity": "Data: Beginning common stock 100,000; beginning retained earnings 40,000; common "
              "stock issued 30,000; net income 25,000; dividends declared/paid 10,000; no other "
              "comprehensive income.\nRequired: Create a statement of changes in equity.",
    "bank": "Data: Bank statement balance 25,000; book cash balance 22,100; deposits in transit "
            "4,000; outstanding checks 6,000; bank service charge 100; NSF customer check 500; note "
            "collected by bank 1,500.\nRequired: Prepare a bank reconciliation, journal entries, and "
            "the cash balance to report.",
    "adjusted_tb": "Data - unadjusted trial balance: Cash 10,000 Dr; AR 20,000 Dr; Supplies 3,000 Dr; "
                   "Equipment 40,000 Dr; Accumulated depreciation 8,000 Cr; AP 12,000 Cr; Unearned "
                   "revenue 5,000 Cr; Common stock 30,000 Cr; Retained earnings 6,000 Cr; Service "
                   "revenue 45,000 Cr; Salaries expense 28,000 Dr; Rent expense 5,000 Dr.\n"
                   "Adjustments: Supplies on hand 1,000; depreciation 4,000; unearned revenue earned "
                   "3,000; accrued salaries 2,000.\n"
                   "Required: Journalize adjustments and create adjusted income statement and "
                   "balance sheet.",
}

EXPECTED = {
    "cogm": {"cost_of_goods_manufactured": 118000, "cost_of_goods_sold": 115000,
             "gross_profit": 85000, "operating_income": 50000},
    "cash_flow": {"net_cash_operating": 58000, "net_cash_investing": -18000,
                  "net_cash_financing": 8000, "net_change_in_cash": 48000, "ending_cash": 63000},
    "equity": {"total_equity_closing": 185000},
    "bank": {"cash_reported": 23000},
    "adjusted_tb": {"net_income": 7000, "total_assets": 59000, "total_liabilities": 16000,
                    "total_equity": 43000},
}


def main():
    failures = 0
    for name, text in CASES.items():
        status, payload = S.handle("POST", [], {"instruction": text, "origin": "manual"})
        scalars = (payload.get("core") or {}).get("scalars") or {}
        wrong = []
        for key, want in EXPECTED[name].items():
            got = scalars.get(key)
            if got is None or float(str(got)) != float(want):
                wrong.append("{}: want {} got {}".format(key, want, got))
        verdict = "OK" if not wrong else "MISMATCH"
        if wrong:
            failures += 1
        print("{:<12} status={}  {}  {}".format(name, status, verdict, "; ".join(wrong)))
    print()
    print(library.gap_report()["proposals"] or "no proposals")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
