import sys
sys.path.insert(0, "src")
from bp import statement_plan, schedule_math
from bp.product import statements as S
S.attach_core(build=statement_plan.build, schedules=schedule_math.compute)
TEXT = ("Data - unadjusted trial balance: Cash 10,000 Dr; AR 20,000 Dr; Supplies 3,000 Dr; "
        "Equipment 40,000 Dr; Accumulated depreciation 8,000 Cr; AP 12,000 Cr; Unearned revenue "
        "5,000 Cr; Common stock 30,000 Cr; Retained earnings 6,000 Cr; Service revenue 45,000 Cr; "
        "Salaries expense 28,000 Dr; Rent expense 5,000 Dr.\n"
        "Adjustments: Supplies on hand 1,000; depreciation 4,000; unearned revenue earned 3,000; "
        "accrued salaries 2,000.\n"
        "Required: Journalize adjustments and create adjusted income statement and balance sheet.")
r = S.solve(TEXT)
print("scalars:", r["core"]["scalars"])
print("keys:", sorted(r["core"]["scalars"]))
