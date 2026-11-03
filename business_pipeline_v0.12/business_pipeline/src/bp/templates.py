"""Structured framework templates (Build Charter Stage 6): SWOT with the STR-18 evidence-to-action audit, and Porter's Five Forces.
A template organizes evidence YOU supply. It never adds a fact, rating, weight, score or option of its own (charter 1.3, manual P1, 8).
Tier T4: nothing is computed. Verification checks the structure and that every word of evidence is reproduced verbatim."""
import re
from collections import Counter
from .methods import DataError

PROV = ("user", "sourced", "assumption", "synthetic")
MATERIALITY = ("high", "medium", "low")
RATINGS = ("low", "moderate", "high")                       # [PROVISIONAL] three-step scale; the catalogue gives none
MAX_ITEMS, MAX_TEXT, MAX_OPTIONS = 60, 400, 20
ID_RE = re.compile(r"[A-Za-z0-9_\-]{1,20}")
CTRL = re.compile(r"[\x00-\x1f\x7f\x85\u2028\u2029]")     # any line break or control character: a multi-line text could forge extra listing lines
QUAD = {"S": ("Strengths", "internal"), "W": ("Weaknesses", "internal"), "O": ("Opportunities", "external"), "T": ("Threats", "external")}
FORCES = {"rivalry": "Industry rivalry", "entrants": "Threat of new entrants", "substitutes": "Threat of substitutes", "buyers": "Buyer power", "suppliers": "Supplier power"}
PERIOD = "cross_section"

def _plural(word):
    return word[:-1] + "ies" if word.endswith("y") else word + "s"


def _label(it):
    """A plain-language label for the student; never a field name or code."""
    p = it["provenance"]
    return {"user": "your evidence", "sourced": f"source: {it.get('source')}",
            "assumption": "assumption (not yet supported)", "synthetic": "illustrative only"}[p]

def _items(inp, key, dim_key, allowed, errs, id_prefix="E"):
    raw = inp.get(key)
    if not isinstance(raw, list) or not raw: errs.append(f"'{key}' must be a non-empty list of evidence items"); return []
    if len(raw) > MAX_ITEMS: errs.append(f"at most {MAX_ITEMS} evidence items"); return []
    out, used = [], set()
    for n, it in enumerate(raw, 1):
        where = f"{key}[{n - 1}]"
        if not isinstance(it, dict): errs.append(f"{where} must be an object"); continue
        text = it.get("text"); 
        if not isinstance(text, str) or not text.strip(): errs.append(f"{where}: 'text' is required"); continue
        text = text.strip()
        if len(text) > MAX_TEXT or CTRL.search(text): errs.append(f"{where}: text must be one line of at most {MAX_TEXT} characters"); continue
        dim = it.get(dim_key) if dim_key else None
        if dim_key and dim not in allowed: errs.append(f"{where}: '{dim_key}' must be one of {sorted(allowed)}"); continue
        prov = it.get("provenance", "user")
        if prov not in PROV: errs.append(f"{where}: provenance must be one of {list(PROV)}"); continue
        src = it.get("source")
        if prov == "sourced" and (not isinstance(src, str) or not src.strip() or CTRL.search(src)): errs.append(f"{where}: sourced evidence needs a 'source' (one line)"); continue
        mat = it.get("materiality")
        if mat is not None and mat not in MATERIALITY: errs.append(f"{where}: materiality must be one of {list(MATERIALITY)}"); continue
        iid = it.get("id", f"{id_prefix}{n}")
        if not isinstance(iid, str) or not ID_RE.fullmatch(iid): errs.append(f"{where}: id must be 1-20 letters, digits, - or _"); continue
        if iid in used: errs.append(f"{where}: duplicate id {iid}"); continue
        used.add(iid); out.append({"id": iid, "text": text, "dim": dim, "provenance": prov, "source": src.strip() if isinstance(src, str) else None, "materiality": mat})
    return out

def normalize(kind, inp):
    errs = []
    if not isinstance(inp, dict): return None, ["inputs must be an object"]
    if kind == "template_swot":
        extra = set(inp) - {"evidence", "options"}
        if extra: errs.append(f"unknown input {sorted(extra)}; allowed: ['evidence', 'options']")
        items = _items(inp, "evidence", "dimension", set(QUAD), errs); ids = {i["id"] for i in items}; opts = []
        raw = inp.get("options", [])
        if not isinstance(raw, list) or len(raw) > MAX_OPTIONS: errs.append(f"'options' must be a list of at most {MAX_OPTIONS}"); raw = []
        for n, o in enumerate(raw, 1):
            if not isinstance(o, dict) or not isinstance(o.get("text"), str) or not o["text"].strip() or len(o["text"].strip()) > MAX_TEXT or CTRL.search(o["text"]): errs.append(f"options[{n - 1}]: 'text' is required (one line, at most {MAX_TEXT} characters)"); continue
            sup = o.get("supports")
            if not isinstance(sup, list) or not sup: errs.append(f"options[{n - 1}]: must cite at least one evidence item in 'supports' (strategic options must follow from the analysis)"); continue
            miss = [s for s in sup if s not in ids]
            if miss: errs.append(f"options[{n - 1}]: cites unknown evidence ids {miss}"); continue
            oid = o.get("id", f"O{n}")
            if not isinstance(oid, str) or not ID_RE.fullmatch(oid) or oid in ids or oid in {x["id"] for x in opts}: errs.append(f"options[{n - 1}]: id must be unique, 1-20 letters, digits, - or _"); continue
            opts.append({"id": oid, "text": o["text"].strip(), "supports": list(dict.fromkeys(sup))})
        return ({"items": items, "options": opts} if not errs else None), errs
    if kind == "template_five_forces":
        extra = set(inp) - {"evidence", "ratings"}
        if extra: errs.append(f"unknown input {sorted(extra)}; allowed: ['evidence', 'ratings']")
        items = _items(inp, "evidence", "force", set(FORCES), errs); rat = inp.get("ratings", {})
        if not isinstance(rat, dict): errs.append("'ratings' must be an object keyed by force"); rat = {}
        by = Counter(i["dim"] for i in items); clean = {}
        for f, r in rat.items():
            if f not in FORCES: errs.append(f"ratings: unknown force {f!r}; use {sorted(FORCES)}"); continue
            if not isinstance(r, dict) or r.get("rating") not in RATINGS: errs.append(f"ratings.{f}: 'rating' must be one of {list(RATINGS)} (your judgment)"); continue
            why = r.get("rationale")
            if not isinstance(why, str) or not why.strip() or len(why.strip()) > MAX_TEXT or CTRL.search(why): errs.append(f"ratings.{f}: a one-line 'rationale' is required"); continue
            if by[f] == 0: errs.append(f"ratings.{f}: a rating needs at least one supporting evidence item for that force"); continue
            clean[f] = {"rating": r["rating"], "rationale": why.strip()}
        return ({"items": items, "ratings": clean} if not errs else None), errs
    return None, [f"unknown template {kind}"]

def validate(kind, inp):
    t = TEMPLATES.get(kind)
    return t["validate"](inp) if t and "validate" in t else normalize(kind, inp)[1]

def _tows(dims):
    i = [d for d in "SW" if d in dims]; e = [d for d in "OT" if d in dims]
    return i[0] + e[0] if len(dims) == 2 and len(i) == 1 and len(e) == 1 else "other"

def build_swot(inp):
    n, errs = normalize("template_swot", inp)
    if errs: raise DataError("; ".join(errs))
    q = {d: {"label": QUAD[d][0], "scope": QUAD[d][1], "items": []} for d in QUAD}
    for it in n["items"]: q[it["dim"]]["items"].append({k: it[k] for k in ("id", "text", "provenance", "source", "materiality")})
    dim = {i["id"]: i["dim"] for i in n["items"]}
    opts = [{**o, "tows": _tows({dim[s] for s in o["supports"]})} for o in n["options"]]
    cited = {s for o in opts for s in o["supports"]}; its = n["items"]
    audit = {"empty_quadrants": [d for d in QUAD if not q[d]["items"]], "items_without_options": [i["id"] for i in its if i["id"] not in cited],
             "unsupported_items": [i["id"] for i in its if i["provenance"] == "assumption"], "synthetic_items": [i["id"] for i in its if i["provenance"] == "synthetic"],
             "materiality": {m: sum(1 for i in its if i["materiality"] == m) for m in MATERIALITY} | {"unrated": sum(1 for i in its if i["materiality"] is None)}}
    counts = {"n_items": len(its), **{f"n_{d}": len(q[d]["items"]) for d in QUAD}, "n_options": len(opts), "n_unsupported": len(audit["unsupported_items"]), "n_no_option": len(audit["items_without_options"])}
    return {"kind": "template_swot", "registry_ids": ["STR-07", "STR-18"], "quadrants": q, "options": opts, "audit": audit, "counts": counts}

def build_five_forces(inp):
    n, errs = normalize("template_five_forces", inp)
    if errs: raise DataError("; ".join(errs))
    f = {k: {"label": v, "evidence": [], "rating": None, "rationale": None, "status": None} for k, v in FORCES.items()}
    for it in n["items"]: f[it["dim"]]["evidence"].append({k: it[k] for k in ("id", "text", "provenance", "source", "materiality")})
    for k, r in n["ratings"].items(): f[k]["rating"], f[k]["rationale"] = r["rating"], r["rationale"]
    for k, v in f.items(): v["status"] = "rated" if v["rating"] else "evidence_only" if v["evidence"] else "no_evidence"
    its = n["items"]; st = Counter(v["status"] for v in f.values())
    audit = {"forces_without_evidence": [k for k, v in f.items() if v["status"] == "no_evidence"], "unsupported_items": [i["id"] for i in its if i["provenance"] == "assumption"],
             "synthetic_items": [i["id"] for i in its if i["provenance"] == "synthetic"]}
    counts = {"n_items": len(its), "n_rated": st["rated"], "n_evidence_only": st["evidence_only"], "n_no_evidence": st["no_evidence"], "n_unsupported": len(audit["unsupported_items"])}
    return {"kind": "template_five_forces", "registry_ids": ["STR-01"], "forces": f, "audit": audit, "counts": counts}

def _line(it): return f"  • {it['text']} — {_label(it)}" + (f"; materiality: {it['materiality']} (your rating)" if it.get("materiality") else "")
def _names(keys, names): return ", ".join(names[k].lower() for k in keys)

def render_swot(a):
    P, a_ = PERIOD, a["audit"]; tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P)
    t = (f"This SWOT organizes {tok('n_items')} evidence items you supplied: {tok('n_S')} strengths, {tok('n_W')} weaknesses, {tok('n_O')} opportunities and {tok('n_T')} threats. "
         "Strengths and weaknesses are treated as internal to the organization, and opportunities and threats as external, according to the dimension you assigned to each item. ")
    if a_["empty_quadrants"]: t += f"No evidence was supplied for: {_names(a_['empty_quadrants'], {d: QUAD[d][0] for d in QUAD})}. These are left empty and are not filled in by the system. "
    t += f"You supplied {tok('n_options')} strategic options, and each cites the items it follows from. "
    if a["counts"]["n_no_option"]: t += f"{tok('n_no_option')} items have no resulting option. "
    if a["counts"]["n_unsupported"]: t += f"{tok('n_unsupported')} items rest on assumptions rather than user-supplied or sourced evidence. "
    if a_["synthetic_items"]: t += "Some items are synthetic and illustrative only; they are not observations. "
    t += "This analysis organizes evidence only. It does not rank or weight items, it does not show which option to pursue, and it adds no facts of its own."
    lines = []
    for d in QUAD:
        qd = a["quadrants"][d]; lines.append(f"{qd['label']} ({qd['scope']})")
        lines += [_line(i) for i in qd["items"]] or ["  No evidence supplied."]
    if a["options"]:
        lines.append("Strategic options you supplied (pairing derived from the dimensions of the items cited)")
        by_id = {i["id"]: i["text"] for d in QUAD for i in a["quadrants"][d]["items"]}
        for o in a["options"]:
            follows = "; ".join(by_id[s] for s in o["supports"])
            lines.append(f"  • {o['tows']}: {o['text']} — follows from: {follows}")
    return t, "\n".join(lines)

def render_five_forces(a):
    P = PERIOD; tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P); a_ = a["audit"]
    t = (f"This Five Forces structure organizes {tok('n_items')} evidence items across the five forces. {tok('n_rated')} forces carry a rating you supplied together with its rationale, "
         f"{tok('n_evidence_only')} have evidence but no rating, and {tok('n_no_evidence')} have no evidence. ")
    if a_["forces_without_evidence"]: t += f"No evidence was supplied for: {_names(a_['forces_without_evidence'], FORCES)}; evidence to look for includes market structure, competitor evidence, switching costs and industry economics. "
    if a["counts"]["n_unsupported"]: t += f"{tok('n_unsupported')} items rest on assumptions rather than user-supplied or sourced evidence. "
    if a_["synthetic_items"]: t += "Some items are synthetic and illustrative only; they are not observations. "
    t += ("Ratings are your judgments, supported by the evidence you attached. The system computed no score and no overall measure of industry attractiveness, and it adds no facts of its own. "
          "Five Forces is mostly qualitative unless data are available.")
    lines = []
    for k, v in a["forces"].items():
        lines.append(f"{v['label']} — " + (f"rating: {v['rating']} (your judgment). Rationale: {v['rationale']}" if v["rating"] else "no rating supplied"))
        lines += [_line(i) for i in v["evidence"]] or ["  No evidence supplied."]
    return t, "\n".join(lines)

# ---------- independent verification (recomputed from the raw input, not from the build) ----------
def _raw_items(inp, dim_key): return [(i.get("id", f"E{n}"), i["text"].strip(), i[dim_key], i.get("provenance", "user")) for n, i in enumerate(inp["evidence"], 1)]

def _common(kind, inp, a, narrative, listing, dim_key):
    raw = _raw_items(inp, dim_key); n = len(raw)
    placed = [i["id"] for grp in (a["quadrants"].values() if kind == "template_swot" else [{"items": v["evidence"]} for v in a["forces"].values()]) for i in grp["items"]]
    c = a["counts"]
    texts_out = set(placed and [i["text"] for grp in (a["quadrants"].values() if kind == "template_swot" else [{"items": v["evidence"]} for v in a["forces"].values()]) for i in grp["items"]])
    if kind == "template_swot": texts_out |= {o["text"] for o in a["options"]}
    allowed = {t for _, t, _, _ in raw} | ({o["text"].strip() for o in inp.get("options", [])} if kind == "template_swot" else set()) | ({r["rationale"].strip() for r in inp.get("ratings", {}).values()} if kind == "template_five_forces" else set())
    out_texts = set(texts_out) | ({v["rationale"] for v in a["forces"].values() if v["rationale"]} if kind == "template_five_forces" else set())
    ok_line = all(f"• {t} — " in listing for i, t, _, _ in raw)
    return [("each_item_placed_exactly_once", sorted(placed) == sorted(i for i, _, _, _ in raw) and len(set(placed)) == n),
            ("listing_reproduces_every_input_text_verbatim", ok_line and listing.count("\n  •") + (1 if listing.startswith("  •") else 0) >= n),
            ("analysis_contains_only_supplied_text", out_texts <= allowed and {t for _, t, _, _ in raw} <= out_texts),
            ("assumptions_and_synthetic_flagged", set(a["audit"]["unsupported_items"]) == {i for i, _, _, p in raw if p == "assumption"} and set(a["audit"]["synthetic_items"]) == {i for i, _, _, p in raw if p == "synthetic"}),
            ("rendering_is_deterministic", (render_swot if kind == "template_swot" else render_five_forces)(a) == (narrative, listing))]

def tests_swot(inp, a, narrative, listing):
    raw = _raw_items(inp, "dimension"); cnt = Counter(d for _, _, d, _ in raw); c = a["counts"]; dims = {i: d for i, _, d, _ in raw}
    r = _common("template_swot", inp, a, narrative, listing, "dimension")
    tows_ok = all(o["tows"] == _tows({dims[s] for s in o["supports"]}) and all(s in dims for s in o["supports"]) for o in a["options"])
    cited = {s for o in inp.get("options", []) for s in o["supports"]}
    return [r[0], ("counts_agree_with_independent_recount", c["n_items"] == len(raw) and all(c[f"n_{d}"] == cnt[d] for d in QUAD) and c["n_options"] == len(inp.get("options", []))), r[1], r[2],
            ("scopes_match_framework_definition", all(a["quadrants"][d]["scope"] == ("internal" if d in "SW" else "external") for d in QUAD) and all(i["id"] in {x for x, _, dd, _ in raw if dd == d} for d in QUAD for i in a["quadrants"][d]["items"])),
            ("options_cite_existing_items_and_pairing_is_consistent", tows_ok and set(a["audit"]["items_without_options"]) == {i for i, _, _, _ in raw} - cited),
            ("empty_quadrants_reported_not_filled", a["audit"]["empty_quadrants"] == [d for d in QUAD if cnt[d] == 0] and all(a["quadrants"][d]["items"] == [] for d in a["audit"]["empty_quadrants"])), r[3], r[4]]

def tests_five_forces(inp, a, narrative, listing):
    raw = _raw_items(inp, "force"); cnt = Counter(d for _, _, d, _ in raw); c = a["counts"]; rat = inp.get("ratings", {})
    r = _common("template_five_forces", inp, a, narrative, listing, "force")
    return [r[0], ("counts_agree_with_independent_recount", c["n_items"] == len(raw) and c["n_rated"] == len(rat) and c["n_no_evidence"] == sum(1 for f in FORCES if cnt[f] == 0)
                   and c["n_rated"] + c["n_evidence_only"] + c["n_no_evidence"] == 5), r[1], r[2],
            ("ratings_have_evidence_and_rationale", all(cnt[f] >= 1 and rat[f].get("rationale", "").strip() and rat[f]["rating"] in RATINGS for f in rat) and all(a["forces"][f]["rating"] == rat[f]["rating"] for f in rat) and all(a["forces"][f]["rating"] is None and a["forces"][f]["rationale"] is None for f in FORCES if f not in rat)
                                                  and all(i["id"] in {x for x, _, dd, _ in raw if dd == f} for f in FORCES for i in a["forces"][f]["evidence"])),
            ("gaps_reported_not_filled", a["audit"]["forces_without_evidence"] == [f for f in FORCES if cnt[f] == 0] and all(a["forces"][f]["evidence"] == [] and a["forces"][f]["rating"] is None for f in a["audit"]["forces_without_evidence"])),
            ("no_aggregate_score_present", not any(k in a for k in ("score", "overall", "total_score")) and not any(k in a["counts"] for k in ("score", "overall"))), r[3], r[4]]

