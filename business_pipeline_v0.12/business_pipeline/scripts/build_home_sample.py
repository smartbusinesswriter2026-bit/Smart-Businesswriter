"""Build the one Home-page worked example: one framework plus one computation.

The sample is produced by the product's own code path - start, answer, confirm,
compute, draft - and exported exactly as a student's export is: a ZIP holding the
paper and its computation explainer.  Nothing is hand-formatted here and nothing
is computed outside the frozen core, so the sample cannot drift from the product.

Evidence comes from `scripts/sample_evidence.py`, the frozen sources already cited
in this repository; the placement below is the same judgement a student makes when
they file a source under a PESTEL dimension.  Dimensions with no matching source
are recorded as gaps, never filled.

Run:  python scripts/build_home_sample.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from bp import methods  # noqa: E402
from bp.methods import LIBRARY  # noqa: E402
from bp.product import chat, explain  # noqa: E402

import sample_evidence  # noqa: E402


def _run(method_id, inputs):
    """The same validated call `bp.server` attaches: the core decides, not the product."""
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


chat.set_compute(LIBRARY["breakeven"].impl)
chat.set_method_compute(_run, methods.describe)

#: The folder the Home page lists as the shipped samples.
OUT_DIR = ROOT / "samples"

#: One framework (PESTEL) and one computation (break-even), in two versions.
#: The length is asked for in the brief, the way a student asks for it.
SHORT = {"stem": "pestel-and-break-even-tehran-device-store", "brief_extra": ""}
FULL = {"stem": "pestel-and-break-even-tehran-device-store-full",
        "brief_extra": " Write about 2500 words."}

SAMPLE = {
    "title": "PESTEL and Break-even: A Tehran Device Store",
    "framework": "pestel",
    "label": "PESTEL + break-even",
    "brief": ("A retailer is considering opening a device store in Tehran. Analyse the Iranian market "
              "environment with PESTEL, and test whether the store pays for itself at the declared fixed "
              "cost of 2000000, price of 40000 and variable cost of 28000."),
    "answers": {
        "decision": "Should the retailer open a device store in Tehran?",
        "geography": "Middle East",
        "period": "5",
        "style": "apa",
        "firm": "A Tehran device store",
    },
    "inputs": {"fixed": "2000000", "price": "40000", "variable": "28000", "expected": "120"},
    "implications": ("Sanctions, water and energy shortages and a controlled digital environment raise "
                     "the cost and the risk of trading in Tehran. At the declared price and cost the store "
                     "must sell more units than the declared expected volume before it covers its fixed "
                     "cost, so the price or the variable cost has to change before entry is viable."),
    #: PESTEL dimension -> frozen source keys, chosen for what each source is about.
    "placement": {
        "political": ["koruzhde", "pesaran"],
        "economic": ["worldbank_overview", "worldbank_data"],
        "social": ["worldbank_data"],
        "technological": ["conduit", "bashirov"],
        "environmental": ["ahmadi", "haji"],
        "legal": ["thomas"],
    },
}


def seed_evidence(state, placement):
    """Place the frozen sources on the plan's dimensions; an unplaced one stays a gap."""
    sources, evidence, gaps, by_key = [], [], [], {}
    for dimension in state["plan"]["dimensions"]:
        keys = placement.get(dimension["key"]) or []
        if not keys:
            gaps.append({"dimension": dimension["key"], "label": dimension["label"],
                         "reason": "no frozen source supports this dimension for the worked example"})
            continue
        for key in keys:
            record = sample_evidence.SOURCE_BY_KEY[key]
            if key not in by_key:
                source = dict(record)
                source.pop("key", None)
                source["id"] = "S%d" % (len(sources) + 1)
                sources.append(source)
                by_key[key] = source["id"]
            evidence.append({"id": "E%d" % (len(evidence) + 1), "dimension": dimension["key"],
                             "claim": record["abstract"], "quote": record["abstract"],
                             "source_id": by_key[key], "status": "accepted"})
    state.update({"sources": sources, "evidence": evidence, "gaps": gaps, "notes": [],
                  "stage": "evidence"})
    return state


def build(sample=SAMPLE):
    """Run the conductor once and return (state, paper bytes, explainer bytes)."""
    state = chat.start(sample["brief"], subject="management", framework=sample["framework"])
    if state["stage"] == "not_supported":
        raise chat.ChatError("The sample brief was refused: " + str(state.get("message")))
    while chat.current_question(state):
        question = chat.current_question(state)
        value = sample["answers"].get(question["id"], question.get("default") or "")
        state = chat.answer(state, question["id"], value)
    state = chat.confirm_plan(state)
    state = chat.run_capability(state, "breakeven", sample["inputs"])
    state = seed_evidence(state, sample["placement"])
    state = chat.draft(state, implications=sample["implications"], style=sample["answers"]["style"])
    paper = chat.docx_bytes(state, byline=["Smart Business Writer",
                                           "Worked example: one framework and one computation"])
    document = explain.paper_document(state)
    explainer = explain.docx_bytes(document)
    return state, paper, explainer


def main():
    """Write the short paper and the full report, each with its explainer.

    Two Word files per version rather than a ZIP: a student double-clicks the
    sample and Word opens it. The export route still ships the pair as a ZIP; the
    samples show the same two files, downloaded separately.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for variant in (SHORT, FULL):
        sample = dict(SAMPLE)
        sample["brief"] = SAMPLE["brief"] + variant["brief_extra"]
        state, paper, explainer = build(sample)
        stem = variant["stem"]
        written = []
        for name, data in ((stem + ".docx", paper), (stem + "-explainer.docx", explainer)):
            path = OUT_DIR / name
            path.write_bytes(data)
            written.append((path, len(data)))
        print("title  ", state["draft"]["title"])
        print("words  ", state["draft"]["words"], "of", state["draft"]["target_words"],
              "| met:", state["draft"]["met_target"], "| missing:", state["draft"]["missing"])
        for path, size in written:
            print("wrote  ", path.name, size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
