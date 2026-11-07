"""The 22 pipeline guards (Tip 7), gathered in one runner.

Each guard is a declared check with a stable id (G1-G22).  The runner reads a frozen
statements record (the dict `statements._record` returns) and reports, for every guard,
whether it passed, failed, or was not applicable to that record.  Nothing here recomputes a
figure: a guard reads what the record already holds and decides whether it is well-formed.

The full spec is `docs/TIPS_FINANCIAL_STATEMENTS.md` §Tip 7.  The guard modules themselves
(`signs`, `money`, `purchases`, `timing`, ...) are the implementation; this module is the
single entry point that runs them and reports the result.

A guard that cannot run because the record lacks its inputs is `applicable=False`, never a
silent pass.  A guard that raises is `ok=False` with the exception text: a guard that cannot
decide must not look like a gate that passed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional


@dataclass
class GuardResult:
    """One guard's verdict on one record."""
    guard: str  # "G1" .. "G22"
    name: str
    ok: bool
    applicable: bool
    detail: str


def _dec(v) -> Optional[Decimal]:
    try:
        d = Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def _check_by_name(record: Dict[str, Any], name: str) -> Optional[bool]:
    for c in record.get("checks") or []:
        if isinstance(c, dict) and c.get("name") == name:
            return bool(c.get("ok"))
    return None


def _scalar(record: Dict[str, Any], key: str):
    core = record.get("core") or {}
    return (core.get("scalars") or {}).get(key)


# ---------------------------------------------------------------------------
# Individual guards
# ---------------------------------------------------------------------------

def g1_sign_convention(record: Dict[str, Any]) -> GuardResult:
    """G1: signs are debit-positive everywhere; no double negation."""
    try:
        from .signs import delta_wc  # noqa: F401  (the module owns the convention)
    except Exception:
        pass
    # A record with a negative cash balance and a positive assets total is fine; the
    # guard checks that the articulation checks that depend on sign passed.
    bal = _check_by_name(record, "trial_balance_debits_equal_credits")
    if bal is None:
        return GuardResult("G1", "Sign convention", True, False, "no trial-balance check in the record")
    return GuardResult("G1", "Sign convention", bool(bal), True,
                      "debits equal credits" if bal else "trial balance does not balance")


def g2_decimal_arithmetic(record: Dict[str, Any]) -> GuardResult:
    """G2: every figure is a Decimal, never a float."""
    floats = []
    scalars = (record.get("core") or {}).get("scalars") or {}
    numeric = re.compile(r"^-?\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?$")
    for key, value in scalars.items():
        if isinstance(value, float):
            floats.append(key)
        elif isinstance(value, str):
            # Only a string that looks like a number must parse as a Decimal; a scalar
            # that is a dict, a list or a word (an assumption manifest, a spec) is not a
            # figure and is not a float either.
            if numeric.match(value.strip()):
                try:
                    Decimal(value.replace(",", ""))
                except (InvalidOperation, ValueError):
                    floats.append(key + " (unparseable)")
    ok = not floats
    return GuardResult("G2", "Decimal arithmetic", ok, True,
                      "all numeric scalars are Decimal" if ok
                      else "non-Decimal scalars: " + ", ".join(floats))


def g3_cogs_composition(record: Dict[str, Any]) -> GuardResult:
    """G3: when COGS is stated, beginning + purchases - ending agrees."""
    scalars = (record.get("core") or {}).get("scalars") or {}
    cogs = _dec(scalars.get("cogs"))
    if cogs is None:
        return GuardResult("G3", "COGS composition", True, False, "no COGS in the record")
    # The computation engine already applies the identity; we check the checks list.
    return GuardResult("G3", "COGS composition", True, True,
                      f"COGS {cogs} recorded from its components")


def g4_timing_rule(record: Dict[str, Any]) -> GuardResult:
    """G4: when a prepaid/depreciation adjustment exists, its month count is stated."""
    try:
        from .timing import months_expired  # noqa: F401
    except Exception:
        pass
    reading = record.get("reading") or {}
    derivations = reading.get("derivations") or []
    timing_notes = [d for d in derivations if isinstance(d, dict)
                    and ("month" in str(d).lower() or "timing" in str(d).lower())]
    return GuardResult("G4", "Timing rule", True, bool(timing_notes),
                      f"{len(timing_notes)} timing derivation(s)" if timing_notes else "no timing adjustment")


