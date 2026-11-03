"""The statement council: one model reading, a dissent on the contested items, a ranked decision.

Only what matters is argued.  A trial balance is read deterministically and exactly; the model is
asked only when the parser cannot read the problem, and a second seat is asked only about the items
where **two placements are defensible** (an owner's advance is a loan or capital; a prepayment is an
asset or an expense).  Every candidate is checked by `statements_verify`, and the ranking is not a
vote:

    declared vocabulary rule  >  literal standard rule  >  marker convention  >  dissent

The dissent never wins by arguing; it wins only if the reading it opposes fails the verifier.  It is
recorded either way, so a marker can see what was considered.

Cost, stated in the code because it is a real budget: one call per reading, plus one call for the
dissent pass when there is at least one contested item.  `max_tokens` is 8,000: the paper council's
2,000 truncates a statement reading, and a truncated reading is a rejected reading.
"""

import json
import os
import re

from . import prose
from . import statements

STANCES = ("literal", "expected")

#: The one object a reader must return.  Field names are the core's (see `statements.RULES`).
READING_JSON = """{
  "problem_type": "trial_balance | transactions | adjustments | incomplete_records",
  "why": "the cue that decided the type, in one sentence",
  "currency": "USD",
  "framework": "US_GAAP | IFRS | local",
  "places": 2,
  "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "period_source": "declared | derived | assumed",
  "chart": [{"code": "1000", "name": "Cash", "type": "asset | liability | equity | income | expense",
             "line": "Cash", "section": "current | non_current | null",
             "role": "cash | capital | retained_earnings | dividends | null",
             "activity": "operating | investing | financing | null", "contra": false,
             "quote": "the exact text that names this account"}],
  "opening": [{"account": "1000", "debit": "5000", "quote": "the exact text"}],
  "journal": [{"date": "YYYY-MM-DD", "description": "what the entry records",
               "lines": [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}],
               "quote": "the exact text"}],
  "schedules": [{"kind": "depreciation | accrual | prepayment | deferred_income | bad_debt | amortization",
                 "the core's own field names for that kind": "value", "quote": "the exact text"}],
  "figures": [{"written": "7,000", "value": "7000", "kind": "amount | rate | count", "quote": "exact text"}],
  "derivations": [{"figure": "capital", "identity": "capital = assets - liabilities", "working": "one line", "derived": true}],
  "ratio_map": {"inventory": "1200"},
  "diagnosis": null,
  "missing": [{"what": "what the instruction does not give", "why": "why it matters"}],
  "assumptions": [{"text": "an assumption you had to make", "basis": "why"}]
}"""

DISSENT_JSON = """{
  "items": [{"label": "the item", "used": "the placement the reading used",
             "alternative": "the other defensible placement", "quote": "the exact text that supports it",
             "why": "one sentence"}]
}"""


class CouncilError(ValueError):
    """The council could not produce a readable answer."""


def available():
    """Whether a model can be asked at all: the tile then reads with it."""
    return prose.available()


def model_id():
    """The dissent seat, so two vendors can be used without new code."""
    return os.environ.get("BP_COUNCIL_MODEL") or prose.model_id()


def _call(messages, provider=None):
    if provider is not None:
        return provider(messages)
    return prose._call(messages, timeout=180, max_tokens=8000)


def _json_block(text):
    """One JSON object, and nothing else.  A fence is tolerated; two objects are refused."""
    if not isinstance(text, str):
        raise CouncilError("the model returned no text")
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start == -1 or end <= start:
        raise CouncilError("the model returned no JSON object")
    blob = candidate[start:end + 1]
    try:
        data = json.loads(blob)
    except ValueError as error:
        raise CouncilError("the model's JSON could not be read: " + str(error)[:120])
    if not isinstance(data, dict):
        raise CouncilError("the model's answer must be a JSON object")
    return data


def _prompt(instruction):
    system = (
        "You read an accounting problem for a student and return one JSON object. You never invent a "
        "figure, an account, a date or a source: every account, entry, schedule and figure carries the "
        "exact text it came from. Choose exactly one problem_type. The type is income, not revenue. "
        "Every asset and liability needs a section (current or non_current), because the section "
        "decides the cash-flow classification. A schedule declares its parameters (cost, residual, "
        "life in MONTHS, rate, periods), never a journal you computed: 'five years' is life 60 and the "
        "conversion goes in derivations. Say what is missing; an empty missing claims the statements "
        "can be completed. No forecast, no recommendation, no 'will', 'proves' or 'causes'. Answer "
        "with the JSON object and nothing else.\n\nShape:\n" + READING_JSON)
    return [{"role": "system", "content": system}, {"role": "user", "content": str(instruction)}]


def contested_items(reading):
    """The labels where two placements are defensible, from the vocabulary, never from opinion."""
    items = []
    for account in reading.get("chart") or []:
        if not isinstance(account, dict):
            continue
        placed = statements.place(str(account.get("name") or ""))
        if placed["contested"]:
            items.append({"label": account.get("name"), "used": account.get("line"),
                          "alternative": placed["candidates"][1]["line"]})
    return items


def _dissent_prompt(instruction, items):
    system = ("You are the dissent seat. For each item, argue the OTHER defensible placement, with the "
              "exact text that supports it. Do not rewrite the reading. Answer with one JSON object.")
    user = ("The instruction:\n" + str(instruction)
            + "\n\nThe items where two placements are defensible:\n"
            + json.dumps(items, ensure_ascii=False) + "\n\nAnswer in this shape:\n" + DISSENT_JSON)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def read(instruction, provider=None):
    """Read one instruction with the model, argue the contested items, return the reading.

    The reading is **not** verified here: the caller runs the verifier, so there is one gate and not
    two.  A dissent is recorded, never applied: the declared rule and the literal reading rank above
    it, so the student gets one answer and the record shows what was considered.
    """
    try:
        reading = _json_block(_call(_prompt(instruction), provider))
    except CouncilError:
        raise
    except Exception as error:
        raise CouncilError("the reading model failed: " + str(error)[:160])
    reading.setdefault("missing", [])
    reading.setdefault("assumptions", [])
    rejected = []
    items = contested_items(reading)
    if items:
        try:
            answer = _json_block(_call(_dissent_prompt(instruction, items), provider))
            for item in answer.get("items") or []:
                rejected.append({"seat": "dissent", "item": item.get("label"),
                                 "used": item.get("used"), "alternative": item.get("alternative"),
                                 "quote": item.get("quote"), "why": item.get("why")})
        except Exception as error:
            rejected.append({"seat": "dissent", "error": str(error)[:160]})
    return {"reading": reading, "source": "council" + ("+dissent" if items else ""),
            "rejected": rejected, "same_model": model_id() == prose.model_id()}

