import sys, os
sys.path.insert(0, "src")
os.environ.setdefault("BP_STATEMENT_LIBRARY_DIR", os.path.join(os.environ.get("TEMP",""), "bp_test_statement_library"))
from bp.product import statements as S

TB_GOOD = ("Cash 7,000\nTrade receivables 3,000\nInventory 1,500\nEquipment 10,000\n"
           "Accumulated depreciation 2,000\nTrade payables 2,500\nCapital 13,000\n"
           "Sales 9,000\nPurchases 4,000\nRent 1,000")

# Check RULES type
print("RULES type:", type(S.RULES), "len:", len(S.RULES))

# Try reading directly
try:
    reading = S.read_deterministic(TB_GOOD, currency="USD", framework="US_GAAP")
    print("read_deterministic OK:", reading.get("problem_type") if reading else None)
    print("missing:", reading.get("missing") if reading else None)
except Exception as e:
    print("read_deterministic FAILED:", type(e).__name__, str(e)[:200])

# Now mutate RULES
new_rule = (r"^(commission|commission expense|commissions)$", "expense", "", "Operating Expenses", "", "operating", False)
S.RULES = [new_rule] + list(S.RULES)
print("RULES type after:", type(S.RULES), "len:", len(S.RULES))

try:
    reading2 = S.read_deterministic(TB_GOOD, currency="USD", framework="US_GAAP")
    print("read_deterministic after mutation:", reading2.get("problem_type") if reading2 else None)
except Exception as e:
    print("FAILED after mutation:", type(e).__name__, str(e)[:200])
PYEOF
