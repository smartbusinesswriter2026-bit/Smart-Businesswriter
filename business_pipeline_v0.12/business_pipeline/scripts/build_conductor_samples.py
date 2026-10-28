"""Build the conductor sample papers with the product's own formatter.

Each sample is produced by the same code path a student uses - start, answer,
plan, draft - and rendered by `bp.product.docx.render_academic` in APA 7 and
Harvard.  Nothing is hand-formatted here, so a sample cannot drift from the
product.  Evidence comes from `scripts/sample_evidence.py`, a frozen set of
sources already cited in this repository; VRIO and Break-even retrieve none.

File names follow the recorded convention:
    <Paper title> - <Framework> - <Referencing style>.docx
with characters Windows forbids removed.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp.methods import LIBRARY  # noqa: E402
from bp.product import chat  # noqa: E402

import sample_evidence  # noqa: E402

#: The repository's shared samples folder, beside the existing Apple-Iran papers.
OUT_DIR = ROOT.parents[1] / "samples"

chat.set_compute(LIBRARY["breakeven"].impl)

STYLES = {"apa": "APA 7", "harvard": "Harvard"}

SAMPLES = [
    {
        "key": "ansoff",
        "short": "Apple's Entry into Iran",
        "title": "Apple's Entry into Iran: An Ansoff Growth Matrix Analysis",
        "framework": "ansoff",
        "label": "Ansoff",
        "brief": ("Apple is considering entering the Iranian market and needs to compare its growth options. "
                  "Use an Ansoff growth matrix for the Middle East over the last 5 years."),
        "answers": {"firm": "Apple", "decision": "Which growth option should Apple pursue in Iran?",
                    "geography": "Middle East", "period": "5"},
        "implications": ("Market development through authorised local partners is the only option the evidence "
                         "supports. Product development and diversification wait on sanctions relief and on payment "
                         "and data channels that the current environment does not provide."),
        "evidence": True,
    },
    {
        "key": "value-chain",
        "short": "Apple's Entry into Iran",
        "title": "Apple's Entry into Iran: A Value Chain Analysis",
        "framework": "value_chain",
        "label": "Value Chain",
        "brief": ("Apple is considering entering the Iranian market. Use Porter's value chain to assess where its "
                  "activities would be constrained in the Middle East over the last 5 years."),
        "answers": {"firm": "Apple", "decision": "Where would Apple's value chain be constrained in Iran?",
                    "geography": "Middle East", "period": "5"},
        "implications": ("Inbound logistics, procurement and technology are the constrained activities, while "
                         "marketing and human resources face fewer structural obstacles. A partner-led entry would "
                         "move part of the chain outside the sanctions perimeter."),
        "evidence": True,
    },
    {
        "key": "vrio",
        "short": "Apple's Resource Position",
        "title": "Apple's Resource Position: A VRIO Analysis",
        "framework": "vrio",
        "label": "VRIO",
        "brief": ("Apply VRIO to Apple's resources and capabilities to assess whether they would support entry "
                  "into the Iranian market."),
        "answers": {
            "decision": "Does Apple hold a resource that would support entry into Iran?",
            "resources": ("Brand and customer loyalty; Integrated hardware, software and services ecosystem; "
                          "Balance sheet and cash reserves; Retail and service network"),
            "valuable": ("Brand - yes: customers pay a premium for it; Ecosystem - yes: it raises switching costs"),
            "rare": ("Ecosystem - yes: few rivals combine devices, software and services at this scale"),
            "costly": ("Brand and ecosystem - yes: imitation would take years and a comparable installed base"),
            "organized": ("Retail and services - partly: organised to capture value in markets where Apple operates"),
        },
        "implications": ("The ecosystem is the resource that passes all four tests. The organisation is built to "
                         "capture it in markets Apple already serves, and sanctions prevent it from doing so in Iran."),
        "evidence": False,
    },
    {
        "key": "break-even",
        "short": "A Tehran Device Store",
        "title": "Break-even for a Tehran Device Store",
        "framework": "breakeven",
        "label": "Break-even",
        "brief": ("Run a break-even analysis for a hypothetical device store in Tehran at the declared price and cost.",
                  ),
        "answers": {"decision": "Is the declared price viable at the expected volume?",
                    "fixed": "2000000", "price": "40000", "variable": "28000", "expected": "120"},
        "implications": ("The declared volume of 120 units is below the break-even quantity, so the price or the "
                         "variable cost must change before the store is viable."),
        "evidence": False,
    },
]


def safe_name(text):
    """Remove the characters Windows forbids and collapse whitespace."""
    text = re.sub(r'[\\/:*?"<>|]', "", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text


def filename(sample, style):
    return "%s - %s - %s.docx" % (safe_name(sample["short"]), sample["label"], STYLES[style])


def seed_evidence(state):
    """Place the frozen sources on the plan's dimensions; unsupported dimensions stay gaps."""
    placement = sample_evidence.PLACEMENT.get(state["framework"], {})
    sources, evidence, gaps, by_key = [], [], [], {}
    for dimension in state["plan"]["dimensions"]:
        keys = placement.get(dimension["key"]) or []
        if not keys:
            gaps.append({"dimension": dimension["key"], "label": dimension["label"],
                         "reason": "no frozen source supports this activity for the worked example"})
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


def build(sample, style):
    """Run the conductor for one sample and one style; return the .docx bytes."""
    state = chat.start(sample["brief"], subject="management", framework=sample["framework"])
    if state["stage"] == "not_supported":
        raise chat.ChatError("The sample brief was refused: " + str(state.get("message")))
    while chat.current_question(state):
        question = chat.current_question(state)
        if question["id"] == "style":
            value = style
        else:
            value = sample["answers"].get(question["id"], question.get("default") or "")
        state = chat.answer(state, question["id"], value)
    state = chat.confirm_plan(state)
    if sample["evidence"]:
        state = seed_evidence(state)
    else:
        state = chat.research(state)
    state = chat.draft(state, implications=sample["implications"], style=style)
    return state, chat.docx_bytes(state, byline=["Smart Business Writer", "Worked example for students"])


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for sample in SAMPLES:
        for style in STYLES:
            state, data = build(sample, style)
            path = OUT_DIR / filename(sample, style)
            path.write_bytes(data)
            written.append((path, len(data), state["draft"]["title"]))
    for path, size, title in written:
        print("%s  (%d bytes)  %s" % (path.name, size, title))


if __name__ == "__main__":
    main()
