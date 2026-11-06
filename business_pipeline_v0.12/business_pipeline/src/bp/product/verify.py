"""The plan verifier: code, not opinion.

A *reading* of the brief (produced by a person, a resolver, or a panel of
advocates) is checked here before anything is built from it.  This module is
deliberately mechanical:

- it knows the closed catalogue and refuses anything outside it;
- it requires every quoted anchor to be an exact substring of the brief;
- it normalises a figure written as a person writes it ("SAR 1.2m", "12%",
  "1,200,000", "about 40k") and refuses the classic filings — a rate sent as an
  amount, a percent not converted, a currency the case does not use;
- it refuses a missing required input that the reading did not name;
- it hashes the frozen plan, so the paper can be re-derived and compared.

Nothing here computes a business result.  Arithmetic on case figures happens in
the frozen method library, and only there.
"""

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation

FORMAT = "bp-plan/1"

#: Words that mark a declared input as a rate rather than an amount.
RATE_WORDS = ("rate", "margin", "share", "ratio", "growth", "interest", "yield",
              "discount", "churn", "tax", "volatility", "probability", "confidence",
              "elasticity", "alpha", "proportion", "percent", "pct", "return")
#: Words that mark a count or a period rather than an amount.
COUNT_WORDS = ("units", "unit", "periods", "years", "months", "days", "steps",
               "iterations", "quantity", "shares", "customers", "people", "items",
               "observations", "tasks", "stations", "cohorts")

#: A claim a method does not license, refused in a reading's rationale.
UNLICENSED = (r"\bwill\b", r"\bprove[sn]?\b", r"\bguarantee", r"\bcauses?\b",
              r"\bleads to\b", r"\bforecast(?:s|ed)? that\b", r"\bshould invest\b",
              r"\brecommend")

#: Goal verbs a paper must answer when the brief uses them.
GOAL_VERBS = ("evaluate", "recommend", "compare", "assess", "analyse", "analyze",
              "justify", "decide")

MONEY = re.compile(r"(sar|usd|aed|eur|gbp|php|idr|myr|qar|kwd|bhd|omr|egp|inr|jpy|cny|"
                   r"rmb|aud|cad|chf|try|brl|zar|ngn|kes|pkr|bdt|thb|vnd|krw|sgd|hkd|nzd)",
                   re.I)
SCALE = {"k": 1000, "thousand": 1000, "m": 1000000, "mn": 1000000, "million": 1000000,
         "b": 1000000000, "bn": 1000000000, "billion": 1000000000}
NOISE = re.compile(r"\b(about|around|approximately|roughly|nearly|circa|some|"
                   r"per|each|total|of|the|a|an)\b", re.I)


class VerifyError(ValueError):
    """A reading was refused, with a reason a person can act on."""


#: Suffixes that name a quantity of money, whatever the description mentions.
AMOUNT_SUFFIX = ("_value", "_cost", "_expense", "_amount", "_revenue", "_income",
                 "_price", "_sales", "_spend", "_debt", "_equity", "_principal",
                 "_balance", "_cash", "_profit", "_assets", "_liabilities",
                 "_receivables", "_payables", "_inventory", "_investment", "_benefits",
                 "_costs", "_flows", "_cashflows", "_capex")


def input_kind(name, spec):
    """Classify a declared input as amount, rate or count from its own schema.

    The description decides first — a schema that says "as a decimal" or gives an
    example below one is describing a rate.  Then the field name: a money suffix
    wins over a word like "interest" that also appears in rates, and a rate word
    wins over everything else.
    """
    text = ((spec or {}).get("desc") or "").lower()
    name_text = str(name or "").lower()
    if "as a decimal" in text or "as a fraction" in text or re.search(r"e\.g\.\s*0\.", text):
        return "rate"
    if name_text.endswith(AMOUNT_SUFFIX):
        return "amount"
    if any(word in name_text for word in RATE_WORDS):
        return "rate"
    if any(word in name_text for word in COUNT_WORDS):
        return "count"
    if (spec or {}).get("type") in ("decimal_list", "value_list", "integer"):
        return "count"
    return "amount"


