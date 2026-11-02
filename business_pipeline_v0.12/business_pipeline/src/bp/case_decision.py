"""Business case decision analysis (Build Charter Stage 4 default slice). Tier T2: custom analysis built on the vetted NPV method.
YOU supply the case facts, the alternatives, their cash flows, the discount rate and range, and (optionally) the decision rule. The system
computes each alternative's NPV, finds where the NPV ranking changes across your rate range, and states a preference ONLY under your own
stated rule. It invents no fact, alternative, weight or winner (charter 1.3; manual P1, 8)."""
import re
from decimal import Decimal as D, InvalidOperation
from . import methods as M
from .methods import DataError
from .templates import TEMPLATES, EXAMPLES, _items, CTRL, MAX_TEXT, PERIOD, ID_RE

RULES = ("highest_npv",)
AID = re.compile(r"[A-Za-z0-9_]{1,12}")
GRID, DENSE, TIE = 400, 997, D("1e-9")

def _num(x):
    if isinstance(x, (bool, float)): raise ValueError("pass numbers as strings, integers or exact decimals, not binary floats")
    d = D(str(x))
    if not d.is_finite(): raise ValueError("not a finite number")
    return d

def normalize(inp):
    errs = []
    if not isinstance(inp, dict): return None, ["inputs must be an object"]
    extra = set(inp) - {"facts", "alternatives", "rate", "rate_provenance", "rate_range", "decision_rule", "currency"}
    if extra: errs.append(f"unknown input {sorted(extra)}")
    facts = _items(inp, "facts", None, None, errs, "F"); fids = {f["id"] for f in facts}
    cur = inp.get("currency")
    if cur is not None and not (isinstance(cur, str) and re.fullmatch(r"[A-Z]{3}", cur)): errs.append("currency must be a three-letter code such as USD")
    rule = inp.get("decision_rule")
    if rule is not None and rule not in RULES: errs.append(f"decision_rule must be null or one of {list(RULES)}; the decision rule is yours and the system will not choose one")
    try:
        rate = _num(inp.get("rate")); lo, hi = (_num(x) for x in inp.get("rate_range"))
        if not (lo > D("-0.99") and lo < hi): errs.append("rate_range must be [low, high] with -0.99 < low < high")
        elif not (lo <= rate <= hi): errs.append("rate must lie inside rate_range")
    except (InvalidOperation, ValueError, TypeError): errs.append("'rate' and 'rate_range' [low, high] are required numbers (strings or integers)"); rate = lo = hi = None
    rp = inp.get("rate_provenance", "user")
    if rp not in ("user", "sourced", "assumption", "synthetic"): errs.append("rate_provenance must be user, sourced, assumption or synthetic")
    raw = inp.get("alternatives"); alts, used = [], set()
    if not isinstance(raw, list) or not 2 <= len(raw) <= 5: errs.append("'alternatives' must be a list of 2 to 5 alternatives you supply"); raw = []
    for n, a in enumerate(raw, 1):
        w = f"alternatives[{n - 1}]"
        if not isinstance(a, dict): errs.append(f"{w} must be an object"); continue
        name = a.get("name")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 60 or CTRL.search(name): errs.append(f"{w}: 'name' is required (one line, at most 60 characters)"); continue
        desc = a.get("description", "")
        if not isinstance(desc, str) or len(desc.strip()) > MAX_TEXT or CTRL.search(desc): errs.append(f"{w}: 'description' must be one line of at most {MAX_TEXT} characters"); continue
        sup = a.get("supports")
        if not isinstance(sup, list) or not sup: errs.append(f"{w}: must cite at least one case fact in 'supports' (alternatives must follow from the case)"); continue
        if [x for x in sup if x not in fids]: errs.append(f"{w}: cites unknown fact ids {[x for x in sup if x not in fids]}"); continue
        cf = a.get("cashflows")
        try:
            if not isinstance(cf, list) or not 2 <= len(cf) <= 30: raise ValueError
            cfd = [_num(x) for x in cf]
        except (InvalidOperation, ValueError, TypeError): errs.append(f"{w}: 'cashflows' must be 2 to 30 numbers (strings or integers), first at t=0"); continue
        prov = a.get("cashflow_provenance")
        if prov not in ("user", "sourced", "assumption", "synthetic"): errs.append(f"{w}: 'cashflow_provenance' is required: user, sourced, assumption or synthetic"); continue
        src = a.get("source")
        if prov == "sourced" and (not isinstance(src, str) or not src.strip() or CTRL.search(src)): errs.append(f"{w}: sourced cash flows need a 'source' (one line)"); continue
        aid = a.get("id", f"A{n}")
        if not isinstance(aid, str) or not AID.fullmatch(aid) or aid in used or aid in fids: errs.append(f"{w}: id must be unique, 1-12 letters, digits or _"); continue
        used.add(aid); alts.append({"id": aid, "name": name.strip(), "description": desc.strip(), "supports": list(dict.fromkeys(sup)), "cashflows": cfd, "provenance": prov, "source": src.strip() if isinstance(src, str) else None})
    for i in range(len(alts)):
        for j in range(i + 1, len(alts)):
            if alts[i]["cashflows"] == alts[j]["cashflows"]: errs.append(f"alternatives {alts[i]['id']} and {alts[j]['id']} have identical cash flows, so they cannot be compared")
    if errs: return None, errs
    return {"facts": facts, "alts": alts, "rate": rate, "lo": lo, "hi": hi, "rule": rule, "currency": cur, "rate_provenance": rp}, []

