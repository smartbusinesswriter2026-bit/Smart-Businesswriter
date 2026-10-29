"""Plans, prices and PayPal subscriptions (product layer).

No network and no third-party import: the PayPal client takes an injected opener, so every response
below is a fixture. The tests pin the three promises this build makes:

* the annual price is derived from the monthly one and cannot drift from the "save N%" badge;
* a credit allowance that has not been decided is reported as ``None``, never as a number;
* a payment is recorded only after PayPal says the subscription is ACTIVE, and never twice.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

from bp.product import api as product_api  # noqa: E402
from bp.product import billing  # noqa: E402
from bp.product import paypal  # noqa: E402


class FakeResponse:
    def __init__(self, payload, status=200):
        self._raw = json.dumps(payload).encode() if payload is not None else b""
        self.status = status

    def read(self):
        return self._raw

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    """A urlopen stand-in: records every call and answers from a route table."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, request, timeout=None):
        url = request.full_url
        self.calls.append((request.get_method(), url))
        # The most specific fragment wins: ".../subscriptions/I-1/cancel" must not be answered by
        # the bare ".../subscriptions" route.
        for (method, fragment), answer in sorted(self.routes.items(), key=lambda row: -len(row[0][1])):
            if request.get_method() == method and fragment in url:
                if isinstance(answer, Exception):
                    raise answer
                payload, status = answer if isinstance(answer, tuple) else (answer, 200)
                return FakeResponse(payload, status)
        raise AssertionError("no fixture for %s %s" % (request.get_method(), url))


def http_error(code, name="INVALID_REQUEST", message="bad request"):
    import io
    body = json.dumps({"name": name, "message": message, "details": []}).encode()
    return urllib.error.HTTPError("https://api-m.paypal.com/x", code, "refused", {}, io.BytesIO(body))


class BillingTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-billing-test-")
        self.previous = {name: os.environ.get(name) for name in
                         ("BP_STATE_DIR", "PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_ENV",
                          "BP_PAYPAL_CLIENT_ID", "BP_PAYPAL_CLIENT_SECRET", "BP_PAYPAL_ENV")}
        os.environ["BP_STATE_DIR"] = self.root
        for name in ("BP_PAYPAL_CLIENT_ID", "BP_PAYPAL_CLIENT_SECRET", "BP_PAYPAL_ENV",
                     "PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_ENV"):
            os.environ.pop(name, None)
        # The suite never reads a credential file from this machine: the lazy loader in paypal.py
        # is disabled here so an "unconfigured" test cannot pick up the developer's live keys.
        paypal._LOADED = True

    def tearDown(self):
        for name, value in self.previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(self.root, ignore_errors=True)

    def configure(self, environment="sandbox"):
        os.environ["BP_PAYPAL_CLIENT_ID"] = "test-client-id"
        os.environ["BP_PAYPAL_CLIENT_SECRET"] = "test-secret-value"
        os.environ["BP_PAYPAL_ENV"] = environment


class CatalogueTest(BillingTestCase):
    def test_four_tiers_in_order(self):
        data = billing.catalogue()
        self.assertEqual([row["tier"] for row in data["tiers"]],
                         ["starter", "pro", "studio", "agency"])
        self.assertEqual([row["name"] for row in data["tiers"]],
                         ["Starter", "Pro", "Studio", "Agency"])

    def test_monthly_prices_are_the_owners_numbers(self):
        self.assertEqual([row["monthly"]["amount"] for row in billing.catalogue()["tiers"]],
                         ["14.99", "29.99", "49.99", "99.99"])

    def test_annual_is_twelve_months_less_twenty_percent(self):
        self.assertEqual(billing.price("starter", "annual"), "143.90")
        self.assertEqual(billing.price("pro", "annual"), "287.90")
        self.assertEqual(billing.price("studio", "annual"), "479.90")
        self.assertEqual(billing.price("agency", "annual"), "959.90")

    def test_annual_is_cheaper_than_twelve_monthly_payments(self):
        from decimal import Decimal
        for tier in billing.TIERS:
            monthly = Decimal(billing.price(tier, "monthly"))
            annual = Decimal(billing.price(tier, "annual"))
            self.assertLess(annual, monthly * 12, "%s annual is not a discount" % tier)

    def test_the_saving_is_reported_not_implied(self):
        saving = billing.card("pro")["annual_saving"]
        self.assertEqual(saving["percent"], "20")
        self.assertEqual(saving["amount"], "71.98")

    def test_credits_are_absent_rather_than_invented(self):
        for row in billing.catalogue()["tiers"]:
            self.assertIsNone(row["credits"])
            self.assertIn("to be confirmed", row["credits_label"].lower())
        self.assertFalse(billing.catalogue()["credits_set"])

    def test_an_unknown_tier_or_cycle_is_refused(self):
        with self.assertRaises(billing.BillingError):
            billing.price("platinum", "monthly")
        with self.assertRaises(billing.BillingError):
            billing.price("pro", "weekly")


