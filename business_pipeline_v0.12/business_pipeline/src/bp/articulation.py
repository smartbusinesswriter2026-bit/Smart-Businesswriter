"""Articulation gate suite (G9)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Tuple


@dataclass
class Diagnostic:
    gate: str
    detail: str
    root_cause: Any = None


GATES: List[Tuple[str, Callable]] = []


def run_gates(tb, is_result, re_result, bs_result, cf_result) -> List[Diagnostic]:
    issues = []
    checks = [
        ("tb_balanced", lambda: getattr(tb, "total_dr", 0) == getattr(tb, "total_cr", 0)),
        ("a_equals_l_plus_e", lambda: getattr(bs_result, "assets", 0) == getattr(bs_result, "liabilities", 0) + getattr(bs_result, "equity", 0)),
        ("ni_articulates_is_re", lambda: getattr(is_result, "net_income", 0) == getattr(re_result, "net_income", 0)),
        ("re_articulates_re_bs", lambda: getattr(re_result, "closing", 0) == getattr(bs_result, "retained_earnings", 0)),
        ("cash_articulates_cf_bs", lambda: getattr(cf_result, "ending_cash", 0) == getattr(bs_result, "cash", 0)),
        ("cf_internal", lambda: getattr(cf_result, "cfo", 0) + getattr(cf_result, "cfi", 0) + getattr(cf_result, "cff", 0) == getattr(cf_result, "net_change", 0)),
    ]
    for name, check in checks:
        try:
            if not check():
                issues.append(Diagnostic(gate=name, detail="gate failed"))
        except Exception as e:
            issues.append(Diagnostic(gate=name, detail=str(e)))
    return issues