def validate(inp): return normalize(inp)[1]

_npv = lambda cf, r: M.npv({"rate": r, "cashflows": cf})
_ref = lambda cf, r: M.npv_reference({"rate": r, "cashflows": cf})

def _roots(a, b, lo, hi, f, grid):
    step = (hi - lo) / grid; xs = [lo + step * k for k in range(grid + 1)]; ds = [f(a, x) - f(b, x) for x in xs]; roots = []
    for k in range(grid):
        if ds[k] == 0 and (not roots or roots[-1] != xs[k]): roots.append(xs[k]); continue
        if ds[k] * ds[k + 1] < 0:
            l, h = xs[k], xs[k + 1]; dl = ds[k]
            for _ in range(100):
                mid = (l + h) / 2; dm = f(a, mid) - f(b, mid)
                if dm == 0: l = h = mid; break
                if (dm > 0) == (dl > 0): l = mid
                else: h = mid
            roots.append((l + h) / 2)
    if ds[-1] == 0 and (not roots or roots[-1] != xs[-1]): roots.append(xs[-1])
    return roots

def _winner(a, b, r, f=_npv):
    d = f(a["cashflows"], r) - f(b["cashflows"], r); return None if abs(d) <= TIE else (a["id"] if d > 0 else b["id"])

def _ranking(alts, r, f=_npv):
    vals = sorted(((f(a["cashflows"], r), a["id"]) for a in alts), key=lambda x: (-x[0], x[1])); groups = []
    for v, i in vals:
        if groups and abs(groups[-1][0] - v) <= TIE: groups[-1][1].append(i)
        else: groups.append([v, [i]])
    return [g[1] for g in groups]

def build(inp):
    n, errs = normalize(inp)
    if errs: raise DataError("; ".join(errs))
    alts, lo, hi, rate = n["alts"], n["lo"], n["hi"], n["rate"]; f = lambda cf, r: _npv(cf, r)
    npv = {a["id"]: _npv(a["cashflows"], rate) for a in alts}; ranking = _ranking(alts, rate); cross = []
    delta = (hi - lo) / D(10 ** 6)
    for i in range(len(alts)):
        for j in range(i + 1, len(alts)):
            A, B = alts[i], alts[j]
            for r in _roots(A["cashflows"], B["cashflows"], lo, hi, f, GRID):
                cross.append({"pair": [A["id"], B["id"]], "rate": str(r), "below": _winner(A, B, max(lo, r - delta)), "above": _winner(A, B, min(hi, r + delta))})
    top = {t for k in range(201) for t in _ranking(alts, lo + (hi - lo) * k / 200)[0]}
    rec = None
    if n["rule"]:
        rec = {"rule": n["rule"], "preferred_at_base": ranking[0], "tied": len(ranking[0]) > 1, "top_over_range": sorted(top), "stable_across_range": top == set(ranking[0])}
    audit = {"assumed_cashflows": [a["id"] for a in alts if a["provenance"] == "assumption"], "synthetic_items": [a["id"] for a in alts if a["provenance"] == "synthetic"] + [x["id"] for x in n["facts"] if x["provenance"] == "synthetic"],
             "unsupported_facts": [x["id"] for x in n["facts"] if x["provenance"] == "assumption"], "negative_npv_at_base": [i for i, v in npv.items() if v < 0],
             "low_end_top": _ranking(alts, lo)[0], "high_end_top": _ranking(alts, hi)[0], "rate_assumed": n["rate_provenance"] == "assumption"}
    cur = n["currency"]
    arts = [{"id": "rate", "metric": "rate", "value": str(rate), "unit": "rate", "precision": 2}, {"id": "rate_low", "metric": "rate_low", "value": str(lo), "unit": "rate", "precision": 2},
            {"id": "rate_high", "metric": "rate_high", "value": str(hi), "unit": "rate", "precision": 2}]
    arts += [{"id": f"npv_{i}", "metric": "npv", "value": str(v), "unit": "currency", "currency": cur, "precision": 2} for i, v in npv.items()]
    arts += [{"id": f"cross_{k + 1}", "metric": "crossover_rate", "value": c["rate"], "unit": "rate", "precision": 2} for k, c in enumerate(cross)]
    counts = {"n_facts": len(n["facts"]), "n_alternatives": len(alts), "n_crossovers": len(cross), "n_assumed": len(audit["assumed_cashflows"]), "n_negative": len(audit["negative_npv_at_base"])}
    arts += [{"id": k, "metric": k, "value": str(v), "unit": "count", "precision": 0} for k, v in counts.items()]
    return {"kind": "case_decision", "registry_ids": ["QNT-FIN-01"], "facts": n["facts"], "alternatives": [{**{k: v for k, v in a.items() if k != "cashflows"}, "cashflows": [str(x) for x in a["cashflows"]]} for a in alts],
            "rate": str(rate), "rate_range": [str(lo), str(hi)], "currency": cur, "npv_at_base": {i: str(v) for i, v in npv.items()}, "ranking_at_base": ranking, "crossovers": cross,
            "recommendation": rec, "audit": audit, "counts": counts, "artifacts": arts, "text_refs": {a["id"]: a["name"] for a in alts}}

