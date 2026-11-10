"""Optional model-written commentary for the Portfolio Lab report.

The model is an editor, never an analyst: it may interpret the stored figures
and the student's own words, and it may not add a number, a fact, a source or
advice.  Every paragraph is checked against the stored record before it is
offered, and again before it can reach the report.

The student owns the text: the model proposes, the student edits or discards.
"""

from __future__ import annotations

import datetime
import re

from . import prose

#: A number in the text: optional thousands separators, optional decimals,
#: optional percent sign.
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?%?")

#: Advice the product refuses in a portfolio commentary.
ADVICE = re.compile(
    r"\b(buy|sell|bought|sold|recommend\w*|advise\w*|suggest\w*|should|must|"
    r"target price|price target|top pick|best stock|attractive|overweight|underweight|"
    r"outperform\w*|underperform\w*|will rise|will fall|guaranteed\w*)\b", re.I)

#: A link, a DOI or a template placeholder.
LINK = re.compile(r"https?://|www\.|doi:|@", re.I)
TEMPLATE = re.compile(r"\[(your|insert|name)\b|\{\{|\}\}|TBD|TODO|XXX", re.I)

MAX_WORDS = 220


class CommentaryRejected(ValueError):
    """The commentary broke a rule of the product."""


# ---------------------------------------------------------------- context

def _numbers_in(value):
    """Every number a stored figure carries, as plain decimal strings."""
    out = set()
    text = str(value if value is not None else "")
    for token in NUMBER.findall(text):
        plain = token.replace(",", "").rstrip("%")
        if not plain:
            continue
        try:
            number = float(plain)
        except ValueError:
            continue
        out.add(_key(number))
        # the same figure may be written as a percentage
        if number == number and abs(number) <= 1:
            out.add(_key(number * 100.0))
            out.add(_key(round(number * 100.0, 2)))
    return out


def _key(number):
    try:
        return "%.6f" % float(number)
    except (TypeError, ValueError):
        return ""


def build_context(snapshot, selection=None, holdings=None):
    """The stored record, as the model is allowed to see it.

    Only what the portfolio already holds: the figures the frozen core produced,
    the prices with their source and date, the selection record and the
    student's own rationale lines.
    """
    snapshot = snapshot or {}
    outputs = snapshot.get("outputs") or {}
    positions = snapshot.get("positions") or []
    prices = snapshot.get("prices") or {}
    figures = {}
    for key, value in outputs.items():
        figures[str(key)] = str(value)
    rows = []
    for position in positions:
        rows.append({str(key): str(value) for key, value in position.items()})
    price_rows = {}
    for symbol, point in (prices or {}).items():
        price_rows[str(symbol)] = {str(k): str(v) for k, v in (point or {}).items()}
    held = {}
    for row in holdings or []:
        symbol = str(row.get("symbol") or "").upper()
        rationale = row.get("rationale")
        if isinstance(rationale, dict):
            rationale = rationale.get("thesis") or ""
        held[symbol] = {"rationale": str(rationale or "")}
    context = {
        "date": str(snapshot.get("date") or ""),
        "currency": str(snapshot.get("currency") or ""),
        "figures": figures,
        "positions": rows,
        "prices": price_rows,
        "holdings": held,
        "selection": selection or {},
    }
    return context


def allowed_numbers(context):
    """Every number the commentary may quote, as decimal strings."""
    allowed = set()
    context = context or {}
    for value in (context.get("figures") or {}).values():
        allowed |= _numbers_in(value)
    for row in context.get("positions") or []:
        for value in row.values():
            allowed |= _numbers_in(value)
    for point in (context.get("prices") or {}).values():
        for value in (point or {}).values():
            allowed |= _numbers_in(value)
    for row in (context.get("selection") or {}).get("rows") or []:
        for value in (row.get("values") or {}).values():
            allowed |= _numbers_in(value)
        allowed |= _numbers_in(row.get("reason"))
    for value in (context.get("holdings") or {}).values():
        allowed |= _numbers_in(value.get("rationale"))
    # the date and its parts are stored, so a year is not an invented number
    day = str(context.get("date") or "")
    if day:
        allowed |= _numbers_in(day)
        for part in day.split("-"):
            allowed |= _numbers_in(part)
    return {value for value in allowed if value}


def _quoted_numbers(text):
    out = set()
    for token in NUMBER.findall(str(text or "")):
        plain = token.replace(",", "").rstrip("%")
        if not plain:
            continue
        try:
            number = float(plain)
        except ValueError:
            continue
        out.add(_key(number))
        if token.endswith("%"):
            out.add(_key(number / 100.0))
    return out


# ---------------------------------------------------------------- guard

def audit(text, context):
    """Raise CommentaryRejected unless the text stays inside the record."""
    text = str(text or "").strip()
    if not text:
        raise CommentaryRejected("the commentary is empty")
    if len(text.split()) > MAX_WORDS:
        raise CommentaryRejected("the commentary is longer than %d words" % MAX_WORDS)
    if LINK.search(text):
        raise CommentaryRejected("the commentary introduced a link")
    if TEMPLATE.search(text):
        raise CommentaryRejected("the commentary contains template text")
    if ADVICE.search(text):
        raise CommentaryRejected("the commentary gives advice")
    allowed = allowed_numbers(context)
    unknown = sorted(value for value in _quoted_numbers(text) if value not in allowed)
    if unknown:
        raise CommentaryRejected(
            "the commentary used a figure that is not in the record: " + ", ".join(unknown))
    return text


# ---------------------------------------------------------------- model

def draft(context, timeout=60):
    """Ask the model for one paragraph.  Nothing is stored here."""
    if not prose.available():
        raise CommentaryRejected(
            "no language model is connected, so no commentary can be written. "
            "Write your own paragraph instead; the report accepts your words as they are.")
    try:
        text = prose.propose_portfolio_paragraph(context, timeout=timeout)
    except prose.ProseError as error:
        raise CommentaryRejected(
            "The model could not write a draft (%s). Write your own paragraph instead; "
            "the report accepts your words as they are." % str(error)[:120])
    audit(text, context)
    return {"text": text, "status": "proposed",
            "model": prose.model_id(),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}


def confirm(text, context):
    """The student's edited text, checked and ready for the report."""
    cleaned = audit(text, context)
    return {"text": cleaned, "status": "confirmed",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
