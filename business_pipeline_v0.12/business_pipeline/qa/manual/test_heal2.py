import sys, os
sys.path.insert(0, "src")
os.environ.setdefault("BP_STATEMENT_LIBRARY_DIR", os.path.join(os.environ.get("TEMP",""), "bp_test_statement_library"))
os.environ.setdefault("BP_STATEMENT_LIBRARY_ORIGIN", "test")

from bp import methods, schedule_math, statement_plan, server as srv
from bp.product import statements as S

S.attach_core(
    solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
    diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
        {"journal": None, "trial_balance": rows, "places": places}),
    ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
    dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
    reader=srv._statement_reader,
    extract=srv._statement_extract,
    build=srv._statement_build,
    set_tier=srv.set_statement_model_tier,
    schedules=schedule_math.compute,
)

TB_GOOD = ("Cash 7,000\nTrade receivables 3,000\nInventory 1,500\nEquipment 10,000\n"
           "Accumulated depreciation 2,000\nTrade payables 2,500\nCapital 13,000\n"
           "Sales 9,000\nPurchases 4,000\nRent 1,000")

# Test solve before any mutation
r = S.solve(TB_GOOD)
print("Before mutation: solved =", r.get("solved"))

# Apply a rule
proposal = (r"^(commission|commission expense|commissions)$", "expense", "", "Operating Expenses", "", "operating", False)
success, reason, passed, tested = S.heal(proposal, [TB_GOOD])
print("Heal result:", success, reason, passed, "/", tested)

# Check if RULES was restored after rejection
print("RULES type:", type(S._t1.get_rules()))
commission_rules = [r for r in (S._t1.get_rules() or []) if "commission" in str(r[0])]
print("Commission rules remaining:", commission_rules)