def _t(i): return "{{txt:%s}}" % i

def render(a):
    P = PERIOD; tok = lambda i, m: "{{ref:%s:%s:%s}}" % (i, m, P); c = a["counts"]; au = a["audit"]; ids = [x["id"] for x in a["alternatives"]]; join = lambda L: ", ".join(_t(i) for i in L)
    t = (f"This case comparison covers {tok('n_alternatives', 'n_alternatives')} alternatives you supplied, each citing the case facts it follows from ({tok('n_facts', 'n_facts')} facts in total). "
         f"Net present value is computed for each alternative from the cash flows you supplied, at a discount rate you set of {tok('rate', 'rate')} and across a range you set from {tok('rate_low', 'rate_low')} to {tok('rate_high', 'rate_high')}. ")
    for i in ids: t += f"{_t(i)} has a net present value of {tok('npv_' + i, 'npv')} at the base rate. "
    t += "By net present value at the base rate the order is " + ", then ".join(("tied: " + join(g)) if len(g) > 1 else _t(g[0]) for g in a["ranking_at_base"]) + ". "
    if not a["crossovers"]: t += "Within your range the order by net present value does not change. "
    for k, x in enumerate(a["crossovers"], 1):
        who = lambda w: _t(w) if w else "neither alternative"
        t += (f"The order of {_t(x['pair'][0])} and {_t(x['pair'][1])} changes at a discount rate of {tok('cross_' + str(k), 'crossover_rate')}: {who(x['below'])} has the higher net present value below that rate and {who(x['above'])} above it. ")
    t += f"At the low end of your range the highest net present value belongs to {join(au['low_end_top'])}, and at the high end to {join(au['high_end_top'])}. "
    r = a["recommendation"]
    if r is None: t += "You supplied no decision rule, so no alternative is recommended. "
    else:
        t += f"Under your stated decision rule (highest net present value) and the inputs you supplied, {join(r['preferred_at_base'])} ranks first at the base rate"
        t += (" and keeps first place across your whole range. " if r["stable_across_range"] else f", but the alternative in first place changes within your range ({join(r['top_over_range'])} each lead somewhere), so the choice depends on the discount rate. ")
    if c["n_assumed"]: t += f"{tok('n_assumed', 'n_assumed')} alternatives rest on assumed cash flows rather than user-supplied or sourced figures. "
    if au["rate_assumed"]: t += "The discount rate itself is an assumption. "
    if c["n_negative"]: t += f"{tok('n_negative', 'n_negative')} alternatives have a negative net present value at the base rate. "
    if au["synthetic_items"]: t += "Some inputs are synthetic and illustrative only; they are not observations. "
    t += ("Net present value treats the cash flows as certain and ignores factors that you did not quantify. The facts, alternatives, cash flows, decision rule and rates are all yours; "
          "the system adds none of them and ranks only by the rule you gave.")
    lab = lambda p, s=None: {"user": "user-supplied", "sourced": f"sourced: {s}", "assumption": "assumption (unsupported)", "synthetic": "synthetic (illustrative only)"}[p]
    lines = ["Case facts (yours)"] + [f"  [{x['id']}] {x['text']} — {lab(x['provenance'], x['source'])}" for x in a["facts"]]
    lines.append("Alternatives (yours)")
    for x in a["alternatives"]:
        lines.append(f"  [{x['id']}] {x['name']}" + (f" — {x['description']}" if x["description"] else "") + f" — follows from {', '.join(x['supports'])}; cash flows: {', '.join(x['cashflows'])} ({lab(x['provenance'], x['source'])})")
    return t, "\n".join(lines)