# ---------- Canvas and plan templates (B-108) ----------
# Structure and an evidence audit only: the student supplies every item, the
# system places it, reproduces it verbatim and reports what is missing.  It
# adds no fact, score, ranking or recommendation.
CANVAS_BLOCKS = {
    "template_business_model_canvas": {
        "key_partners": ("Key partners", "Who you depend on, and what each partner supplies"),
        "key_activities": ("Key activities", "The few things the business must do well to deliver the value"),
        "key_resources": ("Key resources", "What it needs to do those activities: people, equipment, cash, licences"),
        "value_propositions": ("Value propositions", "The value you promise each segment, in the customer's words"),
        "customer_relationships": ("Customer relationships", "How you win a customer, keep them and grow the relationship"),
        "channels": ("Channels", "How the value reaches the customer, from first contact to delivery"),
        "customer_segments": ("Customer segments", "Who you serve, described by need and behaviour, not demographics alone"),
        "cost_structure": ("Cost structure", "The main fixed and variable costs the model creates"),
        "revenue_streams": ("Revenue streams", "How the business earns, and what the customer pays for"),
    },
    "template_lean_canvas": {
        "problem": ("Problem", "The top problems you are solving"),
        "customer_segments": ("Customer segments", "Who has those problems"),
        "unique_value_proposition": ("Unique value proposition", "Why you are different and worth attention"),
        "solution": ("Solution", "The smallest thing that solves the problem"),
        "channels": ("Channels", "The route to customers"),
        "revenue_streams": ("Revenue streams", "How you earn"),
        "cost_structure": ("Cost structure", "The main costs"),
        "key_metrics": ("Key metrics", "The few numbers that show it is working"),
        "unfair_advantage": ("Unfair advantage", "What cannot easily be copied"),
    },
    "template_value_proposition_canvas": {
        "customer_jobs": ("Customer jobs", "What the customer is trying to get done"),
        "customer_pains": ("Pains", "What is costly, risky or annoying"),
        "customer_gains": ("Gains", "What the customer wants to gain"),
        "products_services": ("Products and services", "What you offer"),
        "pain_relievers": ("Pain relievers", "How you remove a stated pain"),
        "gain_creators": ("Gain creators", "How you create a stated gain"),
    },
    "template_marketing_plan": {
        "segmentation": ("Segmentation", "How the market is divided"),
        "targeting": ("Targeting", "Which segments you choose and why"),
        "positioning": ("Positioning", "The place you want to occupy in the customer's mind"),
        "product": ("Product", "What you sell, including features and quality"),
        "price": ("Price", "The price and the pricing rule"),
        "place": ("Place", "How the product reaches the customer"),
        "promotion": ("Promotion", "How you communicate and persuade"),
        "people": ("People", "The staff and service behaviour that carry the promise"),
        "process": ("Process", "The service process the customer experiences"),
        "physical_evidence": ("Physical evidence", "What the customer can see or touch"),
    },
    "template_kano": {
        "must_be": ("Must-be (basic)", "Attributes whose absence disappoints but whose presence earns no delight"),
        "performance": ("Performance (one-dimensional)", "Attributes where more is better and satisfaction rises with the level"),
        "attractive": ("Attractive (delighters)", "Attributes that delight when present but do not disappoint when absent"),
        "indifferent": ("Indifferent", "Attributes the customer does not care about either way"),
        "reverse": ("Reverse", "Attributes whose presence actually disappoints"),
    },
    "template_paid_media_plan": {
        "objective": ("Objective", "The declared campaign objective, such as reach, leads or sales"),
        "audience": ("Audience", "Who is targeted, and the evidence for that audience"),
        "channels_placements": ("Channels and placements", "The paid channels and where in each the message appears"),
        "budget_bid": ("Budget and bid", "Money allocated to each channel and the bid or buying method"),
        "creative_variants": ("Creative variants", "The messages and creative you will run, and the variants to compare"),
        "conversion_definition": ("Conversion definition", "What counts as a conversion, over what window, and who counts it"),
        "measurement": ("Measurement and checks", "The figures you will read at the end, from which source, and what would make you stop"),
    },
    "template_measurement_plan": {
        "questions": ("Questions", "The decision or question each measurement is meant to answer"),
        "metrics": ("Metrics", "The metrics, with the definition and the formula you will use"),
        "events_dimensions": ("Events and dimensions", "The events, parameters and dimensions that make the journey measurable"),
        "data_quality": ("Data quality", "Checks for duplicates, missing tags, bots and consent gaps"),
        "governance": ("Access, consent and ownership", "Who owns the tag, who may see the data, and what consent allows"),
    },
    "template_pestel": {
        "political": ("Political", "Government policy, stability, regulation and trade posture"),
        "economic": ("Economic", "Growth, inflation, interest and exchange rates, and demand"),
        "social": ("Social", "Demographics, culture, lifestyle and labour expectations"),
        "technological": ("Technological", "New technology, automation, research and diffusion"),
        "environmental": ("Environmental", "Climate, resources, emissions and physical risk"),
        "legal": ("Legal", "Laws, regulation, liability, licensing and compliance"),
    },
    "template_value_chain": {
        "firm_infrastructure": ("Support: firm infrastructure", "Planning, finance, legal, quality and management"),
        "human_resource_management": ("Support: human resource management", "Recruiting, developing and rewarding people"),
        "technology_development": ("Support: technology development", "Product, process and information technology"),
        "procurement": ("Support: procurement", "How inputs are bought, not the inputs themselves"),
        "inbound_logistics": ("Primary: inbound logistics", "Receiving, storing and moving inputs"),
        "operations": ("Primary: operations", "Turning inputs into the product or service"),
        "outbound_logistics": ("Primary: outbound logistics", "Storing and delivering the finished offer"),
        "marketing_and_sales": ("Primary: marketing and sales", "Winning customers and setting the offer"),
        "service": ("Primary: service", "Installing, supporting and keeping the offer working"),
    },
    "template_ansoff": {
        "market_penetration": ("Market penetration", "Existing products in existing markets"),
        "market_development": ("Market development", "Existing products in new markets"),
        "product_development": ("Product development", "New products in existing markets"),
        "diversification": ("Diversification", "New products in new markets"),
    },
    "template_blue_ocean_errc": {
        "eliminate": ("Eliminate", "Which factors the industry competes on should be eliminated?"),
        "reduce": ("Reduce", "Which factors should be reduced well below the industry standard?"),
        "raise": ("Raise", "Which factors should be raised well above the industry standard?"),
        "create": ("Create", "Which factors should be created that the industry has never offered?"),
    },
    "template_activity_system_fit": {
        "strategic_position": ("Strategic position", "The choice the activity system is meant to support"),
        "activities": ("Activities", "The main activities that deliver that position"),
        "reinforcing_choices": ("Reinforcing choices", "How the activities reinforce one another"),
        "boundaries": ("What we will not do", "Activities, segments or promises deliberately excluded"),
    },
    "template_project_charter": {
        "objective": ("Objective", "The outcome the project exists to deliver, in one testable statement"),
        "scope_in": ("In scope", "What the project will deliver and cover"),
        "scope_out": ("Out of scope", "What the project deliberately will not do"),
        "deliverables": ("Deliverables", "The verifiable outputs you will hand over"),
        "governance": ("Sponsor and governance", "Who authorises the project, who decides, and how change is controlled"),
        "budget": ("Budget and funding", "The declared budget, its source and the spending authority"),
        "milestones": ("Milestones", "The dated checkpoints and decisions, including the end date"),
        "success_measures": ("Success measures", "How completion and benefit will be judged, with baselines and targets"),
        "assumptions": ("Assumptions", "What must hold for the plan to work, marked as assumptions"),
        "constraints": ("Constraints and dependencies", "Fixed dates, resources, contracts or dependencies outside the project's control"),
    },
    "template_wbs": {
        "deliverables": ("Level 1 deliverables", "The major deliverables the project must produce"),
        "work_packages": ("Work packages", "The smallest pieces of work, each with an owner and a completion test"),
        "acceptance": ("Acceptance criteria", "The test that shows a deliverable or work package is complete"),
        "exclusions": ("Exclusions", "Work the WBS deliberately leaves out"),
    },
    "template_stakeholder_plan": {
        "stakeholders": ("Stakeholders", "Who is affected by the project or can affect it"),
        "interests": ("Interests and concerns", "What each stakeholder wants, fears or needs from the project"),
        "influence": ("Influence and impact", "The influence and impact labels you assign, with the evidence for them"),
        "engagement": ("Engagement approach", "How you will engage: inform, consult, involve or collaborate"),
        "messages": ("Key messages", "What each stakeholder needs to hear, in plain terms"),
        "channels": ("Channels", "The route the message takes: meeting, email, notice, report or one-to-one"),
        "frequency": ("Timing and frequency", "When and how often the communication happens, tied to milestones"),
        "owners": ("Communication owner", "Who is responsible for each message or channel"),
        "risks": ("Communication risks", "What could make the communication fail, and the response"),
    },
    "template_sipoc": {
        "suppliers": ("Suppliers", "Who supplies the process, and what each supplier provides"),
        "inputs": ("Inputs", "What the process consumes: materials, information, people, equipment, licences"),
        "process": ("Process steps", "The steps of the process in order, from the request to the delivery"),
        "outputs": ("Outputs", "What the process produces: the product, service or document it hands on"),
        "customers": ("Customers", "Who receives the output, inside or outside the organisation"),
    },
    "template_value_stream_map": {
        "process_steps": ("Process steps", "Each step of the flow, in order, with what it does"),
        "cycle_and_lead_times": ("Cycle and lead times", "The time each step takes and the time the whole flow takes"),
        "inventory_wip": ("Inventory and work in progress", "What waits between steps, and how much of it"),
        "waits_delays": ("Waits and delays", "Where the flow stops: queues, batches, hand-offs and approvals"),
        "value_added": ("Value-added assessment", "Which steps the customer would pay for, and which they would not"),
        "improvements": ("Improvement opportunities", "The changes you propose, and the measure that would show the effect"),
    },
    "template_toc": {
        "identify": ("Identify the constraint", "The resource or step that limits the whole system, and how you know"),
        "exploit": ("Exploit the constraint", "How the constraint is kept working on what only it can do"),
        "subordinate": ("Subordinate everything else", "How the other steps are paced to the constraint rather than to their own capacity"),
        "elevate": ("Elevate the constraint", "The capacity you add, and the evidence that it raises the system's output"),
        "reassess": ("Reassess", "Where the constraint moved once the change took hold, and the next constraint"),
    },
    "template_a3": {
        "problem": ("Problem", "The problem, stated with the gap between what happens and what should"),
        "current_condition": ("Current condition", "What actually happens now, and the evidence for it"),
        "target": ("Target condition", "What success looks like, and the measure that shows it"),
        "causes": ("Root causes", "The causes you can evidence, not the symptoms"),
        "countermeasures": ("Countermeasures", "The specific changes proposed against each evidenced cause"),
        "plan": ("Plan and owners", "Who does what, by when, and what each step depends on"),
        "follow_up": ("Follow-up", "When the effect is checked, on what measure, and what would trigger a rethink"),
    },
    "template_scor": {
        "plan": ("Plan", "How demand and supply are balanced: the plan the chain runs on"),
        "source": ("Source", "How inputs and goods are procured, and from whom"),
        "make": ("Make", "How the product or service is produced"),
        "deliver": ("Deliver", "How the finished offer reaches the customer"),
        "return": ("Return", "How returns, defects and reverse flows are handled"),
        "enable": ("Enable", "The rules, data, contracts and people that make the other five work"),
    },
    "template_5s": {
        "sort": ("Sort", "What is removed from the workplace because it is not needed"),
        "set_in_order": ("Set in order", "Where each thing belongs, and how that place is marked"),
        "shine": ("Shine", "What is cleaned, inspected and restored, and how often"),
        "standardize": ("Standardize", "The standard that keeps the first three in place"),
        "sustain": ("Sustain", "The audit, habit and owner that keep the standard alive"),
    },
    "template_root_cause": {
        "problem": ("Problem", "The effect, stated with where and when it happens"),
        "people": ("People", "Causes rooted in skills, staffing, training or behaviour"),
        "process": ("Process / method", "Causes rooted in the way the work is designed"),
        "equipment": ("Equipment", "Causes rooted in machines, tools or maintenance"),
        "materials": ("Materials", "Causes rooted in inputs, specifications or supply"),
        "measurement": ("Measurement", "Causes rooted in how the work is measured or judged"),
        "environment": ("Environment", "Causes rooted in the surroundings: layout, light, heat, noise"),
        "root_cause": ("Root cause", "The cause the evidence supports, and the test that showed it"),
    },
    "template_fmea": {
        "failure_modes": ("Failure modes", "The ways the process or product can fail"),
        "effects": ("Effects", "What each failure does to the customer or the next step"),
        "causes": ("Causes", "Why each failure mode happens"),
        "controls": ("Current controls", "What already detects or prevents it"),
        "actions": ("Recommended actions", "The change proposed for the highest-risk modes"),
        "owners": ("Owners and review", "Who acts, by when, and when the risk is reviewed again"),
    },
    "template_kraljic": {
        "criteria": ("Criteria", "How you judge profit impact and supply risk, and the cut-offs you use"),
        "strategic": ("Strategic items", "High impact, high risk: what they are and how they are managed"),
        "leverage": ("Leverage items", "High impact, low risk: what they are and how they are managed"),
        "bottleneck": ("Bottleneck items", "Low impact, high risk: what they are and how they are managed"),
        "non_critical": ("Non-critical items", "Low impact, low risk: what they are and how they are managed"),
    },
    "template_sop": {
        "demand_plan": ("Demand plan", "The demand the chain is planning for, and its basis"),
        "supply_plan": ("Supply plan", "What supply can deliver, and the constraints on it"),
        "inventory_plan": ("Inventory plan", "The stock the plan holds, and why"),
        "capacity_plan": ("Capacity plan", "The capacity the plan assumes, and where it binds"),
        "financial_plan": ("Financial plan", "The revenue, cost and margin the plan implies"),
        "decisions": ("Gaps and decisions", "Where the plans disagree, and the decision taken"),
    },
    "template_pdca": {
        "plan": ("Plan", "The problem, the target and the change you will try"),
        "do": ("Do", "What was actually done, on what scale, and when"),
        "check": ("Check", "What the measure showed, against the target"),
        "act": ("Act", "What is standardised, changed or abandoned, and what happens next"),
    },
    "template_lessons_learned": {
        "went_well": ("What went well", "Practices, decisions or behaviours that worked and should be repeated"),
        "went_poorly": ("What did not go well", "What failed, slipped or caused avoidable cost"),
        "causes": ("Why it happened", "The cause you can evidence, not blame"),
        "changes": ("What to change next time", "The specific change the next project should make"),
        "actions": ("Actions and owners", "Who will make the change, and by when"),
        "share": ("Who should see this", "The teams or roles that need the lesson"),
        "evidence": ("Evidence", "Records, incidents, change requests or data behind the lesson"),
    },
    "template_job_characteristics": {
        "skill_variety": ("Skill variety", "The range of skills and knowledge the role draws on"),
        "task_identity": ("Task identity", "Whether the role produces a whole, identifiable piece of work"),
        "task_significance": ("Task significance", "Whether the role's contribution is visible and consequential"),
        "autonomy": ("Autonomy", "The discretion the person has over how the work is done"),
        "feedback": ("Feedback", "How the person finds out how well the work is going"),
    },
    "template_kirkpatrick": {
        "reaction": ("Reaction", "What participants thought of the training and whether they valued it"),
        "learning": ("Learning", "What participants learned, and what they can show they learned it"),
        "behavior": ("Behaviour", "What participants did differently at work afterwards"),
        "results": ("Results", "What the organisation gained from the training"),
    },
    "template_amo": {
        "ability": ("Ability", "Whether the person has the skill and knowledge to do the work"),
        "motivation": ("Motivation", "Whether the person wants to do the work, and sees the reason to"),
        "opportunity": ("Opportunity", "Whether the person is allowed and equipped to do the work"),
    },
    "template_tuckman": {
        "forming": ("Forming", "The stage where the team is orienting itself to the task and to each other"),
        "storming": ("Storming", "The stage where roles, boundaries and ways of working are contested"),
        "norming": ("Norming", "The stage where the team settles on how it will work together"),
        "performing": ("Performing", "The stage where the team works together on the task"),
        "adjourning": ("Adjourning", "The stage where the team closes down, or changes shape"),
    },
    "template_nine_box": {
        "performance_criteria": ("Performance criteria", "How performance is judged, the criteria you use, and the evidence for each"),
        "potential_criteria": ("Potential criteria", "How potential is judged, the criteria you use, and the evidence for each"),
        "placements": ("Placements", "Where each person you name sits in the nine boxes, and why"),
        "development_actions": ("Development actions", "What the placements require you to do for each group"),
    },
    "template_kotter": {
        "urgency": ("Create urgency", "The case for change, and the evidence that it cannot wait"),
        "coalition": ("Form a powerful coalition", "Who must lead the change, and why that group"),
        "vision": ("Create a vision for change", "What the organisation is aiming at once the change is made"),
        "communicate": ("Communicate the vision", "How the vision reaches people, and what they are told"),
        "empower": ("Empower others to act", "What removes the barriers that stop people acting"),
        "wins": ("Plan for and create short-term wins", "The early results that show the change is working"),
        "consolidate": ("Consolidate gains and produce more change", "How the early wins are used to go further"),
        "institutionalize": ("Institutionalize new approaches", "What anchors the change in how the organisation works day to day"),
    },
    "template_competing_values": {
        "clan": ("Clan culture", "The orientation that puts people, commitment and development first"),
        "adhocracy": ("Adhocracy culture", "The orientation that puts experimentation, innovation and outside challenge first"),
        "market": ("Market culture", "The orientation that puts achievement, competition and the customer first"),
        "hierarchy": ("Hierarchy culture", "The orientation that puts structure, control and predictability first"),
    },
    "template_org_design": {
        "strategy": ("Strategy", "What the organisation is trying to achieve"),
        "decision_rights": ("Decision rights", "Who decides what, and who is accountable for it"),
        "structure": ("Structure", "How the roles and the work are grouped"),
        "processes": ("Processes", "How the work is actually done and governed"),
        "people_capability": ("People and capability", "The skills, roles and capacity the design needs"),
        "incentives": ("Incentives", "What the design rewards people for doing"),
    },
    "template_galbraith_star": {
        "strategy": ("Strategy", "What the organisation is trying to achieve"),
        "structure": ("Structure", "How work and authority are organised"),
        "processes": ("Processes", "How decisions are made and work flows"),
        "rewards": ("Rewards", "What the organisation pays people for"),
        "people": ("People", "The skills, mindsets and capabilities needed"),
    },
    "template_mintzberg": {
        "strategic_apex": ("Strategic Apex", "Those who define the mission and strategy"),
        "middle_line": ("Middle Line", "Those who translate strategy into action"),
        "operating_core": ("Operating Core", "Those who do the basic work of the organisation"),
        "technostructure": ("Technostructure", "Those who design and control the work"),
        "support_staff": ("Support Staff", "Those who provide indirect support"),
    },
    "template_logic_model": {
        "inputs": ("Inputs", "The resources and conditions brought to the effort"),
        "activities": ("Activities", "The actions and interventions carried out"),
        "outputs": ("Outputs", "The direct products of the activities"),
        "outcomes": ("Outcomes", "The short, medium and long-term results achieved"),
        "impact": ("Impact", "The long-term change the programme is meant to contribute to"),
    },
    "template_mckinsey_7s": {
        "strategy": ("Strategy", "The plan for competing and the choices that shape the firm"),
        "structure": ("Structure", "How the firm is organized and who reports to whom"),
        "systems": ("Systems", "The processes, procedures and routines that run the firm"),
        "shared_values": ("Shared Values", "The core values and culture that guide behaviour"),
        "style": ("Style", "The leadership style and how decisions are made"),
        "staff": ("Staff", "The people, their skills and how they are developed"),
        "skills": ("Skills", "The distinctive capabilities the firm possesses"),
    },
    "template_porters_diamond": {
        "factor_conditions": ("Factor Conditions", "The nations endowment of natural, human, capital and infrastructure resources"),
        "demand_conditions": ("Demand Conditions", "The nature of domestic demand and how it shapes competitive advantage"),
        "related_industries": ("Related and Supporting Industries", "The presence of supplier and related industries that are internationally competitive"),
        "firm_strategy": ("Firm Strategy, Structure and Rivalry", "How firms are created, organized and managed, and the nature of domestic rivalry"),
        "government": ("Government", "The role of government in shaping the diamond"),
        "chance": ("Chance", "The role of chance events in shaping competitive advantage"),
    },

    "template_strategic_positioning": {
        "position": ("Position", "Where the firm sits relative to competitors and customers"),
        "differentiation": ("Differentiation", "What makes the firm distinct from competitors"),
        "value_proposition": ("Value Proposition", "The value the firm delivers to customers"),
        "target_segment": ("Target Segment", "The customers the firm chooses to serve"),
    },
    "template_change_organization": {
        "change_type": ("Change Type", "The kind of change being made and its scope"),
        "readiness": ("Readiness", "Whether the organisation is ready for the change"),
        "resistance": ("Resistance", "What pushes back against the change"),
        "support": ("Support", "What enables and sustains the change"),
    },
    "template_stp": {
        "segmentation": ("Segmentation", "How the market is divided into segments"),
        "targeting": ("Targeting", "Which segments are chosen and why"),
        "positioning": ("Positioning", "How the offer is positioned in the market"),
    },
    "template_aida": {
        "attention": ("Attention", "How awareness is captured"),
        "interest": ("Interest", "How interest is sustained"),
        "desire": ("Desire", "How desire is created"),
        "action": ("Action", "How action is triggered"),
    },
    # template_customer_journey is deliberately NOT here: it is a grid (touchpoints x
    # stages), declared in MATRIX_META with its row and column labels.  It was in both
    # maps, which made describe() call it a canvas and gave the page the wrong editor
    # (D-MKT-04).  One artefact, one form.
    "template_funnel": {
        "awareness": ("Awareness", "How prospects enter the funnel"),
        "interest": ("Interest", "How interest is captured"),
        "consideration": ("Consideration", "How prospects evaluate"),
        "intent": ("Intent", "How intent is formed"),
        "evaluation": ("Evaluation", "How the final decision is made"),
        "purchase": ("Purchase", "How the purchase happens"),
    },
    "template_servqual": {
        "tangibles": ("Tangibles", "Physical facilities, equipment and appearance"),
        "reliability": ("Reliability", "Ability to perform the promised service dependably"),
        "responsiveness": ("Responsiveness", "Willingness to help customers and provide prompt service"),
        "assurance": ("Assurance", "Knowledge and courtesy of employees and their ability to inspire trust"),
        "empathy": ("Empathy", "Caring, individualised attention the firm provides its customers"),
    },
    "template_rfm": {
        "recency": ("Recency", "How recently the customer purchased"),
        "frequency": ("Frequency", "How often the customer purchases"),
        "monetary": ("Monetary", "How much the customer spends"),
    },
    "template_tam": {
        "perceived_usefulness": ("Perceived Usefulness", "How useful the technology is perceived to be"),
        "perceived_ease_of_use": ("Perceived Ease of Use", "How easy the technology is perceived to be"),
        "attitude": ("Attitude", "The attitude towards using the technology"),
        "behavioral_intention": ("Behavioral Intention", "The intention to use the technology"),
    },
    "template_utaut": {
        "performance_expectancy": ("Performance Expectancy", "How much the technology helps performance"),
        "effort_expectancy": ("Effort Expectancy", "How easy the technology is to use"),
        "social_influence": ("Social Influence", "How others influence adoption"),
        "facilitating_conditions": ("Facilitating Conditions", "The resources and support available"),
    },
    "template_brand_equity": {
        "awareness": ("Brand Awareness", "How well customers know the brand"),
        "associations": ("Brand Associations", "What customers associate with the brand"),
        "perceived_quality": ("Perceived Quality", "How customers perceive the quality"),
        "loyalty": ("Brand Loyalty", "How loyal customers are to the brand"),
    },
    "template_digital_mix": {
        "owned": ("Owned Channels", "Channels the brand controls"),
        "earned": ("Earned Channels", "Channels gained through PR and word of mouth"),
        "paid": ("Paid Channels", "Channels paid for advertising"),
    },
    "template_seo_content": {
        "keywords": ("Keywords", "The search terms targeted"),
        "content": ("Content", "The content created for search"),
        "technical": ("Technical SEO", "The technical optimisation of the site"),
        "links": ("Links", "The link building strategy"),
    },
    "template_email_crm": {
        "list": ("List", "The email list and its health"),
        "segments": ("Segments", "How the list is segmented"),
        "campaigns": ("Campaigns", "The email campaigns sent"),
        "automation": ("Automation", "The automated email flows"),
    },
    "template_social_media": {
        "platforms": ("Platforms", "Which social platforms are used"),
        "content": ("Content", "The content posted on social media"),
        "engagement": ("Engagement", "How audiences engage with the content"),
        "influencers": ("Influencers", "The influencers and partners used"),
    },
    "template_attribution": {
        "touchpoints": ("Touchpoints", "The customer touchpoints tracked"),
        "model": ("Attribution Model", "The model used to assign credit"),
        "credit": ("Credit Assignment", "How credit is assigned across touchpoints"),
        "reporting": ("Reporting", "How attribution is reported"),
    },
    "template_cro": {
        "hypothesis": ("Hypothesis", "The hypothesis being tested"),
        "variants": ("Variants", "The variants being tested"),
        "metrics": ("Metrics", "The metrics being tracked"),
        "results": ("Results", "The results of the test"),
    },
    "template_marketing_automation": {
        "triggers": ("Triggers", "What triggers automated actions"),
        "flows": ("Flows", "The automated marketing flows"),
        "scoring": ("Lead Scoring", "How leads are scored"),
        "nurture": ("Nurture", "How leads are nurtured"),
    },
    "template_stp_evidence": {
        "segmentation_evidence": ("Segmentation Evidence", "Evidence for the segmentation"),
        "targeting_evidence": ("Targeting Evidence", "Evidence for the targeting"),
        "positioning_evidence": ("Positioning Evidence", "Evidence for the positioning"),
    },

    "template_adkar": {
        "awareness": ("Awareness", "Why the change is needed and why now"),
        "desire": ("Desire", "Why change matters and what people gain"),
        "knowledge": ("Knowledge", "What people need to know and how they are taught"),
        "ability": ("Ability", "What people must do differently"),
        "reinforcement": ("Reinforcement", "What makes the change stick"),
    },
    "template_bcg": {
        "stars": ("Stars", "High growth, high market share - invest to grow"),
        "cash_cows": ("Cash Cows", "Low growth, high market share - harvest for cash"),
        "question_marks": ("Question Marks", "High growth, low market share - invest or divest"),
        "dogs": ("Dogs", "Low growth, low market share - divest or harvest"),
    },
    "template_burke_litwin": {
        "external_environment": ("External Environment", "The external forces that shape the organisation"),
        "mission_strategy": ("Mission and Strategy", "What the organisation is trying to achieve and how"),
        "leadership": ("Leadership", "The style and behaviour of those who lead"),
        "culture": ("Culture", "The shared values, beliefs and assumptions"),
        "structure": ("Structure", "How work is organised and authority is distributed"),
        "management_practices": ("Management Practices", "How managers actually behave and the systems they use"),
        "systems": ("Systems and Policies", "The formal procedures, policies and reward systems"),
        "work_unit_climate": ("Work Unit Climate", "The atmosphere and morale within teams"),
        "task_requirements": ("Task and Individual Skills", "The skills, abilities and motivation of individuals"),
        "motivation": ("Motivation", "What drives people to perform"),
        "individual_values": ("Individual Needs and Values", "What individuals want and value"),
        "performance": ("Individual and Organisational Performance", "The results the organisation achieves"),
    },
    "template_dmaic": {
        "define": ("Define", "The problem, the scope and the goal of the improvement"),
        "measure": ("Measure", "The baseline, the current performance and the data collected"),
        "analyze": ("Analyze", "The root causes and the evidence behind them"),
        "improve": ("Improve", "The changes tested and the results they produced"),
        "control": ("Control", "How the improvement is held in place going forward"),
    },
    "template_ge_mckinsey": {
        "high_high": ("High/High", "High industry attractiveness, high business strength - invest/grow"),
        "high_medium": ("High/Medium", "High industry attractiveness, medium business strength - invest/selectively"),
        "high_low": ("High/Low", "High industry attractiveness, low business strength - protect/selectively"),
        "medium_high": ("Medium/High", "Medium industry attractiveness, high business strength - invest/selectively"),
        "medium_medium": ("Medium/Medium", "Medium industry attractiveness, medium business strength - selectivity/earnings"),
        "medium_low": ("Medium/Low", "Medium industry attractiveness, low business strength - harvest/divest"),
        "low_high": ("Low/High", "Low industry attractiveness, high business strength - protect/earnings"),
        "low_medium": ("Low/Medium", "Low industry attractiveness, medium business strength - harvest/divest"),
        "low_low": ("Low/Low", "Low industry attractiveness, low business strength - divest/liquidate"),
    },
    "template_generic_strategies": {
        "low_cost": ("Low-Cost", "Aims to be the cheapest producer"),
        "differentiation": ("Differentiation", "Focuses on unique product features customers value"),
        "focus_low_cost": ("Focused Low-Cost", "Low cost within a narrow market segment"),
        "focus_differentiation": ("Focused Differentiation", "Unique value within a narrow market segment"),
    },
    "template_lewin": {
        "unfreeze": ("Unfreeze", "Prepare the organisation for change by undermining the existing status quo"),
        "change": ("Change", "Move the organisation to a new state through the steps the change requires"),
        "refreeze": ("Refreeze", "Anchor the new state in daily routines so the change sticks"),
    },
    "template_pdsa": {
        "plan": ("Plan", "What change is planned and what will be measured"),
        "do": ("Do", "What was carried out and on what scale"),
        "study": ("Study", "What the results show and what was learned"),
        "act": ("Act", "What is adopted, adapted or abandoned as a result"),
    },
    "template_theory_of_change": {
        "inputs": ("Inputs", "The resources and conditions brought to the change effort"),
        "activities": ("Activities", "The actions and interventions the change will carry out"),
        "outputs": ("Outputs", "The direct products of the activities, in expected quantity"),
        "outcomes": ("Outcomes", "The short, medium and long-term results the change aims to achieve"),
        "impact": ("Impact", "The longer-term change the programme is intended to contribute to"),
        "assumptions": ("Assumptions", "The conditions each link in the chain depends on"),
    },
}

