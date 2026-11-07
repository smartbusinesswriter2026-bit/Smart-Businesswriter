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
TIERS = ("starter", "pro", "studio", "bundle_starter", "bundle_pro", "bundle_studio", "agency")

#: The tiers that are shown as **cards in the pricing grid**. The bundle is deliberately not one of
#: them: it covers two products, so it is shown as its own band below the grid (owner instruction,
#: 2026-11-03) - a customer reads "two products, one price" from a band and reads "a fourth tier of
#: this product" from a fourth card.
CARD_TIERS = ("starter", "pro", "studio")

#: The bundle ladder, shown as bands below the grid. Each rung is the matching Write Smarter tier
#: paired with a Smart Business Writer tier at one price; the top rung is the unlimited Business
#: Bundle. Owner instruction, 2026-11-08: Starter $20, Pro $39, Studio $65, Business Bundle $99.99.
BUNDLE_TIERS = ("bundle_starter", "bundle_pro", "bundle_studio", "agency")

#: The top bundle. It keeps the ``agency`` key so the PayPal plan cache and every ledger already
#: written against it stay valid.
BUNDLE_TIER = "agency"

#: The catalogue. ``monthly`` is the only price written by hand; ``credits`` and ``highlights`` stay
#: empty until the owner supplies them - see ``billing.py`` in DESIGN_NOTES for where they land.
#:
#: The fourth tier is the owner's Business Bundle (owner instruction, 2026-11-03): one subscription
#: that grants unlimited use of **both** products - this one and Write Smarter. It keeps the
#: ``agency`` key so the PayPal plan cache and every ledger already written against it stay valid;
#: only the name the customer reads and the allowance it grants changed. ``unlimited`` is a
#: declaration, not a number: the other three tiers still report no allowance at all.
#:
#: The bundle's ``products`` list says what the one price buys. Write Smarter's own feature names
#: are used verbatim from that product's pricing page, so a customer reads the same words here as
#: there. The pools are unlimited because the bundle grants no limit at all - they are not a quota
#: and they do not refill.
#: The Write Smarter pool rules, shown with each bundle rung. Published on Write Smarter's own
#: pricing page; repeated here so the bundle tile names the same pools the customer sees there.
POOLS_NOTE = ("Pools reset each billing cycle. Humanizer use draws from the Humanizer & "
              "AI-Detector pool - 1 word rewritten = 1 credit, and AI-detection scans cost "
              "1 credit per word.")

