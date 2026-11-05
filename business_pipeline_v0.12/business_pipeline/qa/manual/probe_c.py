import sys
sys.path.insert(0, "src")
from bp import methods, schedule_math, statement_plan
from bp.product import statements as S, income_statement as is_mod
S.attach_core(build=statement_plan.build, schedules=schedule_math.compute)
C = ("Data: Cash 10,000; AR 15,000; inventory 20,000; equipment 50,000; accumulated "
     "depreciation 10,000; AP 12,000; bank loan 25,000; drawings 10,000; sales 120,000; "
     "expenses 70,000. No additional capital was contributed.\n"
     "Required: Create an income statement, statement of owner's equity, and balance sheet; "
     "determine beginning capital.")
print("detect_given:", is_mod.detect_given_balances(C))
print("detect_owner:", is_mod.detect_owner_equity(C))
r = S._solve_owner_equity(C)
print("route returned:", None if r is None else r.get("problem_type"))
