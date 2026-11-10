"""RRA Runner — orchestrates stages S0–S7.

Runs the full pipeline: scope → discover → scout → read → map → skeptic →
design → evaluate → gate.  Produces a run record, evidence records, coverage
rows, gap specs, and watch items.  Strict pass only (G1–G7) for the owner
queue.

The model may be used in three places, always as a proposal:
  S1b discovery — a better search query (never a URL the search did not return)
  S2  reading   — the passage that matters (checked verbatim by code)
  S5  design    — the spec fields (checked field by field by code)

With no model configured the pipeline still runs: it searches, it reads the
opening words of each page, and it uses the deterministic defaults.
"""
import json
from datetime import datetime, timezone

from . import storage
from . import config as _config
from .schemas import RunRecord, make_run_id
from .s0_scope import (build_run_plan, create_run_record, load_school_list,
                       load_allowlist, load_taxonomy, load_backtest)
from .s1_scout import scout_urls, scout_school_pages
from .s2_reader import snapshots_to_evidence
from .s3_mapper import map_coverage
from .s4_skeptic import skeptic_review
from .s5_designer import design_gap_specs
from .s6_evaluator import evaluate_gap_specs
from .s7_gate import record_decision, pending_decisions


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def run_sweep(url_list=None, school_list=None, allowlist=None, taxonomy=None,
              backtest=None, page_budget=None, token_budget=None,
              topic_list=None, use_model=True, discover=True, delay=0.5,
              progress=None):
    """Run one full RRA sweep.  Returns a dict with run_id, evidence, coverage,
    gaps (strict pass), needs_work, watchitems, and the run record.

    `url_list`    — explicit URLs.  When given, they are the only URLs read.
    `discover`    — when True and no URL list is given, the pipeline searches
                    for the pages itself (S1b) before scouting.
    `use_model`   — the model may draft; it never decides.
    `progress`    — optional callable(name, count) for a long run.
    """
    # S0 — Scope
    plan, err = build_run_plan(
        school_list=school_list, topic_list=topic_list,
        page_budget=page_budget, token_budget=token_budget,
    )
    if err:
        return {"error": err, "stage": "S0"}

    run_record = create_run_record(plan)
    storage.append_run(run_record.to_dict())

    # Load registries if not provided
    if school_list is None:
        school_list = load_school_list()
    if allowlist is None:
        allowlist = load_allowlist()
    if taxonomy is None:
        taxonomy = load_taxonomy()
    if backtest is None:
        backtest = load_backtest()

    # ── S1b — Discover ──
    discovery_notes = []
    per_school = []
    catalogue_urls = []
    if url_list is None:
        if discover:
            from . import discovery as _discovery
            # One budget for both passes: the model fallback is a proposal,
            # not a requirement, and one per school turned a three-minute
            # sweep into a twenty-minute one.  The same budget bounds the
            # **searches**, because the provider rate-limits: a sweep that
            # keeps asking gets HTTP 429 and comes back with nothing, which
            # looks like a finding and is not one.
            budget = _discovery._Budget(
                _discovery.DEFAULT_QUERY_FALLBACK_BUDGET,
                query_limit=_discovery.DEFAULT_SEARCH_BUDGET)
            # discovery reads the school list's own shape (regions + bodies).
            found, discovery_notes, per_school = _discovery.discover_urls(
                school_list or {}, allowlist=allowlist, use_model=use_model,
                progress=progress, budget=budget)
            url_list = found
            # A framework is evidenced in a course catalogue, not in a core
            # list.  Both page types are read.
            catalogue_urls, catalogue_notes, catalogue_schools = _discovery.discover_catalogues(
                school_list or {}, allowlist=allowlist, use_model=use_model,
                budget=budget)
            discovery_notes = list(discovery_notes) + list(catalogue_notes)
            for entry in catalogue_schools:
                per_school.append(entry)
            url_list = list(url_list) + list(catalogue_urls)
            # The question that works: does this school publish a page that
            # names this framework?  A generic curriculum search finds the
            # core-course list, which names subjects; only a search carrying
            # the topic's own name finds the course that teaches it.
            topic_urls, topic_notes, topic_rows = _discovery.discover_topics(
                school_list or {}, taxonomy or {}, allowlist=allowlist,
                budget=budget, max_schools=_config.max_schools() or None)
            discovery_notes = list(discovery_notes) + list(topic_notes)
            per_school.extend(topic_rows)
            url_list = list(url_list) + list(topic_urls)
        if not url_list:
            url_list = scout_school_pages(plan.get("schools", []), allowlist=allowlist)

    # ── S1 — Scout ──
    from . import render as _render
    _render.reset_budget()
    snapshots = scout_urls(url_list, allowlist=allowlist, delay=delay) if url_list else []

    # ── S2 — Read ──
    evidence_records, read_errors = snapshots_to_evidence(
        snapshots, run_id=plan["run_id"], use_model=use_model,
    )
    for rec in evidence_records:
        storage.append_evidence(rec.to_dict() if hasattr(rec, "to_dict") else rec)

    evidence_dicts = [rec.to_dict() if hasattr(rec, "to_dict") else rec
                      for rec in evidence_records]

    # ── S3 — Map ──
    coverage_rows = map_coverage(taxonomy or {}, evidence_records=evidence_dicts)
    for row in coverage_rows:
        storage.append_coverage(row.to_dict() if hasattr(row, "to_dict") else row)

    # ── The measurement's own check (R2) ──
    # The controls are what the system already has.  If too few of them were
    # seen, the measurement cannot see — and no gap may be promoted from it.
    from . import controls as _controls
    control_check = _controls.check(
        [r.to_dict() if hasattr(r, "to_dict") else r for r in coverage_rows],
        evidence_records=evidence_dicts)
    measurement_held = bool(control_check.get("passed"))

    # Identify candidate gaps: topics with status missing or partial
    candidates = []
    for row in coverage_rows:
        rd = row.to_dict() if hasattr(row, "to_dict") else row
        if rd.get("status") in ("missing", "partial", "at-risk"):
            candidates.append({
                "taxonomy_item": rd.get("taxonomy_item", ""),
                "pipeline_artefact_id": rd.get("pipeline_artefact_id", ""),
                "status": rd.get("status", ""),
                "title": rd.get("taxonomy_item", ""),
                "category": _guess_category(rd.get("taxonomy_item", "")),
                "general_capability_statement": rd.get("taxonomy_item", ""),
                "evidence_ids": rd.get("evidence_ids", []),
            })

    # ── S4 — Skeptic ──
    taxonomy_map = {}
    for topic in (taxonomy.get("topics", []) if isinstance(taxonomy, dict) else []):
        taxonomy_map[topic.get("id", "")] = topic
    for cand in candidates:
        for tid, topic in taxonomy_map.items():
            if topic.get("label") == cand.get("taxonomy_item"):
                cand["taxonomy_id"] = tid
                break

    survivors, rejected = skeptic_review(
        candidates, evidence_records=evidence_dicts,
        catalogue=None, backtest=backtest, taxonomy_map=taxonomy_map,
    )

    # ── S5 — Design ──
    gap_specs, design_errors = design_gap_specs(
        survivors, evidence_records=evidence_dicts, use_model=use_model)

    # ── S6 — Evaluate ──
    evidence_lookup = {r.get("id", ""): r for r in evidence_dicts}
    strict_pass, needs_work = evaluate_gap_specs(gap_specs, evidence_lookup=evidence_lookup)

    # A failed measurement promotes nothing.  The controls are what the system
    # already has; if the sweep could not see them, it cannot see the gaps
    # either, and the gap queue would be full of things the method invented.
    withheld = []
    if not measurement_held:
        withheld = strict_pass
        strict_pass = []
        for spec in needs_work:
            spec.setdefault("spec", None)
        needs_work = list(needs_work) + [{"withheld": True,
                                          "reason": "the measurement's controls failed",
                                          "spec": s.to_dict() if hasattr(s, "to_dict") else s}
                                         for s in withheld]

    # Store strict-pass gaps
    for spec in strict_pass:
        storage.append_gap(spec.to_dict() if hasattr(spec, "to_dict") else spec)

    # ── S7 — Gate ──
    # The gaps are now in the owner queue (status=open).  No auto-approval:
    # a recorded human decision is the only way out.

    # ── Back-test ──
    from . import backtest as _backtest
    backtest_result = _backtest.evaluate(
        produced_gaps=[s.to_dict() if hasattr(s, "to_dict") else s for s in strict_pass],
        backtest=backtest,
        coverage_rows=[r.to_dict() if hasattr(r, "to_dict") else r for r in coverage_rows])

    # Watch items: at-risk topics
    watchitems = []
    for row in coverage_rows:
        rd = row.to_dict() if hasattr(row, "to_dict") else row
        if rd.get("status") == "at-risk":
            wi = {
                "item": rd.get("taxonomy_item", ""),
                "why_at_risk": "Depends on a changing standard",
                "signal_to_monitor": "Standard amendment effective dates",
                "trigger_date": "",
                "migration_path": "Review computation or wording when standard changes",
                "last_checked_at": _now_iso(),
                "status": "watching",
            }
            watchitems.append(wi)
            storage.append_watchitem(wi)

    # Update run record
    run_record.status = "completed"
    run_record.finished_at = _now_iso()
    run_record.url_count = len(url_list or [])
    run_record.evidence_count = len(evidence_records)
    run_record.coverage_count = len(coverage_rows)
    run_record.gap_count = len(strict_pass)
    run_record.watchitem_count = len(watchitems)
    run_record.cost_tokens = 0  # the model's own ledger holds the real count
    run_record.controls = control_check
    run_record.withheld_count = len(withheld)
    storage.append_run(run_record.to_dict())

    return {
        "run_id": plan["run_id"],
        "status": "completed",
        "url_count": len(url_list or []),
        "evidence_count": len(evidence_records),
        "read_errors": read_errors,
        "coverage_count": len(coverage_rows),
        "coverage": [r.to_dict() if hasattr(r, "to_dict") else r for r in coverage_rows],
        "candidate_count": len(candidates),
        "survivor_count": len(survivors),
        "rejected_count": len(rejected),
        "rejected": rejected,
        "strict_pass_count": len(strict_pass),
        "strict_pass_gaps": [s.to_dict() if hasattr(s, "to_dict") else s for s in strict_pass],
        "withheld_count": len(withheld),
        "withheld_reason": ("the measurement's controls failed" if withheld else ""),
        "controls": control_check,
        "measurement_held": measurement_held,
        "needs_work_count": len(needs_work),
        "needs_work": needs_work,
        "watchitem_count": len(watchitems),
        "watchitems": watchitems,
        "design_errors": design_errors,
        "discovery_notes": discovery_notes,
        "per_school": per_school,
        "backtest": backtest_result,
    }


def _guess_category(label):
    """Guess a category (A-J) from a label string."""
    low = str(label or "").lower()
    if any(kw in low for kw in ["framework", "scorecard", "okr", "7s", "kotter", "horizon"]):
        return "A"
    if any(kw in low for kw in ["factor", "cluster", "mediation", "survival", "arima", "sem", "stat"]):
        return "B"
    if any(kw in low for kw in ["source", "retrieval", "vetted"]):
        return "C"
    if any(kw in low for kw in ["paper", "reflective", "literature", "legal", "communication", "empirical"]):
        return "D"
    if any(kw in low for kw in ["retrieval", "verification", "hallucination"]):
        return "E"
    if any(kw in low for kw in ["self-healing", "repair", "cause"]):
        return "F"
    if any(kw in low for kw in ["growth", "scaffold", "gap"]):
        return "G"
    if any(kw in low for kw in ["obsolete", "at-risk", "standard", "ifrs", "esrs"]):
        return "H"
    if any(kw in low for kw in ["accessibility", "usability", "admin"]):
        return "I"
    if any(kw in low for kw in ["ethics", "governance", "disclosure", "assessment", "process evidence"]):
        return "J"
    return "A"
