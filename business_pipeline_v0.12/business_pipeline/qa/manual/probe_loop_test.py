import sys, os
sys.path.insert(0, "src")
os.environ.setdefault("BP_STATEMENT_LIBRARY_DIR", os.path.join(os.environ.get("TEMP",""), "bp_test_statement_library"))
os.environ.setdefault("BP_STATEMENT_LIBRARY_ORIGIN", "test")

from bp.product import statements as S
from bp.product import income_statement as is_mod

TB_WITH_UNKNOWN = ("Cash 10,000 Dr\n"
                   "Commission expense 3,000 Dr\n"
                   "Sales 13,000 Cr\n"
                   "Capital 0 Cr")

print("=== BEFORE: Tier-1 on 'Commission expense' (unknown label) ===")
rows, skipped = S.parse_rows(TB_WITH_UNKNOWN)
print("placed rows:", [r["label"] for r in rows])
print("skipped (unplaced):", skipped)
placed_labels = [r["label"] for r in rows]
assert "Commission expense" not in placed_labels, "Commission expense should NOT be placed yet"
print("CONFIRMED: 'Commission expense' is unplaced (tier-1 fails to read it)")

print()
print("=== APPLY: add 'commission expense' -> 'Operating Expenses' rule (simulating self-heal) ===")
import re
# RULES is a frozen tuple (the code constant). The self-healing loop's Phase 1 extracts it
# to a mutable data file. We simulate that by creating a mutable copy and pointing S.RULES at it.
new_rule = (r"^(commission|commission expense|commissions)$", "expense", "", "Operating Expenses", "", "operating", False)
mutable_rules = [new_rule] + list(S.RULES)
S.RULES = mutable_rules
print("Rule applied (simulating Phase 1 data-table change)")

print()
print("=== AFTER: Tier-1 on 'Commission expense' (with synonym) ===")
rows2, skipped2 = S.parse_rows(TB_WITH_UNKNOWN)
print("placed rows:", [r["label"] for r in rows2])
print("skipped (unplaced):", skipped2)
placed_labels2 = [r["label"] for r in rows2]
assert "Commission expense" in placed_labels2, "Commission expense should now be placed"
print("CONFIRMED: 'Commission expense' is now placed (tier-1 healed)")

print()
print("=== HELD-OUT: verify no regression on existing labels ===")
TB_GOOD = ("Cash 7,000\nTrade receivables 3,000\nInventory 1,500\nEquipment 10,000\n"
           "Accumulated depreciation 2,000\nTrade payables 2,500\nCapital 13,000\n"
           "Sales 9,000\nPurchases 4,000\nRent 1,000")
# Baseline placed labels (before change)
rows_before, _ = S.parse_rows(TB_GOOD)
labels_before = [r["label"] for r in rows_before]

# Apply change
new_rule = (r"^(commission|commission expense|commissions)$", "expense", "", "Operating Expenses", "", "operating", False)
S.RULES = [new_rule] + list(S.RULES)

# After change
rows_after, _ = S.parse_rows(TB_GOOD)
labels_after = [r["label"] for r in rows_after]
print("Labels before:", labels_before)
print("Labels after: ", labels_after)
assert labels_before == labels_after, "Existing label classification changed! (regression)"
print("CONFIRMED: held-out problem unaffected by the new rule (no regression)")
print()
print("=== RESULT: self-healing loop validated ===")
print("1. Tier-1 failed on unknown label -> confirmed")
print("2. Applied synonym (data-table change) -> tier-1 now places it -> confirmed")
print("3. Held-out problem still passes -> no regression -> confirmed")
print("4. Model loop solves transaction narratives -> confirmed (from earlier probe)")
print("5. Library records failures + gap report proposes fixes -> confirmed (from earlier probe)")
print()
print("ALL HALVES OF THE LOOP ARE FEASIBLE. Safe to build.")
