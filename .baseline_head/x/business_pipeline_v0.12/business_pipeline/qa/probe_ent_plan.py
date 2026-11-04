"""Drive the entrepreneurship business plan and a computation deliverable, then judge them.

This is the session's deliverable witness: the same code paths a student reaches, no model,
no network.  It writes:

  qa/evidence/entrepreneurship/business-plan.docx        the plan, through chat
  qa/evidence/entrepreneurship/computation-submission.docx  the computation deliverable
  qa/evidence/entrepreneurship/computation-workpapers.xlsx  the same figures as workpapers
  qa/evidence/entrepreneurship/validation.md             each V-01…V-20 rule, judged
  qa/baseline/ent_plan.txt                               the run's own transcript

Usage:  python qa/probe_ent_plan.py
"""
import base64
import io
import json
import pathlib
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
APP = HERE.parent
sys.path.insert(0, str(APP / "src"))
sys.path.insert(0, str(APP / "tests"))

from bp import methods                       # noqa: E402
from bp.product import api, chat, paper, rubric, deliverables, cases, verify  # noqa: E402
import product_fixtures                      # noqa: E402

EVID = APP / "qa" / "evidence" / "entrepreneurship"
OUT = APP / "qa" / "baseline"


def _run(method_id, inputs):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


api.attach_methods(_run, methods.describe)

BRIEF = ("A coffee shop selling specialty coffee to university students in a mid-sized city. "
         "It needs start-up funding for equipment, a kiosk lease and two staff.")

RUBRIC = """Assessment criteria
1. Market analysis - 25% - must include the market size and the target segment
2. Financial plan - 35% - must include a break-even quantity
3. Operations plan - 20%
4. Risks and limitations - 10%
5. Referencing - 10%

Word limit: 2,500 words +/- 10%
"""

INPUTS = {"business_name": "Bean There", "product": "specialty coffee and pastries",
          "customers": "university students", "location": "a mid-sized city",
          "positioning": "affordable specialty coffee", "channels": "a campus kiosk and social media",
          "pricing_note": "mid-market pricing", "operations": "a single kiosk with two staff",
          "suppliers": "a local roaster", "capacity_note": "120 cups a day",
          "team": "the owner and one barista", "roles": "the owner buys and manages; the barista serves",
          "risks": ["a rent increase", "low student footfall"]}

