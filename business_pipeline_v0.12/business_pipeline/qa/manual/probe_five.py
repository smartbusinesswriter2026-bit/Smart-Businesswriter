import sys
sys.path.insert(0, "src")
from bp import methods, statement_plan, schedule_math
from bp.product import statements as S

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
"COGM": ("Data: Direct materials used 50,000; direct labor 40,000; manufacturing overhead 30,000; "
         "beginning WIP 10,000; ending WIP 12,000; beginning finished goods 15,000; ending finished "
         "goods 18,000; sales 200,000; selling and administrative expenses 35,000.\n"
         "Required: Create a cost of goods manufactured schedule and an income statement.",),
"CFS": ("Data: Net income 50,000; depreciation 10,000; gain on sale of equipment 3,000; increase in AR "
        "8,000; decrease in inventory 5,000; increase in AP 4,000; purchase of equipment 25,000; "
        "proceeds from sale of equipment 7,000; issue common stock 20,000; dividends paid 12,000; "
        "beginning cash 15,000.\n"
        "Required: Create a statement of cash flows using the indirect method.",),
"EQUITY": ("Data: Beginning common stock 100,000; beginning retained earnings 40,000; common stock "
           "issued 30,000; net income 25,000; dividends declared/paid 10,000; no other comprehensive "
           "income.\nRequired: Create a statement of changes in equity.",),
"BANK": ("Data: Bank statement balance 25,000; book cash balance 22,100; deposits in transit 4,000; "
         "outstanding checks 6,000; bank service charge 100; NSF customer check 500; note collected "
         "by bank 1,500.\nRequired: Prepare a bank reconciliation, journal entries, and the cash "
         "balance to report.",),
"ADJ": ("Data — unadjusted trial balance: Cash 10,000 Dr; AR 20,000 Dr; Supplies 3,000 Dr; "
        "Equipment 40,000 Dr; Accumulated depreciation 8,000 Cr; AP 12,000 Cr; Unearned revenue "
        "5,000 Cr; Common stock 30,000 Cr; Retained earnings 6,000 Cr; Service revenue 45,000 Cr; "
        "Salaries expense 28,000 Dr; Rent expense 5,000 Dr.\n"
        "Adjustments: Supplies on hand 1,000; depreciation 4,000; unearned revenue earned 3,000; "
        "accrued salaries 2,000.\n"
        "Required: Journalize adjustments and create adjusted income statement and balance sheet.",),
}

for name, (text,) in CASES.items():
    print("=" * 78)
    print(name)
    print("=" * 78)
    try:
        rec = S.solve(text)
    except Exception as e:
        print("FAILED:", type(e).__name__, e)
        continue
    print("solved:", rec.get("solved"), "| problem_type:", rec.get("problem_type"),
          "| reading_source:", rec.get("reading_source"))
    print("scalars:", {k: v for k, v in (rec["core"]["scalars"] or {}).items()
                       if k in ("cost_of_goods_manufactured", "cost_of_goods_sold",
                                "gross_profit", "operating_income", "net_cash_operating",
                                "net_cash_investing", "net_cash_financing", "net_change_in_cash",
                                "ending_cash", "total_equity_closing", "cash_reported")})
    bad = [c for c in rec.get("checks") or [] if not c["ok"]]
    print("checks:", len(rec.get("checks") or []), "failed:", [(c["name"], c["detail"]) for c in bad])
    print()
    print(rec.get("statements_only", ""))
    print()
