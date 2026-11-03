"""The Write Smarter side of the Business Bundle (standard library only).

The owner's Business Bundle is **one order and one charge** (owner instruction, 2026-11-03):
Smart Business Writer takes the money through PayPal, and Write Smarter - the other product -
grants the matching entitlement **without taking a second payment**.

This module is the seam between the two products. It does three things, and nothing else:

* it hands the approved subscription's PayPal **vault id** to the hosted Write Smarter service,
  which creates its own subscription record from that vault and switches that record off so it
  can never bill;
* it reads the entitlement's status back, so a cancellation on either product stops both;
* it revokes the grant when the real subscription is cancelled.

Three rules govern the whole module:

* **Fail closed.** A missing URL, a missing shared secret, a refused call or a body that does
  not say the grant worked are all failures with a reason. Nothing pretends a hand-off happened.
* **The real subscription decides.** The entitlement carries the *billing* subscription id and the
  status is read from PayPal through the other product. This side's own record - the one that was
  switched off - is never the thing that says whether the customer has paid.
* **No money moves here.** This module never calls a PayPal billing endpoint. It cannot take a
  payment even by accident.

The configuration lives in ``Backend/.env``:

    BP_WRITE_SMARTER_URL=https://www.write-smarter.com   the hosted Write Smarter service
    BP_BUNDLE_HANDOFF_SECRET=...                        the shared secret both products carry

Both are optional: without them the bundle still sells here, and this module reports that the
other product was not reached. It never blocks the purchase over it.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 30

#: The endpoint the Write Smarter service exposes for the grant.
GRANT_PATH = "/api/pay/paypal/bundle-entitlement"

#: The endpoint that reports whether the entitlement still stands.
STATUS_PATH = "/api/pay/paypal/bundle-status"


class HandoffError(RuntimeError):
    """The other product could not be reached, or refused the hand-off."""


class HandoffNotConfigured(HandoffError):
    """The other product's address or the shared secret is missing."""

    def __init__(self, missing):
        self.missing = list(missing)
        super().__init__("the Write Smarter hand-off is not configured: set %s and restart the server"
                         % " and ".join(self.missing))


_LOADED = False


def _load():
    """Resolve the two hand-off names from Backend/.env when the launcher did not.

    The normal launcher loads the whole allowlist at startup; this keeps the hand-off working
    when the server is started as ``python -m bp.server``. A value already in the environment
    always wins, and a missing file is not an error.
    """
    global _LOADED
    if _LOADED:
        return
    if not (os.environ.get("BP_WRITE_SMARTER_URL") and os.environ.get("BP_BUNDLE_HANDOFF_SECRET")):
        try:
            from . import source_env
            source_env.load_selected(("WRITE_SMARTER_URL", "BUNDLE_HANDOFF_SECRET"))
        except Exception:            # a broken credential file must not take the page down
            pass
    _LOADED = True


def config():
    """What the account page needs: whether the other product can be reached.

    The secret is never reported - not even as a length or a prefix.
    """
    _load()
    missing = _missing()
    url = (os.environ.get("BP_WRITE_SMARTER_URL") or "").strip()
    return {"configured": not missing, "missing": missing, "url": url or None,
            "note": "The other product is reached over the network with a shared secret; the secret "
                    "never leaves the server." if not missing else
                    "The bundle still sells here. Until these are set the other product is not "
                    "told about the purchase."}