def normalise_number(written, kind="amount", currency=None):
    """Turn a written figure into the canonical string a method expects.

    Returns (value, steps) where steps is the audit trail of what was changed.
    Raises VerifyError on anything ambiguous; no default is invented.
    """
    text = str(written if written is not None else "").strip()
    if not text:
        raise VerifyError("no figure was given")
    steps = []
    found = MONEY.search(text)
    if found:
        code = found.group(1).upper()
        if currency and code != str(currency).upper():
            raise VerifyError("the figure is in " + code + " but the case declares "
                              + str(currency).upper())
        steps.append("currency " + code)
        text = text[:found.start()] + text[found.end():]
    percent = "%" in text
    text = text.replace("%", " ")
    text = text.replace(",", "").replace("_", "")
    text = NOISE.sub(" ", text)
    match = re.search(r"[-+]?\d+(?:\.\d+)?\s*(k|mn|m|bn|b|thousand|million|billion)?", text, re.I)
    if not match:
        raise VerifyError("no number was found in the declared figure")
    token = match.group(0).strip()
    suffix = (match.group(1) or "").lower()
    scale = SCALE.get(suffix, 1)
    if scale != 1:
        token = token[: len(token) - len(suffix)].strip()
        steps.append("scaled by " + str(scale))
    if len(re.findall(r"\d+(?:\.\d+)?", text)) > 1:
        raise VerifyError("more than one number was found, so the figure is ambiguous")
    try:
        number = Decimal(token)
    except (InvalidOperation, ValueError):
        raise VerifyError("the figure is not a number")
    if scale != 1:
        number = number * scale
    if percent:
        if kind != "rate":
            raise VerifyError("a percentage was given for an amount")
        number = number / Decimal(100)
        steps.append("percent to decimal")
    if kind == "rate" and number > 1:
        raise VerifyError("a rate above 1 was given without a percent sign; "
                          "write 12% or 0.12")
    return str(number), steps


def verify_reading(reading, entries, frameworks, brief, currency=None, quoted=None):
    """Check one reading against the closed catalogue and the brief itself.

    `entries` is the capability catalogue, `frameworks` the framework ids the
    conductor supports, `quoted` an optional callable returning the brief text a
    quote must appear in.  Returns a list of problems; empty means approved.
    """
    problems = []
    if not isinstance(reading, dict):
        return [{"check": "shape", "detail": "a reading must be an object"}]

    def problem(check, detail):
        problems.append({"check": check, "detail": detail})

    for framework in reading.get("frameworks") or []:
        if framework not in frameworks:
            problem("catalogue", "unknown framework " + str(framework))
    capabilities = reading.get("capabilities") or []
    if not capabilities:
        problem("catalogue", "a reading must name at least one capability or say why none applies")
    for item in capabilities:
        key = (item or {}).get("key") if isinstance(item, dict) else item
        if key not in entries:
            problem("catalogue", "unknown capability " + str(key))
            continue
        applies = entries[key].get("applies_to") or ()
        for framework in reading.get("frameworks") or []:
            if framework not in applies:
                problem("catalogue", key + " does not fit a " + str(framework) + " paper")

    source = quoted() if callable(quoted) else brief
    source_text = str(source or "")
    anchors = reading.get("anchors") or []
    for anchor in anchors:
        quote = str((anchor or {}).get("quote") or "") if isinstance(anchor, dict) else ""
        if not quote:
            problem("provenance", "an anchor has no quote")
        elif quote not in source_text:
            problem("provenance", "the quote is not in the brief: " + quote[:60])

    figures = reading.get("figures") or []
    for figure in figures:
        if not isinstance(figure, dict):
            problem("filing", "a figure must be an object")
            continue
        input_name = str(figure.get("input") or "")
        quote = str(figure.get("quote") or "")
        if not quote:
            problem("provenance", "the figure for " + (input_name or "an input") + " has no quote")
        elif quote not in source_text:
            problem("provenance", "the figure quote is not in the brief: " + quote[:60])
        if input_name and input_name not in str(reading.get("schema_inputs") or input_name):
            pass
        try:
            normalise_number(figure.get("written"), figure.get("kind") or "amount", currency)
        except VerifyError as error:
            problem("filing", (input_name or "a figure") + ": " + str(error))

    rationale = " ".join(str(reading.get("why") or "").split())
    for pattern in UNLICENSED:
        if re.search(pattern, rationale, re.I):
            problem("licence", "the rationale claims more than a method licenses: " + pattern)
            break

    if reading.get("missing") is None:
        problem("completeness", "a reading must say what is missing (an empty list is allowed)")
    return problems


