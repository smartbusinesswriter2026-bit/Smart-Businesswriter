"""Adjustment completeness guard (G5)."""

from __future__ import annotations

from typing import List


ADJUSTMENT_CLAIM_PATTERNS = {
    "record_depreciation": r"record .* depreciation",
    "record_insurance_expense": r"record insurance expense",
    "record_rent_expense": r"record rent expense",
    "record_accrued_salaries": r"accrued salaries? .* earned .* unpaid|employees earned .* unpaid",
    "record_cogs": r"cost of goods sold.*periodic|use the periodic",
    "record_income_tax": r"income tax rate|tax rate is",
    "record_unearned_earned": r"by Dec\. 31 .* have been earned|months .* earned",
    "record_accrued_interest": r"interest is paid .* at maturity|accrued interest",
    "record_accrued_revenue": r"not been billed|unbilled",
}


def map_claim_to_adjustment_id(text: str):
    import re
    for adj_id, pat in ADJUSTMENT_CLAIM_PATTERNS.items():
        if re.search(pat, text, re.IGNORECASE):
            return adj_id
    return None


def check_adjustment_completeness(claims, executed_adjustments) -> List[str]:
    declared = set()
    for c in claims:
        txt = getattr(c, "text", str(c))
        kind = getattr(c, "kind", None)
        if kind is not None and kind != "adjustment_info":
            # still try mapping; policy claims may imply adjustments but we only
            # count explicit adjustment_info claims here
            pass
        adj_id = map_claim_to_adjustment_id(txt)
        if adj_id is not None:
            declared.add(adj_id)
    executed = set(executed_adjustments)
    return sorted(declared - executed)
