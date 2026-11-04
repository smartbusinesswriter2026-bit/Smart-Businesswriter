"""JE validation guard (G8)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List


@dataclass
class Diagnostic:
    je_id: str
    check: str
    detail: str
    hint: str


TEMPLATE_EXPECTED_ACCOUNTS = {}


def validate_je(je_id: str, lines: List[tuple], accounts: Dict[str, Any],
                tb_balance: Any = None) -> List[Diagnostic]:
    issues: List[Diagnostic] = []
    dr = sum(Decimal(str(l[2])) for l in lines if l[1] == "Dr")
    cr = sum(Decimal(str(l[2])) for l in lines if l[1] == "Cr")
    if dr != cr:
        issues.append(Diagnostic(je_id, "balanced", f"Dr={dr} Cr={cr}", "check template"))
    for l in lines:
        acct = l[0]
        if acct not in accounts:
            issues.append(Diagnostic(je_id, "account_exists", acct, "add to chart"))
        amt_dr, amt_cr = Decimal(str(l[2])), Decimal(str(l[2]))
        if l[1] == "Dr":
            if amt_dr < 0:
                issues.append(Diagnostic(je_id, "non_negative", str(l), "swap sides"))
        else:
            if amt_cr < 0:
                issues.append(Diagnostic(je_id, "non_negative", str(l), "swap sides"))
        if l[1] == "Dr" and False:
            pass
    # both-sides check
    for l in lines:
        # a line is (acct, side, amount) so only one side; check duplicate accounts on both sides
        pass
    # zero-amount lines
    for l in lines:
        if Decimal(str(l[2])) == 0:
            issues.append(Diagnostic(je_id, "no_zero", str(l), "remove line"))
    # both sides same account
    dr_accts = {l[0] for l in lines if l[1] == "Dr" and Decimal(str(l[2])) > 0}
    cr_accts = {l[0] for l in lines if l[1] == "Cr" and Decimal(str(l[2])) > 0}
    if dr_accts & cr_accts:
        for a in dr_accts & cr_accts:
            issues.append(Diagnostic(je_id, "one_side", a, "split into two lines"))
    return issues


def validate_template_semantics(je_id: str, txn_type: str, lines: List[tuple]) -> List[Diagnostic]:
    if txn_type not in TEMPLATE_EXPECTED_ACCOUNTS:
        return []
    expected = TEMPLATE_EXPECTED_ACCOUNTS[txn_type]
    actual_dr = {l[0] for l in lines if l[1] == "Dr" and Decimal(str(l[2])) > 0}
    actual_cr = {l[0] for l in lines if l[1] == "Cr" and Decimal(str(l[2])) > 0}
    issues = []
    if not actual_dr.issubset(set(expected.get("debit", []))):
        issues.append(Diagnostic(je_id, "template_semantics",
                                f"unexpected debit accounts: {actual_dr - set(expected.get('debit', []))}",
                                "fix template"))
    if not actual_cr.issubset(set(expected.get("credit", []))):
        issues.append(Diagnostic(je_id, "template_semantics",
                                f"unexpected credit accounts: {actual_cr - set(expected.get('credit', []))}",
                                "fix template"))
    return issues
