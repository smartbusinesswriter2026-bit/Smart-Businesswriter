"""RRA Stage S5 — Designer.

Generates GapSpecs from surviving gaps.  Each GapSpec must have:
  - a testable acceptance criterion
  - an authoritative reference (standard/statute/published method, not blog)
  - an owner lane (computation or design)
  - constraint check results for all non-negotiables

The model drafts the criterion, the reference and the trap-test idea from the
evidence.  The model is a **proposal**: every field it supplies is checked
before it is kept, and the deterministic defaults below are always available.
"""
from .schemas import (
    GapSpec, CATEGORY_LABELS, VALID_CATEGORIES,
    PRIORITY_P0, PRIORITY_P1, PRIORITY_P2,
    EFFORT_S, EFFORT_M, EFFORT_L,
    OWNER_COMPUTATION, OWNER_DESIGN,
)
from . import storage

_NON_NEGOTIABLES = [
    "no_invented_evidence", "no_invented_numbers", "no_silent_substitution",
    "global_product", "no_template_text", "model_never_does_math",
    "stdlib_only", "human_approval_at_gates", "no_patch_fixes",
    "no_autonomous_code_writing", "frozen_core_respected",
]

#: The default acceptance criterion per category (A–J).  Used when the model
#: is not configured or its answer fails the checks.
_DEFAULT_CRITERIA = {
    "A": "A framework profile exists in framework_profiles.py with dimensions, cues, queries, and a draftable flag; tests cover section order, named gap, unit refusal, and no invented numbers.",
    "B": "A method exists in bp/methods.py with a declared input schema; a capability entry in capabilities.ENTRIES with intent cues, needs_any, and a formatter; trap test proves the method runs on declared inputs.",
    "C": "A vetted source entry in sources.py with domain, tier, topics, and priority; test_sources.py confirms the topic reaches it.",
    "D": "A paper family archetype in paper_families.py with completeness contract; tests validate plan IR and export gate.",
    "E": "A retrieval or verification function with unit tests; no invented evidence.",
    "F": "A cause classification in causes.py with remedy and artifact; test_causes.py asserts classification and closure.",
    "G": "A gap-logging call site with a test proving the finding appears in the Validation panel.",
    "H": "A watch item with trigger date and migration path; documented in KNOWN_LIMITATIONS.",
    "I": "A UI affordance with an accessibility check.",
    "J": "A disclosure or ethics feature with a test; no autonomous code writing.",
}

#: The categories the model may propose.  Anything else is refused.
_VALID_CATEGORIES = VALID_CATEGORIES

_DRAFT_SYSTEM = (
    "You write one capability-gap specification for a business-writing system that "
    "produces student papers. The system computes every number in code, never "
    "invents a source, and never writes a paper from an unwritten plan.\n"
    "You are given a candidate gap and the evidence records behind it. You return:\n"
    "1. \"general_capability_statement\": one sentence naming the general capability "
    "the system should have. It must be jurisdiction-neutral (no country, "
    "exchange, currency or regulator named) and must be a general capability, not "
    "a one-off patch.\n"
    "2. \"why_not_already_covered\": one sentence, in the words of the catalogue, "
    "why the system does not already do this.\n"
    "3. \"authoritative_reference\": the standard, statute, published method or "
    "institutional document that establishes the need. Name it as it is written. "
    "A blog, a course marketplace or a news article is not acceptable — if no such "
    "reference exists, return an empty string.\n"
    "4. \"proposed_acceptance_criterion\": one sentence a developer can test. It "
    "must name what exists afterwards that does not exist now, and what proves it.\n"
    "5. \"trap_test_idea\": one sentence describing a test that FAILS on today's "
    "code and PASSES after the capability is built.\n"
    "6. \"owner_lane\": \"computation\" if the work touches src/bp/** (methods, "
    "capabilities, computations, the frozen core) or \"design\" if it is product "
    "backend, routes, storage or the workbench.\n"
    "7. \"priority\": \"P0\", \"P1\" or \"P2\".\n"
    "8. \"effort\": \"S\", \"M\" or \"L\".\n"
    "9. \"category\": one letter from A to J (A frameworks, B computation methods, "
    "C evidence sources, D paper types, E retrieval/verification, F self-healing, "
    "G growth-loop design, H obsolescence, I accessibility, J ethics/governance).\n"
    "Answer with a JSON object only. Never invent a source, a number, a standard "
    "name or a date that is not in the evidence."
)


def _default_constraint_check():
    """All non-negotiables pass by default (the gap must declare any that fail)."""
    return {rule: True for rule in _NON_NEGOTIABLES}