CANVAS_META = {
    "template_business_model_canvas": {
        "name": "Business Model Canvas with an evidence audit", "short": "business model canvas", "registry_ids": ["STR-15"],
        "intended_use": "Lay your own evidence into the nine business-model blocks, link items that depend on each other, and audit which blocks are still empty or rest on assumptions.",
        "unsupported_use": "Inventing customers, partners, costs, revenue or value propositions; scoring or ranking business models; deciding whether the model will work.",
        "extra_help": "links: optional list of {from, to} item ids; a link records a declared dependency between two items and derives no direction, weight or score.",
    },
    "template_lean_canvas": {
        "name": "Lean Canvas with an evidence audit", "short": "lean canvas", "registry_ids": ["STR-16"],
        "intended_use": "Lay your own evidence into the nine lean-canvas blocks, state the problem and the unfair advantage, link related items and audit what is still missing.",
        "unsupported_use": "Inventing a problem, solution, metric or advantage; scoring or ranking; deciding product-market fit.",
        "extra_help": "links: optional list of {from, to} item ids; a link records a declared dependency between two items and derives no direction, weight or score.",
    },
    "template_value_proposition_canvas": {
        "name": "Value Proposition Canvas with an evidence audit", "short": "value proposition canvas", "registry_ids": ["STR-17"],
        "intended_use": "Lay your customer jobs, pains and gains beside your products, pain relievers and gain creators, link each relief to the pain it addresses, and audit the fit you have evidence for.",
        "unsupported_use": "Inventing customer jobs, pains or gains; claiming fit without evidence; scoring fit or ranking propositions.",
        "extra_help": "links: optional list of {from, to} item ids (for example a pain reliever to the pain it addresses); a link is a declared claim, not a tested fit.",
    },
    "template_marketing_plan": {
        "name": "Marketing plan: segmentation, targeting, positioning and the marketing mix with an evidence audit",
        "short": "marketing plan", "registry_ids": ["MKT-02"],
        "intended_use": "Structure your segmentation, targeting and positioning and the marketing mix, mark the evidence behind each item and audit the sections that are still empty.",
        "unsupported_use": "Choosing a segment or a price for you; inventing customers, competitors or promotions; scoring the plan; replacing market research.",
        "extra_help": "Product, price, place and promotion are the core mix; people, process and physical evidence are the service extension and may stay empty for a goods business.",
    },
    "template_pestel": {
        "name": "PESTEL with an evidence audit", "short": "PESTEL analysis", "registry_ids": ["STR-06"],
        "intended_use": "Organize your evidence on the political, economic, social, technological, environmental and legal context, date each item and audit the dimensions that are still empty.",
        "unsupported_use": "Inventing trends, forecasts or dates; treating a PESTEL list as a forecast; scoring or ranking the external environment; deciding strategy for you.",
        "extra_help": "Each item carries the provenance and, where relevant, the date you declare in its text; the system does not date, predict or weight an item.",
    },
    "template_value_chain": {
        "name": "Porter's Value Chain with an evidence audit", "short": "value chain", "registry_ids": ["STR-03"],
        "intended_use": "Lay your evidence about the five primary and four support activities beside one another, with provenance and materiality, and audit which activities are still empty.",
        "unsupported_use": "Inventing activity costs, margins or cost drivers; allocating costs to activities for you; scoring activities; deciding where advantage lies.",
        "extra_help": "Procurement is the purchasing activity, not the inputs bought; the support activities run across the primary ones. Cost and margin figures stay yours.",
    },
    "template_ansoff": {
        "name": "Ansoff growth matrix with an evidence audit", "short": "Ansoff matrix", "registry_ids": ["STR-09"],
        "intended_use": "Place your growth options in the four product/market cells, state the evidence and risks behind each and audit the cells that are still empty.",
        "unsupported_use": "Choosing a growth option for you; inventing market size, risk or capability evidence; scoring or ranking the cells.",
        "extra_help": "A cell records an option you are considering, not a recommendation. The same option may appear in more than one cell only if you supply it twice with different reasoning.",
    },
    "template_blue_ocean_errc": {
        "name": "Blue Ocean four actions (ERRC) with an evidence audit", "short": "ERRC grid", "registry_ids": ["STR-13"],
        "intended_use": "Organize your evidence behind the four actions - eliminate, reduce, raise and create - and audit which actions are still empty or rest on assumptions.",
        "unsupported_use": "Inventing competitor factors, customer evidence or cost/value hypotheses; scoring the value curve; deciding a blue-ocean move for you.",
        "extra_help": "This worksheet uses the four-action structure generically. Blue Ocean Strategy and the ERRC grid are associated with W. Chan Kim and Renee Mauborgne; no proprietary template is reproduced, and the strategy canvas (factor-by-offering curves) is not built here.",
    },
    "template_activity_system_fit": {
        "name": "Strategic positioning and activity-system fit with an evidence audit", "short": "activity-system map", "registry_ids": ["STR-04"],
        "intended_use": "State the position you are pursuing, list the activities that deliver it, record the fit you claim between activities, and audit what is missing or merely asserted.",
        "unsupported_use": "Choosing a position for you; inventing activities or fit; scoring fit or ranking positions; proving that a set of activities is hard to imitate.",
        "extra_help": "links: optional list of {from, to} activity item ids; a link records a fit you claim between two activities, not a tested relationship. 'What we will not do' keeps the trade-offs visible.",
    },
    "template_kano": {
        "name": "Kano classification with an evidence audit", "short": "Kano grid", "registry_ids": ["MKT-06"],
        "intended_use": "Place each attribute in the Kano category your survey supports - must-be, performance, attractive, indifferent or reverse - with the evidence and its source, and audit the empty categories.",
        "unsupported_use": "Deriving a category from the functional and dysfunctional answers for you; inventing survey results; scoring satisfaction; deciding which attribute to invest in.",
        "extra_help": "The category is your conclusion from the paired answers: the worksheet records and audits it, and applies no lookup table. The Kano model is associated with Noriaki Kano; no proprietary instrument is reproduced.",
    },
    "template_paid_media_plan": {
        "name": "Paid media plan with an evidence audit", "short": "paid media plan", "registry_ids": ["MKT-15"],
        "intended_use": "Set the campaign objective and audience, the channels and placements, the budget and bid for each, the creative variants and the conversion definition, and audit what is still asserted rather than evidenced.",
        "unsupported_use": "Choosing a budget, a bid or a channel for you; inventing audience, cost or platform data; predicting performance; replacing a media buy or the reach and rating-point arithmetic in `media_plan`.",
        "extra_help": "The plan is yours; the arithmetic that turns declared reach, insertions and cost into rating points lives in the `media_plan` tool, not here. A conversion definition must name the action and the window.",
    },
    "template_measurement_plan": {
        "name": "Web and app measurement plan with an evidence audit", "short": "measurement plan", "registry_ids": ["MKT-18"],
        "intended_use": "Tie each measurement question to a metric, the events and dimensions that produce it, the data-quality checks and the access and consent rules, and audit which parts are still missing.",
        "unsupported_use": "Reading an analytics platform; designing an event taxonomy for you; guessing volumes; certifying that a tag fires correctly or that consent is sufficient.",
        "extra_help": "Events and dimensions are declared, not deployed: the worksheet records the plan and its evidence, and nothing here reads a live property.",
    },
    "template_project_charter": {
        "name": "Project charter with an authorisation and scope audit", "short": "project charter", "registry_ids": ["PM-05"],
        "intended_use": "Write the authorisation for the project: objective, scope in and out, deliverables, sponsor and governance, budget, milestones, success measures, assumptions and constraints. Empty blocks are named, not filled.",
        "unsupported_use": "Choosing the objective, budget or sponsor for you; inventing a benefit, a date or an approval; calculating a business case; replacing the sponsor's decision.",
        "extra_help": "The charter records what you have agreed and what is still assumption. A benefit in the success measures is your claim, not a forecast, and the worksheet does not compute a business case.",
    },
    "template_wbs": {
        "name": "Work breakdown structure with a scope and acceptance audit", "short": "WBS", "registry_ids": ["PM-09"],
        "intended_use": "Break the declared scope into deliverables and work packages, give each a completion test, record what is excluded, and link each work package to the deliverable it belongs to.",
        "unsupported_use": "Inventing deliverables or acceptance criteria; estimating effort or cost for you; drawing a tree or Gantt; computing a total, a duration or a critical path; deciding the decomposition is complete.",
        "extra_help": "links: optional list of {from, to} item ids, normally a work package to its deliverable. The worksheet records the hierarchy you declare; it does not draw a tree, sum estimates or prove that the breakdown is mutually exclusive and complete.",
    },
    "template_stakeholder_plan": {
        "name": "Stakeholder engagement and communication plan with an evidence audit", "short": "stakeholder and communication plan", "registry_ids": ["PM-15"],
        "intended_use": "List the stakeholders, their interests and the influence you can evidence, then record how you will engage them, what you will say, through which channel, how often and who owns it. Empty blocks are named.",
        "unsupported_use": "Inventing stakeholders, interests, influence, messages or owners; scoring stakeholders; choosing an engagement strategy for you; guaranteeing that a stakeholder will be satisfied.",
        "extra_help": "The influence and impact entries are labels you declare with their evidence, not a computed power-interest score. A stakeholder with no owner or channel is shown as a gap.",
    },
    "template_toc": {
        "name": "Theory of Constraints: five focusing steps with an evidence audit", "short": "theory of constraints", "registry_ids": ["OPS-06"],
        "intended_use": "Record the system constraint you identified and, for each focusing step, what you are doing about it and the evidence behind the claim; the empty steps are named.",
        "unsupported_use": "Observing the line, measuring throughput or buffer sizes, scheduling with drum-buffer-rope, or deciding the constraint for you; an empty step is a gap, not a finding.",
        "extra_help": "The constraint and each step are yours. A step with no entry is named in the audit; the worksheet computes no throughput, buffer or saving.",
    },
    "template_a3": {
        "name": "A3 problem solving with an evidence audit", "short": "A3", "registry_ids": ["OPS-05"],
        "intended_use": "Work one problem through the A3 sections: problem, current condition, target, evidenced causes, countermeasures, the plan with owners, and the follow-up that tests the effect.",
        "unsupported_use": "Observing the process, timing a step or measuring a defect rate; inventing a cause without evidence; writing a countermeasure with no owner; computing a saving; judging whether the A3 is complete. Empty sections are named.",
        "extra_help": "A countermeasure with no owner, or a follow-up with no measure, is named as a gap. The worksheet records causes you can evidence and infers no motive.",
    },
    "template_scor": {
        "name": "SCOR supply-chain map with an evidence audit", "short": "SCOR", "registry_ids": ["OPS-01"],
        "intended_use": "Lay out the six SCOR processes - plan, source, make, deliver, return and enable - with the evidence for each, and name the processes you cannot evidence.",
        "unsupported_use": "Observing the chain, measuring SCOR metrics, benchmarking against a standard, computing a maturity score or deciding the network design; the worksheet organises declared evidence and computes nothing.",
        "extra_help": "Each process is described from your evidence. Empty processes are named in the audit; no metric, benchmark or maturity level is derived.",
    },
    "template_5s": {
        "name": "5S workplace audit with an evidence audit", "short": "5S", "registry_ids": ["OPS-04"],
        "intended_use": "Record what was done for each of the five S's - sort, set in order, shine, standardize and sustain - with the evidence and the owner, and name the steps still empty.",
        "unsupported_use": "Observing the workplace, scoring the audit, computing a 5S maturity level or assigning owners for you; an empty step is a gap, not a finding.",
        "extra_help": "A step with no evidence stays empty and is named. The worksheet computes no score and judges no workplace.",
    },
    "template_root_cause": {
        "name": "Root cause analysis: 5 Whys and fishbone with an evidence audit", "short": "root cause analysis", "registry_ids": ["OPS-07"],
        "intended_use": "State the problem, gather the candidate causes under the fishbone categories, and record the root cause the evidence supports and the test that showed it.",
        "unsupported_use": "Observing the process, declaring a cause without evidence, treating a diagram as proof of cause, or investigating the problem for you; candidate causes are yours and an unevidenced cause is flagged.",
        "extra_help": "A cause with no evidence is shown as a hypothesis, not a finding. The worksheet derives no cause and no priority.",
    },
    "template_fmea": {
        "name": "Failure mode and effects analysis with an evidence audit", "short": "FMEA", "registry_ids": ["OPS-08"],
        "intended_use": "List the failure modes, their effects and causes, the controls already in place, the actions proposed for the highest-risk modes, and who owns the review.",
        "unsupported_use": "Observing the process, computing a risk priority number, multiplying severity, occurrence and detection into a score, or ranking the modes for you; the labels you declare are recorded, not combined.",
        "extra_help": "Severity, occurrence and detection are labels you declare with their evidence; the worksheet multiplies nothing and produces no RPN.",
    },
    "template_kraljic": {
        "name": "Kraljic purchasing portfolio with an evidence audit", "short": "Kraljic", "registry_ids": ["OPS-10"],
        "intended_use": "Declare the criteria you use for profit impact and supply risk, then place each item in the strategic, leverage, bottleneck or non-critical quadrant with its evidence.",
        "unsupported_use": "Observing purchasing, scoring suppliers, computing a spend figure, or deciding the sourcing strategy for you; the criteria and the placements are yours and the empty quadrants are named.",
        "extra_help": "The two axes are declared, not measured. A quadrant with no item is named; no total spend, score or recommendation is produced.",
    },
    "template_sop": {
        "name": "Sales and operations plan with an evidence audit", "short": "S&OP", "registry_ids": ["OPS-11"],
        "intended_use": "Set the demand, supply, inventory, capacity and financial plans beside one another, name where they disagree, and record the decision taken.",
        "unsupported_use": "Observing the plans, forecasting demand, computing a capacity plan or balancing the plans for you; the figures are yours and the disagreements are named rather than resolved.",
        "extra_help": "The plans are declared. A plan with no entry is named, and a disagreement between plans is recorded with the decision you took.",
    },
    "template_pdca": {
        "name": "PDCA improvement cycle with an evidence audit", "short": "PDCA", "registry_ids": ["OPS-12"],
        "intended_use": "Record the plan, what was actually done, what the measure showed against the target, and what is standardised or changed as a result.",
        "unsupported_use": "Observing the trial, running the experiment, computing the improvement or deciding what to standardise for you; the cycle records what happened and what you decided.",
        "extra_help": "Each stage is recorded as declared. A stage with no entry is named; the worksheet computes no improvement and takes no decision.",
    },
    "template_lessons_learned": {
        "name": "Lessons learned with a cause and action audit", "short": "lessons learned", "registry_ids": ["PM-16"],
        "intended_use": "Record what went well and what did not, the cause you can evidence, the specific change for the next project, who owns it and who should see the lesson.",
        "unsupported_use": "Assigning blame, scoring the project, inventing a cause without evidence, or writing an action with no owner; turning a lesson into a claim about a person.",
        "extra_help": "A lesson without an action is named as a gap; an action without an owner is named too. The worksheet records causes you can evidence and does not infer motive.",
    },
    "template_sipoc": {
        "name": "SIPOC process map with an evidence audit", "short": "SIPOC", "registry_ids": ["OPS-02"],
        "intended_use": "Bound one process: who supplies it, what it consumes, the steps in order, what it hands on and who receives it. Every entry is yours, and each block you leave empty is named.",
        "unsupported_use": "Observing, timing or mapping the real process; measuring capacity, cycle time or quality; deciding which supplier or customer the process should serve; judging whether the map is correct.",
        "extra_help": "links: optional list of {from, to} item ids, normally an input to the process step that uses it or a step to its output. A link records a declared dependency; the worksheet draws no diagram, times no step and derives no sequence order.",
    },
    "template_value_stream_map": {
        "name": "Value stream map with an evidence audit", "short": "value stream map", "registry_ids": ["OPS-03"],
        "intended_use": "Record the steps of a flow, the times you observed or were given for each, what waits between them, which steps the customer would pay for, and the improvements you propose with the measure that would show the effect.",
        "unsupported_use": "Observing the flow or measuring a step yourself; computing takt time, throughput, bottleneck capacity or an improvement saving; classifying a step as value-added for you; claiming an improvement has been achieved.",
        "extra_help": "links: optional list of {from, to} item ids, normally a step to the step it feeds. A cycle or lead time you enter is a declared observation with its own provenance; the worksheet computes no total, no average and no takt.",
    },
    "template_job_characteristics": {
        "name": "Job Characteristics Model with an evidence audit", "short": "Job Characteristics Model", "registry_ids": ["PPL-03"],
        "intended_use": "Record the five job characteristics the model names - skill variety, task identity, task significance, autonomy and feedback - for the role, with the evidence for each, and name the characteristics you cannot evidence.",
        "unsupported_use": "Designing or redesigning the role, scoring the characteristics, validating the measures, or judging whether a job is well designed; the characteristics are yours to state and the empty ones are named.",
        "extra_help": "A characteristic with no evidence is named as a gap. The worksheet computes no score, validates no measure and infers nothing about the person in the role.",
    },
    "template_kirkpatrick": {
        "name": "Kirkpatrick training evaluation with an evidence audit", "short": "Kirkpatrick", "registry_ids": ["PPL-02"],
        "intended_use": "Record the evaluation at the four levels the model names - reaction, learning, behaviour and results - with the baseline, the measure and the follow-up interval for each.",
        "unsupported_use": "Running the evaluation, administering the survey, scoring the levels, or treating satisfaction as learning; a level with no measure is named and the worksheet computes nothing.",
        "extra_help": "The levels run from what participants thought to what the organisation gained. A high reaction score is not evidence of learning, behaviour or results.",
    },
    "template_amo": {
        "name": "AMO performance diagnosis with an evidence audit", "short": "AMO", "registry_ids": ["PPL-01"],
        "intended_use": "Diagnose whether the performance constraint lies in the person's ability, their motivation or the opportunity they are given, with the evidence for each, and name the constraint you cannot evidence.",
        "unsupported_use": "Measuring motivation, scoring the diagnosis, choosing the intervention for you, or claiming a cause; the categories lead to testable interventions that are yours to decide.",
        "extra_help": "A category with no evidence is named. The worksheet judges nothing, ranks no category and proposes no intervention.",
    },
    "template_tuckman": {
        "name": "Team development review using Tuckman's stages", "short": "Tuckman's stages", "registry_ids": ["PPL-05"],
        "intended_use": "Organise a discussion of where the team is and what it may need, using the five stages the model names, with the evidence you observe for each.",
        "unsupported_use": "Diagnosing the team, observing it for you, assigning people to a stage, or treating the stages as a sequence every team must pass through; the stages are a reflective heuristic.",
        "extra_help": "Not every team passes through the stages in order and many move back and forth. A stage with no evidence is named, and no person is assigned to a stage.",
    },
    "template_nine_box": {
        "name": "Nine-box talent grid with an evidence audit", "short": "Nine-box", "registry_ids": ["PPL-04"],
        "intended_use": "Declare the criteria you use for performance and for potential, record who you place and why, and state the action the placements require.",
        "unsupported_use": "Predicting future success, scoring or ranking people, calibrating on your behalf, or treating the grid as an objective measure; the placements are yours to defend and the criteria must be consistent.",
        "extra_help": "The grid places people on two declared axes. It carries no score and no ranking, and the bias safeguards and consistent criteria are yours to state.",
    },
    "template_kotter": {
        "name": "Kotter's eight-step change model with an evidence audit", "short": "Kotter's 8 steps", "registry_ids": ["CHG-01"],
        "intended_use": "Record the eight steps the model names in order - urgency, coalition, vision, communication, empowerment, short-term wins, consolidation and institutionalisation - with the evidence and the progress measure for each.",
        "unsupported_use": "Running the change, measuring adoption or outcome for you, or deciding the sequence for your organisation; the steps are recorded as evidence and the empty ones are named.",
        "extra_help": "A step with no evidence is named as a gap. The worksheet computes no adoption rate and no outcome indicator.",
    },
    "template_competing_values": {
        "name": "Competing Values Framework with an evidence audit", "short": "Competing Values", "registry_ids": ["CHG-12"],
        "intended_use": "Read the organisation's culture through the four competing orientations the model names - clan, adhocracy, market and hierarchy - with the survey or observation evidence behind each.",
        "unsupported_use": "Administering the survey, assigning a type to the organisation, or treating a profile as fixed; profiles are diagnostic and are read against the evidence rather than asserted.",
        "extra_help": "An orientation with no evidence is named. The worksheet assigns no type, computes no score and draws no profile.",
    },
    "template_org_design": {
        "name": "Organisational design star and fit review", "short": "org design review", "registry_ids": ["CHG-11"],
        "intended_use": "Check the fit between strategy, decision rights, structure, processes, people and incentives, and record where the fit breaks.",
        "unsupported_use": "Reorganising the organisation, deciding who decides what, or computing an alignment score; the review names the breaks and the design changes are yours to propose.",
        "extra_help": "The six elements are the ones the review names. A gap between two elements is recorded, not scored; the worksheet computes no alignment.",
    },

    "template_adkar": {
        "name": "ADKAR readiness review with an evidence audit", "short": "ADKAR review", "registry_ids": ["CHG-02"],
        "intended_use": "Read the evidence behind each of the five ADKAR elements for one change programme, and audit the elements that have no evidence behind them.",
        "unsupported_use": "Scoring readiness, diagnosing individual employees, or deciding what a person thinks; the elements describe the change and the evidence is yours.",
        "extra_help": "The five elements are the ones ADKAR names. An element with no evidence is named and left empty; the worksheet computes no readiness index.",
    },
    "template_aida": {
        "name": "AIDA journey with an evidence audit", "short": "AIDA journey", "registry_ids": ["MKT-03"],
        "intended_use": "Read the evidence at each stage of one communication journey and audit the stage the evidence cannot settle.",
        "unsupported_use": "Treating the journey as a rule, filling a stage, or deciding what to spend next; the stages are a simplified lens and the evidence is yours.",
        "extra_help": "The four stages are the ones AIDA names. A stage with no evidence is named and left empty; the worksheet computes no conversion rate.",
    },
    "template_attribution": {
        "name": "Attribution and campaign measurement with an evidence audit", "short": "attribution", "registry_ids": ["MKT-19"],
        "intended_use": "Record the touchpoints, the attribution rule and the credit it gives for one campaign, and audit the part the evidence cannot settle.",
        "unsupported_use": "Claiming what the campaign caused, choosing the model for you, or deriving a budget split; the rule is yours and no causal claim follows from it.",
        "extra_help": "The four parts are the ones the measurement frame names. A part with no evidence is named and left empty; the worksheet computes no share and derives no effect.",
    },
    "template_bcg": {
        "name": "BCG growth-share matrix with an evidence audit", "short": "BCG matrix", "registry_ids": ["STR-10"],
        "intended_use": "Read the evidence that places each business unit in a quadrant, and audit the placement the growth or share estimate cannot support.",
        "unsupported_use": "Deciding what to invest in or divest, ranking the units, or computing a portfolio plan; the quadrants record a placement and the decision is yours.",
        "extra_help": "The quadrants are the ones the matrix names. A quadrant with no evidence is named and left empty; the worksheet computes no growth rate and no share.",
    },
    "template_brand_equity": {
        "name": "Brand equity assessment with an evidence audit", "short": "brand equity", "registry_ids": ["MKT-11"],
        "intended_use": "Read the evidence behind the selected dimensions of one brand and audit the dimension the evidence cannot settle.",
        "unsupported_use": "Mixing variants of brand equity, inventing customer research, or scoring the brand; the measurement and the model are yours to name.",
        "extra_help": "The dimensions are the ones the selected model names. A dimension with no evidence is named and left empty; the worksheet computes no index.",
    },
    "template_burke_litwin": {
        "name": "Burke-Litwin organisational change review with an evidence audit", "short": "Burke-Litwin review", "registry_ids": ["CHG-05"],
        "intended_use": "Trace one change through the twelve elements of one organisation and audit the element the evidence cannot settle.",
        "unsupported_use": "Claiming a causal link between the elements, diagnosing the organisation, or prescribing the change; the elements are traced and the cause is yours to argue.",
        "extra_help": "The twelve elements are the ones the model names. An element with no evidence is named and left empty; the worksheet derives no causal claim.",
    },
    "template_change_organization": {
        "name": "Change and organisation review with an evidence audit", "short": "change and organisation review", "registry_ids": ["CHG-15"],
        "intended_use": "Read one programme of change against the organisation that has to carry it, and audit the element the evidence cannot settle.",
        "unsupported_use": "Predicting whether the change will succeed, diagnosing individual attitudes, or prescribing the intervention; the four elements are read and the plan is yours.",
        "extra_help": "The four elements are the ones the review names. An element with no evidence is named and left empty; the worksheet computes no readiness score.",
    },
    "template_cro": {
        "name": "Conversion-rate optimisation with an evidence audit", "short": "conversion test", "registry_ids": ["MKT-20"],
        "intended_use": "Record the hypothesis, the variants, the measures and the result of one conversion test, and audit the part the evidence cannot settle.",
        "unsupported_use": "Computing significance, recommending a winning variant, or reading a causal effect from a split; the test is yours and the worksheet derives no verdict.",
        "extra_help": "The four parts are the ones the test names. A part with no evidence is named and left empty; the worksheet computes no test and derives no winner.",
    },
    "template_digital_mix": {
        "name": "Digital marketing mix with an evidence audit", "short": "digital mix", "registry_ids": ["MKT-13"],
        "intended_use": "Record the role, the objective and the evidence for each kind of digital channel in one market, and audit the channel the evidence cannot settle.",
        "unsupported_use": "Allocating a budget, predicting reach, or choosing which channel to use; the roles and the amounts are yours and the worksheet allocates nothing.",
        "extra_help": "The three kinds of channel are the ones the mix names. A channel with no evidence is named and left empty; the worksheet computes no spend and derives no reach.",
    },
    "template_dmaic": {
        "name": "DMAIC improvement cycle with an evidence audit", "short": "DMAIC cycle", "registry_ids": ["CHG-10"],
        "intended_use": "Walk one process improvement through the five steps of DMAIC and audit the step the evidence cannot settle.",
        "unsupported_use": "Asserting a root cause without measurement, scoring the improvement, or certifying that the process is now controlled; the steps are recorded and the judgement is yours.",
        "extra_help": "The five steps are the ones DMAIC names. A step with no evidence is named and left empty; the worksheet derives no cause and computes no capability figure.",
    },
    "template_email_crm": {
        "name": "Email, CRM and lifecycle marketing with an evidence audit", "short": "email and CRM plan", "registry_ids": ["MKT-16"],
        "intended_use": "Record the list, the segments, the campaigns and the automation for one lifecycle programme, and audit the element the evidence cannot settle.",
        "unsupported_use": "Computing open or click rates, inventing consent, or claiming revenue from a send; the records are yours and the worksheet derives no figure.",
        "extra_help": "The four elements are the ones the programme names. An element with no evidence is named and left empty; the worksheet counts nothing and derives no engagement rate.",
    },
    "template_funnel": {
        "name": "Marketing funnel with an evidence audit", "short": "marketing funnel", "registry_ids": ["MKT-05"],
        "intended_use": "Read the stage definitions and the evidence at each stage of one funnel, and audit the stage with the largest unexplained drop.",
        "unsupported_use": "Setting the stage definitions for you, inventing conversion rates, or recommending where to spend; the stages and the rates are yours.",
        "extra_help": "The stages are the ones the funnel names. A stage with no evidence is named and left empty; the worksheet computes no conversion rate and derives no leak.",
    },
    "template_galbraith_star": {
        "name": "Galbraith star operating model review with an evidence audit", "short": "star model review", "registry_ids": ["CHG-06"],
        "intended_use": "Read the evidence across the five elements of one operating model and audit the element that does not hold the others up.",
        "unsupported_use": "Reorganising the organisation, choosing the shape of the model, or scoring how well the points of the star fit; the elements are read and the redesign is yours.",
        "extra_help": "The five elements are the ones the model names. An element with no evidence is named and left empty; the worksheet computes no fit score.",
    },
    "template_ge_mckinsey": {
        "name": "GE-McKinsey portfolio matrix with an evidence audit", "short": "GE-McKinsey matrix", "registry_ids": ["STR-11"],
        "intended_use": "Read the scores and weights that place each business unit in a cell, and audit the cell the evidence cannot support.",
        "unsupported_use": "Fixing the criteria or the weights, deriving a portfolio plan, or recommending an allocation; the worksheet records your judgments and derives no plan.",
        "extra_help": "The nine cells are the ones the matrix names. A cell with no evidence is named and left empty; the worksheet computes no score and applies no weighting.",
    },
    "template_generic_strategies": {
        "name": "Porter's generic strategies with an evidence audit", "short": "generic strategies", "registry_ids": ["STR-02"],
        "intended_use": "Read the evidence for where a firm sits against cost leadership and differentiation, and audit the choice the evidence cannot settle.",
        "unsupported_use": "Choosing a strategy for the firm, scoring the trade-off, or claiming the firm can hold both; the types are a lens and the choice is yours.",
        "extra_help": "The four types are the ones the model names. A type with no evidence is named and left empty; the worksheet computes no trade-off score.",
    },
    "template_lewin": {
        "name": "Lewin's three-stage change review with an evidence audit", "short": "Lewin review", "registry_ids": ["CHG-03"],
        "intended_use": "Read the evidence for the three stages of one change programme and audit the stage the evidence cannot settle.",
        "unsupported_use": "Claiming a change has succeeded, skipping a stage, or deciding how an organisation should feel; the stages are a lens and the evidence is yours.",
        "extra_help": "The three stages are the ones Lewin names. A stage with no evidence is named and left empty; the worksheet advances no programme and derives no verdict.",
    },
    "template_logic_model": {
        "name": "Logic model with an evidence audit", "short": "logic model", "registry_ids": ["CHG-08"],
        "intended_use": "Lay the inputs, activities, outputs, outcomes and impact of one programme beside each other and audit the element the evidence cannot settle.",
        "unsupported_use": "Measuring the outcomes, proving the programme worked, or filling an empty element; the worksheet distinguishes what is counted from what is achieved.",
        "extra_help": "Activities are what the programme does and outputs are what it produces directly; outcomes are the changes it aims to cause and impact is the longer-term change it contributes to. The worksheet keeps them apart and computes no indicator.",
    },
    "template_marketing_automation": {
        "name": "Marketing automation and lead scoring with an evidence audit", "short": "marketing automation", "registry_ids": ["MKT-21"],
        "intended_use": "Record the triggers, the flows, the score and the nurture for one automation set, and audit the element the evidence cannot settle.",
        "unsupported_use": "Validating a score, inventing lead data, or deriving revenue from a flow; the rules are yours and the worksheet derives no figure.",
        "extra_help": "The four elements are the ones the automation set names. An element with no evidence is named and left empty; the worksheet scores nothing and derives no revenue.",
    },
    "template_mckinsey_7s": {
        "name": "McKinsey 7-S alignment review with an evidence audit", "short": "7-S review", "registry_ids": ["CHG-04"],
        "intended_use": "Read the evidence across the seven elements of one organisation and record where the elements do not fit each other.",
        "unsupported_use": "Scoring alignment, ranking the elements, or redesigning the organisation; the review names the mismatch and the redesign is yours to propose.",
        "extra_help": "The seven elements are the ones the model names. No single score is authoritative, so the worksheet computes none.",
    },
    "template_mintzberg": {
        "name": "Mintzberg configuration review with an evidence audit", "short": "configuration review", "registry_ids": ["CHG-13"],
        "intended_use": "Read how one organisation is actually put together, part by part, and audit the part the evidence cannot settle.",
        "unsupported_use": "Assigning a configuration type, redesigning the organisation, or deciding which shape it should have; the parts are read and the diagnosis is yours.",
        "extra_help": "The five parts are the ones the model names. A part with no evidence is named and left empty; the worksheet assigns no type and computes no fit.",
    },
    "template_pdsa": {
        "name": "PDSA improvement cycle with an evidence audit", "short": "PDSA cycle", "registry_ids": ["CHG-09"],
        "intended_use": "Record one cycle of a small test of change, from the plan and the prediction to what was studied and what was adopted.",
        "unsupported_use": "Claiming the cycle succeeded, generalising from one cycle, or choosing what to adopt next; the worksheet records the cycle and the decision is yours.",
        "extra_help": "The four steps are the ones PDSA names. A step with no evidence is named and left empty; the worksheet computes no significance and derives no verdict.",
    },
    "template_porters_diamond": {
        "name": "Porter's Diamond with an evidence audit", "short": "Porter's Diamond", "registry_ids": ["STR-05"],
        "intended_use": "Read the conditions that shape one industry in its country and audit the determinant the evidence cannot settle.",
        "unsupported_use": "Attributing an advantage to a country, predicting a national outcome, or deciding where to locate; the determinants are read and the conclusion is yours.",
        "extra_help": "The determinants are the ones the model names. A determinant with no evidence is named and left empty; the worksheet derives no competitive verdict.",
    },
    "template_rfm": {
        "name": "RFM segmentation with an evidence audit", "short": "RFM segmentation", "registry_ids": ["MKT-08"],
        "intended_use": "Read the window, the scoring method and the evidence behind each RFM dimension for one customer list.",
        "unsupported_use": "Setting the window or the scoring bands, inventing customer data, or deriving lifetime value; the grouping is yours and the worksheet computes no segment.",
        "extra_help": "The three dimensions are the ones RFM names. A dimension with no evidence is named and left empty; the worksheet scores nothing and derives no segment.",
    },
    "template_seo_content": {
        "name": "SEO and content plan with an evidence audit", "short": "SEO and content plan", "registry_ids": ["MKT-14"],
        "intended_use": "Read the search demand, the page, the technical base and the links for one content plan, and audit the part the evidence cannot settle.",
        "unsupported_use": "Predicting traffic or a ranking, choosing the keywords for you, or writing the content; the demand and the pages are yours and the worksheet forecasts nothing.",
        "extra_help": "The four parts are the ones the plan names. A part with no evidence is named and left empty; the worksheet computes no search volume and derives no position.",
    },
    "template_social_media": {
        "name": "Social media and influencer marketing with an evidence audit", "short": "social and influencer plan", "registry_ids": ["MKT-17"],
        "intended_use": "Record the platforms, the content, the engagement measures and the creator terms for one plan, and audit the part the evidence cannot settle.",
        "unsupported_use": "Computing engagement rates, inventing creator terms, or recommending a platform; the plan and the terms are yours and the worksheet derives no figure.",
        "extra_help": "The four parts are the ones the plan names. A part with no evidence is named and left empty; the worksheet computes no reach and derives no rate.",
    },
    "template_stp": {
        "name": "Segmentation, targeting and positioning with an evidence audit", "short": "STP", "registry_ids": ["MKT-01"],
        "intended_use": "Lay the segmentation, the target choice and the positioning claim side by side for one market and audit the decision the evidence cannot settle.",
        "unsupported_use": "Choosing a segment for you, inventing customers or competitors, or scoring the fit; the three decisions are yours and the evidence is what you supply.",
        "extra_help": "The three elements are the ones STP names. An element with no evidence is named and left empty; the worksheet computes no market size and derives no position.",
    },
    "template_stp_evidence": {
        "name": "STP evidence-to-action check with an evidence audit", "short": "STP evidence check", "registry_ids": ["MKT-12"],
        "intended_use": "Audit each STP claim against the research behind it and name the claim that rests on nothing.",
        "unsupported_use": "Filling a gap with general background, scoring the evidence, or dropping a claim for you; the check names what is missing and the action is yours.",
        "extra_help": "This is a quality layer on an STP decision, not a second STP. Each claim is read against the research that supports it; the worksheet derives no option.",
    },
    "template_strategic_positioning": {
        "name": "Strategic positioning with an evidence audit", "short": "strategic positioning", "registry_ids": ["STR-19"],
        "intended_use": "Read one positioning claim from its four sides and audit the side the evidence cannot settle.",
        "unsupported_use": "Choosing the segment or the position, scoring the fit, or deciding whether the claim holds; the claim is read and the choice is yours.",
        "extra_help": "The four elements are the ones the review names. An element with no evidence is named and left empty; the worksheet derives no verdict on the position.",
    },
    "template_tam": {
        "name": "Technology Acceptance Model with an evidence audit", "short": "acceptance model", "registry_ids": ["MKT-09"],
        "intended_use": "Read the evidence behind the constructs of one acceptance model for the users of a system, and audit the construct the evidence cannot settle.",
        "unsupported_use": "Administering a survey, treating the constructs as a checklist for any adoption problem, or claiming the model predicts use; the evidence is yours.",
        "extra_help": "The constructs are the ones the model names. A construct with no evidence is named and left empty; the worksheet computes no scale and derives no intention.",
    },
    "template_theory_of_change": {
        "name": "Theory of change with an evidence audit", "short": "theory of change", "registry_ids": ["CHG-07"],
        "intended_use": "Lay the causal links from inputs through activities and outputs to outcomes and impact for one programme, name the assumptions each link rests on, and audit the links that rest on them.",
        "unsupported_use": "Claiming the causal pathway holds, proving impact, or filling a missing link; the links are hypotheses to test and the evidence is yours.",
        "extra_help": "Each link is a hypothesis. An assumption is flagged and left as it is; the worksheet derives no impact estimate.",
    },
    "template_utaut": {
        "name": "UTAUT with an evidence audit", "short": "UTAUT", "registry_ids": ["MKT-10"],
        "intended_use": "Read the evidence behind the constructs of one adoption model for the users of a system, and audit the construct the evidence cannot settle.",
        "unsupported_use": "Administering a survey, treating the constructs as a checklist for any adoption problem, or claiming the model predicts use; the evidence is yours.",
        "extra_help": "The constructs are the ones the model names. A construct with no evidence is named and left empty; the worksheet computes no scale and derives no intention.",
    },
}
CANVAS_MAX_ITEMS_PER_BLOCK = 20

