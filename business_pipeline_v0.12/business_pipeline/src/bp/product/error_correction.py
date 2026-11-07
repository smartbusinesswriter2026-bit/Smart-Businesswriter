"""Error correction engine (Tip 5 Type 4): detect a wrong entry, build the correcting entry.

A correction problem states an entry that was recorded wrongly and asks what the correcting
entry is and what it does to the statements.  The rule is the owner's: **identify the erroneous
entry and the correct one; compute the correcting entry; trace it through the statements.**

This module does that and nothing else.  It never decides what the correct treatment should be
from accounting opinion: the correct treatment is either stated in the problem (``correct`` in
the text) or supplied by a registered pattern whose treatment is a declared accounting rule.
If neither is available, the engine names the gap.

Two modes:

- **stated**: the problem gives the original entry and the correct entry as journal lines.
  The correcting entry is ``correct - original``, computed line by line.
- **pattern**: the problem says "X was expensed instead of capitalised" and a registered
  pattern knows the correcting treatment.  The amount is parsed from the text.

Every correction carries:
- the corrected entry (debit/credit lines);
- the effect on net income, assets, liabilities and equity (signed);
- a trace naming the accounts that move.

All arithmetic is ``Decimal``.  A missing amount is a gap, never a guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple


MONEY = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _money(text: str) -> Optional[Decimal]:
    if text is None:
        return None
    cleaned = str(text).replace(",", "").replace("$", "").strip().strip("()")
    try:
        d = Decimal(cleaned)
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


# ---------------------------------------------------------------------------
# Error patterns
# ---------------------------------------------------------------------------

@dataclass
class ErrorPattern:
    """A wrong-entry pattern and its declared correcting treatment."""
    id: str
    label: str
    detect: str  # regex on the problem text
    debit: str  # correcting debit account (chart label)
    credit: str  # correcting credit account (chart label)
    effect: str  # "expense capitalized" | "revenue deferred" | ...
    amount_hint: str  # regex to pull the amount from the text
    follows_with: Optional[str] = None  # an optional second correcting entry (e.g. depreciation)


PATTERNS: List[ErrorPattern] = [
    ErrorPattern(
        id="equipment_expensed",
        label="Equipment expensed instead of capitalised",
        detect=r"(?:equipment|machine|vehicle|asset)[^.]*?(?:expensed|charged to expense|recorded as (?:an )?expense|wrongly expensed|incorrectly expensed)",
        debit="Equipment",
        credit="Expense",
        effect="an expense was recorded where an asset belongs; reversing it raises assets and net income",
        amount_hint=r"(?:costing|cost of|valued at|amount of)\s*\$?([\d,]+(?:\.\d+)?)",
    ),
    ErrorPattern(
        id="unearned_revenue",
        label="Unearned revenue recorded as revenue",
        detect=r"(?:unearned|deferred|advance|unearned)\s+(?:revenue|income)[^.]*?(?:recorded as|treated as|recognised as|recognized as)\s+(?:revenue|income|sales)",
        debit="Revenue",
        credit="Unearned Revenue",
        effect="revenue was recognised before it was earned; reversing it lowers net income and raises liabilities",
        amount_hint=r"(?:unearned|advance|deferred)[^.]*?\$?([\d,]+(?:\.\d+)?)",
    ),
    ErrorPattern(
        id="depreciation_omitted",
        label="Depreciation omitted",
        detect=r"depreciation[^.]*?(?:omitted|not (?:recorded|charged|booked)|forgot)",
        debit="Depreciation Expense",
        credit="Accumulated Depreciation",
        effect="an expense was omitted; recording it lowers net income and raises accumulated depreciation",
        amount_hint=r"depreciation[^.]*?\$?([\d,]+(?:\.\d+)?)",
    ),
    ErrorPattern(
        id="inventory_overstated",
        label="Ending inventory overstated",
        detect=r"(?:ending|closing)\s+inventory[^.]*?(?:overstated|overvalued|too high)",
        debit="Cost of Goods Sold",
        credit="Inventory",
        effect="ending inventory was too high, so COGS was too low and net income too high; correcting lowers both",
        amount_hint=r"(?:overstated|overvalued|by)\s*\$?([\d,]+(?:\.\d+)?)",
    ),
    ErrorPattern(
        id="accrued_expense_omitted",
        label="Accrued expense not recorded",
        detect=r"(?:accrued|accrual)[^.]*?(?:omitted|not (?:recorded|booked)|forgot|unrecorded)",
        debit="Expense",
        credit="Accrued Liabilities",
        effect="an accrual was omitted; recording it raises liabilities and lowers net income",
        amount_hint=r"(?:accrued|accrual)[^.]*?\$?([\d,]+(?:\.\d+)?)",
    ),
    ErrorPattern(
        id="capital_expenditure_expensed",
        label="Capital expenditure charged to repairs",
        detect=r"(?:repairs|maintenance|revenue expense)[^.]*?(?:should have been capitalised|should be capitalized|was capital in nature)",
        debit="Equipment",
        credit="Repairs Expense",
        effect="a capital cost was charged to repairs; reclassifying it raises assets and net income",
        amount_hint=r"(?:amount of|cost of|spent)\s*\$?([\d,]+(?:\.\d+)?)",
    ),
    ErrorPattern(
        id="prepaid_expensed_in_full",
        label="Prepayment expensed in full instead of split",
        detect=r"(?:insurance|rent|prepaid)[^.]*?(?:expensed in full|charged in full|not (?:split|apportioned|prepaid)|no prepayment recorded)",
        debit="Prepayments",
        credit="Expense",
        effect="a prepayment was expensed in full; the unexpired portion is an asset, so this raises assets and net income",
        amount_hint=r"(?:unexpired portion|prepaid amount|portion)\s*(?:was|is|of|:|=)?\s*\$?([\d,]+(?:\.\d+)?)",
    ),
    ErrorPattern(
        id="sale_not_recorded",
        label="Sale not recorded",
        detect=r"(?:sale|sales|revenue)[^.]*?(?:was not recorded|not been recorded|omitted|unrecorded)",
        debit="Trade receivables",
        credit="Revenue",
        effect="a sale was omitted; recording it raises revenue and receivables",
        amount_hint=r"(?:sale|sales|revenue)[^.]*?\$?([\d,]+(?:\.\d+)?)",
    ),
    ErrorPattern(
        id="purchase_not_recorded",
        label="Purchase not recorded",
        detect=r"(?:purchase|purchases)[^.]*?(?:was not recorded|not been recorded|omitted|unrecorded)",
        debit="Purchases",
        credit="Trade payables",
        effect="a purchase was omitted; recording it raises purchases and payables",
        amount_hint=r"(?:purchase|purchases)[^.]*?\$?([\d,]+(?:\.\d+)?)",
    ),
    ErrorPattern(
        id="interest_not_accrued",
        label="Interest not accrued",
        detect=r"interest[^.]*?(?:was not accrued|not accrued|omitted|unrecorded)",
        debit="Interest Expense",
        credit="Interest Payable",
        effect="interest was not accrued; recording it raises liabilities and lowers net income",
        amount_hint=r"interest[^.]*?\$?([\d,]+(?:\.\d+)?)",
    ),
    ErrorPattern(
        id="wages_not_accrued",
        label="Wages not accrued",
        detect=r"(?:wages|salaries)[^.]*?(?:was not accrued|not accrued|omitted|unrecorded|unpaid)",
        debit="Wages Expense",
        credit="Accrued Liabilities",
        effect="unpaid wages were not accrued; recording them raises liabilities and lowers net income",
        amount_hint=r"(?:wages|salaries)[^.]*?\$?([\d,]+(?:\.\d+)?)",
    ),
]


@dataclass
class CorrectionEntry:
    """One line of the correcting entry."""
    account: str
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None


@dataclass
class CorrectionResult:
    """The full correction: entry, effect and trace."""
    pattern_id: Optional[str]
    label: str
    amount: Decimal
    lines: List[CorrectionEntry]
    effect: str
    net_income_delta: Decimal
    assets_delta: Decimal
    liabilities_delta: Decimal
    equity_delta: Decimal
    trace: List[str] = field(default_factory=list)
    gap: Optional[str] = None


def detect_pattern(text: str) -> Optional[ErrorPattern]:
    """The first registered pattern the text matches, or None."""
    for p in PATTERNS:
        if re.search(p.detect, text, re.I):
            return p
    return None


#: Cues that a problem asks for a correction, not a fresh set of statements.
CORRECTION_CUES = re.compile(
    r"\b(?:was|were)\s+(?:wrongly|incorrectly|erroneously|improperly)\s+(?:recorded|posted|charged|expensed|treated|recognised|recognized)\b"
    r"|\b(?:omitted|not recorded|not booked|forgot to record|failed to record)\b"
    r"|\binstead of\b"
    r"|\berror\b|\berroneous\b|\bcorrect(?:ing|ion)\s+entr(?:y|ies)\b",
    re.I)


def detect_error_problem(text: str) -> bool:
    """True when the text states an error and asks for the correction."""
    if not CORRECTION_CUES.search(text or ""):
        return False
    return detect_pattern(text) is not None


def _amount_for(pattern: ErrorPattern, text: str) -> Optional[Decimal]:
    """The amount stated in the text, from the pattern's hint."""
    m = re.search(pattern.amount_hint, text, re.I)
    if m:
        return _money(m.group(1))
    return None


