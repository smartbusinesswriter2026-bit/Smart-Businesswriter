"""PayPal subscriptions over the REST API, standard library only.

The product's own backend credentials live in ``Backend/.env`` and are read through
``source_env.ALLOWED`` at startup:

    PAYPAL_CLIENT_ID=...        the public id the browser SDK is allowed to see
    PAYPAL_CLIENT_SECRET=...    server only; never returned, logged or printed
    PAYPAL_ENV=live|sandbox     live by default, because the owner asked for live

The design:

* **Fail closed.** A missing credential raises ``PayPalNotConfigured`` naming the variable. The
  routes turn that into a 503 that names it too. Nothing pretends a payment can be taken.
* **Plans are created once and cached.** PayPal billing plans are the object a subscription points
  at, and they are immutable in price. The first checkout creates one product and one plan per tier
  and cycle (four tiers x two cycles), stores the ids in ``state/paypal_plans.json`` and reuses them.
  The cache key carries the environment and a hash of the prices, so changing a price creates new
  plans instead of billing an old one.
* **Verification is server-side.** ``get_subscription`` reads the subscription back from PayPal. The
  browser can ask to activate anything it likes; only what PayPal reports ACTIVE is recorded.
* **No webhook is assumed.** PayPal cannot reach a machine at 127.0.0.1, so a renewal is not pushed.
  ``get_subscription`` is the source of truth whenever the page or the account screen asks.

Tests inject ``opener`` so no test touches the network.
"""

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from . import billing

TIMEOUT = 30

LIVE = "https://api-m.paypal.com"
SANDBOX = "https://api-m.sandbox.paypal.com"


class PayPalError(RuntimeError):
    """PayPal refused the call, or answered with something this client cannot use."""


class PayPalNotConfigured(PayPalError):
    """A credential is missing; the message names the variable and nothing else."""

    def __init__(self, missing):
        self.missing = list(missing)
        super().__init__("PayPal is not configured: set %s in Backend/.env and restart the server"
                         % " and ".join(self.missing))


def _env_name():
    return (os.environ.get("BP_PAYPAL_ENV") or os.environ.get("PAYPAL_ENV") or "live").strip().lower()


_LOADED = False


def _load():
    """Resolve the three PayPal names from Backend/.env when the launcher did not.

    The normal launcher loads the whole allowlist at startup; this keeps the billing routes working
    when the server is started as ``python -m bp.server``, and it reads only these names. A value
    already in the environment always wins, and a missing file is not an error.
    """
    global _LOADED
    if _LOADED:
        return
    if not (os.environ.get("BP_PAYPAL_CLIENT_ID") and os.environ.get("BP_PAYPAL_CLIENT_SECRET")):
        try:
            from . import source_env
            source_env.load_selected(("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_ENV"))
        except Exception:            # a broken credential file must not take the page down
            pass
    _LOADED = True


