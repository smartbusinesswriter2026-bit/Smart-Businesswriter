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
}


from . import case_decision   # registers "case_decision" in TEMPLATES (kept in its own module; imported last to avoid a cycle)
