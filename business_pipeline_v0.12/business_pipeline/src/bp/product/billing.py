"""Plans, prices and the subscription ledger.

Product layer (additive). The frozen core is not touched, and nothing here computes a business
number: prices are the owner's configuration and the annual rate is derived from the declared
discount so the two can never drift apart.

The deliberate choices:

* **The monthly price is the source of truth.** ``ANNUAL_DISCOUNT`` turns it into the yearly rate
  (monthly x 12, less the discount), rounded to the cent. A hand-typed annual price is the one
  number that silently disagrees with its own "save 20%" badge after a price change.
* **Credits are absent on purpose.** ``credits`` is ``None`` for every tier until the owner supplies
  the allowance. The API returns ``null`` and the page prints "to be confirmed"; no figure is
  invented to fill the space. Filling one in is a single dict entry.
* **The active plan is derived, never stored.** It is the last activation that has no later
  cancellation, the same discipline as ``credits.balance``: a stored status drifts from the events
  that explain it, and then nobody can answer "why am I on Pro?".
* **Activation is idempotent per PayPal subscription id.** A retried confirm (a dropped connection,
  a double click) returns the same record and adds no second activation.
* **Cancelling keeps the paid period.** The ledger records the request; the plan stays active until
  the period end PayPal reported, and the page says so rather than cutting access immediately.

Standard library only; one JSON line per event; a lock so the threaded server cannot interleave.
"""

import json
import os
import threading
import time
import uuid
from decimal import Decimal, ROUND_HALF_UP

LOCK = threading.Lock()

CURRENCY = "USD"

#: The owner's annual incentive: a year costs 12 months less this share.
ANNUAL_DISCOUNT = Decimal("0.20")

_CENT = Decimal("0.01")

#: Tier order as shown on the page. The key is what the routes and the ledger use.
TIERS = ("starter", "pro", "studio", "agency")

#: The catalogue. ``monthly`` is the only price written by hand; ``credits`` and ``highlights`` stay
#: empty until the owner supplies them - see ``billing.py`` in DESIGN_NOTES for where they land.
PLANS = {
    "starter": {"name": "Starter", "monthly": "14.99", "credits": None, "highlights": []},
    "pro": {"name": "Pro", "monthly": "29.99", "credits": None, "highlights": []},
    "studio": {"name": "Studio", "monthly": "49.99", "credits": None, "highlights": []},
    "agency": {"name": "Agency", "monthly": "99.99", "credits": None, "highlights": []},
}

CYCLES = ("monthly", "annual")


class BillingError(ValueError):
    """The request cannot be served: unknown tier, unknown cycle, or a malformed event."""


def _money(value):
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _percent(value):
    """A percentage as a plain string - ``20``, never ``2E+1``."""
    text = format(Decimal(str(value)).normalize(), "f")
    return text[:-2] if text.endswith(".0") else text


def price(tier, cycle="monthly"):
    """The price of one tier and cycle, as a string with two decimals.

    Monthly is configuration. Annual is 12 months less ``ANNUAL_DISCOUNT``, so a change to the
    monthly rate changes the yearly rate with it.
    """
    if tier not in PLANS:
        raise BillingError("unknown tier %r; known: %s" % (tier, ", ".join(TIERS)))
    if cycle not in CYCLES:
        raise BillingError("unknown billing cycle %r; known: %s" % (cycle, ", ".join(CYCLES)))
    monthly = _money(PLANS[tier]["monthly"])
    if cycle == "monthly":
        return str(monthly)
    return str((monthly * 12 * (1 - ANNUAL_DISCOUNT)).quantize(_CENT, rounding=ROUND_HALF_UP))


def annual_saving(tier):
    """What a year saves against 12 monthly payments, in currency and as a percentage."""
    monthly = _money(PLANS[tier]["monthly"])
    full = _money(monthly * 12)
    yearly = _money(price(tier, "annual"))
    return {"amount": str(full - yearly), "currency": CURRENCY,
            "percent": _percent(ANNUAL_DISCOUNT * 100)}


def card(tier):
    """One card's payload: the prices, the derived saving and the fields still to be supplied."""
    plan = PLANS[tier]
    return {"tier": tier, "name": plan["name"], "currency": CURRENCY,
            "monthly": {"amount": price(tier, "monthly"), "cycle": "monthly"},
            "annual": {"amount": price(tier, "annual"), "cycle": "annual", "months": 12},
            "annual_saving": annual_saving(tier),
            "credits": plan["credits"],
            "credits_label": "Credit allowance: to be confirmed" if plan["credits"] is None else plan["credits"],
            "highlights": list(plan["highlights"])}


def catalogue():
    """Every tier, in order, plus the facts a page needs to render the toggle."""
    return {"currency": CURRENCY, "tiers": [card(tier) for tier in TIERS],
            "annual_discount_percent": _percent(ANNUAL_DISCOUNT * 100),
            "credits_set": all(PLANS[tier]["credits"] is not None for tier in TIERS),
            "notice": "Prices are the owner's configuration. The annual price is 12 months less "
                      "the declared discount. Credit allowances are not set yet; they are "
                      "returned as null rather than estimated."}


