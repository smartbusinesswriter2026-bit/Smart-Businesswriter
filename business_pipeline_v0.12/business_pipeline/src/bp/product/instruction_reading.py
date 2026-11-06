"""Typed reading of a brief before the conductor plans anything.

This module does for the brief what the paper contract does for the paper:
it turns a loose instruction into typed decisions the rest of the pipeline can
check.  It is deterministic and stdlib only.

What it returns:
- FrameworkReading: resolved / ambiguous / absent / conflict, with every
  framework mention and its role (primary, negated, contrast, incidental).
- Slots: quantities with their value, span, unit, period and status.
- CategoryError: a quantity bound to an entity that cannot have that attribute
  (for example, an interest rate of a strategy framework).

The model never runs here.  The LLM may re-rank candidates later, but it cannot
add a framework or a method.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Tuple

FORMAT = "bp-instruction-reading/1"

#: Closed alias table.  Longer aliases are tried first so "Porter's five forces"
#: is not read as the bare word "porter".
FRAMEWORK_ALIASES = {
    "pestel_swot": ("pestel and swot", "pestel + swot", "pestel & swot"),
    "five_forces_breakeven": ("five forces and a break-even analysis",
                              "five forces and a breakeven analysis",
                              "five forces and break-even analysis",
                              "five forces and breakeven analysis",
                              "five forces and break-even", "five forces and breakeven",
                              "five forces plus break-even"),
    "five_forces": ("porter's five forces", "porters five forces", "porter's model",
                    "porter model", "5 forces", "five forces"),
    "value_chain": ("porter's value chain", "porters value chain", "value chain"),
    "ansoff": ("ansoff growth matrix", "ansoff matrix", "growth matrix", "ansoff"),
    "vrio": ("resource-based view", "resource based view", "vrio framework", "vrio"),
    "pestel": ("pestel analysis", "pestle analysis", "pestel", "pestle"),
    "swot": ("swot analysis", "swot"),
    "breakeven": ("break-even analysis", "breakeven analysis", "break even", "break-even", "breakeven"),
}

#: What each framework does.  Distinct roles can be combined; the same role
#: needs a choice or a comparison-paper path.
FRAMEWORK_ROLES = {
    "pestel": "diagnose_external",
    "five_forces": "diagnose_external",
    "swot": "diagnose_internal",
    "value_chain": "diagnose_internal",
    "vrio": "diagnose_internal",
    "ansoff": "generate_options",
    "breakeven": "evaluate_options",
    "pestel_swot": "diagnose_external",
    "five_forces_breakeven": "diagnose_external",
}

#: Entity types and the attributes they can carry.
ENTITY_TYPES = {
    "financial_instrument": ("loan", "bond", "deposit", "savings", "mortgage", "note", "debenture"),
    "strategy_framework": tuple(FRAMEWORK_ROLES),
    "computation": ("npv", "irr", "wacc", "dcf", "break-even", "breakeven", "payback", "roi"),
}
ENTITY_ATTRIBUTES = {
    "financial_instrument": {"interest_rate", "rate", "coupon", "yield", "maturity"},
    "strategy_framework": set(),
    "computation": {"discount_rate", "rate", "cost_of_capital", "tax_rate"},
}

ATTRIBUTE_PATTERNS = (
    ("interest_rate", r"interest\s+rate"),
    ("coupon", r"coupon"),
    ("yield", r"yield"),
    ("discount_rate", r"discount\s+rate"),
    ("tax_rate", r"tax\s+rate"),
    ("rate", r"\brate\b"),
)


@dataclass(frozen=True)
class Mention:
    framework_id: str
    span: Tuple[int, int]
    role: str  # primary | negated | contrast | incidental


@dataclass(frozen=True)
class FrameworkReading:
    status: str  # resolved | ambiguous | absent | conflict
    mentions: Tuple[Mention, ...] = ()
    combinable: bool = False
    comparison: bool = False

    @property
    def primary(self) -> Optional[str]:
        for mention in self.mentions:
            if mention.role == "primary":
                return mention.framework_id
        return None

    @property
    def selected(self) -> Tuple[str, ...]:
        return tuple(dict.fromkeys(m.framework_id for m in self.mentions if m.role == "primary"))

    @property
    def rejected(self) -> Tuple[str, ...]:
        return tuple(dict.fromkeys(m.framework_id for m in self.mentions if m.role == "negated"))

    @property
    def roles(self) -> Tuple[str, ...]:
        return tuple(sorted({FRAMEWORK_ROLES.get(m.framework_id, "") for m in self.mentions if m.role == "primary"}))


@dataclass(frozen=True)
class Slot:
    name: str
    value: str
    span: Tuple[int, int]
    status: str = "pending"  # pending | consumed | dismissed
    kind: str = "amount"
    period: str = ""
    compounding: str = "unknown"
    candidate_roles: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CategoryError:
    code: str
    found: str
    span: Tuple[int, int]
    why: str
    repairs: Tuple[dict, ...] = ()


def _normalise(text: str) -> str:
    return " ".join(str(text or "").split())


def _alias_pattern(alias: str) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", re.I)


def _role_for(text: str, start: int) -> str:
    prefix = text[max(0, start - 60):start].lower()
    # Negation is local: "not Ansoff" negates Ansoff, but "Not Ansoff, use Five
    # Forces" does not negate Five Forces.  A comma between the negator and the
    # mention ends the negation scope.
    negation = re.search(r"\b(not|no|without|avoid|exclude|excluding|drop|never|do not|don't|dont)\b([^,.;:]{0,24})$", prefix)
    if negation and "," not in negation.group(2):
        return "negated"
    if re.search(r"\b(unlike|versus|vs\.?|compared to|comparison of|compare)\b[^,.;:]{0,30}$", prefix):
        return "contrast"
    if re.search(r"\b(interest rate|rate|yield|coupon|price|cost|value)\s+(of|for)\s*$", prefix):
        return "incidental"
    return "primary"


def read_frameworks(brief: str) -> FrameworkReading:
    """Read every framework mention and classify its role."""
    text = _normalise(brief)
    mentions = []
    occupied = set()
    # Longest alias first, so "Porter's five forces" beats "five forces" and
    # "pestel and swot" beats the two single names.
    for framework_id, aliases in sorted(FRAMEWORK_ALIASES.items(),
                                        key=lambda item: -max(len(a) for a in item[1])):
        for alias in sorted(aliases, key=len, reverse=True):
            for match in _alias_pattern(alias).finditer(text):
                span = (match.start(), match.end())
                if any(start < span[1] and span[0] < end for start, end in occupied):
                    continue
                occupied.add(span)
                mentions.append(Mention(framework_id, span, _role_for(text, match.start())))
                break
    mentions.sort(key=lambda mention: mention.span[0])
    if not mentions:
        return FrameworkReading("absent", ())
    primaries = [m for m in mentions if m.role == "primary"]
    contrasts = [m for m in mentions if m.role == "contrast"]
    if not primaries:
        if contrasts:
            return FrameworkReading("ambiguous", tuple(mentions), combinable=True, comparison=True)
        return FrameworkReading("absent", tuple(mentions))
    if len(primaries) == 1:
        return FrameworkReading("resolved", tuple(mentions))
    roles = {FRAMEWORK_ROLES.get(m.framework_id, "") for m in primaries}
    if len(roles) == 1:
        return FrameworkReading("conflict", tuple(mentions))
    return FrameworkReading("ambiguous", tuple(mentions), combinable=True)


def _entity_before(text: str, position: int) -> Optional[Tuple[str, str, Tuple[int, int]]]:
    tail = text[:position].lower()
    best = None
    for entity_type, names in ENTITY_TYPES.items():
        for name in names:
            pattern = re.compile(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])\s*(?:of|for)?\s*$")
            match = pattern.search(tail)
            if match:
                span = (match.start(), match.end())
                if best is None or span[0] > best[2][0]:
                    best = (entity_type, name, span)
    return best


def find_category_errors(brief: str, reading: Optional[FrameworkReading] = None) -> Tuple[CategoryError, ...]:
    """Find a quantity bound to an entity that cannot have that attribute."""
    text = _normalise(brief)
    errors = []
    for attribute, pattern in ATTRIBUTE_PATTERNS:
        for match in re.finditer(pattern, text, re.I):
            tail = text[match.end():match.end() + 80]
            # The entity follows "interest rate of ...".
            entity_match = re.match(
                r"\s*(?:of|for)\s+(.+?)(?=\s+(?:when|and|or|at|for|to|of|in|with|while|then|but|so)\b|[,.?!;]|$)",
                tail, re.I)
            if not entity_match:
                continue
            entity_text = entity_match.group(1).strip()
            entity_span = (match.end() + entity_match.start(1), match.end() + entity_match.end(1))
            entity_type = None
            framework_id = None
            lowered = entity_text.lower()
            for candidate, aliases in FRAMEWORK_ALIASES.items():
                if any(_alias_pattern(alias).search(lowered) for alias in aliases):
                    entity_type = "strategy_framework"
                    framework_id = candidate
                    break
            if entity_type is None:
                for candidate, names in ENTITY_TYPES.items():
                    if any(_alias_pattern(name).search(lowered) for name in names):
                        entity_type = candidate
                        break
            if entity_type is None:
                continue
            allowed = ENTITY_ATTRIBUTES.get(entity_type, set())
            if attribute in allowed:
                continue
            repairs = []
            if attribute in ("interest_rate", "rate", "discount_rate"):
                repairs = [
                    {"option": "Use the rate as a discount rate in NPV",
                     "method": "npv", "because": "a discount rate is an attribute of a valuation, not a framework"},
                    {"option": "Run the framework without a rate",
                     "method": None, "because": "the framework itself has no rate input"},
                ]
            if entity_type == "strategy_framework":
                labels = {
                    "ansoff": "Ansoff", "five_forces": "Five Forces",
                    "value_chain": "Value Chain", "vrio": "VRIO",
                    "pestel": "PESTEL", "swot": "SWOT",
                    "breakeven": "Break-even", "pestel_swot": "PESTEL + SWOT",
                    "five_forces_breakeven": "Five Forces + Break-even",
                }
                label = labels.get(framework_id or "", str(framework_id or entity_type).replace("_", " "))
                why = (label + " is a strategy framework, not a financial instrument, so it has no "
                       + attribute.replace("_", " ") + ".")
            else:
                why = ("the " + entity_text.lower() + " is a " + entity_type.replace("_", " ")
                       + ", so it has no " + attribute.replace("_", " ") + ".")
            errors.append(CategoryError(
                code="CATEGORY_ERROR",
                found=text[match.start():entity_span[1]],
                span=(match.start(), entity_span[1]),
                why=why,
                repairs=tuple(repairs),
            ))
    return tuple(errors)


def extract_slots(brief: str) -> Tuple[Slot, ...]:
    """Pull quantities out of the brief as typed, pending slots."""
    text = _normalise(brief)
    slots = []
    index = 0
    for match in re.finditer(r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<percent>%|percent)\s*(?P<period>per annum|per year|annually|p\.a\.)?", text, re.I):
        index += 1
        raw = match.group("value").replace(",", ".")
        try:
            value = str(float(raw) / 100.0)
        except ValueError:
            value = raw
        prefix = text[max(0, match.start() - 40):match.start()].lower()
        name = "rate_%d" % index
        if "interest rate" in prefix:
            name = "interest_rate"
        elif "discount rate" in prefix:
            name = "discount_rate"
        elif "growth" in prefix:
            name = "growth_rate"
        slots.append(Slot(name=name, value=value, span=(match.start(), match.end()),
                          kind="rate", period=(match.group("period") or "").lower(),
                          compounding="unknown",
                          candidate_roles=("discount_rate", "borrowing_cost", "growth_rate")))
    for match in re.finditer(r"(?P<value>\$?\s?\d[\d,]*(?:\.\d+)?)", text):
        if any(not (match.end() <= slot.span[0] or match.start() >= slot.span[1]) for slot in slots):
            continue
        if text[match.end():match.end() + 1] == "%" or text[match.end():match.end() + 7].lower() == " percent":
            continue
        index += 1
        slots.append(Slot(name="amount_%d" % index, value=match.group("value").replace("$", "").replace(",", "").strip(),
                          span=(match.start(), match.end()), kind="amount"))
    return tuple(slots)


def pending_slots(slots: Tuple[Slot, ...]) -> Tuple[Slot, ...]:
    return tuple(slot for slot in slots if slot.status == "pending")


def no_silent_drop(slots: Tuple[Slot, ...]) -> Tuple[str, ...]:
    """Names of slots still pending.  A run cannot proceed while this is non-empty."""
    return tuple(slot.name for slot in pending_slots(slots))


def refusal(error: CategoryError, proceed: str = "tell me what the quantity represents") -> dict:
    """The standard refusal shape: code, span, why, nearest options, next step."""
    return {
        "status": "refused",
        "code": error.code,
        "found": error.found,
        "span": list(error.span),
        "why": error.why,
        "options": [dict(row) for row in error.repairs],
        "proceed": proceed,
    }


def next_question(reading: FrameworkReading, slots: Tuple[Slot, ...],
                  intent: Optional[str] = None, errors: Tuple[CategoryError, ...] = ()) -> Optional[dict]:
    """Dependency-ordered clarification planner.

    Order: intent -> category/orphan slot -> framework -> industry -> objective
    -> parameters.  The caller supplies what it already knows.
    """
    if intent is None:
        return {"id": "intent", "prompt": "Is this a paper or a computation?",
                "why": "The answer decides whether a framework or a method runs first.",
                "type": "choice", "choices": [["paper", "A paper"], ["computation", "A computation"]]}
    if errors:
        error = errors[0]
        return {"id": "category_error", "prompt": "What should the quantity do?",
                "why": error.why,
                "type": "choice",
                "choices": [[row.get("method") or "ignore", row["option"]] for row in error.repairs]}
    if pending_slots(slots):
        slot = pending_slots(slots)[0]
        return {"id": "slot:" + slot.name, "prompt": "What does " + slot.name.replace("_", " ") + " do?",
                "why": "Every quantity is consumed, dismissed, or named in the report.",
                "type": "choice",
                "choices": [[role, role.replace("_", " ")] for role in slot.candidate_roles]}
    if reading.status == "resolved":
        return None
    if reading.status == "conflict":
        return {"id": "framework", "prompt": "Which framework should this paper use?",
                "why": "These frameworks do the same job, so the paper carries one of them.",
                "type": "choice",
                "choices": [[m.framework_id, m.framework_id.replace("_", " ")] for m in reading.mentions
                            if m.role == "primary"]}
    if reading.status == "ambiguous":
        return {"id": "framework_order", "prompt": "Which framework is primary, and in what order?",
                "why": "These frameworks do different jobs, so they can be combined.",
                "type": "choice",
                "choices": [[m.framework_id, m.framework_id.replace("_", " ")] for m in reading.mentions
                            if m.role == "primary"]}
    return {"id": "framework", "prompt": "Which framework should this paper use?",
            "why": "No framework was named.",
            "type": "choice", "choices": []}