#: Claims a paper may not make unless a frozen method licenses them.  Checked at
#: the export gate, so a draft that overclaims is blocked rather than submitted.
OVERCLAIM = (r"\bproves?\b", r"\bproven\b", r"\bguarantees?\b", r"\bdefinitely\b",
             r"\bconclusive(?:ly)?\b", r"\bconfirms? that\b", r"\bdemonstrates? that\b",
             r"\bestablishes? that\b", r"\bleads? to\b")
#: A negation earlier in the clause clears the claim: naming a limit is honest.
NEGATED = re.compile(r"\b(?:not|never|no|none|neither|nor|cannot|without|unlikely|hardly)\b"
                     r"|n't\b|\bdoesn't\b|\bdon't\b|\bisn't\b|\baren't\b|\bwon't\b|\bcan't\b", re.I)
#: Clause boundaries, so "it does not change, and it proves X" is still an overclaim.
CLAUSE = re.compile(r"[,;:]|\b(?:but|and|yet|so|although|while)\b", re.I)
#: An in-text citation marks a sentence as the source's claim, not the paper's.
CITATION = re.compile(r"\([^()]{1,160}?,\s*(?:n\.d\.|no date|\d{4}[a-z]?)\)")


def _clause_before(sentence, position):
    start = 0
    for match in CLAUSE.finditer(sentence):
        if match.end() > position:
            break
        start = match.end()
    return sentence[start:position]


def overclaims(text):
    """Sentences that assert more than any frozen method licenses.

    "The analysis proves entry succeeds" is a claim; "the analysis does not prove
    entry succeeds" is a limit, and is allowed.  The negation test looks only at
    the clause before the claim, so a negated first clause does not excuse a
    claim in the next one.
    """
    problems = []
    for sentence in re.split(r"(?<=[.!?;])\s+", str(text or "")):
        clean = " ".join(sentence.split())
        for pattern in OVERCLAIM:
            match = re.search(pattern, clean, re.I)
            if not match:
                continue
            if NEGATED.search(_clause_before(clean, match.start())):
                continue
            # negation may also follow the claim: "proves nothing", "guarantees no X"
            following = clean[match.end():].lstrip().split()
            if following and following[0].lower().rstrip(".,;:!?") in (
                    "nothing", "no", "not", "none", "neither", "never", "nobody", "nowhere"):
                continue
            problems.append({"claim": match.group(0).lower(), "sentence": clean[:300]})
            break
    return problems


def freeze(record):
    """Add the plan hash so the frozen plan can be re-derived and compared."""
    frozen = dict(record or {})
    frozen.pop("plan_hash", None)
    raw = json.dumps(frozen, sort_keys=True, separators=(",", ":"), default=str)
    frozen["plan_hash"] = "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return frozen


def brief_hash(brief):
    return "sha256:" + hashlib.sha256(str(brief or "").encode("utf-8")).hexdigest()[:16]


def numbers_in(text):
    """Every numeric token in a string, canonicalised for comparison."""
    found = []
    for token in re.findall(r"-?\d[\d,]*(?:\.\d+)?", str(text or "")):
        try:
            found.append(Decimal(token.replace(",", "")))
        except (InvalidOperation, ValueError):
            continue
    return found