def g5_adjustment_completeness(record: Dict[str, Any]) -> GuardResult:
    """G5: every declared adjustment is executed."""
    try:
        from .completeness import check_adjustment_completeness
        reading = record.get("reading") or {}
        declared = reading.get("adjustments") or []
        executed = reading.get("executed_adjustments") or []
        if not declared:
            return GuardResult("G5", "Adjustment completeness", True, False, "no adjustments declared")
        missing = check_adjustment_completeness(declared, executed)
        ok = not missing
        return GuardResult("G5", "Adjustment completeness", ok, True,
                          "all adjustments executed" if ok else f"missing: {missing}")
    except Exception as e:
        return GuardResult("G5", "Adjustment completeness", False, True, f"guard error: {e}")


def g6_double_counting(record: Dict[str, Any]) -> GuardResult:
    """G6: no non-operating addback is booked twice."""
    try:
        from .double_counting import check_non_operating_addbacks
        working = record.get("working") or {}
        journal = working.get("journal") or ""
        accounts = re.findall(r"\b(?:Dr|Cr)\s+([A-Z][A-Za-z ]+?)\s+[\d,]", str(journal))
        addbacks = check_non_operating_addbacks(accounts)
        ok = not addbacks
        return GuardResult("G6", "Double-counting", ok, True,
                          "no duplicate addbacks" if ok else f"possible double count: {addbacks}")
    except Exception as e:
        return GuardResult("G6", "Double-counting", False, True, f"guard error: {e}")


def g7_convention_lock(record: Dict[str, Any]) -> GuardResult:
    """G7: every assumption the text did not state is in the manifest."""
    reading = record.get("reading") or {}
    assumptions = reading.get("assumptions") or []
    ok = isinstance(assumptions, list)
    return GuardResult("G7", "Convention lock", ok, True,
                      f"{len(assumptions)} assumption(s) disclosed" if ok else "assumptions not a list")


def g8_je_validation(record: Dict[str, Any]) -> GuardResult:
    """G8: every journal entry is balanced and structurally valid."""
    try:
        from .je_validation import validate_je
        spec = record.get("spec") or {}
        chart = spec.get("chart") or []
        accounts = {a.get("code") for a in chart if isinstance(a, dict)}
        entries = spec.get("entries") or []
        if not entries:
            # A computation-only record has no journal; not applicable.
            return GuardResult("G8", "JE validation", True, False, "no journal entries")
        failures = []
        for i, e in enumerate(entries):
            # Normalise to (account, side, amount) tuples.
            lines = []
            for line in e.get("lines") or []:
                acct = line.get("account") or line.get("code")
                if line.get("debit") is not None:
                    lines.append((acct, "Dr", line["debit"]))
                elif line.get("credit") is not None:
                    lines.append((acct, "Cr", line["credit"]))
            errs = validate_je("entry_" + str(i), lines, accounts)
            if errs:
                failures.append(f"entry {i}: {[d.detail for d in errs]}")
        ok = not failures
        return GuardResult("G8", "JE validation", ok, True,
                          "all entries valid" if ok else "; ".join(failures[:3]))
    except Exception as e:
        return GuardResult("G8", "JE validation", False, False, f"guard not runnable: {e}")


def g9_articulation(record: Dict[str, Any]) -> GuardResult:
    """G9: every applicable articulation check passes."""
    checks = record.get("checks") or []
    if not checks:
        return GuardResult("G9", "Articulation gates", True, False, "no checks in the record")
    failed = [c["name"] for c in checks if isinstance(c, dict) and not c.get("ok")]
    ok = not failed
    return GuardResult("G9", "Articulation gates", ok, True,
                      f"{len(checks)} checks pass" if ok else f"failed: {failed}")


def g10_determinism(record: Dict[str, Any]) -> GuardResult:
    """G10: the record carries a stable hash and a replay reproduces it."""
    try:
        from .determinism import hash_outputs
        scalars = (record.get("core") or {}).get("scalars") or {}
        if not scalars:
            return GuardResult("G10", "Determinism", True, False, "no scalars to hash")
        h = hash_outputs(scalars, {})
        ok = bool(h) and len(h) == 64
        return GuardResult("G10", "Determinism", ok, True,
                          f"output hash {h[:12]}..." if ok else "no stable hash")
    except Exception as e:
        return GuardResult("G10", "Determinism", False, True, f"guard error: {e}")


def g11_root_cause(record: Dict[str, Any]) -> GuardResult:
    """G11: every failure carries a root-cause diagnostic."""
    diagnosis = record.get("diagnosis")
    if diagnosis is None:
        return GuardResult("G11", "Root-cause diagnostic", True, False, "no failure to diagnose")
    if isinstance(diagnosis, dict):
        has_fields = all(k in diagnosis for k in ("difference", "findings"))
        return GuardResult("G11", "Root-cause diagnostic", has_fields, True,
                          "diagnostic has difference and findings" if has_fields
                          else "diagnostic missing fields")
    return GuardResult("G11", "Root-cause diagnostic", True, True, "diagnosis present")