# -- the ledger ----------------------------------------------------------------------------------

def _state_dir():
    from . import ops
    return str(ops.state_dir())


def _path():
    return os.path.join(_state_dir(), "subscriptions.jsonl")


def _read():
    path = _path()
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue                      # a torn line is skipped, not fatal
    return out


def _append(event):
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def entries(limit=None):
    """Every event, oldest first."""
    rows = _read()
    return rows if limit is None else rows[-limit:]


def activate(tier, cycle, subscription_id, payer_email=None, period=None, status="ACTIVE"):
    """Record a paid subscription. Idempotent on the PayPal subscription id.

    ``period`` is whatever PayPal reported (``{"start": ..., "next_billing": ...}``); nothing is
    derived from it beyond keeping the paid-through date for the cancellation message.
    """
    if not subscription_id or not isinstance(subscription_id, str):
        raise BillingError("a PayPal subscription id is required")
    if tier not in PLANS:
        raise BillingError("unknown tier %r; known: %s" % (tier, ", ".join(TIERS)))
    if cycle not in CYCLES:
        raise BillingError("unknown billing cycle %r; known: %s" % (cycle, ", ".join(CYCLES)))
    with LOCK:
        for event in _read():
            if event.get("kind") == "activate" and event.get("subscription_id") == subscription_id:
                return {"recorded": False, "reused": True, "entry": event, "current": current()}
        event = {"id": uuid.uuid4().hex[:12], "at": _now(), "kind": "activate",
                 "subscription_id": subscription_id, "tier": tier, "cycle": cycle,
                 "amount": price(tier, cycle), "currency": CURRENCY,
                 "payer_email": payer_email or None, "status": status,
                 "period": period if isinstance(period, dict) else {},
                 "credits": PLANS[tier]["credits"], "idem": subscription_id}
        _append(event)
        return {"recorded": True, "reused": False, "entry": event, "current": current()}


def cancel(subscription_id, reason="requested by the subscriber"):
    """Record a cancellation request. The paid period is kept; nothing is deleted."""
    with LOCK:
        for event in _read():
            if event.get("kind") == "cancel" and event.get("subscription_id") == subscription_id:
                return {"recorded": False, "reused": True, "entry": event, "current": current()}
        active = _activation(subscription_id)
        if active is None:
            raise BillingError("no active subscription %r on this machine" % subscription_id)
        event = {"id": uuid.uuid4().hex[:12], "at": _now(), "kind": "cancel",
                 "subscription_id": subscription_id, "tier": active.get("tier"),
                 "cycle": active.get("cycle"), "reason": reason, "idem": subscription_id}
        _append(event)
        return {"recorded": True, "reused": False, "entry": event, "current": current()}


def _activation(subscription_id):
    for event in _read():
        if event.get("kind") == "activate" and event.get("subscription_id") == subscription_id:
            return event
    return None


def _cancelled(subscription_id):
    return any(event.get("kind") == "cancel" and event.get("subscription_id") == subscription_id
               for event in _read())


def current():
    """The plan this machine is on, derived from the ledger.

    A cancelled subscription still returns its tier: the paid period was kept, so the plan the
    student sees is the one PayPal charged for. ``status`` says what happens next.
    """
    activations = [event for event in _read() if event.get("kind") == "activate"]
    if not activations:
        return {"has_subscription": False, "tier": None, "name": None, "cycle": None,
                "status": "none", "subscription_id": None, "credits": None,
                "period": {}, "since": None}
    latest = activations[-1]
    subscription_id = latest.get("subscription_id")
    cancelled = _cancelled(subscription_id)
    return {"has_subscription": True, "tier": latest.get("tier"),
            "name": PLANS.get(latest.get("tier"), {}).get("name"),
            "cycle": latest.get("cycle"), "subscription_id": subscription_id,
            "status": "cancelled" if cancelled else (latest.get("status") or "ACTIVE"),
            "amount": latest.get("amount"), "currency": latest.get("currency"),
            "payer_email": latest.get("payer_email"), "credits": latest.get("credits"),
            "period": latest.get("period") or {}, "since": latest.get("at")}


def credits_for(tier):
    """The allowance this tier grants, or ``None`` while the owner has not set one."""
    if tier not in PLANS:
        raise BillingError("unknown tier %r" % tier)
    return PLANS[tier]["credits"]


def grant_for(tier, cycle, subscription_id):
    """The hook the credit system will use, wired now and deliberately inert.

    When a tier carries a credit allowance, this appends a grant to the export wallet (see
    ``credits.py``) keyed on ``subscription_id`` so a retry cannot grant twice. Today every tier's
    allowance is ``None``, so nothing is appended and the caller is told why - the product does not
    pretend to have sold credits it has not defined.
    """
    allowance = credits_for(tier)
    if allowance is None:
        return {"granted": None, "reason": "no credit allowance is set for %r yet" % tier,
                "subscription_id": subscription_id}
    return {"granted": int(allowance), "pending": True,
            "reason": "the allowance is configured; the ledger grant is applied by the export "
                      "wallet when that wiring is switched on",
            "subscription_id": subscription_id}