def correct_pattern(text: str, pattern: ErrorPattern,
                    amount: Optional[Decimal] = None) -> CorrectionResult:
    """Build the correcting entry for a registered pattern."""
    amt = amount if amount is not None else _amount_for(pattern, text)
    if amt is None:
        return CorrectionResult(
            pattern_id=pattern.id, label=pattern.label, amount=Decimal("0"),
            lines=[], effect=pattern.effect,
            net_income_delta=Decimal("0"), assets_delta=Decimal("0"),
            liabilities_delta=Decimal("0"), equity_delta=Decimal("0"),
            gap="the amount is not stated in the problem; name the figure and the correction can be computed",
        )
    lines = [
        CorrectionEntry(account=pattern.debit, debit=amt),
        CorrectionEntry(account=pattern.credit, credit=amt),
    ]
    # Effects by pattern (declared, not inferred).
    effects = {
        "equipment_expensed": dict(ni=amt, assets=amt, liab=Decimal("0"), equity=amt),
        "unearned_revenue": dict(ni=-amt, assets=Decimal("0"), liab=amt, equity=-amt),
        "depreciation_omitted": dict(ni=-amt, assets=Decimal("0"), liab=Decimal("0"), equity=-amt),
        "inventory_overstated": dict(ni=-amt, assets=-amt, liab=Decimal("0"), equity=-amt),
        "accrued_expense_omitted": dict(ni=-amt, assets=Decimal("0"), liab=amt, equity=-amt),
        "capital_expenditure_expensed": dict(ni=amt, assets=amt, liab=Decimal("0"), equity=amt),
        "prepaid_expensed_in_full": dict(ni=amt, assets=amt, liab=Decimal("0"), equity=amt),
        "sale_not_recorded": dict(ni=amt, assets=amt, liab=Decimal("0"), equity=amt),
        "purchase_not_recorded": dict(ni=-amt, assets=Decimal("0"), liab=amt, equity=-amt),
        "interest_not_accrued": dict(ni=-amt, assets=Decimal("0"), liab=amt, equity=-amt),
        "wages_not_accrued": dict(ni=-amt, assets=Decimal("0"), liab=amt, equity=-amt),
    }
    e = effects.get(pattern.id, dict(ni=Decimal("0"), assets=Decimal("0"),
                                     liab=Decimal("0"), equity=Decimal("0")))
    trace = [
        f"Dr {pattern.debit} {amt} / Cr {pattern.credit} {amt}",
        f"Net income {e['ni']:+}, assets {e['assets']:+}, liabilities {e['liab']:+}, equity {e['equity']:+}",
    ]
    return CorrectionResult(
        pattern_id=pattern.id, label=pattern.label, amount=amt, lines=lines,
        effect=pattern.effect,
        net_income_delta=e["ni"], assets_delta=e["assets"],
        liabilities_delta=e["liab"], equity_delta=e["equity"],
        trace=trace,
    )


