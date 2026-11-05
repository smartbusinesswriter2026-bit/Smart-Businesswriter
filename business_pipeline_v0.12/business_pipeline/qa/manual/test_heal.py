import sys, os
sys.path.insert(0, "src")
os.environ.setdefault("BP_STATEMENT_LIBRARY_DIR", os.path.join(os.environ.get("TEMP",""), "bp_test_statement_library"))
os.environ.setdefault("BP_STATEMENT_LIBRARY_ORIGIN", "test")
os.environ["BP_SELF_HEAL"] = "1"

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

# Held-out problems
HELD_OUT = [
    "Cash 7,000\nTrade receivables 3,000\nInventory 1,500\nEquipment 10,000\n"
    "Accumulated depreciation 2,000\nTrade payables 2,500\nCapital 13,000\n"
    "Sales 9,000\nPurchases 4,000\nRent 1,000",
]

# A new synonym proposal
proposal = (r"^(commission|commission expense|commissions)$", "expense", "", "Operating Expenses", "", "operating", False)

print("Testing heal()...")
success, reason, passed, tested = S.heal(proposal, HELD_OUT)
print("Success:", success)
print("Reason:", reason)
print("Passed:", passed, "/", tested)

# Verify the rule was applied
rows, _ = S.parse_rows("Commission expense 3,000 Dr\nCash 3,000 Cr")
print("Commission expense now placed:", "Commission expense" in [r["label"] for r in rows])

# Check heal_log
from bp.product import statement_library as lib
history = lib.heal_history()
print("Heal log entries:", len(history))
if history:
    print("Latest:", history[0]["type"], history[0]["outcome"], history[0]["reason"][:60])
