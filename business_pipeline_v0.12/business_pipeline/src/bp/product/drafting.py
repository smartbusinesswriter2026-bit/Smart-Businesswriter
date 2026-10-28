"""Draft a framework worksheet from retrieved sources (product layer).

The source finder retrieves evidence; this module arranges it.  It never writes a
fact of its own: every drafted item is the source's title plus the first sentence
of its abstract, and its citation is carried into the worksheet as `sourced`.
A source that matches no dimension is reported as unmatched, not forced in.

Supported first: SWOT, Five Forces, PESTEL, Business Model Canvas, Lean Canvas,
Value Proposition Canvas and the marketing plan.
"""

import re

#: keyword cues per block.  A source is placed in the block with the most hits;
#: no hit means unmatched, never a made-up placement.
SCHEMAS = {
    "template_swot": {"kind": "swot", "blocks": [
        ("S", "Strengths", "strength advantage capability resource brand loyal efficient leader patent quality"),
        ("W", "Weaknesses", "weakness disadvantage constraint shortage cost debt dependency capacity inefficiency"),
        ("O", "Opportunities", "opportunity growth demand expansion trend technology policy support"),
        ("T", "Threats", "threat competitor competition substitute regulation risk downturn tariff entry"),
    ]},
    "template_five_forces": {"kind": "forces", "blocks": [
        ("rivalry", "Industry rivalry", "rivalry competitor competition market share price war"),
        ("entrants", "Threat of new entrants", "entry entrant startup capital barrier licence license"),
        ("substitutes", "Threat of substitutes", "substitute alternative switching"),
        ("buyers", "Buyer power", "buyer customer client bargaining concentration"),
        ("suppliers", "Supplier power", "supplier vendor input procurement bargaining"),
    ]},
    "template_pestel": {"kind": "canvas", "blocks": [
        ("political", "Political", "government policy election stability regulation trade"),
        ("economic", "Economic", "growth inflation interest exchange recession demand income"),
        ("social", "Social", "demographic culture consumer behaviour behavior population lifestyle labour"),
        ("technological", "Technological", "technology digital automation innovation research"),
        ("environmental", "Environmental", "climate emission energy sustainability weather"),
        ("legal", "Legal", "law legal compliance liability licence license court"),
    ]},
    "template_business_model_canvas": {"kind": "canvas", "blocks": [
        ("key_partners", "Key partners", "partner supplier alliance"),
        ("key_activities", "Key activities", "activity process operations"),
        ("key_resources", "Key resources", "resource asset capability"),
        ("value_propositions", "Value propositions", "value benefit offering proposition"),
        ("customer_relationships", "Customer relationships", "relationship retention loyalty service"),
        ("channels", "Channels", "channel distribution retail online"),
        ("customer_segments", "Customer segments", "segment customer market"),
        ("cost_structure", "Cost structure", "cost expense fixed variable"),
        ("revenue_streams", "Revenue streams", "revenue price subscription sales"),
    ]},
    "template_lean_canvas": {"kind": "canvas", "blocks": [
        ("problem", "Problem", "problem pain need gap"),
        ("customer_segments", "Customer segments", "segment customer market"),
        ("unique_value_proposition", "Unique value proposition", "value different proposition"),
        ("solution", "Solution", "solution product service"),
        ("channels", "Channels", "channel distribution retail online"),
        ("revenue_streams", "Revenue streams", "revenue price subscription sales"),
        ("cost_structure", "Cost structure", "cost expense fixed variable"),
        ("key_metrics", "Key metrics", "metric measure retention conversion"),
        ("unfair_advantage", "Unfair advantage", "advantage patent exclusive proprietary"),
    ]},
    "template_value_proposition_canvas": {"kind": "canvas", "blocks": [
        ("customer_jobs", "Customer jobs", "job task goal need"),
        ("customer_pains", "Pains", "pain problem risk cost"),
        ("customer_gains", "Gains", "gain benefit outcome"),
        ("products_services", "Products and services", "product service offering"),
        ("pain_relievers", "Pain relievers", "relief reduce remove"),
        ("gain_creators", "Gain creators", "create improve increase"),
    ]},
    "template_marketing_plan": {"kind": "canvas", "blocks": [
        ("segmentation", "Segmentation", "segment market divide"),
        ("targeting", "Targeting", "target choose audience"),
        ("positioning", "Positioning", "position brand perception"),
        ("product", "Product", "product feature quality"),
        ("price", "Price", "price pricing"),
        ("place", "Place", "channel distribution retail online"),
        ("promotion", "Promotion", "advertising promotion campaign"),
        ("people", "People", "staff employee service"),
        ("process", "Process", "process service journey"),
        ("physical_evidence", "Physical evidence", "store packaging website"),
    ]},
}

