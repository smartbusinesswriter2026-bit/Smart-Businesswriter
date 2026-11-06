"""The plan council: advocates propose a reading, code verifies, an examiner decides.

Four roles, only two of them models:

- **advocates** (models, different stances) propose readings of the brief, drawn
  from the closed capability catalogue and quoting the brief;
- **the verifier** (`bp.product.verify`) is code: it vetoes a reading that leaves
  the catalogue, quotes something the brief does not say, files a figure wrongly,
  overclaims, or does not name what is missing;
- **the examiner** (a model that did not propose) ranks only the approved readings
  and returns a verdict with its reasons and the dissent;
- **the registrar** freezes the choice, so the paper is built from a record and
  not from a conversation.

The council is opt-in (`BP_PLAN_COUNCIL=1`) and the deterministic resolver stays
the default and the fallback.  Everything it returns passes through
`verify`, and nothing it writes reaches the paper: the paper is composed by the
deterministic conductor from the frozen plan.
"""

import json
import os
import re

from . import paper_families, prose, verify

FORMAT = "bp-council/1"
MAX_READINGS = 3

STANCES = (
    ("narrow", "Propose the narrowest reading that answers the question the brief actually asks. "
               "Prefer one framework and the fewest computations that answer it."),
    ("expected", "Propose the reading a business-school marker would expect for this kind of assignment: "
                 "the frameworks and computations the rubric would look for."),
    ("dissent", "Propose the reading the other two are least likely to propose, if it is defensible. "
                "Name what the obvious reading would miss."),
)

READING_JSON = """{
  "reading": "a short name for your reading",
  "why": "one or two sentences: what the brief asks and why these frameworks answer it",
  "anchors": [{"quote": "an exact sentence or phrase from the brief", "answers": "decision|scope|period|geography"}],
  "frameworks": ["framework ids from the closed list"],
  "archetype": "one paper-family archetype id from the closed list",
  "capabilities": [{"key": "capability key from the closed catalogue", "because": "what this computation answers"}],
  "figures": [{"input": "declared input name", "written": "the figure as the brief writes it",
               "kind": "amount|rate|count", "quote": "the exact text the figure came from"}],
  "missing": ["what the brief does not give"],
  "not_included": [{"key": "capability key", "reason": "why it is not in this paper"}]
}"""

EXAMINER_JSON = """{
  "chosen": 1,
  "criteria": {"coverage": "how fully it answers the brief", "parsimony": "least machinery that answers it",
               "evidence": "can the evidence be retrieved", "assumptions": "how much it has to assume"},
  "dissent": "the strongest case for the reading you did not choose",
  "confidence": "high|low"
}"""


class CouncilError(ValueError):
    """The council could not decide; the caller falls back and says why."""


def available():
    return os.environ.get("BP_PLAN_COUNCIL") == "1" and prose.available()


def model_id():
    return os.environ.get("BP_COUNCIL_MODEL") or prose.model_id()


def _call(messages, provider=None):
    if provider is not None:
        return provider(messages)
    return prose._call(messages, timeout=90, max_tokens=2000)


def _json_block(text):
    """Read the first JSON object out of a model answer; refuse anything else."""
    if not isinstance(text, str):
        raise CouncilError("the model returned no text")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise CouncilError("the model returned no JSON object")
        candidate = text[start:end + 1]
    try:
        data = json.loads(candidate)
    except ValueError:
        raise CouncilError("the model's JSON could not be read")
    if not isinstance(data, dict):
        raise CouncilError("the model's answer must be a JSON object")
    return data


def catalogue_lines(entries):
    """The closed catalogue as the advocates see it: ids, labels, slots."""
    lines = []
    for key, row in entries.items():
        slot = " / ".join(row.get("slot") or [])
        lines.append(key + " | " + str(row.get("label")) + " | " + slot
                     + " | fits: " + ",".join(row.get("applies_to") or ()))
    return "\n".join(sorted(lines))


def _reading_prompt(stance_text, brief, entries, frameworks, currency):
    system = (
        "You are an advocate on a business-writing council. You do not write the paper and you never "
        "invent a figure. You read the student's brief and propose exactly one reading: which frameworks "
        "and which computations answer it. Answer with one JSON object and nothing else.\n"
        "Rules: choose only ids from the closed lists below; quote the brief exactly; a figure must carry "
        "the text it came from; say what is missing; do not claim causation, forecasts or recommendations "
        "in your rationale.\n"
        "Closed frameworks: " + ", ".join(frameworks) + "\n"
        "Closed archetypes: " + ", ".join(sorted(paper_families.ARCHETYPES)) + "\n"
        "Closed capabilities (key | label | paper slot | applicable frameworks):\n" + catalogue_lines(entries)
        + "\nAnswer in this shape:\n" + READING_JSON)
    user = ("Stance: " + stance_text + "\n"
            + ("The case currency is " + str(currency) + ".\n" if currency else "")
            + "The brief:\n" + str(brief))
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _examiner_prompt(brief, approved):
    system = (
        "You are an independent examiner. You did not propose any reading. You see only the approaches "
        "that already passed a mechanical check. Rank them and choose one. Answer with one JSON object "
        "and nothing else. Do not add a figure, a source, a section or a claim that is not in a reading.")
    user = ("The brief:\n" + str(brief) + "\n\nThe approved readings, in order:\n"
            + json.dumps(approved, indent=1, ensure_ascii=False) + "\n\nAnswer in this shape:\n" + EXAMINER_JSON)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def advise(brief, entries, frameworks, currency=None, provider=None, quoted=None):
    """Run the council and return the approved readings and the verdict.

    No reading is returned unless it passed `verify.verify_reading`; the chosen
    one is the examiner's pick among those.  Raises CouncilError when nothing can
    be approved or the examiner's answer cannot be read.
    """
    readings, rejected = [], []
    for name, stance in STANCES[:MAX_READINGS]:
        try:
            text = _call(_reading_prompt(stance, brief, entries, frameworks, currency), provider)
            reading = _json_block(text)
        except CouncilError as error:
            rejected.append({"stance": name, "reasons": [{"check": "answer", "detail": str(error)}]})
            continue
        problems = verify.verify_reading(reading, entries, frameworks, brief, currency, quoted,
                                        archetypes=list(paper_families.ARCHETYPES))
        if problems:
            rejected.append({"stance": name, "reading": reading, "reasons": problems})
            continue
        reading["stance"] = name
        readings.append(reading)
    if not readings:
        return {"format": FORMAT, "approved": [], "rejected": rejected, "verdict": None,
                "reading": None, "needs_question": True}
    if len(readings) == 1:
        verdict = {"chosen": 1, "criteria": {}, "dissent": "", "confidence": "high",
                   "by": "single approved reading"}
    else:
        try:
            answer = _json_block(_call(_examiner_prompt(brief, readings), provider))
        except CouncilError as error:
            raise CouncilError("the examiner's answer could not be read: " + str(error))
        chosen = answer.get("chosen")
        try:
            chosen = int(chosen)
        except (TypeError, ValueError):
            chosen = 0
        if not 1 <= chosen <= len(readings):
            chosen = 1
        verdict = {"chosen": chosen, "criteria": answer.get("criteria") or {},
                   "dissent": answer.get("dissent") or "",
                   "confidence": str(answer.get("confidence") or "low"),
                   "by": "examiner"}
    return {"format": FORMAT, "approved": readings, "rejected": rejected, "verdict": verdict,
            "reading": readings[verdict["chosen"] - 1], "needs_question": False}
