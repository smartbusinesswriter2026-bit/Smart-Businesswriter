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
    },
    "template_strategic_group_map": {
        "name": "Strategic group map with a declared-axis audit", "short": "strategic group map",
        "registry_ids": ["STR-12"], "row_label": "competitor", "column_label": "axis",
        "min_rows": 2, "max_rows": 12, "min_columns": 2, "max_columns": 2,
        "require_groups": True, "require_rationale": True,
        "intended_use": "List the competitors you have evidence for, declare and justify the two axes, place each competitor on both, and record the strategic group you assign.",
        "unsupported_use": "Choosing the axes or the groups for you; inventing competitor data; drawing or computing a position; scoring or ranking competitors.",
        "extra_help": "Exactly two axes are required, each with a one-line rationale. Placing a competitor is your judgment; the system only records and audits it.",
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
        seen.add((row_id, column_id))
        cells.append({"row": row_id, "column": column_id, "text": cell["text"], "provenance": cell["provenance"],
                      "source": cell["source"], "materiality": cell["materiality"]})
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
    return {"kind": kind, "registry_ids": spec["registry_ids"], "name": spec["name"], "short": spec["short"],
            "row_label": spec["row_label"], "column_label": spec["column_label"],
            "rows": rows, "columns": n["columns"], "audit": audit, "counts": counts}


def render_matrix(a):
    P = PERIOD
    tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P)
    a_ = a["audit"]
    t = (f"This {a['short']} organizes {tok('n_rows')} {a['row_label']}s against {tok('n_columns')} "
         f"{a['column_label']}s, with {tok('n_cells')} cells of evidence you supplied. ")
    if a_["empty_cells"]:
        t += f"{tok('n_empty_cells')} cells are empty. They are named below and are not filled in by the system. "
    if a["counts"]["n_unsupported"]:
        t += f"{tok('n_unsupported')} cells rest on assumptions rather than user-supplied or sourced evidence. "
    if a_["synthetic_cells"]:
        t += "Some cells are synthetic and illustrative only; they are not observations. "
    if a_["rows_without_group"]:
        t += f"{len(a_['rows_without_group'])} {a['row_label']}s have no declared group. "
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
    return {"id": t["id"], "version": t["version"], "name": t["name"], "registry_ids": t["registry_ids"], "tier": t.get("tier", "T4"), "intended_use": t["intended_use"], "unsupported_use": t["unsupported_use"],
            "input_help": t["input_help"], "blocks": blocks, "form_kind": form_kind, "defaults": list(t["defaults"]), "limitations": list(t["limitations"]), "planned_checks": list(t["test_names"]), "example_request": EXAMPLES.get(kind)}

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
            "value_propositions": [{"text": "A hot rice meal under eighty pesos in under ten minutes", "provenance": "synthetic", "id": "VP1"}],
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
            "price": [{"text": "Seventy-five pesos a meal, cost-plus pricing", "provenance": "synthetic"}],
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
}


from . import case_decision   # registers "case_decision" in TEMPLATES (kept in its own module; imported last to avoid a cycle)