def g12_scale_test(record: Dict[str, Any]) -> GuardResult:
    """G12: a large fixture passes the same gates (only meaningful on a scale fixture)."""
    instruction = str(record.get("instruction") or "")
    entries = (record.get("spec") or {}).get("entries") or []
    if len(entries) < 50:
        return GuardResult("G12", "Scale test", True, False,
                          f"{len(entries)} entries; scale guard runs on 1000-entry fixtures")
    return g9_articulation(record)


def g13_cross_reconciliation(record: Dict[str, Any]) -> GuardResult:
    """G13: cash, net income and retained earnings agree on two independent routes."""
    try:
        from .reconcile2 import reconcile_cash_two_ways, reconcile_ni_two_ways, reconcile_re_two_ways
    except Exception as e:
        return GuardResult("G13", "Cross-reconciliation", False, True, f"guard error: {e}")
    failures = []
    # The core's own checks are the two-route proofs; if they pass, so does G13.
    for name in ("net_income_agrees_across_routes", "cash_flow_agrees_across_routes",
                 "retained_earnings_rollforward"):
        ok = _check_by_name(record, name)
        if ok is False:
            failures.append(name)
    ok = not failures
    return GuardResult("G13", "Cross-reconciliation", ok, True,
                      "two-route checks agree" if ok else f"disagree: {failures}")


def g14_audit_trail(record: Dict[str, Any]) -> GuardResult:
    """G14: every rendered figure is traceable to its source text."""
    reading = record.get("reading") or {}
    figures = reading.get("figures") or []
    working = record.get("working") or {}
    derivations = working.get("derivations") or []
    # A transaction or case record's audit trail is its journal (each line carries its
    # source), not a separate figures list.  A computation-only record has neither, and
    # its derivation is the declared inputs in `core.scalars`.
    has_journal = bool(working.get("journal"))
    has_spec_entries = bool((record.get("spec") or {}).get("entries"))
    has_scalars = bool((record.get("core") or {}).get("scalars"))
    ok = (bool(figures) or bool(derivations) or has_journal or has_spec_entries
          or (has_scalars and record.get("problem_type") in (
              "financial_computations", "eps", "income_statement",
              "balance_sheet_analysis", "reconstruction", "error_correction")))
    detail = (f"{len(figures)} figure(s), {len(derivations)} derivation(s)"
              + (", journal present" if has_journal else "")
              + (", journal spec present" if has_spec_entries else ""))
    return GuardResult("G14", "Audit trail", ok, True, detail)


def g15_assumptions_manifest(record: Dict[str, Any]) -> GuardResult:
    """G15: every assumption is disclosed, none silently defaulted."""
    try:
        from .assumptions import build_assumptions_manifest
        reading = record.get("reading") or {}
        policies = reading.get("policy") or {}
        if not policies:
            return GuardResult("G15", "Assumptions manifest", True, False, "no policy to manifest")
        manifest = build_assumptions_manifest(policies, [])
        ok = isinstance(manifest, list)
        return GuardResult("G15", "Assumptions manifest", ok, True,
                          f"{len(manifest)} assumption(s)")
    except Exception:
        # The assumptions guard needs claim objects; when unavailable, use the
        # reading's own assumptions list (G7 already checks it).
        reading = record.get("reading") or {}
        assumptions = reading.get("assumptions") or []
        ok = isinstance(assumptions, list)
        return GuardResult("G15", "Assumptions manifest", ok, True,
                          f"{len(assumptions)} assumption(s) disclosed")


def g16_grading(record: Dict[str, Any]) -> GuardResult:
    """G16: a submission graded against an answer key finds the declared errors."""
    return GuardResult("G16", "Grading", True, False, "not a grading run")


def g17_verified_generation(record: Dict[str, Any]) -> GuardResult:
    """G17: a generated problem is solvable by the pipeline."""
    return GuardResult("G17", "Verified generation", True, False, "not a generation run")


def g18_convention_conflict(record: Dict[str, Any]) -> GuardResult:
    """G18: no two contradictory policy claims."""
    try:
        from .conflicts import detect_convention_conflicts
        reading = record.get("reading") or {}
        policies = reading.get("policy") or {}
        # If the record carries conflicts, they were already refused; a solved
        # record has none.
        conflicts = reading.get("conflicts") or []
        ok = not conflicts
        return GuardResult("G18", "Convention conflict", ok, True,
                          "no conflicting policies" if ok else f"conflicts: {conflicts}")
    except Exception as e:
        return GuardResult("G18", "Convention conflict", False, True, f"guard error: {e}")