class LedgerTest(BillingTestCase):
    def test_no_subscription_reports_itself_honestly(self):
        current = billing.current()
        self.assertFalse(current["has_subscription"])
        self.assertEqual(current["status"], "none")
        self.assertIsNone(current["credits"])

    def test_activation_is_recorded_once(self):
        first = billing.activate("pro", "monthly", "I-ABC123", payer_email="a@example.com",
                                 period={"next_billing": "2026-11-29T00:00:00Z"})
        second = billing.activate("pro", "monthly", "I-ABC123")
        self.assertTrue(first["recorded"])
        self.assertFalse(second["recorded"])
        self.assertTrue(second["reused"])
        self.assertEqual(len([e for e in billing.entries() if e["kind"] == "activate"]), 1)
        self.assertEqual(first["current"]["tier"], "pro")
        self.assertEqual(first["current"]["status"], "ACTIVE")

    def test_the_amount_is_the_declared_price(self):
        billing.activate("studio", "annual", "I-XYZ")
        self.assertEqual(billing.current()["amount"], "479.90")
        self.assertEqual(billing.current()["currency"], "USD")

    def test_cancelling_keeps_the_paid_plan(self):
        billing.activate("starter", "monthly", "I-KEEP")
        result = billing.cancel("I-KEEP")
        self.assertTrue(result["recorded"])
        current = billing.current()
        self.assertEqual(current["tier"], "starter")          # the paid plan, not a downgrade
        self.assertEqual(current["status"], "cancelled")
        self.assertFalse(billing.cancel("I-KEEP")["recorded"])  # idempotent

    def test_cancelling_something_unknown_is_refused(self):
        with self.assertRaises(billing.BillingError):
            billing.cancel("I-NEVER")

    def test_the_ledger_survives_a_reload(self):
        billing.activate("agency", "annual", "I-DURABLE")
        self.assertEqual(billing.current()["subscription_id"], "I-DURABLE")

    def test_credits_are_not_granted_until_an_allowance_exists(self):
        result = billing.grant_for("pro", "monthly", "I-ABC123")
        self.assertIsNone(result["granted"])
        self.assertIn("no credit allowance", result["reason"])