PLANS = {
    "starter": {"name": "Starter", "monthly": "14.99", "credits": None, "highlights": [],
                "color": "navy"},
    "pro": {"name": "Pro", "monthly": "29.99", "credits": None, "highlights": [],
            "color": "indigo"},
    "studio": {"name": "Studio", "monthly": "49.99", "credits": None, "highlights": [],
               "color": "teal"},
    # The lower bundle rungs (owner instruction, 2026-11-08): one subscription buying the matching
    # Write Smarter tier and this product's tier together. The allowance is still the owner's to
    # set, so it stays undecided rather than estimated.
    "bundle_starter": {"name": "Starter Bundle", "monthly": "20.00", "credits": None,
                       "highlights": [], "bundle": True, "unlimited": False, "color": "green",
                       "includes": ["Write Smarter - Basic", "Smart Business Writer - Starter"],
                       "write_smarter": {"tier": "Basic", "pools": [
                           {"label": "Text-Gen pool", "value": "25,000 words"},
                           {"label": "Humanizer & AI-Detector", "value": "5,000 words"},
                           {"label": "Video", "value": "30 min"},
                           {"label": "Source Finder", "value": "Unlimited"}]},
                       "sbw_tier": "Starter",
                       "products": [
                           {"name": "Write Smarter", "features": ["Basic plan", "Source Finder included"]},
                           {"name": "Smart Business Writer", "features": ["Starter plan", "Every framework, shelf and calculator"]},
                       ]},
    "bundle_pro": {"name": "Pro Bundle", "monthly": "39.00", "credits": None,
                   "highlights": [], "bundle": True, "unlimited": False, "color": "green",
                   "includes": ["Write Smarter - Standard", "Smart Business Writer - Pro"],
                   "write_smarter": {"tier": "Standard", "pools": [
                       {"label": "Text-Gen pool", "value": "50,000 words"},
                       {"label": "Humanizer & AI-Detector", "value": "12,000 words"},
                       {"label": "Video", "value": "2 hrs"},
                       {"label": "Source Finder", "value": "Unlimited"}]},
                   "sbw_tier": "Pro",
                   "products": [
                       {"name": "Write Smarter", "features": ["Standard plan", "Source Finder included"]},
                       {"name": "Smart Business Writer", "features": ["Pro plan", "Every framework, shelf and calculator"]},
                   ]},
    "bundle_studio": {"name": "Studio Bundle", "monthly": "65.00", "credits": None,
                      "highlights": [], "bundle": True, "unlimited": False, "color": "green",
                      "includes": ["Write Smarter - Pro", "Smart Business Writer - Studio"],
                      "write_smarter": {"tier": "Pro", "pools": [
                          {"label": "Text-Gen pool", "value": "100,000 words"},
                          {"label": "Humanizer & AI-Detector", "value": "30,000 words"},
                          {"label": "Video", "value": "6 hrs"},
                          {"label": "Source Finder", "value": "Unlimited"}]},
                      "sbw_tier": "Studio",
                      "products": [
                          {"name": "Write Smarter", "features": ["Pro plan", "Source Finder included"]},
                          {"name": "Smart Business Writer", "features": ["Studio plan", "Every framework, shelf and calculator"]},
                      ]},
    "agency": {"name": "Business Bundle", "monthly": "99.99", "credits": None, "highlights": [],
               "unlimited": True,
               "bundle": True,
               "color": "green",
               "includes": ["Write Smarter - unlimited", "Smart Business Writer - unlimited"],
               "write_smarter": {"tier": "Unlimited", "pools": [
                   {"label": "Text-Gen pool", "value": "Unlimited"},
                   {"label": "Humanizer & AI-Detector", "value": "Unlimited"},
                   {"label": "Video", "value": "Unlimited"},
                   {"label": "Source Finder", "value": "Unlimited"}]},
               "sbw_tier": "Unlimited",
               "products": [
                   {"name": "Write Smarter",
                    "features": [
                        "Unlimited Text-Gen",
                        "Unlimited Research Assistant",
                        "Unlimited Humanizer & AI-Detector",
                        "Unlimited Video",
                        "Unlimited use of Source Finder",
                    ]},
                   {"name": "Smart Business Writer",
                    "features": [
                        "Unlimited exports",
                        "Every framework, shelf and calculator",
                    ]},
               ]},
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


def _write_smarter(plan):
    """The Write Smarter tier a bundle buys, and that tier's published pools."""
    ws = plan.get("write_smarter") or {}
    return {"tier": ws.get("tier"),
            "pools": [dict(pool) for pool in (ws.get("pools") or [])]}


def card(tier):
    """One card's payload: the prices, the derived saving and the fields still to be supplied."""
    plan = PLANS[tier]
    unlimited = bool(plan.get("unlimited"))
    if unlimited:
        label = "Unlimited"
    elif plan["credits"] is None:
        label = "Credit allowance: to be confirmed"
    else:
        label = plan["credits"]
    return {"tier": tier, "name": plan["name"], "currency": CURRENCY,
            "monthly": {"amount": price(tier, "monthly"), "cycle": "monthly"},
            "annual": {"amount": price(tier, "annual"), "cycle": "annual", "months": 12},
            "annual_saving": annual_saving(tier),
            "credits": plan["credits"],
            "credits_label": label,
            "unlimited": unlimited,
            "bundle": bool(plan.get("bundle")),
            "color": plan.get("color"),
            "includes": list(plan.get("includes") or []),
            "write_smarter": _write_smarter(plan),
            "sbw_tier": plan.get("sbw_tier"),
            "pools_note": POOLS_NOTE if plan.get("bundle") else None,
            "products": [dict(product, features=list(product.get("features") or []))
                         for product in (plan.get("products") or [])],
            "highlights": list(plan["highlights"])}


def catalogue():
    """Every tier, in order, plus the facts a page needs to render the toggle.

    The page needs to know **which** tiers are cards and **which** is the band: the bundle covers
    two products and is shown below the grid, not as a fourth card in it.
    """
    return {"currency": CURRENCY, "tiers": [card(tier) for tier in TIERS],
            "card_tiers": list(CARD_TIERS),
            "bundle_tiers": list(BUNDLE_TIERS),
            "bundle_tier": BUNDLE_TIER,
            "annual_discount_percent": _percent(ANNUAL_DISCOUNT * 100),
            "credits_set": all(PLANS[tier]["credits"] is not None for tier in TIERS),
            "notice": "Prices are the owner's configuration. The annual price is 12 months less "
                      "the declared discount. Credit allowances are not set yet; they are "
                      "returned as null rather than estimated. The Business Bundle grants no "
                      "limit on either product, and says so rather than quoting an allowance."}


# -- the ledger ----------------------------------------------------------------------------------

def _state_dir():
    from . import ops
    return str(ops.state_dir())


def _path():
    return os.path.join(_state_dir(), "subscriptions.jsonl")


def _pending_path():
    return os.path.join(_state_dir(), "pending_subscriptions.json")


def _read_pending():
    """The subscriptions that were created but not yet approved, and their vault ids.

    PayPal reports the vault id on the **creation** response; the read-back of an approved
    subscription does not always carry it. The Business Bundle needs it - the other product
    creates its own record from that vault - so it is remembered here between the two calls.

    The file holds only what PayPal already reported for a subscription this machine created. It
    is a short-lived working note: an entry is dropped once the subscription is confirmed.
    """
    path = _pending_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_pending(data):
    path = _pending_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, sort_keys=True, indent=2)