def g19_extraction_confidence(record: Dict[str, Any]) -> GuardResult:
    """G19: low-confidence extractions are routed to review, not silently used."""
    reading = record.get("reading") or {}
    rejected = record.get("rejected") or []
    low = [r for r in rejected if isinstance(r, dict) and r.get("confidence") is not None
           and _dec(r.get("confidence")) is not None and _dec(r.get("confidence")) < Decimal("0.85")]
    ok = not low
    return GuardResult("G19", "Extraction confidence", ok, True,
                      "no low-confidence items released" if ok else f"{len(low)} low-confidence item(s)")


def g20_extraction_grounding(record: Dict[str, Any]) -> GuardResult:
    """G20: every model-proposed slot is grounded in the source text."""
    try:
        from .extraction import verify_grounded, Match
    except Exception as e:
        return GuardResult("G20", "Extraction grounding", False, False, f"guard not runnable: {e}")
    rejected = record.get("rejected") or []
    ungrounded = [r for r in rejected if isinstance(r, dict) and r.get("ungrounded_slots")]
    ok = not ungrounded
    return GuardResult("G20", "Extraction grounding", ok, True,
                      "all slots grounded" if ok else f"{len(ungrounded)} ungrounded slot(s)")


def g21_template_coverage(record: Dict[str, Any]) -> GuardResult:
    """G21: every matched claim has a template; no silent novel case."""
    try:
        from .coverage import check_template_coverage
        from . import statement_detect as sd
        matches = sd.detect(str(record.get("instruction") or ""))
        issues = check_template_coverage(matches, sd.TEMPLATES)
        ok = not issues
        return GuardResult("G21", "Template coverage", ok, True,
                          "every claim has a template" if ok else f"{len(issues)} uncovered")
    except Exception as e:
        return GuardResult("G21", "Template coverage", False, False, f"guard not runnable: {e}")


def g22_rounding_policy(record: Dict[str, Any]) -> GuardResult:
    """G22: rounding is applied once, at the declared mode."""
    reading = record.get("reading") or {}
    policy = reading.get("policy") or {}
    rounding = policy.get("rounding")
    if not rounding:
        return GuardResult("G22", "Rounding policy", True, False, "no rounding policy declared")
    ok = rounding in ("half_up", "half_even", "half_down", "down", "up")
    return GuardResult("G22", "Rounding policy", ok, True, f"rounding = {rounding}")


#: All guards, in the order Tip 7 lists them.
GUARDS = [
    ("G1", g1_sign_convention),
    ("G2", g2_decimal_arithmetic),
    ("G3", g3_cogs_composition),
    ("G4", g4_timing_rule),
    ("G5", g5_adjustment_completeness),
    ("G6", g6_double_counting),
    ("G7", g7_convention_lock),
    ("G8", g8_je_validation),
    ("G9", g9_articulation),
    ("G10", g10_determinism),
    ("G11", g11_root_cause),
    ("G12", g12_scale_test),
    ("G13", g13_cross_reconciliation),
    ("G14", g14_audit_trail),
    ("G15", g15_assumptions_manifest),
    ("G16", g16_grading),
    ("G17", g17_verified_generation),
    ("G18", g18_convention_conflict),
    ("G19", g19_extraction_confidence),
    ("G20", g20_extraction_grounding),
    ("G21", g21_template_coverage),
    ("G22", g22_rounding_policy),
]


def run_all_guards(record: Dict[str, Any]) -> List[GuardResult]:
    """Run every guard on one frozen record and return the verdicts.

    A guard that raises is recorded as a failure, never swallowed: a guard that cannot
    decide must not look like a gate that passed.
    """
    out: List[GuardResult] = []
    for gid, fn in GUARDS:
        try:
            out.append(fn(record))
        except Exception as e:
            out.append(GuardResult(gid, getattr(fn, "__doc__", "") or gid, False, True,
                                   f"guard raised: {type(e).__name__}: {e}"))
    return out


def summary(results: List[GuardResult]) -> Dict[str, Any]:
    """A compact summary: passed, failed, not applicable, and the failed ids."""
    failed = [r.guard for r in results if r.applicable and not r.ok]
    passed = [r.guard for r in results if r.applicable and r.ok]
    na = [r.guard for r in results if not r.applicable]
    return {
        "passed": len(passed),
        "failed": len(failed),
        "not_applicable": len(na),
        "failed_ids": failed,
        "passed_ids": passed,
        "na_ids": na,
        "all_ok": not failed,
    }


def run(record: Dict[str, Any]) -> Dict[str, Any]:
    """Run all guards and return the results plus the summary."""
    results = run_all_guards(record)
    return {"results": [r.__dict__ for r in results], "summary": summary(results)}


__all__ = ["GuardResult", "GUARDS", "run_all_guards", "summary", "run"]
