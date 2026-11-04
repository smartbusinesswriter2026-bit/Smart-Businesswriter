"""Assumptions manifest guard (G15)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List


@dataclass
class Assumption:
    policy: str
    value: Any
    source: str  # explicit_statement | default | user_supplied
    span: tuple | None = None
    text: str | None = None
    impact: list = None

    def __post_init__(self):
        if self.impact is None:
            self.impact = []


def build_assumptions_manifest(policies: dict, claims=None) -> List[Assumption]:
    claims = claims or []
    out = []
    for policy, value in policies.items():
        source_claim = None
        for c in claims:
            txt = getattr(c, "text", str(c))
            if policy.split(".")[0] in txt.lower() or policy in txt.lower():
                source_claim = c
                break
        out.append(Assumption(
            policy=policy, value=value,
            source="explicit_statement" if source_claim else "default",
            span=getattr(source_claim, "span", None),
            text=getattr(source_claim, "text", None),
            impact=[policy],
        ))
    return out
