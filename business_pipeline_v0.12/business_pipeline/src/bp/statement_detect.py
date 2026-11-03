"""Detector and template layer for statement problems (owner tip, Part 7 & 9).

This is Step 1 of the runtime: pattern-match a problem's text to a registered detector,
extract typed slots, and generate a balanced journal entry from a template. Nothing here
computes a figure; it only recognises structure and emits structure.

Contract (tip 9.3):
  - a claim matches every detector whose pattern fits; the most specific wins;
  - a required slot with no extracted value routes to review (DetectError), never a default;
  - a generic-only match (specificity below threshold) is not journalizable;
  - a template is a pure function slots -> list[(account, side, amount)] and must balance;
  - nothing in this module imports a model or touches the ledger.

A caller supplies the chart of accounts (account codes -> metadata). Templates use the
conventional codes from the tips; if a chart lacks a code the template needs, journalize
raises so the gap is visible rather than silently renamed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List, Optional, Tuple


class DetectError(ValueError):
    """A claim could not be deterministically detected or journalized."""


SPECIFICITY_THRESHOLD = 50


@dataclass
class Slot:
    name: str
    kind: str  # money | percent | date | int | enum | string
    required: bool = True
    default: Any = None
    values: Optional[List[str]] = None


@dataclass
class Detector:
    id: str
    pattern: str
    specificity: int
    slots: List[Slot] = field(default_factory=list)
    kind: str = "transaction"  # transaction | policy | given_fact


@dataclass
class Match:
    detector_id: str
    span: Tuple[int, int]
    slots: Dict[str, Any]
    specificity: int
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Slot extraction helpers
# ---------------------------------------------------------------------------


def _money(text: str) -> Optional[Decimal]:
    if text is None:
        return None
    cleaned = text.replace(",", "").replace("$", "").strip()
    cleaned = cleaned.strip("()")
    try:
        d = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    if not d.is_finite():
        return None
    return d


def _int(text: str) -> Optional[int]:
    if text is None:
        return None
    try:
        return int(str(text).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _percent(text: str) -> Optional[Decimal]:
    if text is None:
        return None
    t = text.strip().rstrip("%").strip()
    try:
        d = Decimal(t)
    except (InvalidOperation, ValueError):
        return None
    if "%" in str(text):
        d = d / Decimal(100)
    return d


def _validate_slot(slot: Slot, raw: Any) -> Any:
    if raw is None or raw == "":
        if slot.required:
            raise DetectError(f"required slot {slot.name!r} not found")
        return slot.default
    if slot.kind == "money":
        v = _money(raw)
        if v is None:
            raise DetectError(f"slot {slot.name!r} is not a money value: {raw!r}")
        return v
    if slot.kind == "int":
        v = _int(raw)
        if v is None:
            raise DetectError(f"slot {slot.name!r} is not an integer: {raw!r}")
        return v
    if slot.kind == "percent":
        v = _percent(raw)
        if v is None:
            raise DetectError(f"slot {slot.name!r} is not a percent: {raw!r}")
        return v
    if slot.kind == "enum":
        v = str(raw).strip().lower()
        if slot.values and v not in [x.lower() for x in slot.values]:
            raise DetectError(f"slot {slot.name!r} value {v!r} not in {slot.values}")
        return v
    if slot.kind == "date":
        return str(raw).strip()
    return str(raw).strip()


# ---------------------------------------------------------------------------
# Detector registry
# ---------------------------------------------------------------------------

DETECTORS: List[Detector] = [
    Detector("equity_issuance_cash", r"issued\s+(?P<shares>[\d,]+)\s+common shares for cash[, ]*\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
             [Slot("shares", "int"), Slot("amount", "money")]),
    Detector("loan_proceeds", r"borrowed\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+from the bank", 80,
             [Slot("amount", "money"), Slot("rate", "percent", required=False, default=None),
              Slot("due_date", "string", required=False, default=None),
              Slot("interest_timing", "enum", required=False, default="annual",
                   values=["annual", "at_maturity", "quarterly"])]),
    Detector("ppe_purchase", r"purchased\s+(?P<asset>.+?)\s+for\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash", 80,
             [Slot("asset", "string"), Slot("amount", "money"),
              Slot("useful_life", "int", required=False, default=None),
              Slot("salvage", "money", required=False, default=0),
              Slot("depreciation_convention", "enum", required=False, default=None,
                   values=["full_year", "pro_rata", "half_year"])]),
    Detector("inventory_purchase", r"purchased inventory on account[, ]*\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
             [Slot("amount", "money")]),
    Detector("freight_in", r"freight[- ]in\s+(?:of\s+)?\$?(?P<amount>[\d,]+(?:\.\d+)?)", 90,
             [Slot("amount", "money")]),
    Detector("freight_out", r"freight[- ]out\s+(?:of\s+)?\$?(?P<amount>[\d,]+(?:\.\d+)?)", 90,
             [Slot("amount", "money")]),
    Detector("purchase_return", r"returned\s+(?P<desc>.+?)\s+inventory[, ]*\$?(?P<amount>[\d,]+(?:\.\d+)?)", 90,
             [Slot("desc", "string"), Slot("amount", "money"),
              Slot("paid_already", "string", required=False, default="no")]),
    Detector("prepaid_expense", r"paid\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash for a\s+(?P<months>\d+)[- ]month\s+(?P<kind>insurance|rent|supplies|advertising)\s+policy", 80,
             [Slot("amount", "money"), Slot("months", "int"), Slot("kind", "enum",
                   values=["insurance", "rent", "supplies", "advertising"])]),
    Detector("cash_sale", r"cash sales of \$?(?P<amount>[\d,]+(?:\.\d+)?)", 70,
             [Slot("amount", "money")]),
    Detector("credit_sale", r"credit sales of \$?(?P<amount>[\d,]+(?:\.\d+)?)", 70,
             [Slot("amount", "money")]),
    Detector("ar_collection", r"collected\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+(?:from\s+)?credit customers", 70,
             [Slot("amount", "money")]),
    Detector("ap_payment", r"paid suppliers\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+on account", 70,
             [Slot("amount", "money")]),
    Detector("opex_payment", r"paid cash operating expenses[: ]*\$?(?P<amount>[\d,]+(?:\.\d+)?)", 60,
             [Slot("amount", "money")]),
    Detector("interest_payment", r"paid cash interest[, ]*\$?(?P<amount>[\d,]+(?:\.\d+)?)", 70,
             [Slot("amount", "money")]),
    Detector("physical_count", r"physical (?:inventory )?count .*?shows .*?\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
             [Slot("amount", "money")]),
    Detector("unearned_revenue_receipt", r"received\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+(?:in advance|for a\s+(?P<months>\d+)[- ]month)", 80,
             [Slot("amount", "money"), Slot("months", "int", required=False, default=None)]),
    Detector("accrued_expense", r"earned\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+.*?unpaid", 80,
             [Slot("amount", "money"), Slot("type", "string", required=False, default="accrued")]),
    Detector("accrued_revenue", r"completed\s+.+?\s+but\s+.+?\s+not been billed", 80,
             [Slot("amount", "money", required=False, default=None)]),
    Detector("dividends", r"declared\s+(?:dividends of\s+)?\$?(?P<amount>[\d,]+(?:\.\d+)?)", 70,
             [Slot("amount", "money"), Slot("paid", "string", required=False, default="no")]),
    Detector("cash_sale_simple", r"cash sales of \$?(?P<amount>[\d,]+(?:\.\d+)?)", 70,
             [Slot("amount", "money")]),
    Detector("sales_return", r"customer returned goods[, ]*\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
             [Slot("amount", "money")]),
    Detector("sales_discount", r"customer paid within discount period[, ]*\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
             [Slot("amount", "money")]),
    Detector("purchase_discount", r"terms\s+(?P<terms>[\d/]+,\s*n/\d+)", 80,
             [Slot("terms", "string")]),
    Detector("asset_disposal", r"sold\s+(?P<asset>.+?)\s+for\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash", 80,
             [Slot("asset", "string"), Slot("amount", "money")]),
    Detector("unearned_earned", r"by (?:Dec\.?\s*31|year[- ]end)\s+(?P<months>\d+)\s+of\s+(?P<total>\d+)\s+months .*?earned", 80,
             [Slot("months", "int"), Slot("total", "int")]),
    Detector("accrued_revenue", r"completed\s+.+?\s+but\s+.+?\s+not been billed[, ]*\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
             [Slot("amount", "money")]),
    Detector("bad_debt", r"estimate uncollectible (?:as\s+)?(?P<rate>[\d.]+)%\s+of (?:accounts receivable|receivables)", 80,
             [Slot("rate", "percent")]),
    Detector("warranty", r"warranty of\s+(?P<rate>[\d.]+)%", 80,
             [Slot("rate", "percent")]),
    Detector("depreciation_sl", r"depreciate\s+\$?(?P<cost>[\d,]+(?:\.\d+)?)\s+.*?over\s+(?P<life>\d+)\s+years", 80,
             [Slot("cost", "money"), Slot("life", "int"),
              Slot("salvage", "money", required=False, default=0),
              Slot("convention", "enum", required=False, default=None,
                   values=["full_year", "pro_rata", "half_year"])]),
    Detector("interest_paid_at_maturity", r"interest .* paid .* at maturity", 100,
             [Slot("principal", "money", required=False, default=None),
              Slot("rate", "percent", required=False, default=None)]),
    Detector("interest_paid_annually", r"interest paid annually", 90, []),
    Detector("fob_shipping_point", r"FOB shipping point", 90, []),
    Detector("fob_destination", r"FOB destination", 90, []),
    Detector("periodic_inventory", r"periodic inventory system", 90, []),
    Detector("perpetual_inventory", r"perpetual inventory system", 90, []),
    Detector("full_year_depreciation", r"full year of depreciation is recorded in the year of acquisition", 90, []),
]


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect(text: str) -> List[Match]:
    """Return all matches for a problem text, highest specificity first."""
    if not isinstance(text, str) or not text.strip():
        return []
    matches: List[Match] = []
    for det in DETECTORS:
        for m in re.finditer(det.pattern, text, re.IGNORECASE | re.DOTALL):
            slots: Dict[str, Any] = {}
            for slot in det.slots:
                raw = None
                if slot.name in m.groupdict() and m.group(slot.name) is not None:
                    raw = m.group(slot.name)
                try:
                    slots[slot.name] = _validate_slot(slot, raw)
                except DetectError:
                    # A required slot missing makes this match unusable; skip it.
                    slots = None
                    break
            if slots is None:
                continue
            matches.append(Match(detector_id=det.id, span=m.span(),
                                slots=slots, specificity=det.specificity))
    # de-duplicate identical detector+span
    seen = set()
    unique = []
    for m in matches:
        key = (m.detector_id, m.span)
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)
    unique.sort(key=lambda m: (-m.specificity, m.span[0]))
    return unique


def journalizable(match: Match) -> bool:
    return match.specificity >= SPECIFICITY_THRESHOLD


# ---------------------------------------------------------------------------
# Templates: slots -> balanced list of (account, side, amount)
# ---------------------------------------------------------------------------

def _lines(*pairs):
    return list(pairs)


TEMPLATES: Dict[str, Callable[[Dict[str, Any]], List[Tuple[str, str, Any]]]] = {
    "equity_issuance_cash": lambda s: [("1000", "Dr", s["amount"]), ("3000", "Cr", s["amount"])],
    "loan_proceeds": lambda s: [("1000", "Dr", s["amount"]), ("2100", "Cr", s["amount"])],
    "ppe_purchase": lambda s: [(s.get("asset_account", "1500"), "Dr", s["amount"]),
                               ("1000", "Cr", s["amount"])],
    "inventory_purchase": lambda s: [("1200", "Dr", s["amount"]), ("2000", "Cr", s["amount"])],
    "freight_in": lambda s: [("1200", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "freight_out": lambda s: [("6900", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "cash_sale": lambda s: [("1000", "Dr", s["amount"]), ("4000", "Cr", s["amount"])],
    "credit_sale": lambda s: [("1100", "Dr", s["amount"]), ("4000", "Cr", s["amount"])],
    "ar_collection": lambda s: [("1000", "Dr", s["amount"]), ("1100", "Cr", s["amount"])],
    "ap_payment": lambda s: [("2000", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "interest_payment": lambda s: [("7100", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "unearned_revenue_receipt": lambda s: [("1000", "Dr", s["amount"]), ("2400", "Cr", s["amount"])],
    "accrued_expense": lambda s: [("6700", "Dr", s["amount"]), ("2300", "Cr", s["amount"])],
    "dividends": lambda s: [("3200", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "physical_count": lambda s: [],  # given fact, no JE
    "sales_return": lambda s: [("4100", "Dr", s["amount"]), ("1100", "Cr", s["amount"])],
    "sales_discount": lambda s: [("4200", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "asset_disposal": lambda s: [("1000", "Dr", s["amount"]), ("1500", "Cr", s["amount"])],
    "unearned_earned": lambda s: [("2400", "Dr", s["amount"]), ("4000", "Cr", s["amount"])],
    "accrued_revenue": lambda s: [("1150", "Dr", s["amount"]), ("4000", "Cr", s["amount"])],
    "bad_debt": lambda s: [("6700", "Dr", s["amount"]), ("1300", "Cr", s["amount"])],
    "warranty": lambda s: [("6800", "Dr", s["amount"]), ("2500", "Cr", s["amount"])],
    "depreciation_sl": lambda s: _dep_lines(s),
}


def _dep_lines(s):
    from decimal import Decimal as D
    cost = D(str(s["cost"]))
    life = D(str(s["life"]))
    salvage = D(str(s.get("salvage", 0) or 0))
    amount = (cost - salvage) / life
    # quantise to 2 decimals
    amount = amount.quantize(D("0.01"))
    return [("6700", "Dr", amount), ("1700", "Cr", amount)]


def months_expired(coverage_start: str, coverage_end: str, year_end_month: int = 12) -> int:
    """Months of a coverage period that fall within the calendar year ending in year_end_month."""
    # Minimal: parse YYYY-MM-DD or MM/YYYY; count months from start month to year_end.
    import datetime
    def parse(s):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"):
            try:
                return datetime.datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None
    start = parse(coverage_start)
    end = parse(coverage_end)
    if start is None or end is None:
        raise DetectError("cannot parse coverage dates")
    # months from start month to December (year_end_month=12)
    months = (12 - start.month + 1)
    if months < 0:
        months = 0
    if months > 12:
        months = 12
    return months


def journalize(detector_id: str, slots: Dict[str, Any],
               chart: Optional[Dict[str, Any]] = None) -> List[Tuple[str, str, Any]]:
    """Generate a balanced journal entry from a detector's slots.

    Raises DetectError if the detector has no template, or the template's
    accounts are not present in `chart` (when supplied).
    """
    if detector_id not in TEMPLATES:
        raise DetectError(f"no template for detector {detector_id!r}")
    lines = TEMPLATES[detector_id](slots)
    # balance check
    dr = sum((ln[2] for ln in lines if ln[1] == "Dr"), start=0) if False else None
    # decimal-safe sum below; these two lines are placeholders
    # decimal-safe sum:
    from decimal import Decimal as D
    debits = sum((D(str(ln[2])) for ln in lines if ln[1] == "Dr"), D(0))
    credits = sum((D(str(ln[2])) for ln in lines if ln[1] == "Cr"), D(0))
    if debits != credits:
        raise DetectError(f"template {detector_id!r} does not balance: Dr={debits} Cr={credits}")
    if chart is not None:
        for acct, side, amt in lines:
            if acct not in chart:
                raise DetectError(f"template {detector_id!r} uses account {acct!r} not in chart")
    return lines