def _missing():
    """Every setting that is absent, named - all of them, not just the first."""
    _load()
    missing = []
    url = (os.environ.get("BP_WRITE_SMARTER_URL") or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        missing.append("BP_WRITE_SMARTER_URL")
    if not (os.environ.get("BP_BUNDLE_HANDOFF_SECRET") or "").strip():
        missing.append("BP_BUNDLE_HANDOFF_SECRET")
    return missing


def _require():
    """Raise unless both settings are present, naming every one that is not."""
    missing = _missing()
    if missing:
        raise HandoffNotConfigured(missing)
    return ((os.environ.get("BP_WRITE_SMARTER_URL") or "").strip().rstrip("/"),
            (os.environ.get("BP_BUNDLE_HANDOFF_SECRET") or "").strip())


def _base_url():
    return _require()[0]


def _secret():
    return _require()[1]


def _call(method, path, body=None, opener=None):
    """One call to the other product. Returns its parsed body, or raises."""
    url = _base_url() + path
    headers = {"Accept": "application/json",
               "Authorization": "Bearer " + _secret()}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
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
        raise HandoffError("Write Smarter could not be reached: %s" % getattr(error, "reason", error)) from None
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        raise HandoffError("Write Smarter returned a response that is not JSON (HTTP %s)" % status) from None
    if status < 200 or status >= 300:
        raise _refusal(status, raw)
    return payload


def _refusal(code, raw):
    message = ""
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        payload = {}
    if isinstance(payload, dict):
        message = payload.get("error") or payload.get("message") or ""
    return HandoffError("Write Smarter refused the hand-off (HTTP %s)%s"
                        % (code, ": " + message if message else ""))


def grant_bundle(email, vault_id, billing_subscription_id, tier=None, cycle=None, opener=None):
    """Tell the other product that the bundle was bought, and grant it there.

    The vault id is what lets the other product create its own record from the same payment
    source and switch it off. Without it there is nothing to hand over, and that is a failure
    with a reason rather than a silent success.

    Returns the other product's own answer, with the fields this product needs added.
    """
    if not email:
        raise HandoffError("the customer's email address is required to grant the bundle")
    if not vault_id:
        raise HandoffError("PayPal reported no vault id for this subscription, so the other "
                           "product cannot be granted it; nothing was charged twice")
    if not billing_subscription_id:
        raise HandoffError("the billing subscription id is required")
    body = {"action": "grant", "email": email, "vault_id": vault_id,
            "billing_subscription_id": billing_subscription_id}
    if tier:
        body["tier"] = tier
    if cycle:
        body["cycle"] = cycle
    payload = _call("POST", GRANT_PATH, body=body, opener=opener)
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise HandoffError("Write Smarter did not confirm the grant: %s"
                           % (payload.get("error") if isinstance(payload, dict) else payload))
    entitlement = payload.get("entitlement") or {}
    return {"granted": True, "email": email,
            "billing_subscription_id": billing_subscription_id,
            "record_subscription_id": entitlement.get("recordSubscriptionId"),
            "record_status": entitlement.get("recordStatus"),
            "unlimited": bool(entitlement.get("unlimited", True)),
            "note": "The other product granted the bundle and switched its own record off, so "
                    "there is one charge."}


def revoke_bundle(email=None, billing_subscription_id=None, opener=None):
    """Take the grant back on the other product.

    Used when the real subscription is cancelled: the other product's mirror must go with it.
    """
    if not email and not billing_subscription_id:
        raise HandoffError("an email address or a billing subscription id is required")
    body = {"action": "revoke"}
    if email:
        body["email"] = email
    if billing_subscription_id:
        body["billing_subscription_id"] = billing_subscription_id
    payload = _call("POST", GRANT_PATH, body=body, opener=opener)
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise HandoffError("Write Smarter did not confirm the revocation: %s"
                           % (payload.get("error") if isinstance(payload, dict) else payload))
    return {"revoked": bool(payload.get("revoked"))}


def bundle_status(email, opener=None):
    """Ask the other product whether the bundle still stands there.

    The answer follows the **real** subscription, so a cancellation on either side stops both.
    A service that cannot be reached is reported as "not entitled" with the reason, never as a
    quiet success.
    """
    if not email:
        raise HandoffError("an email address is required")
    query = urllib.parse.urlencode({"email": email})
    payload = _call("GET", STATUS_PATH + "?" + query, opener=opener)
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise HandoffError("Write Smarter did not answer the status request: %s"
                           % (payload.get("error") if isinstance(payload, dict) else payload))
    return {"entitled": bool(payload.get("entitled")),
            "status": payload.get("status"),
            "billing_subscription_id": payload.get("billingSubscriptionId"),
            "record_subscription_id": payload.get("recordSubscriptionId"),
            "record_status": payload.get("recordStatus"),
            "reason": payload.get("reason")}
