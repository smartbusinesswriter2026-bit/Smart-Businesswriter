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
    p = it["provenance"]
    return {"user": "user-supplied", "sourced": f"sourced: {it.get('source')}", "assumption": "assumption (unsupported)", "synthetic": "synthetic (illustrative only)"}[p]

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

def _line(it): return f"  [{it['id']}] {it['text']} — {_label(it)}" + (f"; materiality: {it['materiality']} (your rating)" if it.get("materiality") else "")
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
        lines += [f"  [{o['id']}] {o['tows']}: {o['text']} — follows from {', '.join(o['supports'])}" for o in a["options"]]
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
    ok_line = all(f"[{i}] {t} — " in listing for i, t, _, _ in raw)
    return [("each_item_placed_exactly_once", sorted(placed) == sorted(i for i, _, _, _ in raw) and len(set(placed)) == n),
            ("listing_reproduces_every_input_text_verbatim", ok_line and listing.count("\n  [") + (1 if listing.startswith("  [") else 0) >= n),
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
        "key_partners": ("Key partners", "Who you depend on, and for what"),
        "key_activities": ("Key activities", "What the business must do well"),
        "key_resources": ("Key resources", "What it needs to do those activities"),
        "value_propositions": ("Value propositions", "The value you promise each segment"),
        "customer_relationships": ("Customer relationships", "How you win, keep and grow customers"),
        "channels": ("Channels", "How the value reaches the customer"),
        "customer_segments": ("Customer segments", "Who you serve"),
        "cost_structure": ("Cost structure", "The main costs the model creates"),
        "revenue_streams": ("Revenue streams", "How the business earns"),
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
}
CANVAS_MAX_ITEMS_PER_BLOCK = 20


def _canvas_item(it, where, errs, used, n):
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
    iid = it.get("id", f"E{n}")
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
         all(f"[{i}] {t} — " in listing for i, t, _ in raw),
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


def run_template(kind, inp):
    t = TEMPLATES[kind]; a = t["build"](inp); narrative, listing = t["render"](a)
    arts = a.get("artifacts") or [{"id": k, "metric": k, "value": str(v), "unit": "count", "precision": 0} for k, v in a["counts"].items()]
    return {"analysis": a, "narrative": narrative, "listing": listing, "results": [[n, bool(ok)] for n, ok in t["tests"](inp, a, narrative, listing)], "counts": a["counts"],
            "artifacts": arts, "text_refs": a.get("text_refs", {})}

def describe(kind):
    t = TEMPLATES[kind]
    return {"id": t["id"], "version": t["version"], "name": t["name"], "registry_ids": t["registry_ids"], "tier": t.get("tier", "T4"), "intended_use": t["intended_use"], "unsupported_use": t["unsupported_use"],
            "input_help": t["input_help"], "defaults": list(t["defaults"]), "limitations": list(t["limitations"]), "planned_checks": list(t["test_names"]), "example_request": EXAMPLES[kind]}

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
}


from . import case_decision   # registers "case_decision" in TEMPLATES (kept in its own module; imported last to avoid a cycle)
