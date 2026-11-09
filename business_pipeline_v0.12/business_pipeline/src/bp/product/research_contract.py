"""The research contract: what a framework needs, and what the ledger records.

The pipeline's research is not a general search engine.  A framework profile
declares, per dimension, the topic it belongs to, the source tiers it prefers,
how many queries it may spend, what kind of evidence it needs and which tiers
make a dimension citable.  This module holds the closed vocabularies that make
those declarations verifiable, the ledger record every dimension carries, and
the source-type grading rule.

Nothing here searches, ranks or writes prose.  It is data and pure functions so
a new framework declares its research needs without changing the engine.

The vocabularies are closed on purpose.  A free-text need cannot be hashed into
the frozen plan or replayed, and an open reason set would let a new rejection
path slip in unrecorded.  Adding a value is a decision row (B-number), not an
edit to a string.
"""

#: What a dimension is looking for, in the pipeline's own vocabulary.
NEEDS = (
    "market_size",
    "regulation",
    "competitor",
    "customer",
    "technology_trend",
    "industry_structure",
    "country_macro",
    "cost_price",
    "sustainability",
    "methodology",
)
ALL_NEEDS = frozenset(NEEDS)

#: Why a candidate did not become evidence.  Every rejection is recorded.
REASONS = (
    "no_cue",
    "no_geography",
    "tier_missing",
    "blocked_domain",
    "below_floor",
    "duplicate",
    "full_text_cue_missing",
)
ALL_REASONS = frozenset(REASONS)

#: The source tiers a profile may prefer or require, strongest first.
TIERS = ("official", "data", "research", "news")

#: The keys a `research` block may carry.
RESEARCH_KEYS = frozenset({"topics", "tiers", "budget", "needs", "required_tiers"})

BUDGET_MIN = 1
BUDGET_MAX = 5


def is_need(value):
    """True when `value` is a declared research need."""
    return str(value or "") in ALL_NEEDS


def is_reason(value):
    """True when `value` is a declared rejection reason."""
    return str(value or "") in ALL_REASONS


def _is_tier(value):
    return str(value or "") in TIERS


def validate_research(research):
    """The problems with a profile's `research` block, or an empty list.

    An absent block is valid: the profile keeps the old behaviour.  A present
    block is checked against the closed vocabularies so an unknown need, tier or
    key is refused by `profile_for` rather than silently ignored.
    """
    if research is None:
        return []
    if not isinstance(research, dict):
        return ["research must be a mapping"]
    problems = []
    for key in sorted(set(research) - RESEARCH_KEYS):
        problems.append("research: unknown key %s" % key)
    budget = research.get("budget")
    if budget is not None:
        try:
            number = int(budget)
        except (TypeError, ValueError):
            number = None
        if number is None or not (BUDGET_MIN <= number <= BUDGET_MAX):
            problems.append("research: budget must be an integer from %d to %d"
                            % (BUDGET_MIN, BUDGET_MAX))
    for field in ("topics", "tiers", "needs", "required_tiers"):
        value = research.get(field)
        if value is None:
            continue
        if not isinstance(value, dict):
            problems.append("research: %s must be a mapping of dimension to value" % field)
            continue
        for dimension, declared in value.items():
            if field == "topics":
                if not isinstance(declared, str) or not declared.strip():
                    problems.append("research: topics[%s] must be a topic name" % dimension)
                continue
            values = declared if isinstance(declared, (list, tuple)) else [declared]
            for entry in values:
                if field == "needs" and not is_need(entry):
                    problems.append("research: needs[%s] has unknown need %r"
                                    % (dimension, entry))
                if field in ("tiers", "required_tiers") and not _is_tier(entry):
                    problems.append("research: %s[%s] has unknown tier %r"
                                    % (field, dimension, entry))
    return problems


def build_ledger(dimension, accepted=None, rejected=None, gaps=None, background=None):
    """One dimension's evidence ledger.

    `accepted` items keep the fields the pipeline already records (title, source,
    citation, tier); this function adds nothing to them.  `rejected` entries are
    `{candidate, reason}` and a reason outside the closed set is refused, so a
    new rejection path cannot be added without declaring it.
    """
    rejected_rows = []
    for row in rejected or []:
        reason = str((row or {}).get("reason") or "")
        if not is_reason(reason):
            raise ValueError("unknown rejection reason: %r" % reason)
        rejected_rows.append({"candidate": (row or {}).get("candidate"),
                              "reason": reason})
    return {
        "dimension": str(dimension or ""),
        "accepted": list(accepted or []),
        "rejected": rejected_rows,
        "gaps": list(gaps or []),
        "background": list(background or []),
    }


def source_tier_of(item):
    """The source tier of a candidate, or an empty string when it has none.

    Retrieval items carry the source tier in `tier`; a completion item has
    already been given the audit tier (A/B/C/D) in `tier`, so the source tier is
    kept beside it as `source_tier`.  Only the four source tiers count; an audit
    tier is never mistaken for one.
    """
    item = item if isinstance(item, dict) else {}
    for key in ("source_tier", "tier"):
        value = str(item.get(key) or "").strip()
        if value in TIERS:
            return value
    return ""


def filter_by_grade(items, required_tiers):
    """Split items into (kept, rejected) by the profile's required source tiers.

    A known tier outside the required list is rejected; an item with no source
    tier is kept (the old behaviour, and a student item is never dropped).  The
    caller records the rejected items as `tier_missing`.
    """
    required = {str(tier) for tier in (required_tiers or [])}
    kept, rejected = [], []
    for item in items or []:
        tier = source_tier_of(item)
        if required and tier and tier not in required:
            rejected.append(item)
        else:
            kept.append(item)
    return kept, rejected


def grade_dimension(accepted, required_tiers):
    """Whether a dimension is citable at the source type its profile requires.

    `ok` is true when no tier is required, when no accepted item declares a
    source tier, or when at least one accepted item carries one of the required
    tiers.  When it is false the caller turns the dimension into a named gap
    with a probe; this function only returns the verdict, never invents a
    replacement source.
    """
    required = [str(tier) for tier in (required_tiers or [])]
    if not required:
        return {"ok": True, "missing_tiers": []}
    if not accepted:
        # An empty dimension is a gap the caller already names; it is not a
        # source-type failure.
        return {"ok": True, "missing_tiers": []}
    present = {source_tier_of(item) for item in accepted}
    present.discard("")
    if not present:
        return {"ok": True, "missing_tiers": []}
    if present & set(required):
        return {"ok": True, "missing_tiers": []}
    return {"ok": False, "missing_tiers": list(required)}
