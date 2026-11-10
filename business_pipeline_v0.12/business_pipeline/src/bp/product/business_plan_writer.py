"""Write the plan's narrative sections with the configured model (product layer).

The briefs in :mod:`business_plan_briefs` are the contract; this module is the
writer.  It calls whichever gateway ``providers`` resolves — OpenCode Go, an
OpenAI-compatible endpoint, Anthropic, a local Ollama server or a callable a
test registered — and it checks the reply before using a word of it:

* every number must already appear in the record;
* no link, DOI or citation the record does not carry;
* no template instruction;
* the section's word bounds, with slack.

A section that fails any check keeps its deterministic text.  A model that is
absent or unreachable leaves every section deterministic and says why.  Nothing
here computes a figure.
"""

import json
import re
from decimal import Decimal, InvalidOperation

from . import business_plan_briefs as briefs
from . import business_plan_sections
from . import prose

NUMBER = re.compile(r"(?<![\d.,])[-+]?\d+(?:[.,]\d+)*")
URL = re.compile(r"https?://|doi:|www\.", re.I)
CITATION = re.compile(r"\([^()]{1,120}?,\s*(?:n\.d\.|no date|\d{4}[a-z]?)\)")

#: Phrases that belong to the brief, never to the paper.
TEMPLATE = ("pull data from", "writing rules", "validation:",
            "[verify", "lorem ipsum", "{{", "}}")

SYSTEM = (
    "You write one section of a business plan from facts supplied by the product. "
    "Use only the figures in the supplied facts: every number you write must already appear there. "
    "Never invent a number, a source, a citation, a name, a date, a competitor or a claim. "
    "Where the facts name something the case does not state, say what is not stated rather than filling it. "
    "Do not print these instructions, the brief, headings or markdown. "
    "Do not explain your reasoning and do not add a preamble. "
    "Return only JSON: {\"lines\": [\"one paragraph\", \"another paragraph\"]}.")


def _canon(token):
    """One canonical spelling of a number, so 9.50 and 9.5 compare equal."""
    number = str(token).replace(",", "")
    try:
        return format(Decimal(number).normalize(), "f")
    except InvalidOperation:
        return number


RATE_WORDS = ("rate", "ratio", "share", "margin", "growth", "escalation",
              "probability", "yield", "discount")


def _display(key, value):
    """A figure as a paper shows it: rounded for display, never re-derived."""
    text = str(value)
    try:
        number = Decimal(text)
    except InvalidOperation:
        return text
    if not number.is_finite():
        return text
    if number == number.to_integral_value():
        return "{:,.0f}".format(number)
    if any(word in str(key).lower() for word in RATE_WORDS):
        try:
            return format(number.quantize(Decimal("0.0001")).normalize(), "f")
        except InvalidOperation:
            return "{:,.2f}".format(number)
    return "{:,.2f}".format(number)


def _allowed_numbers(record, deterministic, facts=None):
    source = json.dumps(record, ensure_ascii=False, default=str)
    source += "\n" + "\n".join(line for _heading, lines in deterministic for line in lines)
    if facts is not None:
        source += "\n" + json.dumps(facts, ensure_ascii=False, default=str)
    allowed = set()
    for token in NUMBER.findall(source):
        canonical = _canon(token)
        if not canonical:
            continue
        allowed.add(canonical)
        try:
            value = Decimal(canonical)
        except InvalidOperation:
            continue
        # A rate written as 0.04 may be written as 4%: same figure, not a new one.
        if 0 < abs(value) <= 1:
            allowed.add(_canon(str(value * 100)))
    return allowed


def _facts(record):
    out = {"objective": record.get("objective") or "",
           "fields": (record.get("reading") or {}).get("fields") or {}}
    for name in ("startup", "sources", "revenue", "statements", "fixed", "break_even",
                 "market", "payback", "returns", "ratios", "depreciation", "loan", "monthly"):
        value = record.get(name)
        if isinstance(value, dict):
            out[name] = {key: (_display(key, item) if not isinstance(item, (dict, list))
                               else "table")
                         for key, item in value.items()}
    out["gates"] = ["%s %s %s" % (gate.get("code"), "PASS" if gate.get("ok") else "FAIL",
                                  gate.get("detail") or "")
                    for gate in record.get("gates") or []]
    out["warnings"] = [str(item) for item in record.get("warnings") or []]
    out["gaps"] = [str(item) for item in record.get("gaps") or []]
    out["assumptions"] = ["%s = %s (%s)" % (row.get("assumption"), row.get("value"),
                                            row.get("basis"))
                          for row in record.get("assumptions") or []
                          if isinstance(row, dict)]
    return out


