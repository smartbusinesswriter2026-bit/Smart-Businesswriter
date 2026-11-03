"""Convention conflict guard (G18)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class Diagnostic:
    stage: str
    gate: str
    input_ref: str
    expected: str
    actual: list
    hint: str


POLICY_PATTERNS = {
    "inventory_system": r"periodic inventory system|perpetual inventory system",
    "purchase_discount_method": r"gross method|net method",
    "depreciation_convention": r"full year of depreciation|pro-rata|half-year",
    "interest_timing": r"interest paid annually|interest is paid in full at maturity|paid at maturity",
}

POLICY_VALUE_EXTRACTORS = {
    "inventory_system": lambda t: "periodic" if "periodic" in t.lower() else "perpetual",
    "purchase_discount_method": lambda t: "gross" if "gross" in t.lower() else "net",
    "depreciation_convention": lambda t: ("full_year" if "full year" in t.lower()
                                         else "pro_rata" if "pro-rata" in t.lower() or "pro rata" in t.lower()
                                         else "half_year"),
    "interest_timing": lambda t: "annual" if "annually" in t.lower() else "at_maturity",
}


def detect_convention_conflicts(claims) -> List[Diagnostic]:
    issues = []
    policies = {k: [] for k in POLICY_PATTERNS}
    for c in claims:
        txt = getattr(c, "text", str(c))
        for pname, pat in POLICY_PATTERNS.items():
            if re.search(pat, txt, re.IGNORECASE):
                val = POLICY_VALUE_EXTRACTORS[pname](txt)
                policies[pname].append((val, getattr(c, "span", None), txt))
    for pname, found in policies.items():
        distinct = {v for v, _, _ in found}
        if len(distinct) > 1:
            issues.append(Diagnostic(
                stage="RESOLVE", gate="convention_conflict", input_ref=pname,
                expected=f"exactly one of {sorted(distinct)}",
                actual=found,
                hint=f"conflicting claims for {pname}",
            ))
    return issues