class RoutesTest(BillingTestCase):
    def test_the_catalogue_is_served(self):
        status, payload = product_api.handle("GET", "/api/billing/plans")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["tiers"]), 4)

    def test_status_reports_no_plan_on_a_fresh_machine(self):
        status, payload = product_api.handle("GET", "/api/billing/status")
        self.assertEqual(status, 200)
        self.assertFalse(payload["current"]["has_subscription"])
        self.assertFalse(payload["paypal"]["configured"])

    def test_an_unconfigured_checkout_fails_closed_and_names_the_variable(self):
        status, payload = product_api.handle("POST", "/api/billing/subscribe",
                                             {"tier": "starter", "cycle": "monthly"})
        self.assertEqual(status, 503)
        self.assertFalse(payload["configured"])
        self.assertIn("PAYPAL_CLIENT_ID", payload["missing"])
        self.assertIn("PAYPAL_CLIENT_SECRET", payload["missing"])

    def test_the_config_reports_the_public_id_and_never_the_secret(self):
        self.configure("sandbox")
        status, payload = product_api.handle("GET", "/api/billing/config")
        self.assertEqual(status, 200)
        self.assertTrue(payload["configured"])
        self.assertEqual(payload["client_id"], "test-client-id")
        self.assertNotIn("test-secret-value", json.dumps(payload))

    def test_confirm_refuses_a_subscription_paypal_does_not_call_active(self):
        self.configure()
        original = paypal.get_subscription
        paypal.get_subscription = lambda subscription_id, opener=None: {
            "subscription_id": subscription_id, "status": "APPROVAL_PENDING"}
        try:
            status, payload = product_api.handle("POST", "/api/billing/confirm",
                                                 {"subscription_id": "I-PENDING"})
        finally:
            paypal.get_subscription = original
        self.assertEqual(status, 409)
        self.assertFalse(billing.current()["has_subscription"])

    def test_confirm_refuses_a_browser_invented_plan(self):
        self.configure()
        original = paypal.get_subscription
        paypal.get_subscription = lambda subscription_id, opener=None: {
            "subscription_id": subscription_id, "status": "ACTIVE", "custom_id": "platinum:weekly"}
        try:
            status, payload = product_api.handle("POST", "/api/billing/confirm",
                                                 {"subscription_id": "I-ODD"})
        finally:
            paypal.get_subscription = original
        self.assertEqual(status, 422)
        self.assertIn("refusing to guess", payload["error"])

    def test_confirm_records_an_active_subscription_once(self):
        self.configure()
        original = paypal.get_subscription
        paypal.get_subscription = lambda subscription_id, opener=None: {
            "subscription_id": subscription_id, "status": "ACTIVE", "custom_id": "studio:annual",
            "plan_id": "P-1", "payer_email": "payer@example.com",
            "period": {"next_billing": "2027-10-29T00:00:00Z"}}
        try:
            first = product_api.handle("POST", "/api/billing/confirm", {"subscription_id": "I-OK"})
            second = product_api.handle("POST", "/api/billing/confirm", {"subscription_id": "I-OK"})
        finally:
            paypal.get_subscription = original
        self.assertEqual(first[0], 200)
        self.assertTrue(first[1]["recorded"])
        self.assertFalse(second[1]["recorded"])
        current = billing.current()
        self.assertEqual(current["tier"], "studio")
        self.assertEqual(current["cycle"], "annual")
        self.assertIsNone(first[1]["credits"]["granted"])

    def test_cancel_without_a_subscription_is_a_404(self):
        status, _ = product_api.handle("POST", "/api/billing/cancel", {})
        self.assertEqual(status, 404)

    def test_an_unknown_billing_route_is_a_404(self):
        status, _ = product_api.handle("GET", "/api/billing/nope")
        self.assertEqual(status, 404)

    def test_the_billing_family_does_not_swallow_case_routes(self):
        status, payload = product_api.handle("GET", "/api/cases/calculator")
        self.assertEqual(status, 200)
        self.assertIn("groups", payload)