# ---------- verification: recomputed from the raw input by different routes ----------
def tests(inp, a, narrative, listing):
    n, _ = normalize(inp); alts = n["alts"]; lo, hi, rate = n["lo"], n["hi"], n["rate"]; ids = [x["id"] for x in alts]; byid = {x["id"]: x for x in alts}; res = []
    std = all(all(ok for _, ok in M.npv_tests({"rate": rate, "cashflows": [str(c) for c in x["cashflows"]]}, M.npv)) for x in alts)
    res.append(("alternatives_pass_standard_npv_checks", std))
    base_ok = all(abs(D(a["npv_at_base"][i]) - _ref(byid[i]["cashflows"], rate)) <= TIE * max(D(1), abs(_ref(byid[i]["cashflows"], rate))) for i in ids)
    res.append(("base_values_agree_with_independent_recomputation", base_ok and set(a["npv_at_base"]) == set(ids)))
    root_ok = flip_ok = True
    for x in a["crossovers"]:
        A, B = byid[x["pair"][0]], byid[x["pair"][1]]; r = D(x["rate"]); d = _ref(A["cashflows"], r) - _ref(B["cashflows"], r)
        root_ok &= abs(d) <= D("1e-9") * max(D(1), abs(_ref(A["cashflows"], r)), abs(_ref(B["cashflows"], r))) and lo <= r <= hi
        e = (hi - lo) / D(10 ** 6); wl = _winner(A, B, max(lo, r - e), _ref); wa = _winner(A, B, min(hi, r + e), _ref)
        flip_ok &= (wl, wa) == (x["below"], x["above"]) and (wl != wa)
    res += [("crossover_rates_are_roots_of_the_npv_difference", root_ok), ("ranking_changes_at_each_crossover", flip_ok)]
    dense = sum(len(_roots(alts[i]["cashflows"], alts[j]["cashflows"], lo, hi, _ref, DENSE)) for i in range(len(alts)) for j in range(i + 1, len(alts)))
    res.append(("no_crossover_missed_on_a_different_grid", dense == len(a["crossovers"])))
    res.append(("ranking_matches_recomputed_order", a["ranking_at_base"] == _ranking(alts, rate, _ref)))
    # reordering the alternatives must not change any result once ids are mapped back to names (default ids are positional)
    rev = build({**inp, "alternatives": list(reversed(inp["alternatives"]))}); nm = lambda z: {x["id"]: x["name"] for x in z["alternatives"]}
    view = lambda z: ({nm(z)[i]: v for i, v in z["npv_at_base"].items()}, [sorted(nm(z)[i] for i in g) for g in z["ranking_at_base"]],
                      sorted((tuple(sorted(nm(z)[p] for p in c["pair"])), c["rate"][:20]) for c in z["crossovers"]))
    res.append(("order_of_alternatives_does_not_change_results", view(rev) == view(a)))
    texts = {f["text"] for f in n["facts"]} | {x["name"] for x in alts} | {x["description"] for x in alts if x["description"]}
    out_texts = {f["text"] for f in a["facts"]} | {x["name"] for x in a["alternatives"]} | {x["description"] for x in a["alternatives"] if x["description"]}
    res.append(("analysis_contains_only_supplied_text", out_texts == texts and set(a["text_refs"]) == set(ids)))
    res.append(("listing_reproduces_every_input_text_verbatim", all(f"[{f['id']}] {f['text']} — " in listing for f in n["facts"]) and all(f"[{x['id']}] {x['name']}" in listing for x in alts)))
    res.append(("alternatives_cite_existing_facts", all(s in {f["id"] for f in n["facts"]} for x in alts for s in x["supports"]) and all(x["supports"] for x in a["alternatives"])))
    res.append(("cashflows_reproduced_exactly", [[str(c) for c in x["cashflows"]] for x in alts] == [x["cashflows"] for x in a["alternatives"]]))
    top = {t for k in range(201) for t in _ranking(alts, lo + (hi - lo) * k / 200, _ref)[0]}; rk = _ranking(alts, rate, _ref)
    res.append(("recommendation_matches_recomputation", a["recommendation"] is None or (a["recommendation"]["preferred_at_base"] == rk[0] and a["recommendation"]["stable_across_range"] == (top == set(rk[0])) and sorted(top) == a["recommendation"]["top_over_range"])))
    res.append(("no_recommendation_without_your_decision_rule", (a["recommendation"] is None) == (n["rule"] is None)))
    res.append(("assumption_and_synthetic_flags_are_correct", set(a["audit"]["assumed_cashflows"]) == {x["id"] for x in alts if x["provenance"] == "assumption"}
                and set(a["audit"]["synthetic_items"]) == {x["id"] for x in alts if x["provenance"] == "synthetic"} | {f["id"] for f in n["facts"] if f["provenance"] == "synthetic"}))
    res.append(("rendering_is_deterministic", render(a) == (narrative, listing)))
    return res

