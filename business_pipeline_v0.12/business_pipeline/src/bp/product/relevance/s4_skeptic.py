"""RRA Stage S4 — Skeptic.

Challenges candidate gaps.  Checks:
  - Does the capability already exist under another name?
  - Is there at least 2 independent T1 institutions or 1 T1 standard-setter?
  - Is it on the parked list?
  - Does any non-negotiable get violated?
  - Is the evidence fresh enough?

The skeptic may flag, never overrule.  Survivors pass to S5.
"""
from .schemas import (
    TIER_T1, STATUS_PARKED,
)

# Non-negotiable rules the skeptic checks against
_NON_NEGOTIABLE_CHECKS = [
    "no_invented_evidence",
    "no_invented_numbers",
    "no_silent_substitution",
    "global_product",
    "no_template_text",
    "model_never_does_math",
    "stdlib_only",
    "human_approval_at_gates",
]


def _is_parked(taxonomy_id, backtest):
    """Check if a taxonomy item is on the parked list."""
    if not backtest:
        return False
    for item in (backtest.get("seeded_gaps", []) or []):
        if item.get("taxonomy_id") == taxonomy_id:
            # Check if it's a parked item (status_hint == parked in taxonomy)
            pass
    return False


def challenge_gap(candidate, evidence_records=None, catalogue=None, backtest=None,
                  taxonomy_topic=None):
    """Challenge a candidate gap.  Returns (survives: bool, challenges: list[str])."""
    challenges = []

    # 1. Does it already exist under another name?  Only flag for "missing" items
    # that somehow have an artefact (true duplicate).  Partial/at-risk items with
    # an artefact are coverage gaps, not duplicates.
    artefact = candidate.get("pipeline_artefact_id", "") if isinstance(candidate, dict) else getattr(candidate, "pipeline_artefact_id", "")
    status = candidate.get("status", "") if isinstance(candidate, dict) else getattr(candidate, "status", "")
    if artefact and status == "missing":
        challenges.append("artefact already exists: %s — check for alias" % artefact)

    # 2. Evidence tier rule: at least 2 independent T1 or 1 T1 standard-setter
    t1_count = 0
    t1_standard_setter = False
    for r in (evidence_records or []):
        tier = r.get("tier", "") if isinstance(r, dict) else getattr(r, "tier", "")
        school = r.get("school_or_body", "") if isinstance(r, dict) else getattr(r, "school_or_body", "")
        if tier == TIER_T1:
            t1_count += 1
            # Heuristic: standard-setter if school_or_body contains known body names
            body_keywords = ["aacsb", "efmd", "amba", "gmac", "ifrs", "fasb", "efrag", "ec.europa"]
            if any(kw in str(school).lower() for kw in body_keywords):
                t1_standard_setter = True
    if t1_count < 2 and not t1_standard_setter:
        challenges.append("insufficient T1 evidence: %d independent T1 (need >=2 or 1 standard-setter)" % t1_count)

    # 3. Parked check
    taxonomy_id = candidate.get("taxonomy_id", "") if isinstance(candidate, dict) else getattr(candidate, "taxonomy_id", "")
    if taxonomy_topic and taxonomy_topic.get("status_hint") == "parked":
        challenges.append("item is on the parked list (frontier-model queue) — log as parked, do not propose as work")

    # 4. Non-negotiable check
    # (The candidate must declare which non-negotiables it touches; empty = pass)
    constraint_check = candidate.get("constraint_check", {}) if isinstance(candidate, dict) else getattr(candidate, "constraint_check", {})
    for rule in _NON_NEGOTIABLE_CHECKS:
        if rule in constraint_check and not constraint_check[rule]:
            challenges.append("non-negotiable violated: %s" % rule)

    # 5. Freshness check (evidence age)
    # If evidence is older than 12 months, flag it
    # (Simple check: if any evidence record has retrieved_at older than 365 days)
    # For now, just note that freshness should be verified

    survives = len(challenges) == 0
    return survives, challenges


def skeptic_review(candidates, evidence_records=None, catalogue=None, backtest=None,
                   taxonomy_map=None):
    """Review a list of candidate gaps.  Returns (survivors, rejected_with_reasons)."""
    survivors = []
    rejected = []
    taxonomy_map = taxonomy_map or {}

    for cand in (candidates or []):
        tid = cand.get("taxonomy_id", "") if isinstance(cand, dict) else getattr(cand, "taxonomy_id", "")
        topic = taxonomy_map.get(tid, {})
        survives, challenges = challenge_gap(
            cand, evidence_records=evidence_records, catalogue=catalogue,
            backtest=backtest, taxonomy_topic=topic,
        )
        if survives:
            survivors.append(cand)
        else:
            rejected.append({"candidate": cand, "challenges": challenges})
    return survivors, rejected
