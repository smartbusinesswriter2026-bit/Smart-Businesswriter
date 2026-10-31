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
    "template_sipoc": {"kind": "canvas", "blocks": [
        # Only the parts external evidence can legitimately support are drafted
        # into.  The steps, the output and the customer are the student's own
        # process: a published source cannot state them, so a source about them
        # is reported unmatched rather than placed where it does not belong.
        ("suppliers", "Suppliers", "supplier vendor producer mill farm distributor deliverer"),
        ("inputs", "Inputs", "input raw material ingredients stock packaging supply consumption"),
    ]},
    "template_toc": {"kind": "canvas", "blocks": [
        ("identify", "Identify the constraint", "constraint bottleneck capacity throughput limit queue"),
        ("exploit", "Exploit the constraint", "exploit uptime changeover idle bottleneck loss"),
        ("subordinate", "Subordinate everything else", "subordinate pace release buffer scheduling flow"),
        ("elevate", "Elevate the constraint", "elevate invest capacity equipment expansion"),
        ("reassess", "Reassess", "reassess migration next constraint review"),
    ]},
    "template_a3": {"kind": "canvas", "blocks": [
        ("problem", "Problem", "problem defect delay error gap waste"),
        ("current_condition", "Current condition", "current baseline delay queue observation data"),
        ("target", "Target condition", "target benchmark standard reduce within"),
        ("causes", "Root causes", "cause root reason driver factor why"),
        ("countermeasures", "Countermeasures", "countermeasure action change improve redesign"),
        ("plan", "Plan and owners", "plan owner schedule implementation"),
        ("follow_up", "Follow-up", "follow up review measure sustain verify"),
    ]},
    "template_scor": {"kind": "canvas", "blocks": [
        ("plan", "Plan", "plan forecast demand balance"),
        ("source", "Source", "supplier procurement purchasing sourcing"),
        ("make", "Make", "production manufacturing assembly build"),
        ("deliver", "Deliver", "delivery distribution logistics transport"),
        ("return", "Return", "return reverse defect recall"),
        ("enable", "Enable", "governance data contract compliance"),
    ]},
    "template_5s": {"kind": "canvas", "blocks": [
        ("sort", "Sort", "sort remove unnecessary clutter"),
        ("set_in_order", "Set in order", "order place label location"),
        ("shine", "Shine", "clean inspect maintenance"),
        ("standardize", "Standardize", "standard procedure checklist"),
        ("sustain", "Sustain", "audit habit sustain discipline"),
    ]},
    "template_root_cause": {"kind": "canvas", "blocks": [
        ("problem", "Problem", "problem effect defect delay"),
        ("people", "People", "people staff training skill"),
        ("process", "Process / method", "process method procedure workflow"),
        ("equipment", "Equipment", "equipment machine tool maintenance"),
        ("materials", "Materials", "material input specification supply"),
        ("measurement", "Measurement", "measurement metric calibration inspection"),
        ("environment", "Environment", "environment layout light heat noise"),
        ("root_cause", "Root cause", "root cause verified evidence"),
    ]},
    "template_fmea": {"kind": "canvas", "blocks": [
        ("failure_modes", "Failure modes", "failure mode defect error"),
        ("effects", "Effects", "effect impact customer consequence"),
        ("causes", "Causes", "cause reason source"),
        ("controls", "Current controls", "control prevention detection inspection"),
        ("actions", "Recommended actions", "action reduce improve mitigation"),
        ("owners", "Owners and review", "owner review date"),
    ]},
    "template_kraljic": {"kind": "canvas", "blocks": [
        ("criteria", "Criteria", "criteria impact risk threshold"),
        ("strategic", "Strategic items", "strategic partnership critical"),
        ("leverage", "Leverage items", "leverage tender price competition"),
        ("bottleneck", "Bottleneck items", "bottleneck scarce security supply"),
        ("non_critical", "Non-critical items", "non critical routine standard"),
    ]},
    "template_sop": {"kind": "canvas", "blocks": [
        ("demand_plan", "Demand plan", "demand forecast sales plan"),
        ("supply_plan", "Supply plan", "supply production plan"),
        ("inventory_plan", "Inventory plan", "inventory stock buffer"),
        ("capacity_plan", "Capacity plan", "capacity constraint resource"),
        ("financial_plan", "Financial plan", "revenue cost margin budget"),
        ("decisions", "Gaps and decisions", "gap decision reconcile"),
    ]},
    "template_pdca": {"kind": "canvas", "blocks": [
        ("plan", "Plan", "plan target hypothesis"),
        ("do", "Do", "do trial pilot implement"),
        ("check", "Check", "check measure result compare"),
        ("act", "Act", "act standardise change abandon"),
    ]},
    "template_job_characteristics": {"kind": "canvas", "blocks": [
        ("skill_variety", "Skill variety", "skill skills knowledge training qualification multi-skilled versatile"),
        ("task_identity", "Task identity", "task identity whole complete finished unit piece job"),
        ("task_significance", "Task significance", "task significance meaningful consequence impact purpose contribution effect"),
        ("autonomy", "Autonomy", "autonomy discretion control ownership latitude decide decision"),
        ("feedback", "Feedback", "feedback performance information review appraisal results know"),
    ]},
    "template_kirkpatrick": {"kind": "canvas", "blocks": [
        ("reaction", "Reaction", "reaction satisfaction happy useful feedback evaluation participants"),
        ("learning", "Learning", "learning knowledge skill test assessment recall baseline pass"),
        ("behavior", "Behaviour", "behaviour behavior change application practice transfer supervisor observe"),
        ("results", "Results", "results outcome impact benefit productivity quality turnover cost savings"),
    ]},
    "template_amo": {"kind": "canvas", "blocks": [
        ("ability", "Ability", "ability skill knowledge competence training qualified experience capability"),
        ("motivation", "Motivation", "motivation willing effort care morale incentive want commitment"),
        ("opportunity", "Opportunity", "opportunity allowed permitted resources tools time authority blocked process"),
    ]},
    "template_tuckman": {"kind": "canvas", "blocks": [
        ("forming", "Forming", "forming new team orientation first meeting introduction unsure"),
        ("storming", "Storming", "storming conflict argument disagreement friction role clash resistance"),
        ("norming", "Norming", "norming agreement norms routine settle ways working together"),
        ("performing", "Performing", "performing effective working together delivering interdependent flow"),
        ("adjourning", "Adjourning", "adjourning ending break up disband member leaving change team closure"),
    ]},
    "template_nine_box": {"kind": "canvas", "blocks": [
        ("performance_criteria", "Performance criteria", "performance criteria measure result quality rating target assessment"),
        ("potential_criteria", "Potential criteria", "potential criteria ability readiness growth ambition capable future"),
        ("placements", "Placements", "placement placed grid box performance potential team member staff"),
        ("development_actions", "Development actions", "development action plan rotation coaching stretch successor"),
    ]},
    "template_kotter": {"kind": "canvas", "blocks": [
        ("urgency", "Create urgency", "urgency crisis deadline losing competitive complaint decline window"),
        ("coalition", "Form a powerful coalition", "coalition sponsor leadership team group authority power influential"),
        ("vision", "Create a vision for change", "vision future aim goal state strategy direction picture"),
        ("communicate", "Communicate the vision", "communicate message brief meeting tell conversation channel explain"),
        ("empower", "Empower others to act", "empower remove barrier obstacle delegate authority permission freedom"),
        ("wins", "Plan for and create short-term wins", "win early result milestone quick visible early success short-term"),
        ("consolidate", "Consolidate gains and produce more change", "consolidate sustain momentum use gains further wave next change"),
        ("institutionalize", "Institutionalize new approaches", "institutionalize anchor embed culture routine policy standard sustain"),
    ]},
    "template_competing_values": {"kind": "canvas", "blocks": [
        ("clan", "Clan culture", "clan cohesion morale participation family commitment development team care"),
        ("adhocracy", "Adhocracy culture", "adhocracy innovation experimentation creativity growth external change flexible"),
        ("market", "Market culture", "market competition achievement results share customer competitive external"),
        ("hierarchy", "Hierarchy culture", "hierarchy structure control stability predictability process formal rules"),
    ]},
    "template_org_design": {"kind": "canvas", "blocks": [
        ("strategy", "Strategy", "strategy aim goal objective direction plan growth ambition priority"),
        ("decision_rights", "Decision rights", "decision rights authority accountable escalate approval decide responsibility"),
        ("structure", "Structure", "structure grouping team department layer span reporting hierarchy organogram"),
        ("processes", "Processes", "process workflow procedure governance control routine handoff interface"),
        ("people_capability", "People and capability", "people capability skill role capacity number experience resourcing"),
        ("incentives", "Incentives", "incentive reward pay bonus measure target performance appraisal remuneration"),
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