#: Short id prefix per block, so a student can link two items by a readable id
#: (CS1, VP2, ...).  The prefix is presentation only; the engine accepts any id.
CANVAS_PREFIXES = {
    "template_business_model_canvas": {"key_partners": "KP", "key_activities": "KA", "key_resources": "KR",
                                       "value_propositions": "VP", "customer_relationships": "CR", "channels": "CH",
                                       "customer_segments": "CS", "cost_structure": "CO", "revenue_streams": "RS"},
    "template_lean_canvas": {"problem": "PR", "customer_segments": "CS", "unique_value_proposition": "UV",
                             "solution": "SO", "channels": "CH", "revenue_streams": "RS", "cost_structure": "CO",
                             "key_metrics": "KM", "unfair_advantage": "UA"},
    "template_value_proposition_canvas": {"customer_jobs": "CJ", "customer_pains": "CP", "customer_gains": "CG",
                                          "products_services": "PS", "pain_relievers": "PR", "gain_creators": "GC"},
    "template_marketing_plan": {"segmentation": "SG", "targeting": "TG", "positioning": "PO", "product": "PD",
                                "price": "PC", "place": "PL", "promotion": "PM", "people": "PE", "process": "PS",
                                "physical_evidence": "PH"},
    "template_project_charter": {"objective": "OBJ", "scope_in": "IN", "scope_out": "OUT", "deliverables": "DEL",
                                 "governance": "GOV", "budget": "BUD", "milestones": "MS", "success_measures": "SM",
                                 "assumptions": "AS", "constraints": "CON"},
    "template_wbs": {"deliverables": "DEL", "work_packages": "WP", "acceptance": "AC", "exclusions": "EX"},
    "template_stakeholder_plan": {"stakeholders": "STK", "interests": "INT", "influence": "INF", "engagement": "ENG",
                                  "messages": "MSG", "channels": "CH", "frequency": "FQ", "owners": "OWN", "risks": "CR"},
    "template_lessons_learned": {"went_well": "LW", "went_poorly": "LP", "causes": "CA", "changes": "CHG",
                                 "actions": "ACT", "share": "SH", "evidence": "EV"},
    "template_kano": {"must_be": "MB", "performance": "PF", "attractive": "AT", "indifferent": "IN", "reverse": "RV"},
    "template_paid_media_plan": {"objective": "OBJ", "audience": "AUD", "channels_placements": "CHP", "budget_bid": "BUD",
                                 "creative_variants": "CRE", "conversion_definition": "CONV", "measurement": "MSR"},
    "template_measurement_plan": {"questions": "QUE", "metrics": "MET", "events_dimensions": "EVT",
                                  "data_quality": "DQ", "governance": "GOV"},
    "template_sipoc": {"suppliers": "SUP", "inputs": "IN", "process": "P", "outputs": "OUT", "customers": "C"},
    "template_value_stream_map": {"process_steps": "ST", "cycle_and_lead_times": "TM", "inventory_wip": "WIP",
                                  "waits_delays": "DL", "value_added": "VA", "improvements": "IM"},
    "template_toc": {"identify": "ID", "exploit": "EX", "subordinate": "SUB", "elevate": "EL", "reassess": "RE"},
    "template_a3": {"problem": "PR", "current_condition": "CC", "target": "TG", "causes": "CA",
                    "countermeasures": "CM", "plan": "PL", "follow_up": "FU"},
    "template_scor": {"plan": "PL", "source": "SR", "make": "MK", "deliver": "DL", "return": "RT", "enable": "EN"},
    "template_5s": {"sort": "S1", "set_in_order": "S2", "shine": "S3", "standardize": "S4", "sustain": "S5"},
    "template_root_cause": {"problem": "PB", "people": "PE", "process": "PR", "equipment": "EQ",
                            "materials": "MA", "measurement": "ME", "environment": "EV", "root_cause": "RC"},
    "template_fmea": {"failure_modes": "FM", "effects": "EF", "causes": "CA", "controls": "CT",
                      "actions": "AC", "owners": "OW"},
    "template_kraljic": {"criteria": "CR", "strategic": "ST", "leverage": "LV", "bottleneck": "BN",
                         "non_critical": "NC"},
    "template_sop": {"demand_plan": "DM", "supply_plan": "SP", "inventory_plan": "IN", "capacity_plan": "CP",
                     "financial_plan": "FP", "decisions": "DC"},
    "template_pdca": {"plan": "PL", "do": "DO", "check": "CK", "act": "AC"},
    "template_job_characteristics": {"skill_variety": "SV", "task_identity": "TI", "task_significance": "TS",
                                     "autonomy": "AU", "feedback": "FB"},
    "template_kirkpatrick": {"reaction": "RE", "learning": "LE", "behavior": "BE", "results": "RS"},
    "template_amo": {"ability": "AB", "motivation": "MO", "opportunity": "OP"},
    "template_tuckman": {"forming": "FO", "storming": "ST", "norming": "NO", "performing": "PE", "adjourning": "AJ"},
    "template_nine_box": {"performance_criteria": "PC", "potential_criteria": "PO", "placements": "PL",
                          "development_actions": "DA"},
    "template_kotter": {"urgency": "UR", "coalition": "CO", "vision": "VI", "communicate": "CM", "empower": "EM",
                        "wins": "SW", "consolidate": "CG", "institutionalize": "IN"},
    "template_competing_values": {"clan": "CL", "adhocracy": "AD", "market": "MK", "hierarchy": "HI"},
    "template_org_design": {"strategy": "ST", "decision_rights": "DR", "structure": "SC", "processes": "PR",
                            "people_capability": "PC", "incentives": "IN"},

    "template_adkar": {"awareness": "AW", "desire": "DE", "knowledge": "KN", "ability": "AB", "reinforcement": "RE"},
    "template_aida": {"attention": "AT", "interest": "IN", "desire": "DE", "action": "AC"},
    "template_attribution": {"touchpoints": "TP", "model": "MD", "credit": "CR", "reporting": "RP"},
    "template_bcg": {"stars": "ST", "cash_cows": "CC", "question_marks": "QM", "dogs": "DG"},
    "template_brand_equity": {"awareness": "AW", "associations": "AS", "perceived_quality": "PQ", "loyalty": "LY"},
    "template_burke_litwin": {"external_environment": "EE", "mission_strategy": "MS", "leadership": "LD",
                               "culture": "CU", "structure": "SC", "management_practices": "MP", "systems": "SY",
                               "work_unit_climate": "WC", "task_requirements": "TR", "motivation": "MO",
                               "individual_values": "IV", "performance": "PF"},
    "template_change_organization": {"change_type": "CT", "readiness": "RD", "resistance": "RS", "support": "SU"},
    "template_cro": {"hypothesis": "HY", "variants": "VA", "metrics": "ME", "results": "RS"},
    "template_digital_mix": {"owned": "OW", "earned": "EA", "paid": "PD"},
    "template_dmaic": {"define": "DE", "measure": "ME", "analyze": "AN", "improve": "IM", "control": "CO"},
    "template_email_crm": {"list": "LI", "segments": "SG", "campaigns": "CA", "automation": "AU"},
    "template_funnel": {"awareness": "AW", "interest": "IN", "consideration": "CO", "intent": "IT", "evaluation": "EV",
                         "purchase": "PU"},
    "template_galbraith_star": {"strategy": "ST", "structure": "SC", "processes": "PR", "rewards": "RW", "people": "PE"},
    "template_ge_mckinsey": {"high_high": "HH", "high_medium": "HM", "high_low": "HL", "medium_high": "MH",
                              "medium_medium": "MM", "medium_low": "ML", "low_high": "LH", "low_medium": "LM",
                              "low_low": "LL"},
    "template_generic_strategies": {"low_cost": "LC", "differentiation": "DF", "focus_low_cost": "FL",
                                     "focus_differentiation": "FD"},
    "template_lewin": {"unfreeze": "UN", "change": "CH", "refreeze": "RF"},
    "template_logic_model": {"inputs": "IN", "activities": "AC", "outputs": "OU", "outcomes": "OC"},
    "template_marketing_automation": {"triggers": "TR", "flows": "FL", "scoring": "SC", "nurture": "NU"},
    "template_mckinsey_7s": {"strategy": "SG", "structure": "SC", "systems": "SY", "shared_values": "VA", "style": "ST",
                              "staff": "SF", "skills": "SK"},
    "template_mintzberg": {"strategic_apex": "SA", "middle_line": "ML", "operating_core": "OC", "technostructure": "TS",
                            "support_staff": "SS"},
    "template_pdsa": {"plan": "PL", "do": "DO", "study": "SY", "act": "AC"},
    "template_porters_diamond": {"factor_conditions": "FC", "demand_conditions": "DC", "related_industries": "RI",
                                  "firm_strategy": "FS", "government": "GV", "chance": "CH"},
    "template_rfm": {"recency": "RE", "frequency": "FR", "monetary": "MO"},
    "template_seo_content": {"keywords": "KW", "content": "CN", "technical": "TC", "links": "LK"},
    "template_social_media": {"platforms": "PF", "content": "CN", "engagement": "EN", "influencers": "IN"},
    "template_stp": {"segmentation": "SG", "targeting": "TG", "positioning": "PO"},
    "template_stp_evidence": {"segmentation_evidence": "SE", "targeting_evidence": "TE", "positioning_evidence": "PE"},
    "template_strategic_positioning": {"position": "PO", "differentiation": "DF", "value_proposition": "VP",
                                        "target_segment": "TS"},
    "template_tam": {"perceived_usefulness": "PU", "perceived_ease_of_use": "PE", "attitude": "AT",
                      "behavioral_intention": "BI"},
    "template_theory_of_change": {"inputs": "IN", "activities": "AC", "outputs": "OU", "outcomes": "OC"},
    "template_utaut": {"performance_expectancy": "PE", "effort_expectancy": "EE", "social_influence": "SI",
                        "facilitating_conditions": "FC"},
}


def _canvas_item(it, where, errs, used, n, prefix="E"):
    if not isinstance(it, dict):
        errs.append(f"{where} must be an object")
        return None
    text = it.get("text")
    if not isinstance(text, str) or not text.strip():
        errs.append(f"{where}: 'text' is required")
        return None
    text = text.strip()
    if len(text) > MAX_TEXT or CTRL.search(text):
        errs.append(f"{where}: text must be one line of at most {MAX_TEXT} characters")
        return None
    prov = it.get("provenance", "user")
    if prov not in PROV:
        errs.append(f"{where}: provenance must be one of {list(PROV)}")
        return None
    src = it.get("source")
    if prov == "sourced" and (not isinstance(src, str) or not src.strip() or CTRL.search(src)):
        errs.append(f"{where}: sourced evidence needs a 'source' (one line)")
        return None
    mat = it.get("materiality")
    if mat is not None and mat not in MATERIALITY:
        errs.append(f"{where}: materiality must be one of {list(MATERIALITY)}")
        return None
    iid = it.get("id", f"{prefix}{n}")
    if not isinstance(iid, str) or not ID_RE.fullmatch(iid):
        errs.append(f"{where}: id must be 1-20 letters, digits, - or _")
        return None
    if iid in used:
        errs.append(f"{where}: duplicate id {iid}")
        return None
    used.add(iid)
    return {"id": iid, "text": text, "provenance": prov,
            "source": src.strip() if isinstance(src, str) else None, "materiality": mat}


def normalize_canvas(kind, inp):
    errs = []
    if not isinstance(inp, dict):
        return None, ["inputs must be an object"]
    spec = CANVAS_BLOCKS[kind]
    extra = set(inp) - {"blocks", "links"}
    if extra:
        errs.append(f"unknown input {sorted(extra)}; allowed: ['blocks', 'links']")
    raw = inp.get("blocks")
    if not isinstance(raw, dict) or not raw:
        return None, ["'blocks' must be an object of block name -> list of evidence items"]
    unknown = [k for k in raw if k not in spec]
    if unknown:
        errs.append(f"unknown block(s) {sorted(unknown)}; allowed: {sorted(spec)}")
    blocks, used, n = {}, set(), 0
    total = 0
    for key in spec:
        if key not in raw:
            blocks[key] = []
            continue
        items = raw[key]
        if not isinstance(items, list):
            errs.append(f"blocks.{key} must be a list of evidence items")
            blocks[key] = []
            continue
        if len(items) > CANVAS_MAX_ITEMS_PER_BLOCK:
            errs.append(f"blocks.{key} allows at most {CANVAS_MAX_ITEMS_PER_BLOCK} items")
            items = []
        clean = []
        for i, it in enumerate(items, 1):
            n += 1
            item = _canvas_item(it, f"blocks.{key}[{i - 1}]", errs, used, n)
            if item:
                clean.append(item)
        blocks[key] = clean
        total += len(clean)
    if total == 0:
        errs.append("at least one block must carry an evidence item")
    raw_links = inp.get("links", [])
    links = []
    if not isinstance(raw_links, list) or len(raw_links) > 100:
        errs.append("'links' must be a list of at most 100 links")
        raw_links = []
    seen = set()
    for i, link in enumerate(raw_links, 1):
        if not isinstance(link, dict) or set(link) - {"from", "to"} or not {"from", "to"} <= set(link):
            errs.append(f"links[{i - 1}]: must be an object with 'from' and 'to' item ids")
            continue
        a, b = link["from"], link["to"]
        if a not in used or b not in used:
            errs.append(f"links[{i - 1}]: cites unknown item ids {[x for x in (a, b) if x not in used]}")
            continue
        if a == b:
            errs.append(f"links[{i - 1}]: an item cannot link to itself")
            continue
        if (a, b) in seen:
            continue
        seen.add((a, b))
        links.append({"from": a, "to": b})
    return ({"blocks": blocks, "links": links} if not errs else None), errs


def build_canvas(kind, inp):
    n, errs = normalize_canvas(kind, inp)
    if errs:
        raise DataError("; ".join(errs))
    spec = CANVAS_BLOCKS[kind]
    blocks = {k: {"label": spec[k][0], "prompt": spec[k][1], "items": n["blocks"][k]} for k in spec}
    items = [i for k in spec for i in blocks[k]["items"]]
    linked = {x for l in n["links"] for x in (l["from"], l["to"])}
    audit = {"empty_blocks": [k for k in spec if not blocks[k]["items"]],
             "unsupported_items": [i["id"] for i in items if i["provenance"] == "assumption"],
             "synthetic_items": [i["id"] for i in items if i["provenance"] == "synthetic"],
             "items_without_links": [i["id"] for i in items if i["id"] not in linked] if n["links"] else []}
    counts = {"n_items": len(items), "n_blocks": len(spec),
              "n_blocks_filled": sum(1 for k in spec if blocks[k]["items"]),
              "n_blocks_empty": len(audit["empty_blocks"]), "n_links": len(n["links"]),
              "n_unlinked": len(audit["items_without_links"]),
              "n_unsupported": len(audit["unsupported_items"])}
    return {"kind": kind, "registry_ids": CANVAS_META[kind]["registry_ids"], "name": CANVAS_META[kind]["name"],
            "short": CANVAS_META[kind]["short"],
            "blocks": blocks, "links": n["links"], "audit": audit, "counts": counts}


def render_canvas(a):
    P = PERIOD
    tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P)
    spec = CANVAS_BLOCKS[a["kind"]]
    a_ = a["audit"]
    t = (f"This {a['short']} organizes {tok('n_items')} evidence items "
         f"across {tok('n_blocks_filled')} of {tok('n_blocks')} blocks. ")
    if a_["empty_blocks"]:
        t += ("No evidence was supplied for: " + ", ".join(spec[k][0].lower() for k in a_["empty_blocks"]) +
              ". Those blocks are left empty and are not filled in by the system. ")
    if a["counts"]["n_unsupported"]:
        t += f"{tok('n_unsupported')} items rest on assumptions rather than user-supplied or sourced evidence. "
    if a_["synthetic_items"]:
        t += "Some items are synthetic and illustrative only; they are not observations. "
    if a["counts"]["n_links"]:
        t += (f"You declared {tok('n_links')} links between items, and {tok('n_unlinked')} items have no link. "
              "A link is your claim about how the items relate; it is not a test of fit. ")
    t += ("This worksheet organizes evidence only. It does not score, rank or choose between blocks or items, "
          "and it adds no facts of its own.")
    lines = []
    for k in spec:
        b = a["blocks"][k]
        lines.append(f"{b['label']} — {b['prompt']}")
        lines += [_line(i) for i in b["items"]] or ["  No evidence supplied."]
    if a["links"]:
        lines.append("Links you declared between items")
        which = {i["id"]: i["text"] for k in spec for i in a["blocks"][k]["items"]}
        lines += [f"  {l['from']} -> {l['to']}" for l in a["links"]]
    return t, "\n".join(lines)


def tests_canvas(kind, inp, a, narrative, listing):
    spec = CANVAS_BLOCKS[kind]
    raw, n = [], 0
    for key in spec:
        for it in (inp.get("blocks") or {}).get(key, []) or []:
            n += 1
            raw.append((it.get("id", f"E{n}"), it["text"].strip(), key))
    placed = [(i["id"], i["text"], key) for key in spec for i in a["blocks"][key]["items"]]
    c = a["counts"]
    texts_in = {t for _, t, _ in raw}
    texts_out = {i["text"] for key in spec for i in a["blocks"][key]["items"]}
    raw_links = [(l.get("from"), l.get("to")) for l in (inp.get("links") or [])]
    ids = {i for i, _, _ in raw}
    declared = {(f, t) for f, t in raw_links if f in ids and t in ids and f != t}
    placed_pairs = {(l["from"], l["to"]) for l in a["links"]}
    provs = {}
    n = 0
    for key in spec:
        for it in (inp.get("blocks") or {}).get(key, []) or []:
            n += 1
            provs[it.get("id", f"E{n}")] = it.get("provenance", "user")
    checks = [
        ("each_item_placed_exactly_once",
         sorted(i for i, _, _ in placed) == sorted(i for i, _, _ in raw) and len({i for i, _, _ in placed}) == len(raw),
         "every supplied item appears once, in its own block"),
        ("counts_agree_with_independent_recount",
         c["n_items"] == len(raw) and c["n_blocks_filled"] == sum(1 for k in spec if (inp.get("blocks") or {}).get(k))
         and c["n_links"] == len(declared) and c["n_blocks"] == len(spec),
         "the counts are recomputed from the raw input"),
        ("listing_reproduces_every_input_text_verbatim",
         all(f"• {t} — " in listing for i, t, _ in raw),
         "each item's text is reproduced exactly"),
        ("analysis_contains_only_supplied_text",
         texts_out == texts_in,
         "the analysis holds only the texts supplied"),
        ("empty_blocks_reported_not_filled",
         a["audit"]["empty_blocks"] == [k for k in spec if not (inp.get("blocks") or {}).get(k)]
         and all(a["blocks"][k]["items"] == [] for k in a["audit"]["empty_blocks"]),
         "a block with no evidence stays empty and is named"),
        ("links_resolve_to_supplied_items_and_are_kept_verbatim",
         placed_pairs == declared and all(l["from"] in ids and l["to"] in ids for l in a["links"]),
         "every kept link cites two supplied items, and nothing is added"),
        ("assumptions_and_synthetic_flagged",
         set(a["audit"]["unsupported_items"]) == {i for i, p in provs.items() if p == "assumption"}
         and set(a["audit"]["synthetic_items"]) == {i for i, p in provs.items() if p == "synthetic"},
         "assumption and synthetic items are listed as such"),
        ("no_score_or_ranking_present",
         not any(k in a for k in ("score", "overall", "ranking", "total_score"))
         and not any(k in c for k in ("score", "overall", "ranking")),
         "no score, ranking or overall judgement is produced"),
        ("rendering_is_deterministic", render_canvas(a) == (narrative, listing), "the same input renders the same text"),
    ]
    return [(name, ok) for name, ok, _ in checks]


def canvas_validate(kind):
    def validate(inp):
        return normalize_canvas(kind, inp)[1]
    return validate


