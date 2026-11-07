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
    Detector("capital_contribution", r"(?:started|began|opened)\s+(?:the\s+)?business\s+with\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash|owner\s+(?:invested|contributed)\s+\$?(?P<amount2>[\d,]+(?:\.\d+)?)\s+cash", 85,
             [Slot("amount", "money", required=False, default=None),
              Slot("amount2", "money", required=False, default=None)]),
    Detector("equity_issuance_cash", r"(?:invested|issued)\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash\s+(?:in\s+the\s+business\s+)?(?:(?:in\s+exchange\s+|)for\s+)?(?:common\s+)?(?:shares?|stock)|(?:issued|invested)\s+(?P<shares>[\d,]+)?\s*(?:common\s+)?(?:shares?|stock)\s*(?:for\s+)?cash[, ]*\$?(?P<amount2>[\d,]+(?:\.\d+)?)", 80,
             [Slot("shares", "int", required=False, default=None), Slot("amount", "money", required=False, default=None),
              Slot("amount2", "money", required=False, default=None)]),
    Detector("loan_proceeds", r"borrowed\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+from the bank", 80,
             [Slot("amount", "money"), Slot("rate", "percent", required=False, default=None),
              Slot("due_date", "string", required=False, default=None),
              Slot("interest_timing", "enum", required=False, default="annual",
                   values=["annual", "at_maturity", "quarterly"])]),
    Detector("ppe_purchase", r"(?:purchased|bought)\s+(?P<asset>.+?)\s+for\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash", 80,
             [Slot("asset", "string"), Slot("amount", "money"),
              Slot("useful_life", "int", required=False, default=None),
              Slot("salvage", "money", required=False, default=0),
              Slot("depreciation_convention", "enum", required=False, default=None,
                   values=["full_year", "pro_rata", "half_year"])]),
    Detector("inventory_purchase", r"purchased\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+of\s+(?:inventory|supplies)\s+on account|purchased\s+(?:inventory|supplies)\s+on account[, ]*\$?(?P<amount2>[\d,]+(?:\.\d+)?)", 80,
             [Slot("amount", "money", required=False, default=None), Slot("amount2", "money", required=False, default=None)]),
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
    Detector("cash_sale", r"(?:cash sales of\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)|earned\s+\$?(?P<amount2>[\d,]+(?:\.\d+)?)\s+cash sales)", 70,
             [Slot("amount", "money", required=False), Slot("amount2", "money", required=False)]),
    Detector("goods_sale_cash", r"sold\s+(?:goods|merchandise|inventory|stock)\s+for\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash", 85,
             [Slot("amount", "money")]),
    Detector("credit_sale", r"(?:credit sales|provided services on account|services on account|sales on account)[:,]?\s*(?:of\s+)?\$?(?P<amount>[\d,]+(?:\.\d+)?)", 70,
             [Slot("amount", "money")]),
    Detector("ar_collection", r"collected\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+(?:cash\s+)?(?:from\s+)?(?:credit )?customers", 70,
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
    Detector("accrued_expense", r"earned\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+[^.;]*?unpaid", 80,
             [Slot("amount", "money"), Slot("type", "string", required=False, default="accrued")]),
    Detector("accrued_revenue", r"completed\s+.+?\s+but\s+.+?\s+not been billed", 80,
             [Slot("amount", "money", required=False, default=None)]),
    Detector("dividends", r"(?:paid\s+a\s+)?\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash\s+(?:dividend|dividends)|(?:declared\s+)?(?:cash\s+)?(?:dividend|dividends)(?:\s+of\s+)?\$?(?P<amount2>[\d,]+(?:\.\d+)?)", 70,
             [Slot("amount", "money", required=False, default=None), Slot("paid", "string", required=False, default="yes"),
              Slot("amount2", "money", required=False, default=None)]),
    Detector("sales_return", r"customer returned goods[, ]*\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
             [Slot("amount", "money")]),
    Detector("sales_discount", r"customer paid within discount period[, ]*\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
             [Slot("amount", "money")]),
    Detector("purchase_discount", r"terms\s+(?P<terms>[\d/]+,\s*n/\d+)", 80,
             [Slot("terms", "string")]),
    Detector("asset_disposal", r"sold\s+(?P<asset>equipment|machine|machinery|vehicle|land|building|furniture|fixture|plant|asset)\s+for\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash", 80,
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
    Detector("rent_payment", r"paid\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+(?:cash\s+)?(?:for\s+)?(?:january\s+)?rent", 80,
             [Slot("amount", "money")]),
    Detector("rent_payment2", r"paid\s+rent(?:\s+of)?\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
             [Slot("amount", "money")]),
    Detector("utilities_payment", r"paid\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash (?:for\s+)?utilities", 80,
             [Slot("amount", "money")]),
    Detector("salaries_payment", r"(?:incurred\s+)?\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+in\s+salaries?\s+expense,?\s+paid\s+in\s+cash|paid\s+\$?(?P<amount2>[\d,]+(?:\.\d+)?)\s+cash\s+salaries?", 80,
             [Slot("amount", "money", required=False, default=None), Slot("amount2", "money", required=False, default=None)]),
    Detector("bonus_issue", r"bonus\s+issue\s+1-for-(\d+)", 90,
             [Slot("ratio", "int")]),
    Detector("share_options", r"share options?\s+(\d+)\s+with exercise price\s+\$?([\d,]+(?:\.\d+)?)\s+and average market price\s+\$?([\d,]+(?:\.\d+)?)", 90,
             [Slot("count", "int"), Slot("exercise_price", "money"), Slot("market_price", "money")]),
    Detector("convertible_bonds", r"convertible bonds?\s+([\d,]+(?:\.\d+)?)\s+at\s+([\d,]+(?:\.\d+)?)%[,\s]*\s*convertible into\s+(\d+)\s+ordinary shares?", 90,
             [Slot("face_value", "money"), Slot("rate", "percent"), Slot("shares", "int")]),
    Detector("preference_dividends", r"preference dividends?\s+\$?([\d,]+(?:\.\d+)?)", 90,
             [Slot("amount", "money")]),
    Detector("profit_from_continuing_operations", r"profit from continuing operations\s+\$?([\d,]+(?:\.\d+)?)", 90,
             [Slot("amount", "money")]),
    Detector("loss_from_discontinued_operations", r"loss from discontinued operations\s+\$?([\d,]+(?:\.\d+)?)", 90,
             [Slot("amount", "money")]),
    Detector("equity_issuance_cash2", r"issued\s+(?:common\s+)?(?:shares?|stock)\s+for\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash", 80,
              [Slot("amount", "money")]),
    Detector("billed_clients", r"billed\s+(?:clients|customers)\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
              [Slot("amount", "money")]),
    Detector("ar_collection_clients", r"collected\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash\s+from\s+(?:clients|customers)", 80,
              [Slot("amount", "money")]),
    Detector("ar_writeoff", r"wrote\s+off\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+of\s+accounts\s+receivable", 80,
              [Slot("amount", "money")]),
    Detector("accrued_expense2", r"\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+of\s+\w+\s+had been earned but unpaid", 80,
              [Slot("amount", "money")]),
    Detector("allowance_estimate", r"allowance for doubtful accounts.*?estimated at\s+(?P<rate>[\d.]+)%\s+of", 80,
              [Slot("rate", "percent")]),
    Detector("prepaid_expense2", r"paid\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash\s+on\s+[^;]*?for\s+a\s+(?P<months>\d+)[- ]month\s+(?P<kind>insurance|rent|supplies|advertising)\s+policy", 80,
              [Slot("amount", "money"), Slot("months", "int"), Slot("kind", "enum",
                    values=["insurance", "rent", "supplies", "advertising"])]),
    Detector("salaries_payment2", r"paid\s+wages\s+of\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash", 80,
              [Slot("amount", "money")]),
    Detector("utilities_payment2", r"paid\s+utilities\s+of\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash", 80,
              [Slot("amount", "money")]),
    Detector("unearned_revenue_receipt2", r"received\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+cash\s+from\s+a\s+customer\s+for\s+services", 80,
              [Slot("amount", "money")]),
    Detector("loan_proceeds2", r"borrowed\s+\$?(?P<amount>[\d,]+(?:\.\d+)?)\s+on\s+[^;]*?with\s+a?\s*[\d.]+%\s+note", 80,
              [Slot("amount", "money")]),
    Detector("dividends2", r"dividends\s+paid[:\s]+\$?(?P<amount>[\d,]+(?:\.\d+)?)", 80,
              [Slot("amount", "money")]),
]


# ---------------------------------------------------------------------------
# Claim parsing (tip 9.2): split a problem into atomic claims
# ---------------------------------------------------------------------------


@dataclass
class Claim:
    id: str
    text: str
    kind: str  # transaction | adjustment_info | policy | given_fact
    span: Tuple[int, int]


_POLICY_PHRASES = (
    "full year of depreciation", "interest paid annually", "interest is paid in full at maturity",
    "periodic inventory system", "perpetual inventory system", "FOB shipping point",
    "FOB destination", "tax rate", "no dividends", "gross method", "net method",
)
_GIVEN_FACT_PHRASES = (
    "physical inventory count", "ending inventory", "tax rate is", "beginning inventory",
    "residual value", "useful life",
)
_ADJUSTMENT_PHRASES = (
    "record depreciation", "record adjusting", "accrued", "prepaid", "amortize",
    "depreciate", "year-end adjustment",
)


def parse_claims(text: str) -> List[Claim]:
    if not isinstance(text, str) or not text.strip():
        return []
    # split on sentence boundaries
    spans = []
    for m in re.finditer(r"[^.!?]+[.!?]?", text):
        seg = m.group(0).strip()
        if not seg:
            continue
        spans.append((seg, m.span()))
    claims: List[Claim] = []
    for i, (seg, sp) in enumerate(spans, start=1):
        low = seg.lower()
        if any(p in low for p in _POLICY_PHRASES):
            kind = "policy"
        elif any(p in low for p in _GIVEN_FACT_PHRASES):
            kind = "given_fact"
        elif any(p in low for p in _ADJUSTMENT_PHRASES):
            kind = "adjustment_info"
        else:
            kind = "transaction"
        claims.append(Claim(id=f"C{i}", text=seg, kind=kind, span=sp))
    return claims


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


def _amount(slots: Dict[str, Any], *names: str):
    """The figure a detection carries.

    Some detectors read the amount from one of two wordings - "incurred 8,000 in
    salaries expense, paid in cash" and "paid 8,000 cash salaries" - and the wording
    that matched decides which slot holds it.  A template that reached for the first
    slot alone posted a journal entry with no amount at all, and the posting died on
    a conversion error instead of being named and skipped.  The slot that is filled
    wins.
    """
    for name in names:
        value = slots.get(name)
        if value is not None:
            return value
    raise DetectError("the detection carries no amount")


def _simple_entry(dr_account: str, cr_account: str, slots: Dict[str, Any], *amount_slots: str):
    """A balanced two-line journal entry, using whichever amount slot was filled."""
    amount = _amount(slots, *amount_slots)
    return [(dr_account, "Dr", amount), (cr_account, "Cr", amount)]


TEMPLATES: Dict[str, Callable[[Dict[str, Any]], List[Tuple[str, str, Any]]]] = {
    "equity_issuance_cash": lambda s: _simple_entry("1000", "3000", s, "amount", "amount2"),
    "loan_proceeds": lambda s: [("1000", "Dr", s["amount"]), ("2100", "Cr", s["amount"])],
    "ppe_purchase": lambda s: [(s.get("asset_account", "1500"), "Dr", s["amount"]),
                               ("1000", "Cr", s["amount"])],
    "inventory_purchase": lambda s: _simple_entry("1200", "2000", s, "amount", "amount2"),
    "freight_in": lambda s: [("1200", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "freight_out": lambda s: [("6900", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "cash_sale": lambda s: [("1000", "Dr", _amount(s, "amount", "amount2")), ("4000", "Cr", _amount(s, "amount", "amount2"))],
    "credit_sale": lambda s: [("1100", "Dr", s["amount"]), ("4000", "Cr", s["amount"])],
    "ar_collection": lambda s: [("1000", "Dr", s["amount"]), ("1100", "Cr", s["amount"])],
    "ap_payment": lambda s: [("2000", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "interest_payment": lambda s: [("7100", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "unearned_revenue_receipt": lambda s: [("1000", "Dr", s["amount"]), ("2400", "Cr", s["amount"])],
    "accrued_expense": lambda s: [("6700", "Dr", s["amount"]), ("2300", "Cr", s["amount"])],
    "accrued_expense2": lambda s: [("6100", "Dr", s["amount"]), ("2300", "Cr", s["amount"])],
    "dividends": lambda s: _simple_entry("3200", "1000", s, "amount", "amount2"),
    "equity_issuance_cash2": lambda s: _simple_entry("1000", "3000", s, "amount"),
    "billed_clients": lambda s: [("1100", "Dr", s["amount"]), ("4000", "Cr", s["amount"])],
    "ar_collection_clients": lambda s: [("1000", "Dr", s["amount"]), ("1100", "Cr", s["amount"])],
    "ar_writeoff": lambda s: [("1310", "Dr", s["amount"]), ("1100", "Cr", s["amount"])],
    "allowance_estimate": lambda s: [],
    "prepaid_expense2": lambda s: [("1300", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "salaries_payment2": lambda s: [("6100", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "utilities_payment2": lambda s: [("6250", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "unearned_revenue_receipt2": lambda s: [("1000", "Dr", s["amount"]), ("2400", "Cr", s["amount"])],
    "loan_proceeds2": lambda s: [("1000", "Dr", s["amount"]), ("2100", "Cr", s["amount"])],
    "dividends2": lambda s: [("3200", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "physical_count": lambda s: [],  # given fact, no JE
    "capital_contribution": lambda s: [("1000", "Dr", s.get("amount") or s.get("amount2")),
                                       ("3000", "Cr", s.get("amount") or s.get("amount2"))],
    "goods_sale_cash": lambda s: [("1000", "Dr", s["amount"]), ("4000", "Cr", s["amount"])],
    "sales_return": lambda s: [("4100", "Dr", s["amount"]), ("1100", "Cr", s["amount"])],
    "sales_discount": lambda s: [("4200", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "asset_disposal": lambda s: [("1000", "Dr", s["amount"]), ("1500", "Cr", s["amount"])],
    "unearned_earned": lambda s: [("2400", "Dr", s["amount"]), ("4000", "Cr", s["amount"])],
    "accrued_revenue": lambda s: [("1150", "Dr", s["amount"]), ("4000", "Cr", s["amount"])],
    "bad_debt": lambda s: [("6700", "Dr", s["amount"]), ("1310", "Cr", s["amount"])],
    "warranty": lambda s: [("6800", "Dr", s["amount"]), ("2500", "Cr", s["amount"])],
    "depreciation_sl": lambda s: _dep_lines(s),
    "rent_payment": lambda s: [("6200", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "rent_payment2": lambda s: [("6200", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "utilities_payment": lambda s: [("6250", "Dr", s["amount"]), ("1000", "Cr", s["amount"])],
    "salaries_payment": lambda s: _simple_entry("6100", "1000", s, "amount", "amount2"),
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


# ---------------------------------------------------------------------------
# Policy inference (tip 9.4)
# ---------------------------------------------------------------------------


POLICY_INFERENCE = [
    (r"full year of depreciation is recorded in the year of acquisition",
     "depreciation.convention", "full_year"),
    (r"interest paid annually", "interest.timing", "annual"),
    (r"interest .* paid .* at maturity", "interest.timing", "at_maturity"),
    (r"periodic inventory system", "inventory.system", "periodic"),
    (r"perpetual inventory system", "inventory.system", "perpetual"),
    (r"FOB shipping point", "freight.responsibility", "buyer"),
    (r"FOB destination", "freight.responsibility", "seller"),
    (r"gross method", "purchase_discount.method", "gross"),
    (r"net method", "purchase_discount.method", "net"),
]


def infer_policies(text: str) -> dict:
    """Return {policy_key: value} inferred from explicit phrases in the text."""
    out = {}
    conflicts = []
    by_key = {}
    for pattern, key, value in POLICY_INFERENCE:
        if re.search(pattern, text, re.IGNORECASE):
            if key in by_key and by_key[key] != value:
                conflicts.append((key, by_key[key], value))
            by_key[key] = value
            out[key] = value
    return out


def policy_conflicts(text: str) -> list:
    """Return list of (policy_key, value_a, value_b) for contradictory phrases."""
    by_key = {}
    conflicts = []
    for pattern, key, value in POLICY_INFERENCE:
        if re.search(pattern, text, re.IGNORECASE):
            if key in by_key and by_key[key] != value:
                conflicts.append((key, by_key[key], value))
            by_key[key] = value
    return conflicts


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
    # A line with no amount is a gap, and a gap is named rather than posted.
    # It must not reach the decimal sums below: a missing figure there raised a
    # conversion error that nothing in the tile could catch, so the whole answer
    # died instead of this one entry being skipped.
    for acct, side, amt in lines:
        if amt is None:
            raise DetectError(f"template {detector_id!r} has a line with no amount")
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