def _model_draft(candidate, category, evidence_records):
    """Ask the model to draft the spec fields.  Returns a dict (may be empty).

    Only fields that pass the checks below are returned; the rest are dropped
    so a bad answer cannot enter the queue.
    """
    from . import model as _model
    title = candidate.get("title", "") or candidate.get("taxonomy_item", "")
    lines = ["Candidate gap: %s" % title]
    for rec in (evidence_records or [])[:6]:
        if hasattr(rec, "to_dict"):
            rec = rec.to_dict()
        lines.append("- [%s] %s (%s): %s" % (
            rec.get("tier", ""), rec.get("school_or_body", ""),
            rec.get("source_url", ""), rec.get("excerpt", "")))
    if len(evidence_records or []) > 6:
        lines.append("- ... and %d more evidence record(s)" % (len(evidence_records) - 6))

    parsed, _record, err = _model.call_json(
        _DRAFT_SYSTEM, "\n".join(lines), task="relevance-design")
    if err or not isinstance(parsed, dict):
        return {}

    draft = {}
    statement = str(parsed.get("general_capability_statement") or "").strip()
    if statement and len(statement) <= 600:
        draft["general_capability_statement"] = statement

    why = str(parsed.get("why_not_already_covered") or "").strip()
    if why and len(why) <= 400:
        draft["why_not_already_covered"] = why

    reference = str(parsed.get("authoritative_reference") or "").strip()
    if reference and len(reference) <= 300:
        draft["authoritative_reference"] = reference

    criterion = str(parsed.get("proposed_acceptance_criterion") or "").strip()
    if criterion and len(criterion) <= 600:
        draft["proposed_acceptance_criterion"] = criterion

    trap = str(parsed.get("trap_test_idea") or "").strip()
    if trap and len(trap) <= 400:
        draft["trap_test_idea"] = trap

    lane = str(parsed.get("owner_lane") or "").strip().lower()
    if lane in (OWNER_COMPUTATION, OWNER_DESIGN):
        draft["owner_lane"] = lane

    priority = str(parsed.get("priority") or "").strip().upper()
    if priority in (PRIORITY_P0, PRIORITY_P1, PRIORITY_P2):
        draft["priority"] = priority

    effort = str(parsed.get("effort") or "").strip().upper()
    if effort in (EFFORT_S, EFFORT_M, EFFORT_L):
        draft["effort"] = effort

    proposed_category = str(parsed.get("category") or "").strip().upper()
    if proposed_category in _VALID_CATEGORIES:
        draft["category"] = proposed_category

    return draft


def design_gap_spec(candidate, evidence_ids=None, why_not_covered="",
                    authoritative_reference="", owner_lane=OWNER_DESIGN,
                    acceptance_criterion="", trap_test_idea="",
                    priority=PRIORITY_P2, effort=EFFORT_M, risk="",
                    use_model=True, evidence_records=None):
    """Build a GapSpec from a candidate gap.  Returns (spec, error)."""
    if not isinstance(candidate, dict):
        candidate = {}

    title = candidate.get("title", "") or candidate.get("label", "") or candidate.get("taxonomy_item", "")
    category = candidate.get("category", "")
    if category not in VALID_CATEGORIES:
        category = "A"  # default to frameworks

    capability_statement = candidate.get("general_capability_statement", "") or candidate.get("label", "")
    if not capability_statement:
        capability_statement = title

    if not why_not_covered:
        why_not_covered = candidate.get("why_not_already_covered", "") or "Not present in the catalogue"

    # ── Model draft (a proposal; every field is checked before it is kept) ──
    draft = {}
    if use_model:
        draft = _model_draft(candidate, category, evidence_records or [])

    if category == "A" and draft.get("category") and draft["category"] != category:
        # The model may reclassify, but only when it names a valid category.
        category = draft["category"]

    capability_statement = draft.get("general_capability_statement") or capability_statement
    why_not_covered = draft.get("why_not_already_covered") or why_not_covered
    authoritative_reference = authoritative_reference or draft.get("authoritative_reference", "")
    acceptance_criterion = acceptance_criterion or draft.get("proposed_acceptance_criterion", "")
    trap_test_idea = trap_test_idea or draft.get("trap_test_idea", "")
    owner_lane = draft.get("owner_lane", owner_lane)
    priority = draft.get("priority", priority)
    effort = draft.get("effort", effort)

    if not authoritative_reference:
        authoritative_reference = candidate.get("authoritative_reference", "")
    if not authoritative_reference:
        # Use the evidence ids as the pointer when nothing else is known.
        eids = evidence_ids or candidate.get("evidence_ids", [])
        if eids:
            authoritative_reference = "Evidence: %s" % ", ".join(str(e) for e in eids[:3])
        else:
            authoritative_reference = "To be determined by owner review"

    if not acceptance_criterion:
        acceptance_criterion = candidate.get("proposed_acceptance_criterion", "")
    if not acceptance_criterion:
        acceptance_criterion = _DEFAULT_CRITERIA.get(
            category, "A testable acceptance criterion is defined by the owner.")

    if not trap_test_idea:
        trap_test_idea = candidate.get("trap_test_idea", "")
    if not trap_test_idea:
        trap_test_idea = "Add a test that fails on the current code and passes after the capability is implemented."

    spec = GapSpec(
        id="",  # set below
        title=title,
        category=category,
        general_capability_statement=capability_statement,
        evidence_ids=list(evidence_ids or candidate.get("evidence_ids", [])),
        why_not_already_covered=why_not_covered,
        authoritative_reference=authoritative_reference,
        owner_lane=owner_lane,
        proposed_acceptance_criterion=acceptance_criterion,
        trap_test_idea=trap_test_idea,
        constraint_check=_default_constraint_check(),
        priority=priority,
        effort=effort,
        risk=risk,
        status="open",
    )
    spec.id = spec.make_id()

    # Read growth_brief if available (error_db)
    try:
        from .. import error_db as _edb
        brief = _edb.growth_brief(
            subject=candidate.get("subject", ""),
            tile=candidate.get("tile", ""),
            text=capability_statement,
        )
        if brief:
            spec.risk = (spec.risk + " | Growth brief: " + str(brief)[:200]).strip(" |")
    except Exception:
        pass

    return spec, ""


def design_gap_specs(candidates, evidence_ids=None, evidence_records=None, use_model=True):
    """Design GapSpecs from a list of surviving candidates."""
    specs = []
    errors = []
    for cand in (candidates or []):
        spec, err = design_gap_spec(cand, evidence_ids=evidence_ids,
                                    evidence_records=evidence_records,
                                    use_model=use_model)
        if err:
            errors.append({"candidate": cand, "error": err})
        else:
            specs.append(spec)
    return specs, errors