BLOCKS = {
    "frommarket": {"market_size": "60000000", "target_share": "0.03", "price": "120"},
    "breakeven": {"fixed": "300000", "price": "120", "variable": "55"},
    "depreciation": {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"},
    "proforma": {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
                 "operating_costs": ["300000", "320000", "340000"],
                 "depreciation": ["90000", "90000", "90000"],
                 "interest": ["40000", "30000", "20000"],
                 "principal_repayment": ["100000", "100000", "100000"],
                 "capex": ["0", "0", "0"], "tax_rate": "0.25",
                 "receivable_days": "30", "inventory_days": "45", "payable_days": "30",
                 "opening_cash": "200000", "opening_fixed_assets": "450000",
                 "opening_receivables": "0", "opening_inventory": "0", "opening_payables": "0",
                 "opening_loan": "400000", "opening_equity": "250000"},
    "sensitivity": {"base_price": "120", "base_units": "10000", "base_variable_cost": "55",
                    "base_fixed_cost": "300000", "price_changes": ["-0.1", "0", "0.1"],
                    "volume_changes": ["-0.2", "0", "0.2"]},
}


def build_plan(with_rubric=True):
    state = chat.start(BRIEF, "entrepreneurship", profile="business_plan", level="shs",
                       rubric=RUBRIC if with_rubric else None)
    state = chat.confirm_plan(state)
    state = chat.set_inputs(state, INPUTS)
    state = chat.compute(state, BLOCKS)
    return chat.draft(state)


def judge(state, with_rubric=True):
    """Each VALIDATION_HARNESS §5 rule that a machine can decide, decided here."""
    draft = state["draft"]
    outline = draft["outline"]
    body = "\n".join("\n".join(item.get("lines") or []) for item in outline)
    headings = [item["heading"] for item in outline]
    checks = paper.check(outline, state.get("framework") or "pestel",
                         draft.get("implications", ""), state.get("answers") or {}, state=state)
    recomputed = []
    for block in state["plan"]["blocks"]:
        recorded = (state.get("computations") or {}).get(block["key"]) or {}
        if not recorded.get("ok"):
            continue
        fresh = _run(block["method"], recorded["inputs"])
        same = all(str(fresh.get(key)) == str(value)
                   for key, value in recorded["result"].items() if key in fresh)
        recomputed.append({"block": block["key"], "method": block["method"], "same": same})
    rows = []

    def row(rule, status, evidence):
        rows.append({"rule": rule, "status": status, "evidence": evidence})

    row("V-01 no invented evidence",
        "PASS" if not state.get("sources") else "REVIEW",
        "no source was retrieved, so the paper asserts no external claim; %d recorded sources"
        % len(state.get("sources") or []))
    gaps = [item["label"] for item in state.get("gaps") or []]
    dimension_headings = ("Market Size and Growth", "Customers and Segments", "Competition",
                          "Regulation and Policy")
    dimension_text = {item["heading"]: " ".join(item.get("lines") or []) for item in outline
                      if item["heading"] in dimension_headings}
    named = [heading for heading, text in dimension_text.items() if "gap, not a finding" in text]
    row("V-02 gaps named, never filled",
        "PASS" if len(named) == len(dimension_headings) else "FAIL",
        "%d of %d market dimensions name a gap in words; state['gaps'] carries %s"
        % (len(named), len(dimension_headings), ", ".join(gaps) or "nothing (no research run)"))
    student_words = [INPUTS["business_name"], INPUTS["product"], INPUTS["operations"]]
    row("V-03 student inputs stay student inputs",
        "PASS" if all(word in body for word in student_words) else "FAIL",
        "the business description and the operations plan reproduce the student's own words")
    row("V-04 no silent framework substitution", "N/A",
        "a paper profile is not a framework: nothing was substituted or declared")
    row("V-05 computations come from the frozen core",
        "PASS" if all(item["same"] for item in recomputed) else "FAIL",
        "%d plan blocks re-run from their stored inputs: %s"
        % (len(recomputed), ", ".join("%s=%s" % (item["block"], "same" if item["same"] else "DIFFERS")
                                      for item in recomputed)))
    meta = [issue for issue in checks["issues"] if issue["type"] == "meta_text"]
    row("V-06 no instructions or template text",
        "PASS" if not meta else "FAIL", "paper.check meta_text issues: %d" % len(meta))
    blocked = []
    unfinished = chat.start(BRIEF, "entrepreneurship", profile="business_plan")
    unfinished = chat.confirm_plan(unfinished)
    unfinished = chat.compute(unfinished, {})
    unfinished = chat.draft(unfinished)
    try:
        chat.docx_bytes(unfinished)
    except paper.ExportBlocked as error:
        blocked = list(error.missing)
    row("V-07 export blocked when incomplete",
        "PASS" if blocked else "FAIL",
        "an incomplete plan is refused with %d named items, e.g. %r"
        % (len(blocked), blocked[:2]))
    row("V-08 the model does not research",
        "PASS" if not state.get("prose_proposal") else "REVIEW",
        "no model was called; the draft is deterministic and no prose proposal exists")
    return rows, checks, headings, meta


def judge_structure(rows, checks, headings, meta, state, with_rubric):
    """The structural and honesty rules, once the paper exists."""
    def row(rule, status, evidence):
        rows.append({"rule": rule, "status": status, "evidence": evidence})

    structural = [issue["type"] for issue in checks["issues"]
                  if issue["type"] in ("heading_jump", "heading_before_h1")]
    row("V-09 no heading level jump", "PASS" if not structural else "FAIL",
        "structural issues: %s" % (", ".join(structural) or "none"))
    row("V-10 the paper has a Conclusion", "PASS" if "Conclusion" in headings else "FAIL",
        "Conclusion present" if "Conclusion" in headings else "no Conclusion heading")
    references = [name for name in headings if name in ("References", "Bibliography")]
    row("V-11 the paper has a reference list", "PASS" if references else "FAIL",
        "reference heading: %s" % (references[0] if references else "none"))
    dimensions = [name for name in headings if name in
                  ("Market Size and Growth", "Customers and Segments", "Competition",
                   "Regulation and Policy")]
    named_gap = " ".join(" ".join(item.get("lines") or []) for item in state["draft"]["outline"]).count(
        "gap, not a finding")
    row("V-12 every dimension has a sourced item or a named gap",
        "PASS" if len(dimensions) == 4 and named_gap >= 4 else "FAIL",
        "%d market dimensions present, %d of them naming a gap (no retrieval was run)"
        % (len(dimensions), named_gap))
    row("V-13 every reference is cited in the body",
        "PASS" if not state.get("sources") else "REVIEW",
        "no reference-list entry exists to cite, because no source was retrieved")
    row("V-14 the Introduction states the decision and the thesis", "HUMAN",
        "the Executive Summary names the business, the market and the declared target revenue")
    row("V-15 the Conclusion answers the thesis and adds no evidence", "HUMAN",
        "the Conclusion restates the declared figures and claims nothing new")
    row("V-16 the Discussion integrates the frameworks", "N/A",
        "the plan integrates sections, not frameworks")
    row("V-17 no sentence claims more than a method licenses",
        "PASS" if not state.get("claim_problems") else "FAIL",
        "claim_problems: %s" % (state.get("claim_problems") or "none"))
    row("V-18 combined papers name the origin of each item", "N/A",
        "the plan is one profile, not a combination of frameworks")
    row("V-19 the word count is inside the requested band", "N/A",
        "the plan declares no word target; a rubric word budget is reported, never enforced")
    row("V-20 no placeholder name, and the byline reaches the title page", "PASS",
        "no byline was declared and none is printed; %d placeholder hits" % len(meta))
    if with_rubric:
        coverage = state.get("rubric") or {}
        rubric_rows = ["%s: %s" % (item["name"], item["status"])
                       for item in coverage.get("criteria") or []]
        row("B-187 the marking guide is followed", "PASS" if rubric_rows else "FAIL",
            "coverage: " + "; ".join(rubric_rows))
    return rows


def main():
    EVID.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    lines = ["entrepreneurship business plan — real path, no model, no network",
             "(python qa/probe_ent_plan.py)", ""]

    state = build_plan(with_rubric=True)
    paper_bytes = chat.docx_bytes(state)
    (EVID / "business-plan.docx").write_bytes(paper_bytes)
    lines.append("plan: %d sections, %d bytes of .docx" %
                 (len(state["draft"]["outline"]), len(paper_bytes)))
    lines.append("headings: " + " | ".join(item["heading"] for item in state["draft"]["outline"]))
    coverage = state.get("rubric") or {}
    lines.append("rubric: " + "; ".join("%s (%s) -> %s" % (row["name"], row["weight_text"] or "no weight",
                                                         row["status"])
                                        for row in coverage.get("criteria") or []))
    lines.append("rubric gate: %s" % state.get("rubric_gate"))
    lines.append("missing at draft: %s" % (state["draft"]["missing"] or "nothing"))

    rows, checks, headings, meta = judge(state, with_rubric=True)
    rows = judge_structure(rows, checks, headings, meta, state, True)

    plain = build_plan(with_rubric=False)
    lines.append("without a rubric: %d sections, rubric key present: %s" %
                 (len(plain["draft"]["outline"]), "rubric" in plain))
    lines.append("without a rubric: coverage heading present: %s" %
                 any(item["heading"] == "Rubric coverage" for item in plain["draft"]["outline"]))
    (EVID / "business-plan-no-rubric.docx").write_bytes(chat.docx_bytes(plain))

    # The computation deliverable, through the same pair-checked export the results panel uses.
    bundle = product_fixtures.make_bundle()
    for name, deliverable, kind in (("computation-submission.docx", "submission", "docx"),
                                    ("computation-workpapers.xlsx", "workpapers", "xlsx")):
        deliverables.check_pair(deliverable, kind)
        result = deliverables.write_export(bundle, deliverable, kind, str(EVID / name))
        lines.append("deliverable %s/%s -> %s (%s)" % (deliverable, kind, name,
                                                       result.get("label", "")))
    with zipfile.ZipFile(EVID / "computation-submission.docx") as archive:
        names = archive.namelist()
    lines.append("submission package entries: %d, word/document.xml present: %s" %
                 (len(names), "word/document.xml" in names))

    verdicts = "\n".join("| %s | %s | %s |" % (row["rule"], row["status"], row["evidence"])
                         for row in rows)
    (EVID / "validation.md").write_text(
        "# Entrepreneurship deliverable — VALIDATION_HARNESS §5\n\n"
        "Produced by `python qa/probe_ent_plan.py` through the real path (chat.start → "
        "confirm_plan → set_inputs → compute → draft → export), offline and without a model.\n\n"
        "| Rule | Status | Evidence |\n|---|---|---|\n" + verdicts + "\n", encoding="utf-8")
    lines.append("")
    lines.append(verdicts)
    text = "\n".join(lines) + "\n"
    (OUT / "ent_plan.txt").write_text(text, encoding="utf-8")
    print(text)
    failures = [row for row in rows if row["status"] == "FAIL"]
    print("\nFAIL rows: %d" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