def remember_pending(subscription_id, vault_id=None, tier=None, cycle=None):
    """Remember a subscription this machine created, and the vault id PayPal reported for it.

    Called at creation, because that is the only moment PayPal reliably names the vault.
    """
    if not subscription_id or not isinstance(subscription_id, str):
        raise BillingError("a PayPal subscription id is required")
    with LOCK:
        pending = _read_pending()
        entry = pending.get(subscription_id) or {}
        if vault_id:
            entry["vault_id"] = vault_id
        if tier:
            entry["tier"] = tier
        if cycle:
            entry["cycle"] = cycle
        pending[subscription_id] = entry
        _write_pending(pending)
        return entry


def pending_vault_id(subscription_id):
    """The vault id remembered for a subscription, or None. Never guessed."""
    if not subscription_id or not isinstance(subscription_id, str):
        return None
    entry = _read_pending().get(subscription_id) or {}
    return entry.get("vault_id") or None


def forget_pending(subscription_id):
    """Drop a subscription's working note once it is confirmed and recorded."""
    if not subscription_id or not isinstance(subscription_id, str):
        return False
    with LOCK:
        pending = _read_pending()
        if subscription_id not in pending:
            return False
        pending.pop(subscription_id, None)
        _write_pending(pending)
        return True


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
    """Record a paid subscription. Idempotent on the subscription id *and* the tier it carries.

    PayPal keeps the same subscription id when the plan changes, so a plan change is a **new**
    activation of the same subscription - it must be recorded, or the account page would keep
    reporting the tier the customer left. A retried confirmation of the same tier records
    nothing new.

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
            # Idempotent on the subscription id *and* the tier it carries. PayPal keeps the same
            # subscription id when the plan changes, so a plan change is a new activation of the
            # same subscription - it must be recorded, while a retried confirmation of the same
            # tier must not append a second line.
            if (event.get("kind") == "activate" and event.get("subscription_id") == subscription_id
                    and event.get("tier") == tier and event.get("cycle") == cycle):
                return {"recorded": False, "reused": True, "entry": event, "current": current()}
        event = {"id": uuid.uuid4().hex[:12], "at": _now(), "kind": "activate",
                 "subscription_id": subscription_id, "tier": tier, "cycle": cycle,
                 "amount": price(tier, cycle), "currency": CURRENCY,
                 "payer_email": payer_email or None, "status": status,
                 "period": period if isinstance(period, dict) else {},
                 "credits": PLANS[tier]["credits"], "unlimited": unlimited_for(tier),
                 "idem": subscription_id}
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
    """The activation that stands for this subscription: the latest one.

    A plan change keeps the PayPal subscription id and appends a new activation carrying the new
    tier, so the latest line is the plan the customer is on. The cancellation message and the
    account page must read that line, not the first one.
    """
    found = None
    for event in _read():
        if event.get("kind") == "activate" and event.get("subscription_id") == subscription_id:
            found = event
    return found


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
                "status": "none", "subscription_id": None, "credits": None, "unlimited": False,
                "period": {}, "since": None}
    latest = activations[-1]
    subscription_id = latest.get("subscription_id")
    cancelled = _cancelled(subscription_id)
    tier = latest.get("tier")
    unlimited = bool(latest.get("unlimited"))
    if not unlimited and tier in PLANS:
        unlimited = unlimited_for(tier)
    return {"has_subscription": True, "tier": tier,
            "name": PLANS.get(tier, {}).get("name"),
            "cycle": latest.get("cycle"), "subscription_id": subscription_id,
            "status": "cancelled" if cancelled else (latest.get("status") or "ACTIVE"),
            "amount": latest.get("amount"), "currency": latest.get("currency"),
            "payer_email": latest.get("payer_email"), "credits": latest.get("credits"),
            "unlimited": unlimited,
            # The products this plan covers, so the account page can name them without a second
            # request and without the page naming them itself.
            "products": [dict(product, features=list(product.get("features") or []))
                         for product in (PLANS.get(tier, {}).get("products") or [])],
            "period": latest.get("period") or {}, "since": latest.get("at")}


def credits_for(tier):
    """The allowance this tier grants, or ``None`` while the owner has not set one."""
    if tier not in PLANS:
        raise BillingError("unknown tier %r" % tier)
    return PLANS[tier]["credits"]


def unlimited_for(tier):
    """True when the tier grants no limit at all.

    The Business Bundle is the owner's declaration that neither product meters the customer, so
    the wallet stops blocking for it. A tier that has no allowance set yet is **not** unlimited:
    it is undecided, and undecided is not free.
    """
    if tier not in PLANS:
        raise BillingError("unknown tier %r" % tier)
    return bool(PLANS[tier].get("unlimited"))


def grant_for(tier, cycle, subscription_id):
    """The hook the credit system will use, wired now and deliberately inert.

    When a tier carries a credit allowance, this appends a grant to the export wallet (see
    ``credits.py``) keyed on ``subscription_id`` so a retry cannot grant twice. Today every tier's
    allowance is ``None``, so nothing is appended and the caller is told why - the product does not
    pretend to have sold credits it has not defined.

    The Business Bundle grants no limit instead of an allowance, and says so: the wallet stops
    blocking for it rather than pretending to hold a number of credits.
    """
    if unlimited_for(tier):
        return {"granted": None, "unlimited": True,
                "reason": "the %s tier grants no limit, so there is no allowance to grant"
                          % PLANS[tier]["name"],
                "subscription_id": subscription_id}
    allowance = credits_for(tier)
    if allowance is None:
        return {"granted": None, "reason": "no credit allowance is set for %r yet" % tier,
                "subscription_id": subscription_id}
    return {"granted": int(allowance), "pending": True,
            "reason": "the allowance is configured; the ledger grant is applied by the export "
                      "wallet when that wiring is switched on",
            "subscription_id": subscription_id}