MAX_ITEMS = 20
MAX_PER_BLOCK = 5
MAX_TEXT = 400


def supported(template):
    return template in SCHEMAS


def _squash(value, limit):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _citation(source):
    authors = _squash(source.get("authors"), 120)
    year = source.get("year")
    venue = _squash(source.get("venue"), 100)
    link = source.get("doi") or source.get("url") or ""
    parts = []
    for part in (authors, str(year) if year else "", venue, link):
        if part and part not in parts:
            parts.append(part)
    return _squash("; ".join(parts), 400)


def _evidence(source):
    title = _squash(source.get("title"), 220)
    abstract = _squash(source.get("abstract") or source.get("description"), 800)
    sentence = re.split(r"(?<=[.!?])\s+", abstract)[0] if abstract else ""
    text = title + (" — " + sentence if sentence and sentence != title else "")
    return _squash(text, MAX_TEXT)


def _keys(source):
    return set(re.findall(r"[a-z][a-z0-9'-]+", (
        _squash(source.get("title"), 400) + " " + _squash(source.get("abstract") or source.get("description"), 1600)
    ).lower()))


def _best_block(schema, source):
    words = _keys(source)
    best, best_score = None, 0
    for key, _label, cues in schema["blocks"]:
        score = sum(1 for cue in cues.split() if cue in words)
        if score > best_score:
            best, best_score = key, score
    return best, best_score


def draft(template, sources, max_items=MAX_ITEMS):
    """Return worksheet inputs plus a transparent placement report."""
    schema = SCHEMAS.get(template)
    if not schema:
        raise ValueError("drafting is not supported for this worksheet yet")
    if not isinstance(sources, list) or not sources:
        raise ValueError("at least one retrieved source is required")

    placed = {key: [] for key, _label, _cues in schema["blocks"]}
    assigned, unmatched, seen = [], [], set()
    for source in sources[:40]:
        if not isinstance(source, dict) or not source.get("title"):
            continue
        key = source.get("doi") or _squash(source.get("title"), 120).lower()
        if key in seen:
            continue
        seen.add(key)
        block, score = _best_block(schema, source)
        if not block or score == 0:
            unmatched.append({"title": _squash(source.get("title"), 180), "reason": "no dimension matched"})
            continue
        if len(placed[block]) >= MAX_PER_BLOCK:
            unmatched.append({"title": _squash(source.get("title"), 180), "reason": "block is full"})
            continue
        item = {"text": _evidence(source), "provenance": "sourced", "source": _citation(source)}
        placed[block].append(item)
        assigned.append({"block": block, "title": _squash(source.get("title"), 180),
                         "citation": item["source"]})
        if sum(len(items) for items in placed.values()) >= max_items:
            break

    if schema["kind"] == "swot":
        inputs = {"evidence": [dict(item, dimension=key) for key, _label, _cues in schema["blocks"]
                               for item in placed[key]], "options": []}
    elif schema["kind"] == "forces":
        inputs = {"evidence": [dict(item, force=key) for key, _label, _cues in schema["blocks"]
                               for item in placed[key]], "ratings": {}}
    else:
        inputs = {"blocks": {key: placed[key] for key, _label, _cues in schema["blocks"]}, "links": []}

    counts = {key: len(items) for key, items in placed.items()}
    return {"template": template, "inputs": inputs, "assigned": assigned, "unmatched": unmatched,
            "counts": counts, "labels": {key: label for key, label, _cues in schema["blocks"]},
            "n_items": sum(counts.values()),
            "note": ("Every drafted item is a source title plus a sentence from its abstract, with the "
                     "citation recorded. Review it before running; no fact or number was invented.")}
