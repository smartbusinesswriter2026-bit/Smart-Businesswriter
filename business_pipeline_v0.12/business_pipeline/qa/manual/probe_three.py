import sys
sys.path.insert(0, "src")
from bp import methods, schedule_math, statement_plan
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
"A_disposal": ("Data: Equipment cost 100,000; residual value 10,000; useful life 5 years; "
               "straight-line depreciation. Sold on Dec. 31 of Year 3 for 35,000.\n"
               "Required: Compute annual depreciation, accumulated depreciation at sale, "
               "gain/loss, and show financial statement effects."),
"B_ratios": ("Data: Current assets 50,000; inventory 20,000; current liabilities 25,000; total "
             "assets 150,000; total liabilities 90,000; equity 60,000; sales 300,000; COGS "
             "180,000; net income 30,000; accounts receivable 25,000.\n"
             "Required: Compute current ratio, quick ratio, debt ratio, gross margin, net margin, "
             "ROA, ROE, asset turnover, receivables turnover, and days sales outstanding."),
"C_sole_trader": ("Data: Cash 10,000; AR 15,000; inventory 20,000; equipment 50,000; accumulated "
                 "depreciation 10,000; AP 12,000; bank loan 25,000; drawings 10,000; sales 120,000; "
                 "expenses 70,000. No additional capital was contributed.\n"
                 "Required: Create an income statement, statement of owner's equity, and balance "
                 "sheet; determine beginning capital."),
}

for name, text in CASES.items():
    print("=" * 78)
    print(name)
    print("=" * 78)
    try:
        record = S.solve(text)
    except Exception as error:
        print("RAISED:", type(error).__name__, str(error)[:600])
        print()
        continue
    print("problem_type:", record.get("problem_type"), "| source:", record.get("reading_source"))
    print("scalars:", record["core"]["scalars"])
    failed = [c for c in record.get("checks") or [] if not c["ok"]]
    print("checks:", len(record.get("checks") or []), "failed:", failed)
    print()
    print(record.get("statements_only", "")[:3000])
    print()