# ---------- Declared-matrix templates (scenario planning, strategic groups) ----------
# Two frameworks whose output is a table of evidence: scenarios against drivers, or
# competitors against two declared axes.  The user supplies every cell, the system
# places it and names the empty cells.  It derives no position, probability or score.
MATRIX_META = {
    "template_scenario_planning": {
        "name": "Scenario planning matrix with an evidence audit", "short": "scenario matrix",
        "registry_ids": ["STR-14"], "row_label": "scenario", "column_label": "driver",
        "min_rows": 2, "max_rows": 4, "min_columns": 2, "max_columns": 6,
        "require_groups": False, "require_rationale": False,
        "intended_use": "Set two to four plausible scenarios against the drivers that distinguish them, record what you assume about each driver in each scenario, and audit the cells that are still empty.",
        "unsupported_use": "Forecasting, assigning probabilities or choosing the most likely scenario; inventing drivers or evidence; deciding a robust action for you.",
        "extra_help": "A cell states the direction or condition you assume for that driver in that scenario. Scenarios are not forecasts and carry no probability.",
        "form_copy": {
            "rows_label": "Scenarios",
            "cols_label": "Drivers",
            "cols_hint": "Two to six, one per line",
            "intro": ("List the scenarios you are planning for, then the drivers that distinguish them. "
                      "Each cell records what you assume about that driver in that scenario. Scenarios "
                      "are not forecasts and carry no probability, so no cell is scored. A cell you "
                      "cannot fill stays empty and is named in the audit."),
        },
    },
    "template_strategic_group_map": {
        "name": "Strategic group map with a declared-axis audit", "short": "strategic group map",
        "registry_ids": ["STR-12"], "row_label": "competitor", "column_label": "axis",
        "min_rows": 2, "max_rows": 12, "min_columns": 2, "max_columns": 2,
        "require_groups": True, "require_rationale": True,
        "intended_use": "List the competitors you have evidence for, declare and justify the two axes, place each competitor on both, and record the strategic group you assign.",
        "unsupported_use": "Choosing the axes or the groups for you; inventing competitor data; drawing or computing a position; scoring or ranking competitors.",
        "extra_help": "Exactly two axes are required, each with a one-line rationale. Placing a competitor is your judgment; the system only records and audits it.",
        "form_copy": {
            "rows_label": "Competitors",
            "cols_label": "Two axes",
            "cols_hint": "Exactly two, one per line",
            "intro": ("List the competitors you have evidence for, the group you assign to each, and "
                      "the two axes with a reason for each. Placing a competitor is your judgment; "
                      "the worksheet records and audits it, and draws and scores nothing. A cell you "
                      "cannot fill stays empty and is named in the audit."),
        },
    },
    "template_customer_journey": {
        "name": "Customer journey map with an evidence audit", "short": "journey map",
        "registry_ids": ["MKT-04"], "row_label": "touchpoint", "column_label": "stage",
        "min_rows": 3, "max_rows": 12, "min_columns": 2, "max_columns": 6,
        "require_groups": False, "require_rationale": False,
        "intended_use": "Lay the touchpoints you have evidence for against the journey stages you declare, record what the customer does, sees or feels at each crossing, and audit the cells you could not fill.",
        "unsupported_use": "Inventing stages, touchpoints or customer feelings; scoring friction or emotion; drawing a journey diagram; deciding where to intervene.",
        "extra_help": "A cell records what you know happens at that touchpoint in that stage, with its provenance. The stages and touchpoints are yours; nothing is plotted and no friction or sentiment score is computed.",
        "form_copy": {
            "rows_label": "Touchpoints",
            "cols_label": "Stages",
            "cols_hint": "Two to six, one per line",
            "intro": ("List the touchpoints you have evidence for, then the stages of the journey they "
                      "sit in. Each cell records what the customer does, sees or feels at that "
                      "crossing, with its source. Nothing is plotted and no friction or sentiment "
                      "score is computed. A cell you cannot fill stays empty and is named in the audit."),
        },
    },
    "template_servqual": {
        "name": "Service-quality gap grid with an evidence audit", "short": "SERVQUAL grid",
        "registry_ids": ["MKT-07"], "row_label": "service dimension", "column_label": "measure",
        "min_rows": 2, "max_rows": 10, "min_columns": 3, "max_columns": 5,
        "require_groups": False, "require_rationale": False,
        "intended_use": "Record, for each service dimension you declare, the expectation, the perception and the gap you concluded, with the evidence behind each, and audit the cells that are still empty.",
        "unsupported_use": "Computing an average, a weighted score or an overall service-quality index; designing the questionnaire; inventing responses; deciding what to improve.",
        "extra_help": "The conventional columns are the expectation, the perception and the gap; any numbers in a cell are yours, and the worksheet computes no average or score. The five SERVQUAL dimensions (tangibles, reliability, responsiveness, assurance, empathy) are associated with Parasuraman, Zeithaml and Berry; no proprietary instrument is reproduced.",
        "form_copy": {
            "rows_label": "Service dimensions",
            "cols_label": "Measures",
            "cols_hint": "Three to five, one per line",
            "intro": ("List the service dimensions you have evidence for, then the measures you took "
                      "on each: the expectation, the perception and the gap you concluded. Any number "
                      "in a cell is yours; the worksheet computes no average and no score. A cell you "
                      "cannot fill stays empty and is named in the audit."),
        },
    },
    "template_raci": {
        "name": "RACI responsibility matrix with a declared-role audit", "short": "RACI matrix",
        "registry_ids": ["PM-10"], "row_label": "activity", "column_label": "role",
        "min_rows": 2, "max_rows": 20, "min_columns": 2, "max_columns": 12,
        "require_groups": False, "require_rationale": False, "raci": True,
        "intended_use": "List the activities and the roles you have confirmed, then assign R, A, C or I to each cell: responsible does the work, accountable owns the outcome, consulted gives input, informed is kept up to date.",
        "unsupported_use": "Deciding who should be accountable; inventing roles or decision rights; scoring or ranking roles; enforcing an organisation chart or a single-A rule you have not declared.",
        "extra_help": "Each cell starts with one letter, R, A, C or I, optionally followed by a note (for example 'R - prepares the draft'). Every activity must have exactly one A and at least one R; the audit names any activity without them. A cell with no letter stays empty and is named.",
        "form_copy": {
            "rows_label": "Activities",
            "cols_label": "Roles",
            "cols_hint": "One role per line",
            "intro": ("List the activities and the roles you have confirmed. Then write R, A, C or I in each "
                      "cell: R does the work, A owns the outcome, C is consulted, I is informed. Every "
                      "activity needs exactly one A and at least one R. A cell you cannot fill stays empty "
                      "and is named in the audit."),
        },
    },
    "template_risk_register": {
        "name": "Risk register with a declared-response audit", "short": "risk register",
        "registry_ids": ["PM-06"], "row_label": "risk", "column_label": "field",
        "min_rows": 2, "max_rows": 30, "min_columns": 4, "max_columns": 4,
        "require_groups": False, "require_rationale": False,
        "intended_use": "List each risk, then record the likelihood and impact labels you declare, the response you will take and the owner. Audit which cells are still empty.",
        "unsupported_use": "Assigning probabilities, computing an expected loss or a risk score, ranking risks for you, or inventing a response or owner.",
        "extra_help": "Declare exactly four fields: Likelihood (your label), Impact (your label), Response and Owner. No probability, expected value or risk score is computed; an empty cell is named and stays empty.",
        "form_copy": {
            "rows_label": "Risks",
            "cols_label": "Fields",
            "cols_hint": "Four fields: likelihood, impact, response, owner",
            "intro": ("List the risks, then choose four fields: likelihood (your label), impact (your label), "
                      "response and owner. Likelihood and impact are labels you declare; no probability "
                      "or score is computed. A cell you cannot fill stays empty and is named in the audit."),
        },
    },
    "template_balanced_scorecard": {
        "name": "Balanced Scorecard with a declared-measure audit", "short": "balanced scorecard",
        "registry_ids": ["PM-01"], "row_label": "perspective", "column_label": "measure field",
        "min_rows": 4, "max_rows": 6, "min_columns": 4, "max_columns": 4,
        "require_groups": False, "require_rationale": False,
        "intended_use": "Declare the perspectives you are steering the project by, then record for each one the objective, the measure, the target and the initiative you have evidence for, and audit the cells that are still empty.",
        "unsupported_use": "Weighting the perspectives, scoring or ranking objectives, computing a composite index, inventing a measure or a target, or choosing the strategy for you.",
        "extra_help": "Declare exactly four fields per perspective: Objective, Measure, Target and Initiative. The four perspectives of the Balanced Scorecard (financial, customer/stakeholder, internal process, organisational capacity) are associated with Kaplan and Norton; no proprietary instrument is reproduced. Any figure in a cell is yours, and no score, weight or composite index is computed.",
        "form_copy": {
            "rows_label": "Perspectives",
            "cols_label": "Fields for each perspective",
            "cols_hint": "Exactly four: Objective, Measure, Target, Initiative - one per line",
            "intro": ("Write the perspectives you steer by, one per line. Then four fields for each: "
                      "the objective, the measure that shows it moving, the target you are aiming at "
                      "and the initiative that gets you there. A cell you cannot fill stays empty and "
                      "is named in the audit. No weights, no score."),
        },
    },
    "template_strategy_map": {
        "name": "Strategy map with a declared cause-and-effect audit", "short": "strategy map",
        "registry_ids": ["PM-02"], "row_label": "objective", "column_label": "map field",
        "min_rows": 4, "max_rows": 12, "min_columns": 4, "max_columns": 4,
        "require_groups": False, "require_rationale": False,
        "intended_use": "List the objectives you are steering by, place each in the perspective it belongs to, declare which other objective it drives, and record the measure that shows it moving. Audit the objectives with no driver and the cells that are still empty.",
        "unsupported_use": "Drawing the arrows for you, inferring a causal link you have not declared, weighting or ranking objectives, or inventing a measure.",
        "extra_help": "Declare exactly four fields per objective: Perspective, Objective, Drives (the objective it is meant to move) and Measure. A causal link exists only where you write one; the worksheet records it and never derives a chain, a weight or a score.",
        "form_copy": {
            "rows_label": "Objectives",
            "cols_label": "Fields for each objective",
            "cols_hint": "Exactly four: Perspective, Objective, Drives, Measure - one per line",
            "intro": ("Write the objectives you are steering by, one per line, then the four fields for "
                      "each: the perspective it belongs to, the objective itself, the objective it is "
                      "meant to drive and the measure that shows it moving. A link exists only where "
                      "you write it - the map does not draw arrows and does not infer a chain. A cell "
                      "you cannot fill stays empty and is named in the audit."),
        },
    },
    "template_kpi_tree": {
        "name": "KPI tree with a declared-formula audit", "short": "KPI tree",
        "registry_ids": ["PM-03"], "row_label": "metric", "column_label": "tree field",
        "min_rows": 3, "max_rows": 20, "min_columns": 4, "max_columns": 4,
        "require_groups": False, "require_rationale": False,
        "intended_use": "Record the outcome metric at the top of the tree, then the drivers it decomposes into and the inputs beneath them, with the formula or definition that connects each level and where the number comes from.",
        "unsupported_use": "Calculating a metric from raw data, choosing the drivers for you, weighting the branches, or inventing a source.",
        "extra_help": "Declare exactly four fields per metric: Level (outcome, driver or input), Metric, Formula or definition, and Source. The worksheet records the decomposition you declare; it computes no value and checks no arithmetic.",
        "form_copy": {
            "rows_label": "Metrics",
            "cols_label": "Fields for each metric",
            "cols_hint": "Exactly four: Level, Metric, Formula or definition, Source - one per line",
            "intro": ("Write the metrics on the tree, one per line: the outcome metric at the top, the "
                      "drivers beneath it and the inputs under those. Then the four fields for each: "
                      "the level it sits at, the metric itself, the formula or definition that connects "
                      "it and the source the number is read from. The tree records the decomposition "
                      "you declare and calculates nothing. A metric with no source stays empty and is "
                      "named in the audit."),
        },
    },
    "template_okrs": {
        "name": "OKR set with a declared-baseline audit", "short": "OKRs",
        "registry_ids": ["PM-04"], "row_label": "objective", "column_label": "OKR field",
        "min_rows": 1, "max_rows": 8, "min_columns": 4, "max_columns": 4,
        "require_groups": False, "require_rationale": False,
        "intended_use": "State each objective, then the key results under it with a baseline, a target and the source the number is read from. Audit the key results that have no baseline and the cells that are still empty.",
        "unsupported_use": "Turning an OKR into a score, an attainment percentage or a ranking; inventing a baseline or a target; writing your key results for you.",
        "extra_help": "Declare exactly four fields per objective: Objective, Key results, Baseline to target, and Source. A key result without a baseline cannot be judged at review, and the audit names it. No attainment score is computed.",
        "form_copy": {
            "rows_label": "Objectives",
            "cols_label": "Fields for each objective",
            "cols_hint": "Exactly four: Objective, Key results, Baseline to target, Source - one per line",
            "intro": ("Write the objectives you commit to, one per line. Then the four fields for each: "
                      "the objective itself, the key results that make it checkable, the baseline and "
                      "target they run from and the source the number is read from. A key result with no "
                      "baseline is named at audit, and no attainment score is produced. A field you "
                      "cannot fill stays empty."),
        },
    },
}


def _one_line(value, where, errs, required=False, what="text"):
    """Validate one optional or required single-line string."""
    if value is None:
        if required:
            errs.append(f"{where}: {what} is required")
        return None
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > MAX_TEXT or CTRL.search(value):
        errs.append(f"{where}: {what} must be one line of at most {MAX_TEXT} characters")
        return None
    return value.strip()


def normalize_matrix(kind, inp):
    errs = []
    spec = MATRIX_META[kind]
    if not isinstance(inp, dict):
        return None, ["inputs must be an object"]
    extra = set(inp) - {"rows", "columns", "cells"}
    if extra:
        errs.append(f"unknown input {sorted(extra)}; allowed: ['rows', 'columns', 'cells']")
    raw_rows = inp.get("rows")
    if not isinstance(raw_rows, list) or not (spec["min_rows"] <= len(raw_rows) <= spec["max_rows"]):
        return None, [f"'rows' must be a list of {spec['min_rows']} to {spec['max_rows']} {spec['row_label']}s"]
    rows, used = [], set()
    for n, it in enumerate(raw_rows, 1):
        row = _canvas_item(it, f"rows[{n - 1}]", errs, used, n, prefix="R")
        if not row:
            continue
        group = _one_line(it.get("group"), f"rows[{n - 1}]", errs, required=spec["require_groups"], what="'group'")
        if spec["require_groups"] and group is None:
            continue
        row["group"] = group
        rows.append(row)
    raw_columns = inp.get("columns")
    if not isinstance(raw_columns, list) or not (spec["min_columns"] <= len(raw_columns) <= spec["max_columns"]):
        return None, [f"'columns' must be a list of {spec['min_columns']} to {spec['max_columns']} {spec['column_label']}s"]
    columns, col_used = [], set()
    for n, it in enumerate(raw_columns, 1):
        column = _canvas_item(it, f"columns[{n - 1}]", errs, col_used, n, prefix="C")
        if not column:
            continue
        rationale = _one_line(it.get("rationale"), f"columns[{n - 1}]", errs, required=spec["require_rationale"], what="'rationale'")
        if spec["require_rationale"] and rationale is None:
            continue
        column["rationale"] = rationale
        columns.append(column)
    raw_cells = inp.get("cells")
    if not isinstance(raw_cells, list) or not raw_cells:
        return None, ["'cells' must be a non-empty list of {row, column, text, provenance} objects"]
    if len(raw_cells) > spec["max_rows"] * spec["max_columns"]:
        errs.append(f"at most {spec['max_rows'] * spec['max_columns']} cells")
    row_ids = {r["id"] for r in rows}
    column_ids = {c["id"] for c in columns}
    cells, seen, cell_used = [], set(), set()
    for n, it in enumerate(raw_cells, 1):
        where = f"cells[{n - 1}]"
        if not isinstance(it, dict):
            errs.append(f"{where} must be an object")
            continue
        row_id, column_id = it.get("row"), it.get("column")
        if row_id not in row_ids:
            errs.append(f"{where}: 'row' must be one of {sorted(row_ids)}")
            continue
        if column_id not in column_ids:
            errs.append(f"{where}: 'column' must be one of {sorted(column_ids)}")
            continue
        if (row_id, column_id) in seen:
            errs.append(f"{where}: duplicate cell for row {row_id}, column {column_id}")
            continue
        cell = _canvas_item(it, where, errs, cell_used, n, prefix="X")
        if not cell:
            continue
        if spec.get("raci"):
            letter = re.match(r"^([RACI])(?:\s*[-—:]\s*(.*))?$", cell["text"], re.I)
            if not letter:
                errs.append(f"{where}: text must start with one letter, R, A, C or I, optionally followed by a note")
                continue
            cell["assignment"] = letter.group(1).upper()
        seen.add((row_id, column_id))
        cells.append({"row": row_id, "column": column_id, "text": cell["text"], "provenance": cell["provenance"],
                      "source": cell["source"], "materiality": cell["materiality"],
                      **({"assignment": cell["assignment"]} if spec.get("raci") else {})})
    return ({"rows": rows, "columns": columns, "cells": cells} if not errs else None), errs


def build_matrix(kind, inp):
    n, errs = normalize_matrix(kind, inp)
    if errs:
        raise DataError("; ".join(errs))
    spec = MATRIX_META[kind]
    by = {(c["row"], c["column"]): c for c in n["cells"]}
    rows = []
    for row in n["rows"]:
        rows.append({**row, "cells": {c["id"]: by.get((row["id"], c["id"])) for c in n["columns"]}})
    audit = {
        "empty_cells": [f"{r['id']}:{c['id']}" for r in n["rows"] for c in n["columns"] if (r["id"], c["id"]) not in by],
        "rows_without_cells": [r["id"] for r in n["rows"] if not any((r["id"], c["id"]) in by for c in n["columns"])],
        "columns_without_cells": [c["id"] for c in n["columns"] if not any((r["id"], c["id"]) in by for r in n["rows"])],
        "unsupported_cells": [f"{c['row']}:{c['column']}" for c in n["cells"] if c["provenance"] == "assumption"],
        "synthetic_cells": [f"{c['row']}:{c['column']}" for c in n["cells"] if c["provenance"] == "synthetic"],
        "rows_without_group": [r["id"] for r in n["rows"] if spec["require_groups"] and not r.get("group")],
    }
    counts = {"n_rows": len(n["rows"]), "n_columns": len(n["columns"]), "n_cells": len(n["cells"]),
              "n_empty_cells": len(audit["empty_cells"]), "n_unsupported": len(audit["unsupported_cells"]),
              "n_rows_without_group": len(audit["rows_without_group"])}
    if spec.get("raci"):
        audit["rows_without_accountable"] = [
            r["id"] for r in n["rows"]
            if sum(1 for c in n["cells"] if c["row"] == r["id"] and c.get("assignment") == "A") != 1]
        audit["rows_without_responsible"] = [
            r["id"] for r in n["rows"]
            if not any(c["row"] == r["id"] and c.get("assignment") == "R" for c in n["cells"])]
        counts["n_rows_without_accountable"] = len(audit["rows_without_accountable"])
        counts["n_rows_without_responsible"] = len(audit["rows_without_responsible"])
    return {"kind": kind, "registry_ids": spec["registry_ids"], "name": spec["name"], "short": spec["short"],
            "row_label": spec["row_label"], "column_label": spec["column_label"],
            "rows": rows, "columns": n["columns"], "audit": audit, "counts": counts}


def render_matrix(a):
    P = PERIOD
    tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P)
    a_ = a["audit"]
    t = (f"This {a['short']} organizes {tok('n_rows')} {_plural(a['row_label'])} against {tok('n_columns')} "
         f"{a['column_label']}s, with {tok('n_cells')} cells of evidence you supplied. ")
    if a_["empty_cells"]:
        t += f"{tok('n_empty_cells')} cells are empty. They are named below and are not filled in by the system. "
    if a["counts"]["n_unsupported"]:
        t += f"{tok('n_unsupported')} cells rest on assumptions rather than user-supplied or sourced evidence. "
    if a_["synthetic_cells"]:
        t += "Some cells are synthetic and illustrative only; they are not observations. "
    if a_["rows_without_group"]:
        t += f"{len(a_['rows_without_group'])} {_plural(a['row_label'])} have no declared group. "
    if a_.get("rows_without_accountable"):
        t += f"{len(a_['rows_without_accountable'])} activities do not have exactly one accountable role. "
    if a_.get("rows_without_responsible"):
        t += f"{len(a_['rows_without_responsible'])} activities have no responsible role. "
    t += ("This worksheet records the evidence and assumptions you declare. It attaches no probability, computes no "
          "position, ranks nothing and predicts nothing.")
    lines = []
    if any(c.get("rationale") for c in a["columns"]):
        lines.append(f"The {a['column_label']}s you declared, and why")
        lines += [f"  {c['text']} — {c['rationale']}" for c in a["columns"]]
    for row in a["rows"]:
        head = row['text']
        if row.get("group"):
            head += f" — group: {row['group']}"
        lines.append(head)
        for column in a["columns"]:
            cell = row["cells"][column["id"]]
            lines.append(f"  {column['text']}: " + (
                f"{cell['text']} — {_label(cell)}" + (f"; materiality: {cell['materiality']} (your rating)" if cell.get("materiality") else "")
                if cell else "No evidence supplied."))
    return t, "\n".join(lines)


def tests_matrix(kind, inp, a, narrative, listing):
    spec = MATRIX_META[kind]
    raw_rows = inp.get("rows") or []
    raw_columns = inp.get("columns") or []
    raw_cells = inp.get("cells") or []
    row_ids = [r.get("id", f"R{n}") for n, r in enumerate(raw_rows, 1)]
    column_ids = [c.get("id", f"C{n}") for n, c in enumerate(raw_columns, 1)]
    declared = [(c.get("row"), c.get("column")) for c in raw_cells]
    placed = [(r["id"], cid) for r in a["rows"] for cid, cell in r["cells"].items() if cell]
    texts_in = ({r["text"].strip() for r in raw_rows} | {c["text"].strip() for c in raw_columns}
                | {c["text"].strip() for c in raw_cells} | {str(r.get("group")).strip() for r in raw_rows if r.get("group")}
                | {str(c.get("rationale")).strip() for c in raw_columns if c.get("rationale")})
    texts_out = ({r["text"] for r in a["rows"]} | {c["text"] for c in a["columns"]}
                 | {cell["text"] for r in a["rows"] for cell in r["cells"].values() if cell}
                 | {r["group"] for r in a["rows"] if r.get("group")}
                 | {c["rationale"] for c in a["columns"] if c.get("rationale")})
    empty = [f"{rid}:{cid}" for rid in row_ids for cid in column_ids if (rid, cid) not in set(declared)]
    checks = [
        ("each_cell_placed_exactly_once", sorted(placed) == sorted(declared) and len(set(placed)) == len(declared),
         "every supplied cell appears once, under its own row and column"),
        ("counts_agree_with_independent_recount",
         a["counts"]["n_rows"] == len(raw_rows) and a["counts"]["n_columns"] == len(raw_columns)
         and a["counts"]["n_cells"] == len(set(declared)), "the counts are recomputed from the raw input"),
        ("listing_reproduces_every_input_text_verbatim",
         all(r["text"] in listing for r in a["rows"])
         and all(f"  {c['text']}: " in listing for c in a["columns"])
         and all((not cell) or f"{cell['text']} — " in listing for r in a["rows"] for cell in r["cells"].values()),
         "each row, column and cell text is reproduced exactly"),
        ("analysis_contains_only_supplied_text", texts_out == texts_in, "the analysis holds only the texts supplied"),
        ("empty_cells_reported_not_filled",
         a["audit"]["empty_cells"] == empty and all(r["cells"][cid] is None for r in a["rows"] for cid in r["cells"] if f"{r['id']}:{cid}" in empty),
         "an empty cell is named and stays empty"),
        ("assumptions_and_synthetic_flagged",
         set(a["audit"]["unsupported_cells"]) == {f"{c.get('row')}:{c.get('column')}" for c in raw_cells if c.get("provenance", "user") == "assumption"}
         and set(a["audit"]["synthetic_cells"]) == {f"{c.get('row')}:{c.get('column')}" for c in raw_cells if c.get("provenance", "user") == "synthetic"},
         "assumption and synthetic cells are listed as such"),
        ("no_score_ranking_or_probability",
         not any(k in a for k in ("score", "overall", "ranking", "probability", "total_score"))
         and not any(k in a["counts"] for k in ("score", "overall", "ranking", "probability")),
         "no score, probability, ranking or overall judgement is produced"),
        ("rendering_is_deterministic", render_matrix(a) == (narrative, listing), "the same input renders the same text"),
    ]
    if spec["require_rationale"]:
        checks.insert(4, ("axes_are_declared_with_a_rationale",
                          len(a["columns"]) == 2 and all(c.get("rationale") for c in a["columns"]),
                          "both axes are declared and each carries a reason"))
    if spec["require_groups"]:
        checks.insert(5, ("every_row_declares_a_group",
                          all(r.get("group") for r in a["rows"]), "every competitor carries the group you assigned"))
    if spec.get("raci"):
        raw_by_row = {}
        for cell in raw_cells:
            raw_by_row.setdefault(cell.get("row"), []).append(str(cell.get("text", "")).strip()[:1].upper())
        expected_no_a = [rid for rid in row_ids
                         if sum(1 for letter in raw_by_row.get(rid, []) if letter == "A") != 1]
        expected_no_r = [rid for rid in row_ids if "R" not in raw_by_row.get(rid, [])]
        checks.insert(6, ("every_activity_has_exactly_one_accountable",
                          a["audit"]["rows_without_accountable"] == expected_no_a and not expected_no_a,
                          "each activity has exactly one A"))
        checks.insert(7, ("every_activity_has_at_least_one_responsible",
                          a["audit"]["rows_without_responsible"] == expected_no_r and not expected_no_r,
                          "each activity has at least one R"))
    return [(name, ok) for name, ok, _ in checks]


def matrix_validate(kind):
    def validate(inp):
        return normalize_matrix(kind, inp)[1]
    return validate


# ---------- VRIO (declared answers, no derived verdict) ----------
# Each resource carries the student's four answers and the evidence behind them.  The
# system reports completeness and unsupported answers; it deliberately does not turn
# VRIO into a yes/no score or derive the competitive implication for the student.
VRIO_QUESTIONS = {
    "valuable": ("V - Valuable", "Does the resource enable the firm to exploit an opportunity or neutralise a threat?"),
    "rare": ("R - Rare", "Is it held by few current or potential competitors?"),
    "costly_to_imitate": ("I - Costly to imitate", "Would competitors face a cost or difficulty in imitating it?"),
    "organized": ("O - Organized to capture value", "Do the firm's structure and processes let it capture the value?"),
}
VRIO_ANSWERS = ("yes", "no", "unsure")


def normalize_vrio(inp):
    errs = []
    if not isinstance(inp, dict):
        return None, ["inputs must be an object"]
    extra = set(inp) - {"resources"}
    if extra:
        errs.append(f"unknown input {sorted(extra)}; allowed: ['resources']")
    raw = inp.get("resources")
    if not isinstance(raw, list) or not raw:
        return None, ["'resources' must be a non-empty list of resources"]
    if len(raw) > 12:
        return None, ["at most 12 resources"]
    resources, used, ev_used, n_ev = [], set(), set(), 0
    for n, it in enumerate(raw, 1):
        where = f"resources[{n - 1}]"
        resource = _canvas_item(it, where, errs, used, n, prefix="R")
        if not resource:
            continue
        answers = it.get("answers")
        if not isinstance(answers, dict) or set(answers) != set(VRIO_QUESTIONS):
            errs.append(f"{where}: 'answers' must carry exactly {sorted(VRIO_QUESTIONS)}")
            continue
        clean, bad = {}, False
        for question in VRIO_QUESTIONS:
            if answers[question] not in VRIO_ANSWERS:
                errs.append(f"{where}.answers.{question}: must be one of {list(VRIO_ANSWERS)} (your answer)")
                bad = True
            else:
                clean[question] = answers[question]
        if bad:
            continue
        raw_ev = it.get("evidence", [])
        if not isinstance(raw_ev, list) or len(raw_ev) > 20:
            errs.append(f"{where}.evidence must be a list of at most 20 items")
            raw_ev = []
        evidence = []
        for j, item in enumerate(raw_ev, 1):
            n_ev += 1
            ewhere = f"{where}.evidence[{j - 1}]"
            entry = _canvas_item(item, ewhere, errs, ev_used, n_ev, prefix="E")
            if not entry:
                continue
            question = item.get("question")
            if question not in VRIO_QUESTIONS:
                errs.append(f"{ewhere}: 'question' must be one of {sorted(VRIO_QUESTIONS)}")
                continue
            entry["question"] = question
            evidence.append(entry)
        conclusion = _one_line(it.get("conclusion"), where, errs, what="'conclusion'")
        resources.append({**resource, "answers": clean, "evidence": evidence, "conclusion": conclusion})
    return ({"resources": resources} if not errs else None), errs


def build_vrio(inp):
    n, errs = normalize_vrio(inp)
    if errs:
        raise DataError("; ".join(errs))
    resources = []
    for resource in n["resources"]:
        by_question = {q: [e for e in resource["evidence"] if e["question"] == q] for q in VRIO_QUESTIONS}
        unsupported = [q for q in VRIO_QUESTIONS if resource["answers"][q] in ("yes", "no") and not by_question[q]]
        resources.append({**resource, "evidence_by_question": by_question, "unsupported_answers": unsupported})
    audit = {
        "resources_without_evidence": [r["id"] for r in resources if not r["evidence"]],
        "unsupported_answers": [f"{r['id']}:{q}" for r in resources for q in r["unsupported_answers"]],
        "unsure_answers": [f"{r['id']}:{q}" for r in resources for q in VRIO_QUESTIONS if r["answers"][q] == "unsure"],
        "unsupported_items": [e["id"] for r in resources for e in r["evidence"] if e["provenance"] == "assumption"],
        "synthetic_items": [e["id"] for r in resources for e in r["evidence"] if e["provenance"] == "synthetic"],
    }
    counts = {"n_resources": len(resources), "n_evidence": sum(len(r["evidence"]) for r in resources),
              "n_unsure": len(audit["unsure_answers"]), "n_unsupported_answers": len(audit["unsupported_answers"]),
              "n_with_conclusion": sum(1 for r in resources if r["conclusion"])}
    return {"kind": "template_vrio", "registry_ids": ["STR-08"], "name": "VRIO with an evidence audit",
            "short": "VRIO worksheet", "questions": {q: VRIO_QUESTIONS[q][0] for q in VRIO_QUESTIONS},
            "resources": resources, "audit": audit, "counts": counts}