def correct_stated(original: List[Tuple[str, str, Decimal]],
                   correct: List[Tuple[str, str, Decimal]]) -> CorrectionResult:
    """Build the correcting entry from two stated entries.

    ``original`` and ``correct`` are lists of ``(account, side, amount)`` with side ``"Dr"``
    or ``"Cr"``.  The correcting entry is ``correct - original``: a line in ``correct`` not in
    ``original`` is added; a line in ``original`` not in ``correct`` is reversed.
    """
    def net(lines):
        out: Dict[Tuple[str, str], Decimal] = {}
        for acct, side, amt in lines:
            out[(acct, side)] = out.get((acct, side), Decimal("0")) + amt
        return out

    o, c = net(original), net(correct)
    keys = set(o) | set(c)
    diff: List[Tuple[str, str, Decimal]] = []
    for key in keys:
        delta = c.get(key, Decimal("0")) - o.get(key, Decimal("0"))
        if delta != 0:
            diff.append((key[0], key[1], delta))
    # A delta on one side is the correcting line; reduce a two-sided pair to one entry.
    lines: List[CorrectionEntry] = []
    total = sum((d for _, side, d in diff if side == "Dr"), Decimal("0"))
    total_cr = sum((d for _, side, d in diff if side == "Cr"), Decimal("0"))
    for acct, side, d in diff:
        if d > 0:
            if side == "Dr":
                lines.append(CorrectionEntry(account=acct, debit=d))
            else:
                lines.append(CorrectionEntry(account=acct, credit=d))
        else:
            if side == "Dr":
                lines.append(CorrectionEntry(account=acct, credit=-d))
            else:
                lines.append(CorrectionEntry(account=acct, debit=-d))
    return CorrectionResult(
        pattern_id=None, label="stated correction", amount=total,
        lines=lines, effect="stated original and correct entries; the correcting entry is the difference",
        net_income_delta=Decimal("0"), assets_delta=Decimal("0"),
        liabilities_delta=Decimal("0"), equity_delta=Decimal("0"),
        trace=[f"{acct} {side} {d:+}" for acct, side, d in diff],
    )


def correct(text: str, amount: Optional[Decimal] = None) -> Optional[CorrectionResult]:
    """Detect the error in the text and build the correction, or None when no pattern matches."""
    p = detect_pattern(text)
    if p is None:
        return None
    return correct_pattern(text, p, amount)


__all__ = [
    "ErrorPattern", "PATTERNS", "CorrectionEntry", "CorrectionResult",
    "detect_pattern", "correct_pattern", "correct_stated", "correct",
    "detect_error_problem", "CORRECTION_CUES",
]