def config():
    """What the page needs: whether checkout can run, and the public client id.

    The secret is never reported, not even as a length or a prefix.
    """
    _load()
    client_id = (os.environ.get("BP_PAYPAL_CLIENT_ID") or os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
    secret = (os.environ.get("BP_PAYPAL_CLIENT_SECRET") or os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
    missing = [name for name, value in (("PAYPAL_CLIENT_ID", client_id),
                                        ("PAYPAL_CLIENT_SECRET", secret)) if not value]
    environment = _env_name()
    return {"configured": not missing, "missing": missing, "environment": environment,
            "base_url": SANDBOX if environment == "sandbox" else LIVE,
            "client_id": client_id or None,
            "note": "The client id is public and is what the browser SDK loads. The secret stays "
                    "on this machine." if not missing else
                    "Checkout is off until %s is set in Backend/.env." % " and ".join(missing)}


def _base():
    return SANDBOX if _env_name() == "sandbox" else LIVE


def _credentials():
    _load()
    client_id = (os.environ.get("BP_PAYPAL_CLIENT_ID") or os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
    secret = (os.environ.get("BP_PAYPAL_CLIENT_SECRET") or os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
    missing = [name for name, value in (("PAYPAL_CLIENT_ID", client_id),
                                        ("PAYPAL_CLIENT_SECRET", secret)) if not value]
    if missing:
        raise PayPalNotConfigured(missing)
    return client_id, secret


def _call(method, path, token=None, body=None, form=None, opener=None):
    """One HTTP call. Returns ``(status, payload)``; raises ``PayPalError`` on a refusal."""
    url = _base() + path
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    open_call = opener or urllib.request.urlopen
    try:
        with open_call(request, timeout=TIMEOUT) as response:
            raw = response.read()
            status = getattr(response, "status", None) or response.getcode()
    except urllib.error.HTTPError as error:
        raw = error.read() or b""
        raise _refusal(error.code, raw) from None
    except urllib.error.URLError as error:
        raise PayPalError("PayPal could not be reached: %s" % getattr(error, "reason", error)) from None
    if status == 204 or not raw:
        return status, {}
    try:
        return status, json.loads(raw.decode("utf-8"))
    except ValueError:
        raise PayPalError("PayPal returned a response that is not JSON (HTTP %s)" % status) from None


def _refusal(code, raw):
    name, message = "", ""
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        payload = {}
    if isinstance(payload, dict):
        name = payload.get("name") or ""
        message = payload.get("message") or ""
        details = payload.get("details") or []
        if not message and details and isinstance(details, list):
            message = "; ".join(str(item.get("description") or item.get("issue") or "") for item in details
                                if isinstance(item, dict))
    text = "%s%s%s" % (name, " - " if name and message else "", message)
    return PayPalError("PayPal refused the call (HTTP %s)%s" % (code, ": " + text if text else ""))


def token(opener=None):
    """A client-credentials access token."""
    client_id, secret = _credentials()
    basic = base64.b64encode(("%s:%s" % (client_id, secret)).encode()).decode()
    url = _base() + "/v1/oauth2/token"
    request = urllib.request.Request(
        url, data=b"grant_type=client_credentials", method="POST",
        headers={"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    open_call = opener or urllib.request.urlopen
    try:
        with open_call(request, timeout=TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise _refusal(error.code, error.read() or b"") from None
    except urllib.error.URLError as error:
        raise PayPalError("PayPal could not be reached: %s" % getattr(error, "reason", error)) from None
    except ValueError:
        raise PayPalError("PayPal returned a token response that is not JSON") from None
    value = payload.get("access_token")
    if not value:
        raise PayPalError("PayPal returned no access token")
    return value


# -- the plan cache ------------------------------------------------------------------------------

def _state_dir():
    from . import ops
    return str(ops.state_dir())


def _cache_path():
    return os.path.join(_state_dir(), "paypal_plans.json")


def _catalogue_hash():
    """Changes whenever a price or the tier list changes, so stale plans are not reused."""
    shape = {tier: {"monthly": billing.PLANS[tier]["monthly"],
                    "annual": billing.price(tier, "annual")} for tier in billing.TIERS}
    shape["_currency"] = billing.CURRENCY
    return hashlib.sha256(json.dumps(shape, sort_keys=True).encode()).hexdigest()[:16]


def _read_cache():
    path = _cache_path()
    try:
        with open(path, encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_cache(data):
    path = _cache_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(temporary, path)


def product_name():
    return "Smart BusinessWriter"


def _plan_name(tier, cycle):
    return "%s - %s (%s)" % (product_name(), billing.PLANS[tier]["name"], cycle)


def _ensure_product(access, opener=None):
    cache = _read_cache()
    if cache.get("env") == _env_name() and cache.get("product_id") and cache.get("catalog") == _catalogue_hash():
        return cache["product_id"]
    _, payload = _call("POST", "/v1/catalogs/products", token=access, opener=opener, body={
        "name": product_name(), "description": "Business writing and calculation workbench.",
        "type": "SERVICE", "category": "SOFTWARE"})
    product_id = payload.get("id")
    if not product_id:
        raise PayPalError("PayPal created no product id")
    cache = {"env": _env_name(), "product_id": product_id, "catalog": _catalogue_hash(), "plans": {}}
    _write_cache(cache)
    return product_id


def plan_id(tier, cycle, opener=None):
    """The billing plan id for one tier and cycle, created on first use and cached after."""
    if tier not in billing.PLANS:
        raise billing.BillingError("unknown tier %r" % tier)
    if cycle not in billing.CYCLES:
        raise billing.BillingError("unknown billing cycle %r" % cycle)
    cache = _read_cache()
    key = "%s:%s" % (tier, cycle)
    if (cache.get("env") == _env_name() and cache.get("catalog") == _catalogue_hash()
            and (cache.get("plans") or {}).get(key)):
        return cache["plans"][key]
    access = token(opener=opener)
    product_id = _ensure_product(access, opener=opener)
    unit = "MONTH" if cycle == "monthly" else "YEAR"
    _, payload = _call("POST", "/v1/billing/plans", token=access, opener=opener, body={
        "product_id": product_id,
        "name": _plan_name(tier, cycle),
        "description": "%s, billed %s." % (billing.PLANS[tier]["name"],
                                           "monthly" if cycle == "monthly" else "yearly"),
        "status": "ACTIVE",
        "billing_cycles": [{
            "frequency": {"interval_unit": unit, "interval_count": 1},
            "tenure_type": "REGULAR", "sequence": 1, "total_cycles": 0,
            "pricing_scheme": {"fixed_price": {"value": billing.price(tier, cycle),
                                               "currency_code": billing.CURRENCY}}}],
        "payment_preferences": {"auto_bill_outstanding": True,
                                "setup_fee_failure_action": "CONTINUE",
                                "payment_failure_threshold": 3}})
    created = payload.get("id")
    if not created:
        raise PayPalError("PayPal created no plan id for %s %s" % (tier, cycle))
    cache = _read_cache()
    if cache.get("env") != _env_name() or cache.get("catalog") != _catalogue_hash():
        cache = {"env": _env_name(), "product_id": product_id, "catalog": _catalogue_hash(), "plans": {}}
    cache.setdefault("plans", {})[key] = created
    cache["env"] = _env_name()
    cache["product_id"] = product_id
    cache["catalog"] = _catalogue_hash()
    _write_cache(cache)
    return created


def create_subscription(tier, cycle, opener=None):
    """Create a subscription that is not yet approved. Returns the id the SDK must approve."""
    plan = plan_id(tier, cycle, opener=opener)
    access = token(opener=opener)
    _, payload = _call("POST", "/v1/billing/subscriptions", token=access, opener=opener, body={
        "plan_id": plan,
        "custom_id": "%s:%s" % (tier, cycle),
        "application_context": {"brand_name": product_name(), "locale": "en-US",
                                "shipping_preference": "NO_SHIPPING", "user_action": "SUBSCRIBE_NOW"}})
    subscription_id = payload.get("id")
    if not subscription_id:
        raise PayPalError("PayPal created no subscription id")
    return {"subscription_id": subscription_id, "plan_id": plan, "tier": tier, "cycle": cycle,
            "status": payload.get("status")}


def _period(payload):
    """The dates PayPal reported, kept verbatim."""
    period = {}
    for source, target in (("start_time", "start"), ("status_update_time", "updated")):
        if payload.get(source):
            period[target] = payload[source]
    billing_info = payload.get("billing_info") or {}
    if isinstance(billing_info, dict) and billing_info.get("next_billing_time"):
        period["next_billing"] = billing_info["next_billing_time"]
    return period


def get_subscription(subscription_id, opener=None):
    """Read a subscription back from PayPal. This is what activation is verified against."""
    if not subscription_id or not isinstance(subscription_id, str):
        raise billing.BillingError("a PayPal subscription id is required")
    access = token(opener=opener)
    _, payload = _call("GET", "/v1/billing/subscriptions/" + urllib.parse.quote(subscription_id),
                       token=access, opener=opener)
    subscriber = payload.get("subscriber") or {}
    return {"subscription_id": payload.get("id") or subscription_id,
            "status": payload.get("status"),
            "plan_id": payload.get("plan_id"),
            "custom_id": payload.get("custom_id"),
            "payer_email": subscriber.get("email_address") if isinstance(subscriber, dict) else None,
            "period": _period(payload)}


def cancel_subscription(subscription_id, reason="Cancelled from the Smart BusinessWriter pricing page",
                        opener=None):
    """Ask PayPal to stop billing. Returns ``{"cancelled": True}`` on a 204."""
    if not subscription_id or not isinstance(subscription_id, str):
        raise billing.BillingError("a PayPal subscription id is required")
    access = token(opener=opener)
    status, _ = _call("POST", "/v1/billing/subscriptions/%s/cancel" % urllib.parse.quote(subscription_id),
                      token=access, opener=opener, body={"reason": reason})
    if status not in (200, 204):
        raise PayPalError("PayPal did not confirm the cancellation (HTTP %s)" % status)
    return {"cancelled": True, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
