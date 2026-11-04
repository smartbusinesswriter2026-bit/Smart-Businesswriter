"""Cross-statement reconciliation guard (G13)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional


@dataclass
class Diagnostic:
    stage: str
    gate: str
    expected: Any
    actual: Any
    hint: str


def reconcile_cash_two_ways(tb_balance_cash: Decimal, journal_cash: Decimal) -> Optional[Diagnostic]:
    if tb_balance_cash != journal_cash:
        return Diagnostic(stage="VALIDATE", gate="cash_two_ways",
                         expected=journal_cash, actual=tb_balance_cash,
                         hint="TB and journal disagree on cash — posting error")
    return None


def reconcile_ni_two_ways(ni_is: Decimal, ni_tb: Decimal) -> Optional[Diagnostic]:
    if ni_is != ni_tb:
        return Diagnostic(stage="VALIDATE", gate="ni_two_ways",
                         expected=ni_tb, actual=ni_is,
                         hint="IS and TB disagree on net income")
    return None


def reconcile_re_two_ways(re_closing: Decimal, bs_re: Decimal) -> Optional[Diagnostic]:
    if re_closing != bs_re:
        return Diagnostic(stage="VALIDATE", gate="re_two_ways",
                         expected=re_closing, actual=bs_re,
                         hint="RE statement and BS disagree on closing RE")
    return None