class PayPalClientTest(BillingTestCase):
    TOKEN = ("POST", "/v1/oauth2/token", {"access_token": "A21AA-test", "expires_in": 3000})
    PRODUCT = ("POST", "/v1/catalogs/products", {"id": "PROD-1"})
    PLAN = ("POST", "/v1/billing/plans", {"id": "P-1"})
    SUB = ("POST", "/v1/billing/subscriptions", {"id": "I-SUB1", "status": "APPROVAL_PENDING"})

    def routes(self, extra=None):
        table = {(self.TOKEN[0], self.TOKEN[1]): self.TOKEN[2],
                 (self.PRODUCT[0], self.PRODUCT[1]): self.PRODUCT[2],
                 (self.PLAN[0], self.PLAN[1]): {"id": "P-NEW"},
                 (self.SUB[0], self.SUB[1]): self.SUB[2]}
        table.update(extra or {})
        return table

    def test_a_missing_credential_fails_closed(self):
        with self.assertRaises(paypal.PayPalNotConfigured) as caught:
            paypal.token(opener=FakeOpener({}))
        self.assertIn("PAYPAL_CLIENT_ID", str(caught.exception))

    def test_the_plan_is_created_once_and_cached(self):
        self.configure("sandbox")
        opener = FakeOpener(self.routes())
        first = paypal.plan_id("pro", "monthly", opener=opener)
        calls_after_first = len(opener.calls)
        second = paypal.plan_id("pro", "monthly", opener=opener)
        self.assertEqual(first, second)
        self.assertEqual(first, "P-NEW")
        self.assertEqual(len(opener.calls), calls_after_first, "the cached plan was created again")
        plans = [call for call in opener.calls if call[1].endswith("/v1/billing/plans")]
        self.assertEqual(len(plans), 1)

    def test_the_plan_carries_the_declared_price(self):
        self.configure("sandbox")
        seen = {}

        class Recorder(FakeOpener):
            def __call__(inner, request, timeout=None):
                if request.full_url.endswith("/v1/billing/plans"):
                    seen.update(json.loads(request.data.decode()))
                return FakeOpener.__call__(inner, request, timeout=timeout)

        paypal.plan_id("agency", "annual", opener=Recorder(self.routes()))
        price = seen["billing_cycles"][0]["pricing_scheme"]["fixed_price"]
        self.assertEqual(price["value"], "959.90")
        self.assertEqual(price["currency_code"], "USD")
        self.assertEqual(seen["billing_cycles"][0]["frequency"]["interval_unit"], "YEAR")

    def test_a_price_change_creates_a_new_plan(self):
        self.configure("sandbox")
        opener = FakeOpener(self.routes())
        paypal.plan_id("pro", "monthly", opener=opener)
        original = billing.PLANS["pro"]["monthly"]
        billing.PLANS["pro"]["monthly"] = "31.99"
        try:
            paypal.plan_id("pro", "monthly", opener=opener)
        finally:
            billing.PLANS["pro"]["monthly"] = original
        plans = [call for call in opener.calls if call[1].endswith("/v1/billing/plans")]
        self.assertEqual(len(plans), 2, "a changed price reused the old PayPal plan")

    def test_creating_a_subscription_returns_its_id(self):
        self.configure("sandbox")
        result = paypal.create_subscription("starter", "monthly", opener=FakeOpener(self.routes()))
        self.assertEqual(result["subscription_id"], "I-SUB1")
        self.assertEqual(result["tier"], "starter")
        self.assertEqual(result["cycle"], "monthly")

    def test_a_subscription_is_read_back_with_its_period(self):
        self.configure("sandbox")
        opener = FakeOpener(self.routes({("GET", "/v1/billing/subscriptions/I-1"): {
            "id": "I-1", "status": "ACTIVE", "plan_id": "P-1", "custom_id": "pro:monthly",
            "subscriber": {"email_address": "payer@example.com"},
            "billing_info": {"next_billing_time": "2026-11-29T10:00:00Z"}}}))
        remote = paypal.get_subscription("I-1", opener=opener)
        self.assertEqual(remote["status"], "ACTIVE")
        self.assertEqual(remote["payer_email"], "payer@example.com")
        self.assertEqual(remote["period"]["next_billing"], "2026-11-29T10:00:00Z")

    def test_cancelling_confirms_only_on_a_success_status(self):
        self.configure("sandbox")
        opener = FakeOpener(self.routes({("POST", "/v1/billing/subscriptions/I-1/cancel"):
                                           (None, 204)}))
        self.assertTrue(paypal.cancel_subscription("I-1", opener=opener)["cancelled"])
        refusing = FakeOpener(self.routes({("POST", "/v1/billing/subscriptions/I-1/cancel"):
                                             http_error(422, "SUBSCRIPTION_STATUS_INVALID",
                                                        "Subscription is not active")}))
        with self.assertRaises(paypal.PayPalError) as caught:
            paypal.cancel_subscription("I-1", opener=refusing)
        self.assertIn("SUBSCRIPTION_STATUS_INVALID", str(caught.exception))

    def test_a_refusal_is_reported_not_swallowed(self):
        self.configure("sandbox")
        opener = FakeOpener(self.routes({("POST", "/v1/billing/subscriptions"):
                                           http_error(400, "INVALID_REQUEST", "plan is not active")}))
        with self.assertRaises(paypal.PayPalError) as caught:
            paypal.create_subscription("pro", "monthly", opener=opener)
        self.assertIn("plan is not active", str(caught.exception))

    def test_sandbox_and_live_point_at_different_hosts(self):
        self.configure("sandbox")
        self.assertEqual(paypal.config()["base_url"], paypal.SANDBOX)
        self.configure("live")
        self.assertEqual(paypal.config()["base_url"], paypal.LIVE)

    def test_credentials_are_resolved_from_the_credential_file(self):
        """`python -m bp.server` does not run the launcher, so the module resolves its own names."""
        path = os.path.join(self.root, "creds.env")
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("PAYPAL_CLIENT_ID=from-file\nPAYPAL_CLIENT_SECRET=from-file-secret\n"
                         "PAYPAL_ENV=sandbox\nUNRELATED_SECRET=ignored\n")
        paypal._LOADED = False
        os.environ["BP_SOURCE_ENV"] = path
        try:
            config = paypal.config()
        finally:
            os.environ.pop("BP_SOURCE_ENV", None)
            paypal._LOADED = True
        self.assertTrue(config["configured"])
        self.assertEqual(config["environment"], "sandbox")
        self.assertEqual(config["client_id"], "from-file")
        self.assertNotIn("UNRELATED_SECRET", os.environ)


if __name__ == "__main__":
    unittest.main()