def render_vrio(a):
    P = PERIOD
    tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P)
    a_ = a["audit"]
    t = (f"This VRIO worksheet organizes {tok('n_resources')} resources or capabilities, each with four answers you "
         f"supplied and {tok('n_evidence')} evidence items. ")
    if a["counts"]["n_unsure"]:
        t += f"{tok('n_unsure')} answers are 'unsure'; they are shown as unanswered judgments, not as a no. "
    if a["counts"]["n_unsupported_answers"]:
        t += f"{tok('n_unsupported_answers')} yes/no answers carry no evidence for that question and are flagged. "
    if a_["resources_without_evidence"]:
        t += "Some resources have no evidence at all. "
    if a_["synthetic_items"]:
        t += "Some evidence is synthetic and illustrative only; it is not an observation. "
    if a["counts"]["n_with_conclusion"] < a["counts"]["n_resources"]:
        t += "Where you supplied no conclusion, none is invented. "
    t += ("The four answers and the competitive implication are yours. The system does not derive a verdict, score or "
          "ranking from the answers, and it adds no facts of its own.")
    lines = []
    for resource in a["resources"]:
        lines.append(f"{resource['text']} — {_label(resource)}")
        for question, (label, _prompt) in VRIO_QUESTIONS.items():
            lines.append(f"  {label}: {resource['answers'][question]} (your answer)")
            evidence = resource["evidence_by_question"][question]
            lines += [_line(e) for e in evidence] or ["    No evidence for this question."]
        lines.append(f"  Your conclusion: {resource['conclusion']}" if resource["conclusion"]
                     else "  No conclusion supplied; the system does not derive one.")
    return t, "\n".join(lines)


def tests_vrio(inp, a, narrative, listing):
    raw = inp.get("resources") or []
    placed = [r["id"] for r in a["resources"]]
    declared_ids = [r.get("id", f"R{n}") for n, r in enumerate(raw, 1)]
    answers_ok = all(a["resources"][i]["answers"] == {q: raw[i]["answers"][q] for q in VRIO_QUESTIONS} for i in range(len(raw)))
    raw_ev = [(e.get("id", f"E{n}"), e.get("question")) for n, e in enumerate(
        [e for r in raw for e in (r.get("evidence") or [])], 1)]
    placed_ev = [(e["id"], e["question"]) for r in a["resources"] for e in r["evidence"]]
    unsupported = {f"{r.get('id', f'R{i + 1}')}:{q}" for i, r in enumerate(raw) for q in VRIO_QUESTIONS
                   if r["answers"][q] in ("yes", "no") and not any(
                       e.get("question") == q for e in (r.get("evidence") or []))}
    conclusion_ok = all((not a["resources"][i]["conclusion"] and not raw[i].get("conclusion"))
                        or a["resources"][i]["conclusion"] == str(raw[i].get("conclusion", "")).strip()
                        for i in range(len(raw)))
    texts_in = ({r["text"].strip() for r in raw}
                | {e["text"].strip() for r in raw for e in (r.get("evidence") or [])}
                | {str(r.get("conclusion", "")).strip() for r in raw if r.get("conclusion")})
    texts_out = ({r["text"] for r in a["resources"]}
                 | {e["text"] for r in a["resources"] for e in r["evidence"]}
                 | {r["conclusion"] for r in a["resources"] if r["conclusion"]})
    checks = [
        ("each_resource_placed_exactly_once", sorted(placed) == sorted(declared_ids) and len(set(placed)) == len(raw),
         "every resource appears once"),
        ("answers_are_reproduced_from_the_input", answers_ok, "the four answers are the ones supplied"),
        ("evidence_resolves_to_its_question", sorted(placed_ev) == sorted(raw_ev),
         "every evidence item is kept under the question it supports"),
        ("unsupported_answers_are_flagged", set(a["audit"]["unsupported_answers"]) == unsupported,
         "a yes/no answer with no evidence for that question is flagged"),
        ("conclusions_are_yours_and_reproduced_verbatim", conclusion_ok,
         "a conclusion is shown exactly as supplied, or none is invented"),
        ("analysis_contains_only_supplied_text", texts_out == texts_in, "the analysis holds only the texts supplied"),
        ("no_derived_verdict_or_score",
         not any(k in a for k in ("score", "overall", "ranking", "verdict", "implication", "total_score"))
         and not any(k in a["counts"] for k in ("score", "overall", "ranking", "verdict")),
         "no competitive-implication verdict, score or ranking is derived"),
        ("rendering_is_deterministic", render_vrio(a) == (narrative, listing), "the same input renders the same text"),
    ]
    return [(name, ok) for name, ok, _ in checks]


def vrio_validate(inp):
    return normalize_vrio(inp)[1]


TEMPLATES = {
    "template_swot": {"id": "template_swot", "version": "0.1.0", "name": "SWOT with evidence-to-action audit", "registry_ids": ["STR-07", "STR-18"], "build": build_swot, "render": render_swot, "tests": tests_swot,
        "test_names": ("each_item_placed_exactly_once", "counts_agree_with_independent_recount", "listing_reproduces_every_input_text_verbatim", "analysis_contains_only_supplied_text", "scopes_match_framework_definition",
                       "options_cite_existing_items_and_pairing_is_consistent", "empty_quadrants_reported_not_filled", "assumptions_and_synthetic_flagged", "rendering_is_deterministic"),
        "intended_use": "Organize your own evidence into strengths, weaknesses, opportunities and threats, link your strategic options to the items they follow from, and audit which items lack options or rest on assumptions.",
        "unsupported_use": "Generating facts, items, ratings, weights or options; ranking or scoring items; deciding what to do. TOWS options are yours; the system only derives the pairing label.",
        "input_help": {"evidence": "list of {text, dimension S|W|O|T, provenance user|sourced|assumption|synthetic, source (required if sourced), materiality high|medium|low (optional, your rating), id (optional)}",
                       "options": "optional list of {text, supports: [evidence ids]}; every option must cite at least one item"},
        "defaults": ({"question": "Internal versus external", "default_chosen": "Strengths and weaknesses are internal and opportunities and threats external, exactly as you assign them; the system does not reclassify.", "impact": "A misassigned item sits in the wrong quadrant."},
                     {"question": "Materiality and ranking", "default_chosen": "Materiality is shown only if you rate it. No ranking, weighting or scoring is applied.", "impact": "Prioritization remains your judgment."},
                     {"question": "TOWS pairing", "default_chosen": "An option is labelled SO, ST, WO or WT only when it cites items from exactly one internal and one external dimension; otherwise 'other'.", "impact": "Labels are derived, not judged."}),
        "limitations": ("The system adds no evidence: quality depends entirely on what you supply.", "No check that an item truly is internal or external, or that evidence is accurate.", "No materiality calculation; ratings are yours.")},
    "template_five_forces": {"id": "template_five_forces", "version": "0.1.0", "name": "Porter's Five Forces", "registry_ids": ["STR-01"], "build": build_five_forces, "render": render_five_forces, "tests": tests_five_forces,
        "test_names": ("each_item_placed_exactly_once", "counts_agree_with_independent_recount", "listing_reproduces_every_input_text_verbatim", "analysis_contains_only_supplied_text",
                       "ratings_have_evidence_and_rationale", "gaps_reported_not_filled", "no_aggregate_score_present", "assumptions_and_synthetic_flagged", "rendering_is_deterministic"),
        "intended_use": "Organize your evidence about industry rivalry, new entrants, substitutes, buyers and suppliers, with your own rating and rationale for each force you choose to rate.",
        "unsupported_use": "Generating evidence or ratings; computing an overall attractiveness score; competitor analysis beyond the evidence supplied.",
        "input_help": {"evidence": "list of {text, force rivalry|entrants|substitutes|buyers|suppliers, provenance user|sourced|assumption|synthetic, source (required if sourced), id (optional)}",
                       "ratings": "optional {force: {rating low|moderate|high, rationale}}; a rating needs at least one evidence item for that force"},
        "defaults": ({"question": "Rating scale", "default_chosen": "Low, moderate or high, entered by you with a one-line rationale; the scale is a provisional choice.", "impact": "A finer scale would need defined cut-offs."},
                     {"question": "Overall assessment", "default_chosen": "None. No score or overall industry attractiveness is produced.", "impact": "Aggregating forces needs weights that you own."}),
        "limitations": ("The system adds no evidence or ratings.", "Mostly qualitative unless data are available (catalogue).", "Five forces describe an industry, not a single firm's position.")},
}

# The canvas and plan templates share one builder, renderer and check set.
_CANVAS_TEST_NAMES = ("each_item_placed_exactly_once", "counts_agree_with_independent_recount",
                      "listing_reproduces_every_input_text_verbatim", "analysis_contains_only_supplied_text",
                      "empty_blocks_reported_not_filled", "links_resolve_to_supplied_items_and_are_kept_verbatim",
                      "assumptions_and_synthetic_flagged", "no_score_or_ranking_present", "rendering_is_deterministic")
for _kind, _meta in CANVAS_META.items():
    TEMPLATES[_kind] = {
        "id": _kind, "version": "0.1.0", "tier": "T4", "name": _meta["name"],
        "registry_ids": _meta["registry_ids"],
        "build": (lambda inp, _k=_kind: build_canvas(_k, inp)),
        "render": render_canvas,
        "tests": (lambda inp, a, narrative, listing, _k=_kind: tests_canvas(_k, inp, a, narrative, listing)),
        "validate": canvas_validate(_kind),
        "test_names": _CANVAS_TEST_NAMES,
        "intended_use": _meta["intended_use"],
        "unsupported_use": _meta["unsupported_use"],
        "input_help": {
            "blocks": "object of block name -> list of {text, provenance user|sourced|assumption|synthetic, source (required if sourced), materiality high|medium|low (optional, your rating), id (optional)}; block names: "
                      + ", ".join(CANVAS_BLOCKS[_kind]),
            "links": _meta["extra_help"],
        },
        "defaults": (
            {"question": "Block set", "default_chosen": "The blocks of the named framework, in their conventional order.", "impact": "A different block set is a different framework."},
            {"question": "Evidence and gaps", "default_chosen": "Every item is yours; a block with no evidence stays empty and is named in the audit.", "impact": "The worksheet never fills a gap to look complete."},
            {"question": "Links", "default_chosen": "A link is a declared dependency between two of your items; no direction, weight or score is derived.", "impact": "A link is a claim about your evidence, not a tested relationship."},
        ),
        "limitations": (
            "The system adds no evidence, judgment or recommendation; quality depends on what you supply.",
            "No check that an item is true, that a customer segment exists, or that a claimed link holds in reality.",
            "No scoring, ranking or overall verdict on the canvas.",
        ),
    }

# The two declared-matrix templates share one builder, renderer and check set.
_MATRIX_TEST_NAMES = ("each_cell_placed_exactly_once", "counts_agree_with_independent_recount",
                      "listing_reproduces_every_input_text_verbatim", "analysis_contains_only_supplied_text",
                      "empty_cells_reported_not_filled", "assumptions_and_synthetic_flagged",
                      "no_score_ranking_or_probability", "rendering_is_deterministic")
for _kind, _meta in MATRIX_META.items():
    _matrix_names = list(_MATRIX_TEST_NAMES)
    if _meta["require_rationale"]:
        _matrix_names.insert(4, "axes_are_declared_with_a_rationale")
    if _meta["require_groups"]:
        _matrix_names.insert(5, "every_row_declares_a_group")
    if _meta.get("raci"):
        _matrix_names.insert(6, "every_activity_has_exactly_one_accountable")
        _matrix_names.insert(7, "every_activity_has_at_least_one_responsible")
    TEMPLATES[_kind] = {
        "id": _kind, "version": "0.1.0", "tier": "T4", "name": _meta["name"],
        "registry_ids": _meta["registry_ids"],
        "build": (lambda inp, _k=_kind: build_matrix(_k, inp)),
        "render": render_matrix,
        "tests": (lambda inp, a, narrative, listing, _k=_kind: tests_matrix(_k, inp, a, narrative, listing)),
        "validate": matrix_validate(_kind),
        "test_names": tuple(_matrix_names),
        "intended_use": _meta["intended_use"],
        "unsupported_use": _meta["unsupported_use"],
        "input_help": {
            "rows": f"list of {_meta['min_rows']} to {_meta['max_rows']} {_meta['row_label']}s: {{id, text, provenance user|sourced|assumption|synthetic, source (required if sourced), materiality high|medium|low (optional), group (required for a strategic group map)}}",
            "columns": f"list of {_meta['min_columns']} to {_meta['max_columns']} {_meta['column_label']}s: {{id, text, rationale (required for a strategic group map)}}",
            "cells": "list of {row, column, text, provenance, source (required if sourced), materiality (optional)}; a cell you leave out stays empty and is audited",
        },
        "defaults": (
            {"question": "The grid is yours", "default_chosen": f"The {_meta['row_label']}s and {_meta['column_label']}s are the ones you declare; the system reclassifies nothing.", "impact": "A different grid is a different analysis."},
            {"question": "Empty cells", "default_chosen": "A cell with no evidence stays empty and is named in the audit.", "impact": "The worksheet never fills a gap to look complete."},
            {"question": "Probability, position and rank", "default_chosen": "None. No probability, plotted position, score or ranking is computed.", "impact": "Those would need data and a model you own."},
        ),
        "limitations": (
            "The system adds no evidence, probability, position or recommendation; quality depends on what you supply.",
            "No check that a declared axis, driver or group is the right one, or that a cell is accurate.",
            "No scoring, ranking or overall verdict.",
        ),
    }

TEMPLATES["template_vrio"] = {
    "id": "template_vrio", "version": "0.1.0", "tier": "T4", "name": "VRIO with an evidence audit",
    "registry_ids": ["STR-08"], "build": build_vrio, "render": render_vrio, "tests": tests_vrio,
    "validate": vrio_validate,
    "test_names": ("each_resource_placed_exactly_once", "answers_are_reproduced_from_the_input",
                   "evidence_resolves_to_its_question", "unsupported_answers_are_flagged",
                   "conclusions_are_yours_and_reproduced_verbatim", "analysis_contains_only_supplied_text",
                   "no_derived_verdict_or_score", "rendering_is_deterministic"),
    "intended_use": "Record, for each resource or capability, your four VRIO answers and the evidence behind them, and audit which answers are unsupported or still unsure.",
    "unsupported_use": "Scoring resources yes/no and presenting the total as an advantage; deriving the competitive implication for you; inventing resources, answers or evidence.",
    "input_help": {"resources": "list of {id, text, provenance user|sourced|assumption|synthetic, source (required if sourced), materiality high|medium|low (optional), answers {valuable, rare, costly_to_imitate, organized: yes|no|unsure}, evidence [{text, question valuable|rare|costly_to_imitate|organized, provenance, source}], conclusion (optional, one line, yours)}"},
    "defaults": (
        {"question": "The verdict", "default_chosen": "None. The four answers and the competitive implication are yours; the system derives no verdict, score or ranking.", "impact": "A derived verdict would turn your judgments into false precision."},
        {"question": "Unsure", "default_chosen": "'Unsure' is kept as an unanswered judgment, not treated as a no.", "impact": "Treating it as a no would invent an answer."},
        {"question": "Evidence per question", "default_chosen": "A yes/no answer with no evidence for that question is flagged as unsupported.", "impact": "The flag is a prompt to find evidence, not a finding about the resource."},
    ),
    "limitations": (
        "The system adds no answers, evidence or conclusion; quality depends on what you supply.",
        "No check that a resource is truly valuable, rare, costly to imitate or organizationally supported.",
        "No competitive-implication verdict, score or ranking is derived.",
    ),
}


def run_template(kind, inp):
    t = TEMPLATES[kind]; a = t["build"](inp); narrative, listing = t["render"](a)
    arts = a.get("artifacts") or [{"id": k, "metric": k, "value": str(v), "unit": "count", "precision": 0} for k, v in a["counts"].items()]
    return {"analysis": a, "narrative": narrative, "listing": listing, "results": [[n, bool(ok)] for n, ok in t["tests"](inp, a, narrative, listing)], "counts": a["counts"],
            "artifacts": arts, "text_refs": a.get("text_refs", {})}

def describe(kind):
    t = TEMPLATES[kind]
    blocks = []
    if kind in CANVAS_BLOCKS:
        prefixes = CANVAS_PREFIXES.get(kind, {})
        blocks = [{"key": key, "label": CANVAS_BLOCKS[kind][key][0], "prompt": CANVAS_BLOCKS[kind][key][1],
                   "prefix": prefixes.get(key) or ("B%d_" % (i + 1))}
                  for i, key in enumerate(CANVAS_BLOCKS[kind])]
    form_kind = ("canvas" if kind in CANVAS_BLOCKS else
                 "swot" if kind == "template_swot" else
                 "five_forces" if kind == "template_five_forces" else
                 "matrix" if kind in MATRIX_META else
                 "vrio" if kind == "template_vrio" else "none")
    # A grid names its own axes.  Without this the page could only fall back to generic
    # wording (it said "Scenarios / Drivers" on every grid), so a journey map or a
    # SERVQUAL grid was labelled as if it were scenario planning.
    grid = MATRIX_META.get(kind)
    matrix = ({"row_label": grid.get("row_label"), "column_label": grid.get("column_label"),
               "min_rows": grid.get("min_rows"), "max_rows": grid.get("max_rows"),
               "min_columns": grid.get("min_columns"), "max_columns": grid.get("max_columns"),
               "require_groups": bool(grid.get("require_groups")),
               "require_rationale": bool(grid.get("require_rationale")),
               "raci": bool(grid.get("raci"))}
              if grid else None)
    # `form_copy` is the form's own copy, declared beside the grid: the labels the
    # student reads and the sentence that explains what belongs in the grid.  The
    # page reads it and falls back to its older wording when a grid has none, so
    # adding a framework means adding a profile, never a branch in the renderer.
    form_copy = dict(grid["form_copy"]) if grid and grid.get("form_copy") else None
    return {"id": t["id"], "version": t["version"], "name": t["name"], "registry_ids": t["registry_ids"], "tier": t.get("tier", "T4"), "intended_use": t["intended_use"], "unsupported_use": t["unsupported_use"],
            "input_help": t["input_help"], "blocks": blocks, "form_kind": form_kind, "matrix": matrix, "form_copy": form_copy,
            "defaults": list(t["defaults"]), "limitations": list(t["limitations"]), "planned_checks": list(t["test_names"]), "example_request": EXAMPLES.get(kind)}

