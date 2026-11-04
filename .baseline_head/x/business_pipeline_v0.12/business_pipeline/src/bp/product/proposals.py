"""Model-assisted cell proposals for the chat (product layer).

The student sometimes does not know what to write in a cell.  The model may
help: it reads the brief the student typed and the evidence the student
accepted, and proposes candidate statements *drawn from those words only*.

It may not answer the question.  A proposal that carries a number, a name or a
link that is not in the student's own words is refused, and the student is left
with the question instead.  Nothing a proposal says reaches the paper until the
student accepts it, and what reaches the paper is then the student's answer,
not the model's.
"""

import datetime
import json
import re

from . import prose

#: A figure is a fact the model may not add.  So is a percentage.
NUMBER = re.compile(r"\d+(?:[.,]\d+)?%?")
URL = re.compile(r"https?://|www\.|doi:", re.I)
#: A capitalised word is a name: allowed only if the student already wrote it.
PROPER = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
WORD = re.compile(r"[A-Za-z][A-Za-z\-']{2,}")


def _supplied_text(state):
    """Everything the student themselves wrote, which is all the model may use."""
    answers = state.get("answers") or {}
    parts = [str(state.get("brief") or ""), str(answers.get("decision") or "")]
    for value in answers.values():
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, str):
            parts.append(value)
    for item in state.get("evidence") or []:
        parts.append(str(item.get("quote") or ""))
    return " ".join(part for part in parts if part)


def _allowed_numbers(text):
    return set(NUMBER.findall(text))


def _allowed_names(text):
    return {word.lower() for word in WORD.findall(text)}


def _problems(candidate, supplied):
    """Why a candidate may not be offered to the student, or an empty list."""
    text = str(candidate or "").strip()
    if not text:
        return ["empty"]
    if len(text) > 300:
        return ["too long"]
    if URL.search(text):
        return ["link"]
    if not set(NUMBER.findall(text)) <= _allowed_numbers(supplied):
        return ["number"]
    allowed = _allowed_names(supplied)
    for name in sorted(set(PROPER.findall(text))):
        if name.lower() not in allowed:
            return ["name " + name]
    return []


def propose(state, key, label):
    """Propose candidate statements for one cell, drawn from the student's words."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    out = {"key": key, "label": label, "candidates": [], "model": None, "created_at": now}
    if not prose.available():
        return out
    supplied = _supplied_text(state)
    system = ("You are helping a student fill one cell of a business analysis. Propose up to three short "
              "candidate statements for the cell. Use ONLY words the student has already supplied: restate "
              "their own facts, do not add a fact, a number, a name, a statistic, a source or a conclusion. "
              "Each candidate must be a plain statement the student could have written themselves. "
              "Return ONLY a JSON object: {\"candidates\": [\"...\", \"...\"]}. No markdown.")
    user = json.dumps({"cell": label, "supplied": supplied[:4000]}, ensure_ascii=False)
    try:
        raw = prose._call([{"role": "system", "content": system},
                           {"role": "user", "content": user}])
        data = prose._parse(raw)
    except Exception:
        return out
    if not isinstance(data, dict):
        return out
    candidates = []
    for candidate in (data.get("candidates") or [])[:5]:
        text = str(candidate or "").strip()
        if _problems(text, supplied):
            continue
        if text in candidates:
            continue
        candidates.append(text)
    out["candidates"] = candidates
    out["model"] = prose.model_id()
    return out
