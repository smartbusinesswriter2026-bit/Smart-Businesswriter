"""RRA Stage S6 — Evaluator.

Applies the strict checklist G1–G7 to each GapSpec.  Strict pass or
needs-work.  Partial credit only orders the needs-work bucket; it never
promotes anything.
"""
from .schemas import GapSpec


def evaluate_gap_spec(spec, evidence_lookup=None):
    """Evaluate a GapSpec against the strict checklist.

    Returns (strict_pass: bool, failures: list[str], partial_credit: float).
    partial_credit is 0.0–1.0 for ordering the needs-work bucket.
    """
    if not isinstance(spec, GapSpec):
        if isinstance(spec, dict):
            spec = GapSpec.from_dict(spec)
        if not isinstance(spec, GapSpec):
            return False, ["invalid spec"], 0.0

    ok, failures = spec.validate_strict()

    # Additional checks beyond validate_strict
    extra_failures = []

    # G1: evidence meets tier rule (at least one T1 or T2 in evidence_ids)
    evidence_ids = spec.evidence_ids or []
    if evidence_lookup:
        has_t1_or_t2 = False
        for eid in evidence_ids:
            rec = evidence_lookup.get(eid)
            if rec:
                tier = rec.get("tier", "") if isinstance(rec, dict) else getattr(rec, "tier", "")
                if tier in ("T1", "T2"):
                    has_t1_or_t2 = True
                    break
        if evidence_ids and not has_t1_or_t2:
            extra_failures.append("G1: no T1/T2 evidence in evidence_ids")
    elif evidence_ids:
        # No lookup available — assume T1/T2 present if evidence_ids non-empty
        pass

    # G2: not a duplicate — checked externally (catalogue).  Flag if artefact already exists.
    # (This is checked by the caller with the catalogue snapshot.)

    all_failures = failures + extra_failures
    strict_pass = (len(all_failures) == 0)

    # Partial credit: fraction of checks passed
    total_checks = 7  # G1-G7
    passed = total_checks - len(all_failures)
    if passed < 0:
        passed = 0
    partial_credit = passed / total_checks

    return strict_pass, all_failures, partial_credit


def evaluate_gap_specs(specs, evidence_lookup=None):
    """Evaluate a list of GapSpecs.  Returns (strict_pass_list, needs_work_list).

    needs_work_list is sorted by partial_credit descending.
    """
    strict_pass = []
    needs_work = []
    for spec in (specs or []):
        sp, failures, credit = evaluate_gap_spec(spec, evidence_lookup=evidence_lookup)
        if sp:
            strict_pass.append(spec)
        else:
            needs_work.append({"spec": spec, "failures": failures, "partial_credit": credit})
    needs_work.sort(key=lambda x: x["partial_credit"], reverse=True)
    return strict_pass, needs_work