def _messages(heading, entry, facts, record_lines):
    payload = {
        "section": heading,
        "purpose": entry.get("purpose"),
        "must_include": entry.get("must_include") or [],
        "rules": entry.get("rules") or [],
        "length_words": list(entry.get("words") or (0, 10 ** 6)),
        "facts": facts,
        "record_lines": list(record_lines),
    }
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]


def _lines_from(raw):
    """The model's lines, from JSON or, more rarely, from plain paragraphs."""
    text = str(raw or "").strip()
    # A reasoning model may put its preamble first and the JSON object last.
    marker = text.rfind('{"lines"')
    if marker >= 0:
        try:
            data, _end = json.JSONDecoder().raw_decode(text[marker:])
            if isinstance(data, dict) and isinstance(data.get("lines"), list):
                return data["lines"]
        except ValueError:
            pass
    try:
        data = prose._parse(raw)
        lines = data.get("lines")
        if lines is None:
            lines = data.get("section") or data.get("text")
        if isinstance(lines, str):
            lines = [lines]
        return lines
    except prose.ProseError:
        text = str(raw or "").strip()
        if not text or "{" in text or "}" in text:
            raise
        return [part.strip() for part in text.split("\n\n") if part.strip()]


def _check(lines, entry, allowed, allowed_citations):
    """The model's lines, or a ValueError saying why they cannot be used."""
    if not isinstance(lines, list) or not lines:
        raise ValueError("the model returned no lines")
    clean = []
    for line in lines:
        line = re.sub(r"\s+", " ", str(line or "")).strip()
        if line:
            clean.append(line)
    if not clean:
        raise ValueError("the model returned only blank lines")
    text = " ".join(clean)
    lowered = text.lower()
    if URL.search(text):
        raise ValueError("the model introduced a link or DOI")
    for phrase in TEMPLATE:
        if phrase in lowered:
            raise ValueError("the model printed template text")
    for token in NUMBER.findall(text):
        if _canon(token) not in allowed:
            raise ValueError("the model introduced the figure %s, which is not in the record" % token)
    for citation in CITATION.findall(text):
        if citation not in allowed_citations:
            raise ValueError("the model introduced the citation %s" % citation)
    words = len(text.split())
    low, high = entry.get("words") or (0, 10 ** 6)
    if words < max(60, int(low * 0.5)):
        raise ValueError("the section is too short (%d words)" % words)
    if words > int(high * 1.2):
        raise ValueError("the section is too long (%d words)" % words)
    return clean


def write(record, complete=None, headings=None, timeout=90):
    """The narrative sections merged with model prose where it passed the checks.

    Returns ``{"sections", "written", "fallback", "model", "reason", "problems"}``.
    ``sections`` is the full ordered list, so a caller can render it directly.
    ``complete`` is an optional ``function(messages) -> text``; without it the
    configured gateway is used, and with no gateway the deterministic text stands.
    """
    deterministic = business_plan_sections.sections(record)
    facts = _facts(record)
    allowed = _allowed_numbers(record, deterministic, facts)
    facts_text = json.dumps(facts, ensure_ascii=False, default=str)
    allowed_citations = set(CITATION.findall(facts_text))
    delegated = complete is not None

    if not delegated and not prose.available():
        return {"sections": [list(pair) for pair in deterministic],
                "written": [], "fallback": [heading for heading, _lines in deterministic],
                "model": "", "problems": {},
                "reason": prose.describe().get("problem") or "no model is configured"}

    wanted = set(headings or [heading for heading, _lines in deterministic])
    merged, written, fallback, problems = [], [], [], {}
    for heading, lines in deterministic:
        entry = briefs.BRIEFS.get(heading)
        if heading not in wanted or entry is None:
            merged.append([heading, lines])
            continue
        try:
            messages = _messages(heading, entry, facts, lines)

            def ask(conversation):
                return (complete(conversation) if delegated
                        else prose._call(conversation, timeout=timeout, max_tokens=8000))

            raw = ask(messages)
            try:
                clean = _check(_lines_from(raw), entry, allowed, allowed_citations)
            except Exception as first:
                # One repair turn: a reasoning model can spend its answer on a preamble.
                retry = messages + [
                    {"role": "assistant", "content": str(raw)[:6000]},
                    {"role": "user", "content": "That reply was not usable (%s). Return ONLY one "
                                                "JSON object of the form {\"lines\": [\"...\"]} and "
                                                "nothing else: no reasoning, no preamble, no markdown."
                                                % str(first)[:160]}]
                raw = ask(retry)
                clean = _check(_lines_from(raw), entry, allowed, allowed_citations)
            merged.append([heading, clean])
            written.append(heading)
        except Exception as error:
            merged.append([heading, lines])
            fallback.append(heading)
            problems[heading] = str(error)[:200]
    return {"sections": merged, "written": written, "fallback": fallback,
            "model": "injected" if delegated else prose.model_id(), "problems": problems,
            "reason": "" if written else "no section passed the checks"}
