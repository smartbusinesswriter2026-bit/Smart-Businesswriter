"""Held-out evaluation scaffold for model proposals (charter 8.3, decision B-039). PROVISIONAL; not wired into the pipeline.

Model quality is unmeasured: this scores proposals against human-labelled gold data. Fact extraction is scored automatically
(precision/recall/F1 on exact quotes, which the code already forces); alternatives use a coarse containment proxy and critique
uses category+target coverage. Those two remain human-judged, so their scores are indicators, not verdicts. Driving the harness
with MockProvider keeps it deterministic in CI; a real run needs the owner's provider key and real held-out cases. No real case
data or keys are committed here."""
import json, re
from . import assist
from .llm import ProviderError, BudgetExceeded, ConsentRequired

def _norm(s): return re.sub(r"\s+", " ", s or "").strip()

def score_facts(proposed, gold):
    """proposed: proposal dicts with 'text'; gold: exact quote strings. Exact-normalised match (the rule the code enforces)."""
    P = {_norm(p.get("text")) for p in proposed if isinstance(p, dict) and p.get("text")}
    G = {_norm(g) for g in (gold or []) if g}
    matched = len(P & G)
    precision = matched / len(P) if P else 0.0
    recall = matched / len(G) if G else 1.0
    f1 = 0.0 if not (precision or recall) else 2 * precision * recall / (precision + recall)
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "matched": matched, "proposed": len(P), "gold": len(G)}

def score_alternatives(proposed, gold):
    """Coarse containment proxy: a gold theme label counts as covered if its normalised, lowercased text appears in a proposed
    name+description. This is a screen for human review, not a measure of quality."""
    blob = " ".join(_norm(f"{p.get('name', '')} {p.get('description', '')}").lower() for p in (proposed or []) if isinstance(p, dict))
    gold = [g for g in (gold or []) if _norm(g)]
    covered = sum(1 for g in gold if _norm(g).lower() in blob)
    return {"proposed": len(proposed or []), "gold": len(gold), "covered": covered, "coverage": round(covered / len(gold), 4) if gold else 1.0,
            "note": "coarse containment proxy only; human review required"}

def score_critique(items, gold):
    """Coverage of gold (category, target) pairs. Relevance of the text remains human-judged."""
    got = {(i.get("category"), i.get("target")) for i in (items or []) if isinstance(i, dict)}
    want = {(g.get("category"), g.get("target")) for g in (gold or []) if isinstance(g, dict)}
    matched = len(got & want)
    return {"proposed": len(got), "gold": len(want), "covered": matched, "coverage": round(matched / len(want), 4) if want else 1.0}

def load_cases(path):
    with open(path, encoding="utf-8") as f: cases = json.load(f)
    if not isinstance(cases, list) or not cases: raise ValueError("eval cases must be a non-empty JSON list")
    for c in cases:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or not isinstance(c.get("case_text"), str) or not isinstance(c.get("objective"), str):
            raise ValueError("each eval case needs id, case_text and objective")
    return cases

def run_case(models, case, consent=True):
    row = {"case": case.get("id")}
    try:
        facts = assist.extract_facts(models, case["case_text"], consent)["proposals"]; row["facts"] = score_facts(facts, case.get("gold_facts"))
    except (assist.AssistError, ProviderError, BudgetExceeded, ConsentRequired) as e:
        facts = []; row["facts"] = {"error": f"{type(e).__name__}: {e}"}
    fids = [{"id": f"F{i + 1}", "text": f["text"]} for i, f in enumerate(facts)]
    try:
        alts = assist.propose_alternatives(models, fids, case["objective"], consent)["proposals"] if fids else []
        row["alternatives"] = score_alternatives(alts, case.get("gold_alternatives")) if fids else {"skipped": "no valid facts"}
    except (assist.AssistError, ProviderError, BudgetExceeded, ConsentRequired) as e:
        alts = []; row["alternatives"] = {"error": f"{type(e).__name__}: {e}"}
    try:
        items = assist.critique(models, facts, alts, consent)["items"] if fids and alts else []
        row["critique"] = score_critique(items, case.get("gold_critique")) if fids and alts else {"skipped": "no valid facts and alternatives"}
    except (assist.AssistError, ProviderError, BudgetExceeded, ConsentRequired) as e:
        row["critique"] = {"error": f"{type(e).__name__}: {e}"}
    return row

def evaluate(models, cases, consent=True):
    """Run every held-out case and return per-row scores plus a mean-facts summary."""
    rows = [run_case(models, c, consent) for c in cases]
    ok = [r["facts"] for r in rows if isinstance(r.get("facts"), dict) and "f1" in r["facts"]]
    mean = lambda k: round(sum(r[k] for r in ok) / len(ok), 4) if ok else None
    summary = {"cases": len(rows), "cases_with_valid_facts": len(ok), "facts_mean_precision": mean("precision"), "facts_mean_recall": mean("recall"), "facts_mean_f1": mean("f1")}
    return {"summary": summary, "rows": rows,
            "note": "PROVISIONAL scaffold: scores are indicators, not a verdict. Run against real held-out cases with your own key before trusting a prompt; alternatives and critique need human review."}

def main(argv=None):
    import os, sys
    argv = argv if argv is not None else sys.argv[1:]
    path = argv[0] if argv else os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures", "eval_cases.json")
    from .llm import from_env
    models = from_env()
    if not models: print("model assistance is not configured; set BP_LLM_PROVIDER/BP_LLM_MODEL and the provider's API key"); return 2
    print(json.dumps(evaluate(models, load_cases(path)), indent=2)); return 0

if __name__ == "__main__": raise SystemExit(main())
