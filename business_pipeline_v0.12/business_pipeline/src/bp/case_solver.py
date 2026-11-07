"""Integrated case solver (Tip 5 Type 7 / Tip 6 state machine).

A case problem is read as a sequence of claims, each matched to a detector, journalized
through a balanced template, posted, adjusted, projected and validated.  This module runs
that sequence as an explicit state machine and records every stage's outcome, so a failure
names the stage that refused and what it expected.

The stages are the ones Tip 6 names:

    INGEST -> PARSE -> DETECT -> RESOLVE -> JOURNALIZE -> POST -> ADJUST -> PROJECT -> VALIDATE

A stage that fails returns a `CaseResult` with `status="review"` and a `Stage` carrying the
failure.  The solver never auto-corrects: an unbalanced journal, a conflicting policy or an
unmatched claim is a review, not a patch.

The deterministic template layer (`statement_detect`) supplies the journal; `statement_plan`
supplies the projection, the adjustment DAG and the articulation gate.  This module is the
orchestrator between them: it adds the stage trace, the policy resolution and the diagnostics
that neither layer holds on its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from . import statement_detect as sd
from . import statement_plan as sp

_MONEY = re.compile(r"\$?\d[\d,]*(?:\.\d+)?")


def _amounts(text: str):
    """Every dollar figure the text states, as Decimals."""
    out = set()
    for match in _MONEY.finditer(str(text or "")):
        try:
            out.add(Decimal(match.group(0).replace(",", "").replace("$", "")))
        except (InvalidOperation, ValueError):
            continue
    return out


@dataclass
class Stage:
    """One state-machine stage and its outcome."""
    name: str
    ok: bool
    detail: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseResult:
    """The result of one case run."""
    status: str  # "ok" | "review"
    stages: List[Stage] = field(default_factory=list)
    plan: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    review: Optional[str] = None
    diagnostics: List[str] = field(default_factory=list)
    unused_amounts: List[Decimal] = field(default_factory=list)


def _journal_lines(lines, chart):
    """`statement_detect.journalize` returns (account, side, amount) tuples; convert to entry lines."""
    out = []
    by_code = {a["code"] for a in chart} if chart else set()
    for line in lines:
        acct, side, amount = line
        # A template may name a chart label; map it to its code where possible.
        code = None
        if acct in by_code:
            code = acct
        else:
            for a in (chart or []):
                if a.get("name") == acct or a.get("line") == acct:
                    code = a["code"]
                    break
        if code is None:
            code = acct
        entry = {"account": code}
        if side == "Dr":
            entry["debit"] = str(amount)
        else:
            entry["credit"] = str(amount)
        out.append(entry)
    return out


def solve_case(text: str, chart: Optional[List[Dict[str, Any]]] = None,
               adjustments: Optional[List[Dict[str, Any]]] = None,
               period: Optional[Dict[str, str]] = None,
               currency: str = "USD", framework: str = "US_GAAP") -> CaseResult:
    """Run one case problem through the full state machine.

    Returns a `CaseResult` with the stage trace; `result` is set only when every stage
    passed, and `review` names the first stage that refused.
    """
    chart = chart or sp.DEFAULT_CHART
    period = period or {"start": "2026-01-01", "end": "2026-12-31"}
    stages: List[Stage] = []

    # INGEST
    if not isinstance(text, str) or not text.strip():
        return CaseResult("review", [Stage("INGEST", False, "empty problem text",
                                           {"expected": "a non-empty string"})],
                          review="empty problem text")
    stages.append(Stage("INGEST", True, f"{len(text)} characters"))

    # PARSE
    try:
        claims = sd.parse_claims(text)
    except Exception as e:
        return CaseResult("review", stages + [Stage("PARSE", False, str(e))],
                          review="could not split the problem into claims")
    stages.append(Stage("PARSE", True, f"{len(claims)} claim(s)",
                        {"claims": [getattr(c, "__dict__", str(c)) for c in claims[:10]]}))

    # DETECT
    try:
        matches = sd.detect(text)
    except Exception as e:
        return CaseResult("review", stages + [Stage("DETECT", False, str(e))],
                          review="detector layer refused the text")
    journalizable = [m for m in matches if sd.journalizable(m)]
    if not journalizable:
        return CaseResult("review",
                          stages + [Stage("DETECT", False,
                                          "no specific detector matched any transaction claim",
                                          {"expected": "a transaction with a detector at specificity >= 50",
                                           "matches": len(matches)})],
                          review="no transaction could be journalized from this text")
    stages.append(Stage("DETECT", True, f"{len(journalizable)} journalizable match(es)",
                        {"detectors": [m.detector_id for m in journalizable]}))

    # RESOLVE
    try:
        policies = sd.infer_policies(text)
        conflicts = sd.policy_conflicts(text)
    except Exception as e:
        return CaseResult("review", stages + [Stage("RESOLVE", False, str(e))],
                          review="policy resolution failed")
    if conflicts:
        return CaseResult("review",
                          stages + [Stage("RESOLVE", False, "contradictory policy claims",
                                          {"conflicts": conflicts})],
                          review="the problem states two contradictory policies")
    stages.append(Stage("RESOLVE", True, f"{len(policies)} policy claim(s)",
                        {"policies": policies}))

    # JOURNALIZE
    entries = []
    chart_codes = {a["code"]: a for a in chart}  # journalize checks `acct in chart`
    for m in journalizable:
        try:
            lines = sd.journalize(m.detector_id, m.slots, chart_codes)
        except sd.DetectError as e:
            return CaseResult("review",
                              stages + [Stage("JOURNALIZE", False, str(e),
                                              {"detector": m.detector_id})],
                              review=f"template {m.detector_id!r} refused its slots")
        entries.append({"date": period["end"], "description": m.detector_id,
                        "lines": _journal_lines(lines, chart)})
    stages.append(Stage("JOURNALIZE", True, f"{len(entries)} entry(ies)"))

    # A statement figure that no entry uses is a transaction the detector layer did not
    # recognise.  Name it: a case that posts 30,000 of an 80,000 narrative is incomplete, and
    # the caller may prefer the model reader when one is configured.
    used = set()
    for m in journalizable:
        for value in (m.slots or {}).values():
            if isinstance(value, Decimal):
                used.add(value)
    unused = sorted(_amounts(text) - used)

    # POST -> ADJUST -> PROJECT -> VALIDATE, all inside statement_plan.build
    plan = {
        "period": period, "currency": currency, "framework": framework, "places": 2,
        "policy": policies or {"rounding": "half_up"},
        "prior_closing": {}, "opening": [], "entries": entries,
        "adjustments": adjustments or [], "schedules": [],
        "chart": chart, "problem_type": "transactions",
    }
    try:
        result = sp.build(plan)
    except sp.PlanError as e:
        return CaseResult("review",
                          stages + [Stage("VALIDATE", False, str(e),
                                          {"expected": "every articulation identity passes"})],
                          review="the ledger did not satisfy the articulation gates: " + str(e)[:400],
                          diagnostics=[str(e)], unused_amounts=unused)
    stages.append(Stage("POST", True, "journal posted to the trial balance"))
    stages.append(Stage("ADJUST", True, f"{len(adjustments or [])} adjustment(s) applied"))
    stages.append(Stage("PROJECT", True, "statements projected from the trial balance"))
    stages.append(Stage("VALIDATE", True, "articulation gates passed"))
    return CaseResult("ok", stages, plan, result, None, unused_amounts=unused)


__all__ = ["Stage", "CaseResult", "solve_case"]
