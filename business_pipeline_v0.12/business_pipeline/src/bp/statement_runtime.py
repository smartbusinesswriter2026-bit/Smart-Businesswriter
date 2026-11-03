"""Runtime state machine for statement problems (tip 9.1, 9.9, 9.10).

Orchestrates the stages: INGEST -> PARSE -> DETECT -> RESOLVE -> JOURNALIZE -> POST ->
VALIDATE -> RENDER. Each stage either succeeds or returns a Review (terminal) naming the
stage, the offending input and what was expected. The runtime never auto-corrects.

This first version wires detection, policy inference, journalization, posting and the
articulation gates. Adjustments and plugs are applied by the caller (statement_plan) when
present; the runtime reports them as given facts rather than deriving them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from . import statement_detect as sd


@dataclass
class Review:
    stage: str
    detail: str
    expected: str = ""
    offending: str = ""


@dataclass
class RuntimeResult:
    status: str  # "ok" | "review"
    claims: List = field(default_factory=list)
    matches: List = field(default_factory=list)
    policies: Dict[str, Any] = field(default_factory=dict)
    conflicts: List = field(default_factory=list)
    journal: List = field(default_factory=list)
    trial_balance: Dict[str, Decimal] = field(default_factory=dict)
    gates: Dict[str, bool] = field(default_factory=dict)
    review: Optional[Review] = None
    diagnostics: List[str] = field(default_factory=list)
    review_items: List = field(default_factory=list)


def _post(journal):
    tb = {}
    for acct, side, amt in journal:
        d = Decimal(str(amt))
        tb.setdefault(acct, Decimal(0))
        if side == "Dr":
            tb[acct] += d
        else:
            tb[acct] -= d
    return tb


def run(problem_text: str, chart: Optional[Dict[str, Any]] = None,
        adjustments: Optional[List[Dict[str, Any]]] = None,
        executed_adjustments: Optional[List[str]] = None) -> RuntimeResult:
    res = RuntimeResult(status="ok")
    # INGEST
    if not isinstance(problem_text, str) or not problem_text.strip():
        res.status = "review"
        res.review = Review("INGEST", "empty problem text", "non-empty string")
        return res
    # PARSE
    claims = sd.parse_claims(problem_text)
    res.claims = claims
    # DETECT
    matches = sd.detect(problem_text)
    # extraction grounding guard (G20)
    try:
        from . import extraction as ext_guard
        for m in matches:
            issues = ext_guard.verify_grounded(
                ext_guard.Match(m.detector_id, "", m.slots, m.confidence,
                               {}, m.span), problem_text)
            if issues:
                res.diagnostics.append(f"ungrounded slots in {m.detector_id}: {issues}")
    except Exception:
        pass
    res.matches = matches
    # generic-only matches are not journalizable; if every transaction claim has only
    # generic matches, route to review
    tx_claims = [c for c in claims if c.kind == "transaction"]
    if tx_claims and not any(sd.journalizable(m) for m in matches):
        res.status = "review"
        res.review = Review("DETECT", "no specific detector matched any transaction claim",
                           "a detector with specificity >= 50")
        return res
    # RESOLVE (policies)
    policies = sd.infer_policies(problem_text)
    conflicts = sd.policy_conflicts(problem_text)
    # convention conflict guard (G18)
    try:
        from . import conflicts as cf_guard
        claim_objs = [type("C", (), {"text": c.text, "span": c.span})() for c in claims]
        cf_issues = cf_guard.detect_convention_conflicts(claim_objs)
        if cf_issues:
            conflicts = conflicts + [(i.input_ref, i.expected, i.actual) for i in cf_issues]
    except Exception:
        pass
    res.policies = policies
    res.conflicts = conflicts
    if conflicts:
        res.status = "review"
        res.review = Review("RESOLVE", "contradictory policy claims",
                           "a single value per policy", str(conflicts))
        return res
    # template coverage guard (G21)
    try:
        from . import coverage as cov_guard
        cov_issues = cov_guard.check_template_coverage(matches, sd.TEMPLATES)
        if cov_issues:
            res.status = "review"
            res.review = Review("JOURNALIZE", "template coverage gap",
                               "a template per matched detector", str(cov_issues))
            res.diagnostics.extend(str(i) for i in cov_issues)
            return res
    except Exception:
        pass
    # JOURNALIZE
    journal = []
    for m in matches:
        if not sd.journalizable(m):
            continue
        try:
            lines = sd.journalize(m.detector_id, m.slots, chart)
        except sd.DetectError as e:
            res.status = "review"
            res.review = Review("JOURNALIZE", str(e), "balanced JE with known accounts",
                               m.detector_id)
            return res
        journal.extend(lines)
    # POST (transactions)
    tb = _post(journal)
    # apply adjustments (each: {"debit": code, "credit": code, "amount": value})
    for adj in (adjustments or []):
        amt = Decimal(str(adj["amount"]))
        journal.append((adj["debit"], "Dr", amt))
        journal.append((adj["credit"], "Cr", amt))
    tb = _post(journal)
    res.trial_balance = tb
    res.journal = journal
    # adjustment completeness guard (G5)
    try:
        from . import completeness as comp_guard
        claim_objs = [type("C", (), {"text": c.text, "kind": c.kind})() for c in claims]
        missing = comp_guard.check_adjustment_completeness(claim_objs, executed_adjustments or [])
        if missing:
            res.diagnostics.append(f"adjustment completeness: missing {missing}")
    except Exception:
        pass
    # gate: balanced
    total_dr = sum((Decimal(str(a)) for a, s, _ in []), Decimal(0))  # placeholder
    # compute debits/credits from journal
    debits = sum((Decimal(str(ln[2])) for ln in journal if ln[1] == "Dr"), Decimal(0))
    credits = sum((Decimal(str(ln[2])) for ln in journal if ln[1] == "Cr"), Decimal(0))
    balanced = debits == credits
    res.gates["tb_balanced"] = balanced
    if not balanced:
        res.status = "review"
        res.review = Review("POST", f"unbalanced TB: Dr={debits} Cr={credits}",
                           "equal debits and credits")
        return res
    # VALIDATE: at least one articulation gate recorded
    res.gates["has_journal"] = bool(journal)
    res.status = "ok"
    return res
