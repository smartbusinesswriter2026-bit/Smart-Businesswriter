"""Audit trail guard (G14)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, List


@dataclass
class TraceNode:
    label: str
    value: Decimal
    kind: str
    account: str | None = None
    je_refs: list = None
    claim_refs: list = None
    formula: str | None = None
    inputs: list = None

    def __post_init__(self):
        if self.je_refs is None:
            self.je_refs = []
        if self.claim_refs is None:
            self.claim_refs = []
        if self.inputs is None:
            self.inputs = []


def explain(label: str, value, kind: str = "account_balance",
            account: str | None = None, je_refs=None, claim_refs=None,
            formula=None, inputs=None) -> TraceNode:
    return TraceNode(label=label, value=Decimal(str(value)), kind=kind, account=account,
                     je_refs=je_refs or [], claim_refs=claim_refs or [],
                     formula=formula, inputs=inputs or [])