BAKERY = "Illustrative bakery case (synthetic)"
EXAMPLES = {
    "template_swot": {"objective": "Organize the evidence on our bakery's position", "method": "template_swot", "inputs": {
        "evidence": [{"text": "Loyal weekday customers", "dimension": "S", "provenance": "synthetic", "materiality": "high"},
                     {"text": "Small baking capacity", "dimension": "W", "provenance": "synthetic"},
                     {"text": "New office park nearby", "dimension": "O", "provenance": "synthetic"},
                     {"text": "A supermarket chain opened a bakery counter", "dimension": "T", "provenance": "synthetic", "materiality": "high"}],
        "options": [{"text": "Offer office catering", "supports": ["E1", "E3"]}]}},
    "template_five_forces": {"objective": "Organize the evidence on competition in our local bakery market", "method": "template_five_forces", "inputs": {
        "evidence": [{"text": "Three bakeries and a supermarket counter within a short walk", "force": "rivalry", "provenance": "synthetic"},
                     {"text": "Little capital needed to open a small bakery", "force": "entrants", "provenance": "synthetic"},
                     {"text": "Flour comes from one regional mill", "force": "suppliers", "provenance": "synthetic"}],
        "ratings": {"rivalry": {"rating": "high", "rationale": "Several close competitors"}}}},
    "template_business_model_canvas": {"objective": "Lay out the evidence for our campus meal business model", "method": "template_business_model_canvas", "inputs": {
        "blocks": {
            "customer_segments": [{"text": "Students living within walking distance of the campus", "provenance": "synthetic", "id": "CS1", "materiality": "high"}],
            "value_propositions": [{"text": "A hot rice meal under eight dollars in under ten minutes", "provenance": "synthetic", "id": "VP1"}],
            "channels": [{"text": "A counter beside the main gate and a phone order line", "provenance": "synthetic"}],
            "cost_structure": [{"text": "Rent, ingredients and two part-time staff", "provenance": "synthetic"}],
            "revenue_streams": [{"text": "Walk-in meals and prepaid meal cards", "provenance": "synthetic"}]},
        "links": [{"from": "VP1", "to": "CS1"}]}},
    "template_lean_canvas": {"objective": "Test the assumptions behind the campus meal idea", "method": "template_lean_canvas", "inputs": {
        "blocks": {
            "problem": [{"text": "Students skip lunch when the queue is long", "provenance": "synthetic"}],
            "customer_segments": [{"text": "Students with a short break between classes", "provenance": "synthetic"}],
            "solution": [{"text": "Pre-ordered meals collected from a counter", "provenance": "synthetic"}],
            "unique_value_proposition": [{"text": "Ready in ten minutes at a student price", "provenance": "synthetic"}],
            "key_metrics": [{"text": "Meals collected per day and average wait", "provenance": "synthetic"}],
            "unfair_advantage": [{"text": "A lease beside the gate that a competitor cannot copy quickly", "provenance": "synthetic"}]}}},
    "template_value_proposition_canvas": {"objective": "Map the value proposition for the campus meal service", "method": "template_value_proposition_canvas", "inputs": {
        "blocks": {
            "customer_jobs": [{"text": "Eat a proper lunch between classes", "provenance": "synthetic"}],
            "customer_pains": [{"text": "Long queues leave no time to eat", "provenance": "synthetic", "id": "P1"}],
            "customer_gains": [{"text": "A predictable, affordable meal", "provenance": "synthetic", "id": "G1"}],
            "products_services": [{"text": "Pre-ordered rice meals", "provenance": "synthetic"}],
            "pain_relievers": [{"text": "Order ahead and collect without queuing", "provenance": "synthetic", "id": "PR1"}],
            "gain_creators": [{"text": "A fixed student price with a meal card", "provenance": "synthetic", "id": "GC1"}]},
        "links": [{"from": "PR1", "to": "P1"}, {"from": "GC1", "to": "G1"}]}},
    "template_marketing_plan": {"objective": "Structure the marketing plan for the campus meal service", "method": "template_marketing_plan", "inputs": {
        "blocks": {
            "segmentation": [{"text": "Students by year level and length of break", "provenance": "synthetic"}],
            "targeting": [{"text": "First- and second-year students with a short midday break", "provenance": "synthetic"}],
            "positioning": [{"text": "The fastest student-priced hot meal beside the gate", "provenance": "synthetic"}],
            "product": [{"text": "Three rice meals and two drinks", "provenance": "synthetic"}],
            "price": [{"text": "Seventy-five dollars a meal, cost-plus pricing", "provenance": "synthetic"}],
            "place": [{"text": "Counter beside the main gate", "provenance": "synthetic"}],
            "promotion": [{"text": "Class-group chats and a first-week meal-card discount", "provenance": "synthetic"}]}}},
    "template_pestel": {"objective": "Organize the external evidence for the campus meal service", "method": "template_pestel", "inputs": {
        "blocks": {
            "political": [{"text": "The campus allows one food concession per gate", "provenance": "synthetic", "materiality": "high"}],
            "economic": [{"text": "Student allowances are fixed for the semester", "provenance": "synthetic"}],
            "social": [{"text": "Students increasingly order food from their phones", "provenance": "synthetic"}],
            "technological": [{"text": "A phone ordering line is cheap to run", "provenance": "synthetic"}],
            "environmental": [{"text": "Single-use packaging is restricted on campus", "provenance": "synthetic"}],
            "legal": [{"text": "A food-handling permit is required", "provenance": "synthetic"}]}}},
    "template_value_chain": {"objective": "Map the activities of the campus meal service", "method": "template_value_chain", "inputs": {
        "blocks": {
            "procurement": [{"text": "Rice and vegetables bought from one market supplier", "provenance": "synthetic"}],
            "inbound_logistics": [{"text": "Daily market run before six in the morning", "provenance": "synthetic"}],
            "operations": [{"text": "One kitchen line cooks and packs meals", "provenance": "synthetic"}],
            "outbound_logistics": [{"text": "Meals carried to the gate counter", "provenance": "synthetic"}],
            "marketing_and_sales": [{"text": "Class-group chats and a meal-card stall", "provenance": "synthetic"}],
            "service": [{"text": "Replacement of a meal that arrives cold", "provenance": "synthetic"}]}}},
    "template_ansoff": {"objective": "Place the growth options for the campus meal service", "method": "template_ansoff", "inputs": {
        "blocks": {
            "market_penetration": [{"text": "Sell a second meal a day to current students", "provenance": "synthetic", "materiality": "high"}],
            "market_development": [{"text": "Open a counter at the second campus gate", "provenance": "synthetic"}],
            "product_development": [{"text": "Add breakfast packs for the same students", "provenance": "synthetic"}],
            "diversification": [{"text": "Cater a nearby office building", "provenance": "assumption"}]}}},
    "template_blue_ocean_errc": {"objective": "Record the four actions for the campus meal service", "method": "template_blue_ocean_errc", "inputs": {
        "blocks": {
            "eliminate": [{"text": "The queue at the counter", "provenance": "synthetic"}],
            "reduce": [{"text": "The time between ordering and eating", "provenance": "synthetic"}],
            "raise": [{"text": "The reliability of a hot meal at a fixed price", "provenance": "synthetic"}],
            "create": [{"text": "A prepaid meal card shared with a class group", "provenance": "synthetic"}]}}},
    "template_activity_system_fit": {"objective": "Map the activity system behind the campus meal service", "method": "template_activity_system_fit", "inputs": {
        "blocks": {
            "strategic_position": [{"text": "The fastest student-priced hot meal beside the gate", "provenance": "synthetic"}],
            "activities": [{"text": "Pre-order by phone", "provenance": "synthetic", "id": "A1"},
                           {"text": "A single kitchen line with a fixed menu", "provenance": "synthetic", "id": "A2"},
                           {"text": "Collection shelves beside the gate", "provenance": "synthetic", "id": "A3"}],
            "reinforcing_choices": [{"text": "A fixed menu makes pre-order and one kitchen line possible", "provenance": "synthetic"}],
            "boundaries": [{"text": "No table service and no delivery beyond the gate", "provenance": "synthetic"}]},
        "links": [{"from": "A1", "to": "A2"}, {"from": "A2", "to": "A3"}]}},
    "template_scenario_planning": {"objective": "Set out two scenarios for the campus meal service", "method": "template_scenario_planning", "inputs": {
        "rows": [{"id": "S1", "text": "Scenario A: the campus keeps one concession per gate", "provenance": "synthetic"},
                 {"id": "S2", "text": "Scenario B: the campus opens catering to outside vendors", "provenance": "synthetic"}],
        "columns": [{"id": "D1", "text": "Number of competing food outlets"},
                    {"id": "D2", "text": "Student allowance"},
                    {"id": "D3", "text": "Phone ordering adoption"}],
        "cells": [{"row": "S1", "column": "D1", "text": "One outlet per gate", "provenance": "synthetic"},
                  {"row": "S1", "column": "D2", "text": "Fixed for the semester", "provenance": "synthetic"},
                  {"row": "S1", "column": "D3", "text": "Slow growth", "provenance": "synthetic"},
                  {"row": "S2", "column": "D1", "text": "Several vendors per gate", "provenance": "synthetic"},
                  {"row": "S2", "column": "D2", "text": "Fixed for the semester", "provenance": "synthetic"},
                  {"row": "S2", "column": "D3", "text": "Rapid growth", "provenance": "synthetic"}]}},
    "template_strategic_group_map": {"objective": "Map the strategic groups in the campus food market", "method": "template_strategic_group_map", "inputs": {
        "rows": [{"id": "A", "text": "Gate counter", "group": "Fast student meals", "provenance": "synthetic"},
                 {"id": "B", "text": "Canteen", "group": "Full-service campus food", "provenance": "synthetic"},
                 {"id": "C", "text": "Outside delivery app", "group": "Off-campus delivery", "provenance": "synthetic"}],
        "columns": [{"id": "X", "text": "Price level", "rationale": "The main choice students describe"},
                    {"id": "Y", "text": "Time to receive", "rationale": "The constraint between classes"}],
        "cells": [{"row": "A", "column": "X", "text": "Low", "provenance": "synthetic"},
                  {"row": "A", "column": "Y", "text": "Under ten minutes", "provenance": "synthetic"},
                  {"row": "B", "column": "X", "text": "Medium", "provenance": "synthetic"},
                  {"row": "B", "column": "Y", "text": "Fifteen to thirty minutes", "provenance": "synthetic"},
                  {"row": "C", "column": "X", "text": "Medium to high", "provenance": "synthetic"},
                  {"row": "C", "column": "Y", "text": "Twenty to forty minutes", "provenance": "synthetic"}]}},
    "template_vrio": {"objective": "Record the VRIO evidence for the campus meal service", "method": "template_vrio", "inputs": {
        "resources": [{"id": "R1", "text": "The lease beside the main gate", "provenance": "synthetic", "materiality": "high",
                       "answers": {"valuable": "yes", "rare": "yes", "costly_to_imitate": "yes", "organized": "unsure"},
                       "evidence": [{"text": "The lease is exclusive for the gate", "question": "valuable", "provenance": "synthetic"},
                                    {"text": "No other food counter is within the gate", "question": "rare", "provenance": "synthetic"},
                                    {"text": "A second lease at the gate is not offered", "question": "costly_to_imitate", "provenance": "synthetic"}],
                       "conclusion": "The location is the advantage if the kitchen can keep the queue short."},
                      {"id": "R2", "text": "The phone ordering line", "provenance": "synthetic",
                       "answers": {"valuable": "yes", "rare": "no", "costly_to_imitate": "no", "organized": "yes"},
                       "evidence": [{"text": "Students order ahead to skip the queue", "question": "valuable", "provenance": "synthetic"},
                                    {"text": "Two nearby stalls use the same app", "question": "rare", "provenance": "synthetic"},
                                    {"text": "The app is available to any vendor", "question": "costly_to_imitate", "provenance": "synthetic"}]}]}},
    "template_project_charter": {"objective": "Authorise the campus meal counter project", "method": "template_project_charter", "inputs": {
        "blocks": {
            "objective": [{"text": "Serve 150 hot meals a day from the main-gate counter by the end of the semester", "provenance": "synthetic"}],
            "scope_in": [{"text": "Fit out the gate counter, hire two part-time staff, launch a phone order line", "provenance": "synthetic"}],
            "scope_out": [{"text": "No delivery beyond the gate and no second campus location", "provenance": "synthetic"}],
            "deliverables": [{"text": "A fitted counter with a food-handling permit", "provenance": "synthetic", "id": "DEL1"},
                             {"text": "A phone order line and a prepaid meal card", "provenance": "synthetic", "id": "DEL2"}],
            "governance": [{"text": "The student affairs office sponsors the project; the owner approves spend above 50,000 dollars", "provenance": "synthetic"}],
            "budget": [{"text": "450,000 dollars from the student services fund", "provenance": "synthetic"}],
            "milestones": [{"text": "Permit approved by week 4; counter open by week 10", "provenance": "synthetic"}],
            "success_measures": [{"text": "150 meals a day and a queue under five minutes by week 12", "provenance": "assumption"}],
            "assumptions": [{"text": "The gate stays open for the whole semester", "provenance": "assumption"}],
            "constraints": [{"text": "The counter must close during the mid-semester break", "provenance": "synthetic"}]}}},
    "template_wbs": {"objective": "Break down the campus meal counter scope", "method": "template_wbs", "inputs": {
        "blocks": {
            "deliverables": [{"text": "Counter and permit", "provenance": "synthetic", "id": "DEL1"},
                             {"text": "Ordering and payment", "provenance": "synthetic", "id": "DEL2"}],
            "work_packages": [{"text": "Fit the counter and pass the food-handling inspection", "provenance": "synthetic", "id": "WP1"},
                              {"text": "Set up the phone line and meal-card process", "provenance": "synthetic", "id": "WP2"}],
            "acceptance": [{"text": "The counter passes inspection and serves a test meal", "provenance": "synthetic"},
                           {"text": "A student can order and collect a meal without queuing", "provenance": "synthetic"}],
            "exclusions": [{"text": "Delivery and a second location are outside this breakdown", "provenance": "synthetic"}]},
        "links": [{"from": "WP1", "to": "DEL1"}, {"from": "WP2", "to": "DEL2"}]}},
    "template_raci": {"objective": "Assign responsibilities for the campus meal counter", "method": "template_raci", "inputs": {
        "rows": [{"id": "A1", "text": "Approve the budget", "provenance": "synthetic"},
                 {"id": "A2", "text": "Fit out the counter", "provenance": "synthetic"},
                 {"id": "A3", "text": "Run the daily service", "provenance": "synthetic"}],
        "columns": [{"id": "C1", "text": "Project owner"}, {"id": "C2", "text": "Project lead"}, {"id": "C3", "text": "Student affairs office"}],
        "cells": [{"row": "A1", "column": "C1", "text": "A", "provenance": "synthetic"},
                  {"row": "A1", "column": "C2", "text": "R", "provenance": "synthetic"},
                  {"row": "A1", "column": "C3", "text": "C", "provenance": "synthetic"},
                  {"row": "A2", "column": "C1", "text": "I", "provenance": "synthetic"},
                  {"row": "A2", "column": "C2", "text": "A", "provenance": "synthetic"},
                  {"row": "A2", "column": "C3", "text": "R", "provenance": "synthetic"},
                  {"row": "A3", "column": "C1", "text": "C", "provenance": "synthetic"},
                  {"row": "A3", "column": "C2", "text": "R", "provenance": "synthetic"},
                  {"row": "A3", "column": "C3", "text": "A", "provenance": "synthetic"}]}},
    "template_balanced_scorecard": {"objective": "Steer the campus meal counter with a balanced scorecard", "method": "template_balanced_scorecard", "inputs": {
        "rows": [{"id": "P1", "text": "Financial", "provenance": "synthetic"},
                 {"id": "P2", "text": "Customer", "provenance": "synthetic"},
                 {"id": "P3", "text": "Internal process", "provenance": "synthetic"},
                 {"id": "P4", "text": "Organisational capacity", "provenance": "synthetic"}],
        "columns": [{"id": "C1", "text": "Objective"}, {"id": "C2", "text": "Measure"},
                    {"id": "C3", "text": "Target"}, {"id": "C4", "text": "Initiative"}],
        "cells": [{"row": "P1", "column": "C1", "text": "Break even within two terms", "provenance": "synthetic"},
                  {"row": "P1", "column": "C2", "text": "Monthly contribution after food and rent", "provenance": "synthetic"},
                  {"row": "P1", "column": "C3", "text": "A declared figure the owner sets", "provenance": "assumption"},
                  {"row": "P1", "column": "C4", "text": "Prepaid meal cards", "provenance": "synthetic"},
                  {"row": "P2", "column": "C1", "text": "Students collect lunch inside their break", "provenance": "synthetic"},
                  {"row": "P2", "column": "C2", "text": "Average wait from order to collection", "provenance": "synthetic"},
                  {"row": "P2", "column": "C3", "text": "A declared wait the owner sets", "provenance": "assumption"},
                  {"row": "P2", "column": "C4", "text": "A pre-order line beside the gate", "provenance": "synthetic"},
                  {"row": "P3", "column": "C1", "text": "Orders are assembled without a queue", "provenance": "synthetic"},
                  {"row": "P3", "column": "C2", "text": "Meals assembled per staff hour", "provenance": "synthetic"},
                  {"row": "P3", "column": "C3", "text": "A declared rate the owner sets", "provenance": "assumption"},
                  {"row": "P3", "column": "C4", "text": "One assembly station with a fixed menu", "provenance": "synthetic"},
                  {"row": "P4", "column": "C1", "text": "Two staff can run a shift unaided", "provenance": "synthetic"},
                  {"row": "P4", "column": "C2", "text": "Shifts run without the owner present", "provenance": "synthetic"},
                  {"row": "P4", "column": "C3", "text": "A declared number of shifts the owner sets", "provenance": "assumption"},
                  {"row": "P4", "column": "C4", "text": "A cross-training rota", "provenance": "synthetic"}]}},
    "template_strategy_map": {"objective": "Map how the campus meal counter's objectives drive one another", "method": "template_strategy_map", "inputs": {
        "rows": [{"id": "O1", "text": "Capability: two staff can run a shift", "provenance": "synthetic"},
                 {"id": "O2", "text": "Process: assembly without a queue", "provenance": "synthetic"},
                 {"id": "O3", "text": "Customer: lunch collected inside the break", "provenance": "synthetic"},
                 {"id": "O4", "text": "Outcome: the counter covers its costs", "provenance": "synthetic"}],
        "columns": [{"id": "C1", "text": "Perspective"}, {"id": "C2", "text": "Objective"},
                    {"id": "C3", "text": "Drives"}, {"id": "C4", "text": "Measure"}],
        "cells": [{"row": "O1", "column": "C1", "text": "Capability", "provenance": "synthetic"},
                  {"row": "O1", "column": "C2", "text": "Two staff can run a shift unaided", "provenance": "synthetic"},
                  {"row": "O1", "column": "C3", "text": "Assembly without a queue", "provenance": "synthetic"},
                  {"row": "O1", "column": "C4", "text": "Shifts run per week without the owner", "provenance": "synthetic"},
                  {"row": "O2", "column": "C1", "text": "Process", "provenance": "synthetic"},
                  {"row": "O2", "column": "C2", "text": "Meals assembled without a queue", "provenance": "synthetic"},
                  {"row": "O2", "column": "C3", "text": "Lunch collected inside the break", "provenance": "synthetic"},
                  {"row": "O2", "column": "C4", "text": "Meals per staff hour", "provenance": "synthetic"},
                  {"row": "O3", "column": "C1", "text": "Customer", "provenance": "synthetic"},
                  {"row": "O3", "column": "C2", "text": "Lunch collected inside the break", "provenance": "synthetic"},
                  {"row": "O3", "column": "C3", "text": "The counter covers its costs", "provenance": "synthetic"},
                  {"row": "O3", "column": "C4", "text": "Average wait from order to collection", "provenance": "synthetic"},
                  {"row": "O4", "column": "C1", "text": "Outcome", "provenance": "synthetic"},
                  {"row": "O4", "column": "C2", "text": "The counter covers its costs", "provenance": "synthetic"},
                  {"row": "O4", "column": "C3", "text": "The board's funding decision", "provenance": "assumption"},
                  {"row": "O4", "column": "C4", "text": "Monthly contribution after food and rent", "provenance": "synthetic"}]}},
    "template_kpi_tree": {"objective": "Decompose the meal counter's outcome metric", "method": "template_kpi_tree", "inputs": {
        "rows": [{"id": "M1", "text": "Meals sold per day", "provenance": "synthetic"},
                 {"id": "M2", "text": "Students who walk past the counter", "provenance": "synthetic"},
                 {"id": "M3", "text": "Share of those who order", "provenance": "synthetic"}],
        "columns": [{"id": "C1", "text": "Level"}, {"id": "C2", "text": "Metric"},
                    {"id": "C3", "text": "Formula or definition"}, {"id": "C4", "text": "Source"}],
        "cells": [{"row": "M1", "column": "C1", "text": "Outcome", "provenance": "synthetic"},
                  {"row": "M1", "column": "C2", "text": "Meals sold per day", "provenance": "synthetic"},
                  {"row": "M1", "column": "C3", "text": "Walk-past students multiplied by the share who order", "provenance": "synthetic"},
                  {"row": "M1", "column": "C4", "text": "The counter's daily till record", "provenance": "synthetic"},
                  {"row": "M2", "column": "C1", "text": "Driver", "provenance": "synthetic"},
                  {"row": "M2", "column": "C2", "text": "Students who walk past the counter", "provenance": "synthetic"},
                  {"row": "M2", "column": "C3", "text": "A counted figure, logged by the shift lead", "provenance": "synthetic"},
                  {"row": "M2", "column": "C4", "text": "The shift log", "provenance": "synthetic"},
                  {"row": "M3", "column": "C1", "text": "Driver", "provenance": "synthetic"},
                  {"row": "M3", "column": "C2", "text": "Share of those who order", "provenance": "synthetic"},
                  {"row": "M3", "column": "C3", "text": "Orders divided by walk-past students", "provenance": "synthetic"},
                  {"row": "M3", "column": "C4", "text": "The till record and the shift log", "provenance": "synthetic"}]}},
    "template_okrs": {"objective": "Set the meal counter's objectives and key results", "method": "template_okrs", "inputs": {
        "rows": [{"id": "G1", "text": "Make the lunch break usable again", "provenance": "synthetic"},
                 {"id": "G2", "text": "Run the counter without the owner present", "provenance": "synthetic"}],
        "columns": [{"id": "C1", "text": "Objective"}, {"id": "C2", "text": "Key results"},
                    {"id": "C3", "text": "Baseline to target"}, {"id": "C4", "text": "Source"}],
        "cells": [{"row": "G1", "column": "C1", "text": "Make the lunch break usable again", "provenance": "synthetic"},
                  {"row": "G1", "column": "C2", "text": "Students collect lunch within their break", "provenance": "synthetic"},
                  {"row": "G1", "column": "C3", "text": "The current wait, declared by the owner, brought down to the declared target", "provenance": "assumption"},
                  {"row": "G1", "column": "C4", "text": "The collection timestamps at the counter", "provenance": "synthetic"},
                  {"row": "G2", "column": "C1", "text": "Run the counter without the owner present", "provenance": "synthetic"},
                  {"row": "G2", "column": "C2", "text": "Shifts run unaided", "provenance": "synthetic"},
                  {"row": "G2", "column": "C3", "text": "No unaided shifts today to the declared number per week", "provenance": "assumption"},
                  {"row": "G2", "column": "C4", "text": "The shift rota and the shift log", "provenance": "synthetic"}]}},
    "template_risk_register": {"objective": "Record the risks on the campus meal counter project", "method": "template_risk_register", "inputs": {
        "rows": [{"id": "R1", "text": "The food-handling permit is delayed", "provenance": "synthetic"},
                 {"id": "R2", "text": "Demand is lower than 150 meals a day", "provenance": "synthetic"}],
        "columns": [{"id": "C1", "text": "Likelihood (your label)"}, {"id": "C2", "text": "Impact (your label)"},
                    {"id": "C3", "text": "Response"}, {"id": "C4", "text": "Owner"}],
        "cells": [{"row": "R1", "column": "C1", "text": "Medium", "provenance": "assumption"},
                  {"row": "R1", "column": "C2", "text": "High", "provenance": "assumption"},
                  {"row": "R1", "column": "C3", "text": "Submit the permit in week 1 and keep a fallback menu", "provenance": "synthetic"},
                  {"row": "R1", "column": "C4", "text": "Project lead", "provenance": "synthetic"},
                  {"row": "R2", "column": "C1", "text": "Medium", "provenance": "assumption"},
                  {"row": "R2", "column": "C2", "text": "Medium", "provenance": "assumption"},
                  {"row": "R2", "column": "C3", "text": "Pre-sell meal cards and track daily covers", "provenance": "synthetic"},
                  {"row": "R2", "column": "C4", "text": "Project owner", "provenance": "synthetic"}]}},
    "template_kano": {"objective": "Classify the meal-counter attributes with the survey evidence", "method": "template_kano", "inputs": {
        "blocks": {
            "must_be": [{"text": "The meal is hot and safely handled", "provenance": "synthetic"}],
            "performance": [{"text": "The queue is shorter than it was last semester", "provenance": "synthetic"}],
            "attractive": [{"text": "A student can see the day's menu on a phone before walking over", "provenance": "assumption"}],
            "indifferent": []}}},
    "template_paid_media_plan": {"objective": "Plan the paid launch of the campus meal counter", "method": "template_paid_media_plan", "inputs": {
        "blocks": {
            "objective": [{"text": "Fill the counter at lunchtime during the first month", "provenance": "user"}],
            "audience": [{"text": "Students with a break between the late morning and early afternoon classes", "provenance": "assumption"}],
            "channels_placements": [{"text": "Campus social feed and a booth beside the gate", "provenance": "user"}],
            "budget_bid": [{"text": "A fixed daily budget for the feed and a flat fee for the booth", "provenance": "user"}],
            "conversion_definition": [{"text": "A meal collected at the counter within the same day as the ad click", "provenance": "user"}],
            "creative_variants": [], "measurement": []}}},
    "template_measurement_plan": {"objective": "Make the meal-counter journey measurable", "method": "template_measurement_plan", "inputs": {
        "blocks": {
            "questions": [{"text": "Which channel brings the students who actually collect a meal?", "provenance": "user"}],
            "metrics": [{"text": "Meals collected per day, by entry channel", "provenance": "user"}],
            "events_dimensions": [{"text": "A page view with the channel parameter, and an order-collected event", "provenance": "user"}],
            "data_quality": [{"text": "Check that the counter staff record every collection on the same device", "provenance": "assumption"}],
            "governance": []}}},
    "template_customer_journey": {"objective": "Map the meal-counter customer journey", "method": "template_customer_journey", "inputs": {
        "rows": [{"id": "T1", "text": "A student sees the menu on a phone", "provenance": "synthetic"},
                 {"id": "T2", "text": "The student walks to the gate counter", "provenance": "synthetic"},
                 {"id": "T3", "text": "The student collects and pays", "provenance": "synthetic"}],
        "columns": [{"id": "S1", "text": "Notices the offer"}, {"id": "S2", "text": "Decides and orders"}, {"id": "S3", "text": "Collects the meal"}],
        "cells": [{"row": "T1", "column": "S1", "text": "Sees the day's menu in the campus feed", "provenance": "synthetic"},
                  {"row": "T1", "column": "S2", "text": "Checks the price and the queue estimate", "provenance": "assumption"},
                  {"row": "T2", "column": "S2", "text": "Walks over only if the queue looks short", "provenance": "assumption"},
                  {"row": "T3", "column": "S3", "text": "Pays at the counter and takes the meal", "provenance": "synthetic"}]}},
    "template_servqual": {"objective": "Audit the service-quality gaps at the meal counter", "method": "template_servqual", "inputs": {
        "rows": [{"id": "D1", "text": "Reliability: the counter is open when it says it is", "provenance": "user"},
                 {"id": "D2", "text": "Responsiveness: the queue moves quickly", "provenance": "user"},
                 {"id": "D3", "text": "Tangibles: the counter is clean and the food looks fresh", "provenance": "user"}],
        "columns": [{"id": "C1", "text": "Expectation (your note)"}, {"id": "C2", "text": "Perception (your note)"},
                    {"id": "C3", "text": "Gap you concluded"}],
        "cells": [{"row": "D1", "column": "C1", "text": "Open through the lunch break", "provenance": "assumption"},
                  {"row": "D1", "column": "C2", "text": "Closed twice last week without notice", "provenance": "synthetic"},
                  {"row": "D1", "column": "C3", "text": "A shortfall the students mentioned", "provenance": "assumption"},
                  {"row": "D2", "column": "C1", "text": "Under five minutes", "provenance": "assumption"},
                  {"row": "D2", "column": "C2", "text": "About eight minutes at noon", "provenance": "synthetic"},
                  {"row": "D3", "column": "C2", "text": "Clean and visibly freshly cooked", "provenance": "synthetic"}]}},
    "template_stakeholder_plan": {"objective": "Plan stakeholder communication for the meal counter project", "method": "template_stakeholder_plan", "inputs": {
        "blocks": {
            "stakeholders": [{"text": "Student affairs office", "provenance": "synthetic", "id": "STK1"},
                             {"text": "Students using the gate", "provenance": "synthetic", "id": "STK2"},
                             {"text": "Food-handling inspector", "provenance": "synthetic", "id": "STK3"}],
            "interests": [{"text": "The office needs the counter to open on schedule", "provenance": "synthetic"},
                          {"text": "Students want a fast, affordable meal", "provenance": "synthetic"},
                          {"text": "The inspector needs the permit conditions met", "provenance": "synthetic"}],
            "influence": [{"text": "High influence: the office approves the site and the budget", "provenance": "synthetic"},
                          {"text": "Medium influence: students choose whether to buy", "provenance": "synthetic"}],
            "engagement": [{"text": "Collaborate with the student affairs office", "provenance": "synthetic"},
                           {"text": "Inform students through class-group chats", "provenance": "synthetic"}],
            "messages": [{"text": "The counter opens on the published date", "provenance": "synthetic"},
                         {"text": "Orders can be placed ahead and collected without queuing", "provenance": "synthetic"}],
            "channels": [{"text": "A short email to the office", "provenance": "synthetic"},
                         {"text": "Class-group chat and a poster at the gate", "provenance": "synthetic"}],
            "frequency": [{"text": "A weekly update to the office until opening", "provenance": "synthetic"},
                          {"text": "A daily message to students in the first week", "provenance": "synthetic"}],
            "owners": [{"text": "Project lead owns the office updates", "provenance": "synthetic"},
                       {"text": "Counter supervisor owns the student messages", "provenance": "synthetic"}],
            "risks": [{"text": "The opening date slips and students arrive at a closed counter", "provenance": "assumption"}]}}},
    "template_lessons_learned": {"objective": "Record lessons from the meal counter opening", "method": "template_lessons_learned", "inputs": {
        "blocks": {
            "went_well": [{"text": "Pre-orders cut the lunch queue", "provenance": "synthetic"}],
            "went_poorly": [{"text": "The permit arrived two weeks late", "provenance": "synthetic"}],
            "causes": [{"text": "The permit application was submitted after the fit-out started", "provenance": "synthetic"}],
            "changes": [{"text": "Submit permits in the first week, before any fit-out", "provenance": "synthetic"}],
            "actions": [{"text": "Project lead adds a permit milestone to the next charter", "provenance": "synthetic"}],
            "share": [{"text": "The next campus food project team", "provenance": "synthetic"}],
            "evidence": [{"text": "The permit log and the change request", "provenance": "synthetic"}]}}},

    "template_adkar": {"objective": "Read the readiness evidence for the move to a contactless meal card", "method": "template_adkar", "inputs": {
        "blocks": {
            "awareness": [{"text": "The change is announced in the same email that closes the old card", "provenance": "synthetic"}],
            "desire": [{"text": "Counter staff have asked for the change because the old card is slow to load", "provenance": "synthetic"}],
            "knowledge": [{"text": "Nobody has written the steps for loading a new balance", "provenance": "assumption"}],
            "ability": [{"text": "Training for the new card is a single session at the counter", "provenance": "synthetic"}]
        }
}},
    "template_aida": {"objective": "Read the communication journey for the campus meal service", "method": "template_aida", "inputs": {
        "blocks": {
            "attention": [{"text": "A poster in the corridor where class groups wait", "provenance": "synthetic"}],
            "interest": [{"text": "The opening offer was posted in the class chat of the subject with the longest queue", "provenance": "synthetic"}],
            "desire": [{"text": "The price of the first meal card is lower than the walk-up price", "provenance": "synthetic"}],
            "action": [{"text": "The meal card can be bought at the counter without a queue", "provenance": "synthetic"}]
        }
}},
    "template_amo": {"objective": "Read why service on the meal counter is slow", "method": "template_amo", "inputs": {
        "blocks": {
            "ability": [{"text": "Two of the four counter staff have worked the till before", "provenance": "synthetic"}],
            "motivation": [{"text": "Counter staff have asked for the queue to be reduced before the next rota", "provenance": "synthetic"}],
            "opportunity": [{"text": "The counter has one till, so the queue cannot be split", "provenance": "assumption"}]
        }
    }},
    "template_attribution": {"objective": "Record how credit is given for the campus meal campaign", "method": "template_attribution", "inputs": {
        "blocks": {
            "touchpoints": [{"text": "The corridor poster, the class chat and the counter are the three recorded touchpoints", "provenance": "synthetic"}],
            "model": [{"text": "The last recorded touchpoint before a meal card is bought gets the credit", "provenance": "synthetic"}],
            "credit": [{"text": "The counter is credited for most of the new meal cards", "provenance": "assumption"}]
        }
}},
    "template_bcg": {"objective": "Place the campus food lines on the growth-share matrix", "method": "template_bcg", "inputs": {
        "blocks": {
            "stars": [{"text": "The hot meal line grows with the student population and holds the largest share of campus meals", "provenance": "synthetic"}],
            "cash_cows": [{"text": "The drinks counter has a high share of campus spending and no growth", "provenance": "synthetic"}],
            "question_marks": [{"text": "Breakfast packs are growing but hold a small share", "provenance": "assumption"}]
        }
}},
    "template_brand_equity": {"objective": "Read the brand equity of the campus meal service", "method": "template_brand_equity", "inputs": {
        "blocks": {
            "awareness": [{"text": "A short survey asked students whether they had heard of the counter", "provenance": "synthetic"}],
            "associations": [{"text": "The same survey asked what students associate the counter with", "provenance": "synthetic"}],
            "perceived_quality": [{"text": "Perceived quality was not asked in the survey", "provenance": "assumption"}]
        }
}},
    "template_burke_litwin": {"objective": "Trace the catering reorganisation through the organisation it affects", "method": "template_burke_litwin", "inputs": {
        "blocks": {
            "external_environment": [{"text": "The university is moving food concessions to a single supplier next year", "provenance": "synthetic"}],
            "mission_strategy": [{"text": "The canteen intends to keep its own cooking team", "provenance": "synthetic"}],
            "leadership": [{"text": "The canteen manager sets the rota and approves all leave personally", "provenance": "synthetic"}],
            "culture": [{"text": "The team has always been told the menu is fixed and cannot be argued with", "provenance": "synthetic"}],
            "structure": [{"text": "Cooking and counter service sit in two separate line-management structures", "provenance": "synthetic"}],
            "management_practices": [{"text": "The kitchen and the counter do not hold a shared daily meeting", "provenance": "assumption"}]
        }
}},
    "template_change_organization": {"objective": "Read the organisation behind the contactless meal card change", "method": "template_change_organization", "inputs": {
        "blocks": {
            "change_type": [{"text": "The change alters how students pay, not how the kitchen works", "provenance": "synthetic"}],
            "readiness": [{"text": "Counter staff asked for the change after the old card became unreliable", "provenance": "synthetic"}],
            "resistance": [{"text": "Students who pay in cash at the counter have not been considered", "provenance": "assumption"}],
            "support": [{"text": "A short session is planned for counter staff", "provenance": "synthetic"}]
        }
}},
    "template_competing_values": {"objective": "Read the culture of the campus catering team", "method": "template_competing_values", "inputs": {
        "blocks": {
            "clan": [{"text": "The team meets for ten minutes before service and talks through the day's problems", "provenance": "synthetic"}],
            "adhocracy": [{"text": "Two counter staff ran a trial of a new tray layout without asking the manager", "provenance": "synthetic"}],
            "hierarchy": [{"text": "Any change to the allergen procedure is signed off by the estate office before it is used", "provenance": "synthetic"}]
        }
    }},
    "template_cro": {"objective": "Record the first conversion test on the campus meal page", "method": "template_cro", "inputs": {
        "blocks": {
            "hypothesis": [{"text": "Putting the price before the menu will raise the number of meal cards bought", "provenance": "synthetic"}],
            "variants": [{"text": "The menu first and the price first are the two versions", "provenance": "synthetic"}],
            "metrics": [{"text": "Meal cards bought per visitor over one week", "provenance": "synthetic"}],
            "results": [{"text": "The test has not run yet", "provenance": "assumption"}]
        }
}},
    "template_digital_mix": {"objective": "Record the digital channel mix for the campus meal service", "method": "template_digital_mix", "inputs": {
        "blocks": {
            "owned": [{"text": "The class group and the counter page, both posted by the counter team", "provenance": "synthetic"}],
            "earned": [{"text": "A student food blog mentioned the counter once", "provenance": "synthetic"}],
            "paid": [{"text": "No paid channel has been used", "provenance": "assumption"}]
        }
}},
    "template_dmaic": {"objective": "Walk the campus meal card service through a DMAIC cycle", "method": "template_dmaic", "inputs": {
        "blocks": {
            "define": [{"text": "Students give up on lunch when the queue at the counter is long", "provenance": "synthetic"}],
            "measure": [{"text": "The wait at the counter was timed on a sheet for one week", "provenance": "synthetic"}],
            "analyze": [{"text": "Most of the wait comes from meals cooked to order rather than from serving", "provenance": "assumption"}],
            "improve": [{"text": "Two meals are cooked in advance and held for the rush", "provenance": "synthetic"}],
            "control": [{"text": "Nothing is in place to hold the change once the test ends", "provenance": "assumption"}]
        }
}},
    "template_email_crm": {"objective": "Record the lifecycle programme for the campus meal service", "method": "template_email_crm", "inputs": {
        "blocks": {
            "list": [{"text": "Students sign up at the counter and the list is kept in a spreadsheet", "provenance": "synthetic"}],
            "segments": [{"text": "Students are split by whether they have bought a meal card", "provenance": "synthetic"}],
            "campaigns": [{"text": "A welcome email goes out when a student signs up", "provenance": "synthetic"}],
            "automation": [{"text": "Nothing is sent automatically and no reminder is set", "provenance": "assumption"}]
        }
}},
    "template_funnel": {"objective": "Read the funnel for the campus meal service", "method": "template_funnel", "inputs": {
        "blocks": {
            "awareness": [{"text": "Posters in the corridor and a mention in the class chat", "provenance": "synthetic"}],
            "interest": [{"text": "A sample plate is shown at the counter during the first week", "provenance": "synthetic"}],
            "consideration": [{"text": "The menu is posted at the counter and on the class page", "provenance": "synthetic"}],
            "purchase": [{"text": "Most students pay cash at the counter rather than buying a meal card", "provenance": "assumption"}]
        }
}},
    "template_galbraith_star": {"objective": "Read the operating model of the campus catering service", "method": "template_galbraith_star", "inputs": {
        "blocks": {
            "strategy": [{"text": "The service aims to be the fastest student-priced hot meal on campus", "provenance": "synthetic"}],
            "structure": [{"text": "One kitchen line and one counter, with the counter team reporting to the estate office", "provenance": "synthetic"}],
            "processes": [{"text": "Orders are taken by phone and cooked to order at the counter", "provenance": "synthetic"}],
            "rewards": [{"text": "Staff are rewarded for meals sold rather than for queue time", "provenance": "assumption"}],
            "people": [{"text": "The counter team is three part-time students and one supervisor", "provenance": "synthetic"}]
        }
}},
    "template_ge_mckinsey": {"objective": "Place the campus food lines on the GE-McKinsey matrix", "method": "template_ge_mckinsey", "inputs": {
        "blocks": {
            "high_high": [{"text": "The hot meal line sits in a growing segment and holds the strongest position", "provenance": "synthetic"}],
            "medium_medium": [{"text": "The drinks counter sits in a slow segment with a middling position", "provenance": "assumption"}]
        }
}},
    "template_generic_strategies": {"objective": "Read the competitive range of the campus meal service", "method": "template_generic_strategies", "inputs": {
        "blocks": {
            "low_cost": [{"text": "Ingredients are bought at the wholesale market and cooked in one batch", "provenance": "synthetic"}],
            "differentiation": [{"text": "Meals are cooked to order from a menu that changes each week", "provenance": "synthetic"}],
            "focus_low_cost": [{"text": "The service is positioned as the cheapest hot meal for students on campus", "provenance": "synthetic"}]
        }
}},
    "template_job_characteristics": {"objective": "Read the shape of the kitchen supervisor's role", "method": "template_job_characteristics", "inputs": {
        "blocks": {
            "skill_variety": [{"text": "The role covers ordering, the rota and the weekly stock count, so three kinds of skill are needed at once", "provenance": "synthetic"}],
            "task_identity": [{"text": "The supervisor signs the weekly order and the rota is published under their name", "provenance": "synthetic"}],
            "task_significance": [{"text": "The supervisor is not told when a meal line sells out, so the consequence of the role is invisible", "provenance": "assumption"}],
            "autonomy": [{"text": "The supplier can be changed without asking the kitchen manager", "provenance": "synthetic"}]
        }
    }},
    "template_kirkpatrick": {"objective": "Read the evidence from the food-safety induction for kitchen staff", "method": "template_kirkpatrick", "inputs": {
        "blocks": {
            "reaction": [{"text": "The induction was run twice, and the second session was better attended", "provenance": "synthetic"}],
            "learning": [{"text": "Staff could name the three temperatures that have to be logged", "provenance": "synthetic"}],
            "behavior": [{"text": "Nobody has checked whether the log is completed on a busy Saturday", "provenance": "assumption"}]
        }
    }},
    "template_kotter": {"objective": "Read the eight steps of the move to a contactless meal card", "method": "template_kotter", "inputs": {
        "blocks": {
            "urgency": [{"text": "The card reader at the counter failed twice in the same week", "provenance": "synthetic"}],
            "coalition": [{"text": "The estate office, the counter team and the students' union have to agree before the old card is withdrawn", "provenance": "synthetic"}],
            "empower": [{"text": "Counter staff can order a second card reader without asking the estate office first", "provenance": "synthetic"}],
            "wins": [{"text": "No result has been recorded, because the change has not started", "provenance": "assumption"}]
        }
    }},
    "template_lewin": {"objective": "Read where the contactless meal card change stands", "method": "template_lewin", "inputs": {
        "blocks": {
            "unfreeze": [{"text": "The old card is kept live for one more term, so nothing has been given up yet", "provenance": "synthetic"}],
            "change": [{"text": "The new card is loaded at the counter and staff take payment on a second device", "provenance": "synthetic"}],
            "refreeze": [{"text": "The new card is still a temporary arrangement at the counter", "provenance": "assumption"}]
        }
}},
    "template_logic_model": {"objective": "Lay out the logic of the campus mentoring programme", "method": "template_logic_model", "inputs": {
        "blocks": {
            "inputs": [{"id": "I1", "text": "Two trained mentors and a room booked for one afternoon a week", "provenance": "synthetic"}],
            "activities": [{"id": "I2", "text": "Each mentor sees a small group of first-year students for an hour", "provenance": "synthetic"}],
            "outputs": [{"id": "I3", "text": "A session record is kept for each group", "provenance": "synthetic"}],
            "outcomes": [{"id": "I4", "text": "No measure of student retention has been agreed yet", "provenance": "assumption"}],
            "impact": [{"id": "I5", "text": "Retention of first-year students in the years the programme has run", "provenance": "assumption"}]
        },
        "links": [
            {"from": "I1", "to": "I2"},
            {"from": "I2", "to": "I3"},
            {"from": "I3", "to": "I4"},
            {"from": "I4", "to": "I5"}
        ]
}},
    "template_marketing_automation": {"objective": "Record the automation behind the campus meal enquiry", "method": "template_marketing_automation", "inputs": {
        "blocks": {
            "triggers": [{"text": "A form on the counter page starts the sequence", "provenance": "synthetic"}],
            "flows": [{"text": "Enquiry, sample offered, meal card sold", "provenance": "synthetic"}],
            "scoring": [{"text": "The score counts form visits and has never been checked against sales", "provenance": "assumption"}],
            "nurture": [{"text": "One email a week for a month, then the contact is left alone", "provenance": "synthetic"}]
        }
}},
    "template_mckinsey_7s": {"objective": "Check the fit of the seven elements for the campus catering service", "method": "template_mckinsey_7s", "inputs": {
        "blocks": {
            "strategy": [{"text": "The service aims to be the fastest student-priced hot meal on campus", "provenance": "synthetic"}],
            "structure": [{"text": "One kitchen line and one counter, with the counter team reporting to the estate office", "provenance": "synthetic"}],
            "systems": [{"text": "Ordering is by phone, and no record is kept of what was ordered", "provenance": "assumption"}],
            "shared_values": [{"text": "The team treats the queue as the problem to be hidden rather than removed", "provenance": "synthetic"}],
            "skills": [{"text": "Two of the four counter staff have run the kitchen before", "provenance": "synthetic"}]
        }
}},
    "template_mintzberg": {"objective": "Read how the campus catering service is actually put together", "method": "template_mintzberg", "inputs": {
        "blocks": {
            "strategic_apex": [{"text": "The estate office decides the concession and sets the rent", "provenance": "synthetic"}],
            "middle_line": [{"text": "The canteen manager sits between the estate office and the kitchen", "provenance": "synthetic"}],
            "operating_core": [{"text": "The kitchen and the counter teams cook and serve", "provenance": "synthetic"}],
            "technostructure": [{"text": "Nobody writes the food-handling procedure the kitchen follows", "provenance": "assumption"}]
        }
}},
    "template_nine_box": {"objective": "Record how the counter team is reviewed", "method": "template_nine_box", "inputs": {
        "blocks": {
            "performance_criteria": [{"text": "Performance is judged on the queue at the counter and on the complaints the cafe receives", "provenance": "synthetic"}],
            "potential_criteria": [{"text": "Potential is judged on whether the person has run a shift on their own", "provenance": "synthetic"}],
            "placements": [{"text": "The manager has placed two counter staff in the strong performance and strong potential cell, and two in the strong performance and developing potential cell, with the reason recorded for each", "provenance": "synthetic"}]
        }
    }},
    "template_org_design": {"objective": "Read the design of the university catering unit", "method": "template_org_design", "inputs": {
        "blocks": {
            "strategy": [{"text": "The unit aims to run the same service across three sites with one kitchen team", "provenance": "synthetic"}],
            "decision_rights": [{"text": "The estate office decides the budget and the kitchen manager decides the rota", "provenance": "synthetic"}],
            "structure": [{"text": "One kitchen line and one counter, with the counter team reporting to the estate office", "provenance": "synthetic"}],
            "processes": [{"text": "Nobody has written down how a stock count is passed from the counter to the kitchen", "provenance": "assumption"}],
            "incentives": [{"text": "The kitchen team is measured on meals served, and not on the complaints the service produces", "provenance": "synthetic"}]
        }
    }},
    "template_pdsa": {"objective": "Record the first cycle of the contactless meal card trial", "method": "template_pdsa", "inputs": {
        "blocks": {
            "plan": [{"text": "Test a pre-order shelf for ten minutes at the counter, and record the wait at the counter", "provenance": "synthetic"}],
            "do": [{"text": "The shelf was run at the counter on four days", "provenance": "synthetic"}],
            "study": [{"text": "Wait times were noted on a sheet but the count was never totalled", "provenance": "assumption"}]
        }
}},
    "template_porters_diamond": {"objective": "Read the conditions shaping the campus food industry", "method": "template_porters_diamond", "inputs": {
        "blocks": {
            "factor_conditions": [{"text": "Vegetables are bought from a market a few hours from campus", "provenance": "synthetic"}],
            "demand_conditions": [{"text": "Most students eat on campus between classes", "provenance": "synthetic"}],
            "related_industries": [{"text": "A printing shop on the same street supplies menus and flyers", "provenance": "synthetic"}],
            "firm_strategy": [{"text": "Two counters compete on price and one competes on variety", "provenance": "synthetic"}]
        }
}},
    "template_rfm": {"objective": "Read the RFM grouping of the campus meal customers", "method": "template_rfm", "inputs": {
        "blocks": {
            "recency": [{"text": "Recency is measured from the last meal card top-up in the register", "provenance": "synthetic"}],
            "frequency": [{"text": "Frequency is the number of meals bought in the term", "provenance": "synthetic"}],
            "monetary": [{"text": "The window is a term, and students who left are not in the list", "provenance": "assumption"}]
        }
}},
    "template_seo_content": {"objective": "Record the search and content plan for the campus meal service", "method": "template_seo_content", "inputs": {
        "blocks": {
            "keywords": [{"text": "Students search for cheap meals near campus during a short break", "provenance": "synthetic"}],
            "content": [{"text": "A page listing the meal times and the fixed price", "provenance": "synthetic"}],
            "technical": [{"text": "The page loads slowly on a phone", "provenance": "assumption"}]
        }
}},
    "template_social_media": {"objective": "Record the social and influencer plan for the campus meal service", "method": "template_social_media", "inputs": {
        "blocks": {
            "platforms": [{"text": "The counter posts in the campus student group", "provenance": "synthetic"}],
            "content": [{"text": "A daily post of the day's menu", "provenance": "synthetic"}],
            "engagement": [{"text": "Reach is read by eye from the group and is not recorded", "provenance": "assumption"}],
            "influencers": [{"text": "One student creator posts once in return for a free meal card", "provenance": "synthetic"}]
        }
}},
    "template_stp": {"objective": "Lay out the STP decisions for the campus meal market", "method": "template_stp", "inputs": {
        "blocks": {
            "segmentation": [{"text": "Students are divided by the length of the break between their classes", "provenance": "synthetic"}],
            "targeting": [{"text": "First- and second-year students with a short midday break", "provenance": "synthetic"}],
            "positioning": [{"text": "The fastest student-priced hot meal beside the gate", "provenance": "synthetic"}]
        }
}},
    "template_stp_evidence": {"objective": "Audit the evidence behind the STP decisions for the campus meal market", "method": "template_stp_evidence", "inputs": {
        "blocks": {
            "segmentation_evidence": [{"text": "Break lengths were taken from the published timetable", "provenance": "synthetic"}],
            "targeting_evidence": [{"text": "The chosen segment has not been surveyed for how often it eats on campus", "provenance": "assumption"}],
            "positioning_evidence": [{"text": "A count of the wait at the two counters was kept for a week", "provenance": "synthetic"}]
        }
}},
    "template_strategic_positioning": {"objective": "Read the positioning claim of the campus meal service", "method": "template_strategic_positioning", "inputs": {
        "blocks": {
            "position": [{"text": "The fastest student-priced hot meal on campus", "provenance": "synthetic"}],
            "differentiation": [{"text": "Meals are ready within ten minutes because they are cooked in advance", "provenance": "synthetic"}],
            "value_proposition": [{"text": "A hot meal you can eat between classes without leaving the gate", "provenance": "synthetic"}],
            "target_segment": [{"text": "Students with a short break between classes", "provenance": "synthetic"}]
        }
}},
    "template_tam": {"objective": "Read the acceptance evidence for the meal card ordering system", "method": "template_tam", "inputs": {
        "blocks": {
            "perceived_usefulness": [{"text": "Students were asked whether pre-ordering saves their break", "provenance": "synthetic"}],
            "perceived_ease_of_use": [{"text": "No question asked whether ordering by phone is easy", "provenance": "assumption"}],
            "attitude": [{"text": "The survey closed before the attitude questions were asked", "provenance": "assumption"}]
        }
}},
    "template_theory_of_change": {"objective": "Set out the causal pathway for the campus mentoring programme", "method": "template_theory_of_change", "inputs": {
        "blocks": {
            "inputs": [{"id": "I1", "text": "Two trained mentors and a room booked for one afternoon a week", "provenance": "synthetic"}],
            "activities": [{"id": "I2", "text": "Each mentor sees a small group of first-year students for an hour", "provenance": "synthetic"}],
            "outputs": [{"id": "I3", "text": "A record of the sessions held and the students who attended", "provenance": "synthetic"}],
            "outcomes": [{"id": "I4", "text": "Students report that they know where to ask for help", "provenance": "assumption"}],
            "impact": [{"id": "I5", "text": "The programme is kept in the induction timetable in the year after the funding ends", "provenance": "assumption"}],
            "assumptions": [{"id": "A6", "text": "First-year students who join no society are the ones who find a mentor, and the mentors stay for a year", "provenance": "assumption"}]
        },
        "links": [
            {"from": "I1", "to": "I2"},
            {"from": "I2", "to": "I3"},
            {"from": "I3", "to": "I4"},
            {"from": "I4", "to": "I5"}
        ]
}},
    "template_tuckman": {"objective": "Read how the tray assembly team is working together", "method": "template_tuckman", "inputs": {
        "blocks": {
            "forming": [{"text": "The tray assembly team was put together in the week the kitchen moved", "provenance": "synthetic"}],
            "storming": [{"text": "Two members of the team disagreed about who took the orders", "provenance": "synthetic"}],
            "norming": [{"text": "The team now sets up the trays in the same order every shift", "provenance": "synthetic"}],
            "adjourning": [{"text": "The team will be split when the summer staff arrive", "provenance": "assumption"}]
        }
    }},
    "template_utaut": {"objective": "Read the adoption evidence for the meal card ordering system", "method": "template_utaut", "inputs": {
        "blocks": {
            "performance_expectancy": [{"text": "Students were asked whether pre-ordering saves their break", "provenance": "synthetic"}],
            "effort_expectancy": [{"text": "No question asked whether ordering by phone is easy", "provenance": "assumption"}],
            "facilitating_conditions": [{"text": "The counter has one phone that staff cannot leave unattended", "provenance": "synthetic"}]
        }
}},
    # ---- Operations management (session 8) --------------------------------------
    # Eleven worked examples, one per worksheet on the Operations shelf.  Each is a
    # *synthetic* illustrative case (the campus meal counter the shelf's own unit
    # examples already use), and each satisfies its template's own `validate()`:
    # `tests/test_operations_frameworks.py::ExampleTest` runs it through
    # `run_template` and requires every declared check to pass.  They are examples,
    # not advice: nothing here is a finding about a real business, and the figure
    # the paper draws is built from these items, never from a model.
    "template_scor": {"objective": "Map the meal counter's supply chain across the six SCOR processes", "method": "template_scor", "inputs": {
        "blocks": {
            "plan": [{"text": "Orders are forecast from last week's counter totals and the prep list is set the evening before", "provenance": "synthetic"}],
            "source": [{"text": "Bread comes from one regional bakery each morning; vegetables from the wholesale market twice a week", "provenance": "synthetic"}],
            "make": [{"text": "Meals are cooked to order on a single line, packed at the counter and handed over", "provenance": "synthetic"}],
            "deliver": [{"text": "Students collect at the counter; there is no delivery beyond the campus gate", "provenance": "synthetic"}],
            "return": [{"text": "A meal that is sent back is remade and the reason is written on the day sheet", "provenance": "synthetic"}],
            "enable": [{"text": "One supervisor holds the food-safety log, the supplier list and the rota", "provenance": "synthetic"}]}}},
    "template_sipoc": {"objective": "Bound the lunch service at the meal counter from supplier to customer", "method": "template_sipoc", "inputs": {
        "blocks": {
            "suppliers": [{"text": "A regional bakery supplies bread; the wholesale market supplies vegetables; the estate office provides the counter", "provenance": "synthetic"}],
            "inputs": [{"text": "Bread, vegetables, gas, one oven, the food-safety licence and the day's order list", "provenance": "synthetic"}],
            "process": [{"text": "The order is taken, the meal is assembled and packed, and the student collects and pays", "provenance": "synthetic"}],
            "outputs": [{"text": "A packed hot meal and a payment receipt", "provenance": "synthetic"}],
            "customers": [{"text": "Students on the lunch break, and the supervisor who reviews the day sheet", "provenance": "synthetic"}]}}},
    "template_value_stream_map": {"objective": "Follow one lunch order from request to collection at the meal counter", "method": "template_value_stream_map", "inputs": {
        "blocks": {
            "process_steps": [{"text": "Take the order, assemble the meal, pack it, and the student collects and pays", "provenance": "synthetic"}],
            "cycle_and_lead_times": [{"text": "Taking the order takes about a minute, assembling and packing four, and the wait at noon is twelve", "provenance": "synthetic"}],
            "inventory_wip": [{"text": "Packed meals wait on the shelf in a batch of roughly fifteen before collection", "provenance": "synthetic"}],
            "waits_delays": [{"text": "The flow stops in front of the oven, which bakes one tray at a time, and again at payment", "provenance": "synthetic"}],
            "value_added": [{"text": "Cooking and packing change the meal; waiting for the oven and for payment do not (my judgement)", "provenance": "synthetic"}],
            "improvements": [{"text": "Load the oven trays before the noon peak and measure the change in the noon wait", "provenance": "synthetic"}]}}},
    "template_5s": {"objective": "Audit the meal counter against the five S", "method": "template_5s", "inputs": {
        "blocks": {
            "sort": [{"text": "Serving trays, spare menus and a broken card reader were taken off the counter bench", "provenance": "synthetic"}],
            "set_in_order": [{"text": "Bread, trays, receipts and cleaning cloths each have a marked place under the bench", "provenance": "synthetic"}],
            "shine": [{"text": "The oven and the counter are cleaned and inspected at close, and the log is signed", "provenance": "synthetic"}],
            "standardize": [{"text": "A photograph of the bench with its marked places is posted at the door", "provenance": "synthetic"}],
            "sustain": [{"text": "The supervisor audits the bench every Friday and writes the result on the day sheet", "provenance": "synthetic"}]}}},
    "template_a3": {"objective": "State and counter the noon queue at the meal counter on one page", "method": "template_a3", "inputs": {
        "blocks": {
            "problem": [{"text": "At the noon peak the wait for a packed meal reaches twelve minutes against a five-minute standard", "provenance": "synthetic"}],
            "current_condition": [{"text": "One oven bakes one tray at a time, and orders are only taken at the counter", "provenance": "synthetic"}],
            "target": [{"text": "Hold the noon wait under five minutes without buying a second oven", "provenance": "synthetic"}],
            "causes": [{"text": "Orders are taken only at the counter, so cooking cannot start before a student reaches it", "provenance": "synthetic"}],
            "countermeasures": [{"text": "Take orders by phone from the break before noon and cook to those orders in one batch", "provenance": "synthetic"}],
            "plan": [{"text": "The supervisor opens the phone line in week one and the kitchen tries two batches a day in week two", "provenance": "synthetic"}],
            "follow_up": [{"text": "The noon wait is logged daily and reviewed after four weeks; a wait above eight minutes reopens the analysis", "provenance": "synthetic"}]}}},
    "template_toc": {"objective": "Find and exploit the constraint at the meal counter", "method": "template_toc", "inputs": {
        "blocks": {
            "identify": [{"text": "The oven limits the counter: it bakes one tray at a time and no other step serves more meals than it bakes", "provenance": "synthetic"}],
            "exploit": [{"text": "The oven never idles at noon: trays are loaded before the peak and the supervisor keeps it fed", "provenance": "synthetic"}],
            "subordinate": [{"text": "Assembling and packing are paced to the oven's tray, not to the number of staff at the counter", "provenance": "synthetic"}],
            "elevate": [{"text": "A second tray shelf shortens loading; the test is whether meals per hour rise at the same staff level", "provenance": "synthetic"}],
            "reassess": [{"text": "If loading stops being the loss, the constraint may move to payment, where one reader serves every collection", "provenance": "synthetic"}]}}},
    "template_root_cause": {"objective": "Trace the late noon hand-over at the meal counter to a cause", "method": "template_root_cause", "inputs": {
        "blocks": {
            "problem": [{"text": "Meals are handed over late at the noon peak, at the counter beside the main gate, every weekday", "provenance": "synthetic"}],
            "people": [{"text": "Two of the three counter staff are new and take longer to assemble a meal", "provenance": "synthetic"}],
            "process": [{"text": "Orders are taken only at the counter, so cooking cannot start until a student arrives", "provenance": "synthetic", "id": "PRC"}],
            "equipment": [{"text": "The single oven bakes one tray at a time and has no second shelf", "provenance": "synthetic"}],
            "materials": [{"text": "Bread arrives after the peak twice a week, so the first batch is delayed", "provenance": "synthetic"}],
            "measurement": [{"text": "The wait is timed from collection, not from arrival, so the queue is not counted", "provenance": "synthetic"}],
            "environment": [{"text": "The counter faces the gate and the noon sun, and the serving area has no shade", "provenance": "assumption"}],
            "root_cause": [{"text": "Taking orders only at the counter is the cause the timings support; the oven and the rota add to it", "provenance": "synthetic", "id": "RC"}]},
        "links": [{"from": "PRC", "to": "RC"}]}},
    "template_fmea": {"objective": "Anticipate how the meal counter fails at the noon peak", "method": "template_fmea", "inputs": {
        "blocks": {
            "failure_modes": [{"text": "A meal is packed with the wrong filling; the card reader fails at collection; the bread runs out", "provenance": "synthetic"}],
            "effects": [{"text": "The wrong filling means a complaint and a remake; a failed reader lengthens the queue; a sell-out loses the sale", "provenance": "synthetic"}],
            "causes": [{"text": "The filling is called out verbally; there is no spare reader; bread arrives once a day", "provenance": "synthetic"}],
            "controls": [{"text": "The day sheet records remakes, the reader is tested at opening, and the bread order is fixed weekly", "provenance": "synthetic"}],
            "actions": [{"text": "Read the filling back to the student, keep one spare reader at the counter and raise the Tuesday bread order", "provenance": "synthetic"}],
            "owners": [{"text": "The counter supervisor owns the first two actions and reviews them at the weekly rota meeting", "provenance": "synthetic"}]}}},
    "template_kraljic": {"objective": "Place what the meal counter buys on the Kraljic portfolio", "method": "template_kraljic", "inputs": {
        "blocks": {
            "criteria": [{"text": "Profit impact is the share of meal cost; supply risk is how many alternative suppliers can serve within a week", "provenance": "synthetic"}],
            "strategic": [{"text": "Bread from the single regional bakery: a high cost share and no alternative supplier at short notice", "provenance": "synthetic"}],
            "leverage": [{"text": "Vegetables from the wholesale market: a high cost share with several sellers", "provenance": "synthetic"}],
            "bottleneck": [{"text": "The gas contract for the oven: a low cost share with one supplier for the building", "provenance": "synthetic"}],
            "non_critical": [{"text": "Packaging, receipts and cleaning cloths: a low cost share with many sellers", "provenance": "synthetic"}]}}},
    "template_sop": {"objective": "Set the five plans of the meal counter beside each other", "method": "template_sop", "inputs": {
        "blocks": {
            "demand_plan": [{"text": "The plan assumes the same number of meals as last term, with a peak of ninety at noon", "provenance": "synthetic"}],
            "supply_plan": [{"text": "One oven, three counter staff and one bread delivery a day can serve the peak if two batches are pre-loaded", "provenance": "synthetic"}],
            "inventory_plan": [{"text": "Half a day of bread and a day of dry goods are held; nothing perishable is held overnight", "provenance": "synthetic"}],
            "capacity_plan": [{"text": "Capacity binds at the oven during the noon hour, not at the counter", "provenance": "synthetic"}],
            "financial_plan": [{"text": "At the current price the plan holds its margin only if no second oven is bought this term", "provenance": "synthetic"}],
            "decisions": [{"text": "The plans disagree on the peak: demand needs two pre-loaded batches, so the kitchen shifts prep earlier", "provenance": "synthetic"}]}}},
    "template_pdca": {"objective": "Run one improvement cycle on the noon wait at the meal counter", "method": "template_pdca", "inputs": {
        "blocks": {
            "plan": [{"text": "Reduce the noon wait from twelve minutes to five by taking phone orders before the break", "provenance": "synthetic"}],
            "do": [{"text": "The phone line ran for three weeks at the main gate counter only", "provenance": "synthetic"}],
            "check": [{"text": "The noon wait fell to seven minutes on four of five days; Wednesday stayed at eleven", "provenance": "synthetic"}],
            "act": [{"text": "The change is written into the opening checklist, and Wednesday is the next cycle's problem", "provenance": "synthetic"}]}}},

}


from . import case_decision   # registers "case_decision" in TEMPLATES (kept in its own module; imported last to avoid a cycle)