NAMES = ("alternatives_pass_standard_npv_checks", "base_values_agree_with_independent_recomputation", "crossover_rates_are_roots_of_the_npv_difference", "ranking_changes_at_each_crossover",
         "no_crossover_missed_on_a_different_grid", "ranking_matches_recomputed_order", "order_of_alternatives_does_not_change_results", "analysis_contains_only_supplied_text",
         "listing_reproduces_every_input_text_verbatim", "alternatives_cite_existing_facts", "cashflows_reproduced_exactly", "recommendation_matches_recomputation", "no_recommendation_without_your_decision_rule", "assumption_and_synthetic_flags_are_correct", "rendering_is_deterministic")

TEMPLATES["case_decision"] = {"id": "case_decision", "version": "0.1.0", "tier": "T2", "name": "Business case: alternatives compared by net present value", "registry_ids": ["QNT-FIN-01"], "build": build, "render": render, "tests": tests,
    "test_names": NAMES, "validate": validate, "sensitivity": True,
    "intended_use": "Compare two to five alternatives you define, each grounded in case facts you supply, by net present value at your discount rate, and see where the ranking changes across your rate range. A preference is stated only under a decision rule you set.",
    "unsupported_use": "Choosing alternatives, facts, cash flows, rates or weights for you; qualitative or multi-criteria judgments; risk or probability weighting; unequal-length or mutually exclusive project adjustments beyond what NPV captures.",
    "input_help": {"facts": "list of {text, provenance user|sourced|assumption|synthetic, source (if sourced), id (optional)}", "alternatives": "2-5 of {name, description (optional), supports: [fact ids], cashflows: [numbers, first at t=0], cashflow_provenance, source (if sourced), id (optional)}",
                   "rate / rate_range": "your base discount rate and [low, high] range for the sensitivity analysis (rate must lie inside the range)", "decision_rule": "null (no recommendation) or \"highest_npv\"", "currency": "optional three-letter code"},
    "defaults": ({"question": "Decision rule", "default_chosen": "None. A preference is stated only if you set decision_rule; otherwise the comparison is shown without a recommendation.", "impact": "The rule encodes your values; the system will not choose one."},
                 {"question": "Cash-flow timing and rate", "default_chosen": "Cash flows occur at period end, the first at t=0 undiscounted; the discount rate is the one you set.", "impact": "NPV and crossover rates move if timing or the rate differ."},
                 {"question": "Ties and crossovers", "default_chosen": "NPVs within 1e-9 are tied. Crossovers are searched on a 400-point grid across your range and refined by bisection; a second, different grid cross-checks that none was missed.", "impact": "Two crossovers closer than the grid spacing could be missed; the cross-check would then block."}),
    "limitations": ("NPV treats cash flows as certain and ignores unquantified factors.", "Alternatives, facts and cash flows are yours; the system checks structure and arithmetic, not whether they are realistic.", "Custom analysis (T2): built on the vetted NPV method, expert review pending."),
    "example": None}

EXAMPLES["case_decision"] = {"objective": "Which option should the bakery pursue? Compare the alternatives by net present value.", "method": "case_decision", "inputs": {
    "currency": "USD",
    "facts": [{"text": "A supermarket chain opened a bakery counter nearby", "provenance": "synthetic"}, {"text": "An office park opens next year", "provenance": "synthetic"}],
    "alternatives": [{"name": "Expand the shop", "description": "Add seating and extend hours", "supports": ["F1"], "cashflows": ["-12000", "3000", "4000", "5000", "6000"], "cashflow_provenance": "synthetic"},
                     {"name": "Office catering", "description": "Deliver lunches to the office park", "supports": ["F2"], "cashflows": ["-4000", "1500", "1800", "2000", "2200"], "cashflow_provenance": "assumption"}],
    "rate": "0.08", "rate_provenance": "assumption", "rate_range": ["0.02", "0.25"], "decision_rule": "highest_npv"}}
