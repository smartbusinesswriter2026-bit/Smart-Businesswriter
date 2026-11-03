"""Double-counting guard (G6)."""

from __future__ import annotations

from decimal import Decimal
from typing import List


def bad_debt_expense(target_allowance: Decimal, existing_allowance: Decimal) -> Decimal:
    return target_allowance - existing_allowance


NON_OPERATING_ADDBACK = {
    "gain_on_disposal": "subtract",
    "loss_on_disposal": "add",
    "unrealized_gain_trading": "subtract",
    "unrealized_loss_trading": "add",
}


def check_non_operating_addbacks(journal_accounts: List[str]) -> List[str]:
    issues = []
    for acct in journal_accounts:
        if acct in NON_OPERATING_ADDBACK:
            issues.append(acct)
    return issues
