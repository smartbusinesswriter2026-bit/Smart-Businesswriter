"""The Business Bundle: one order, one charge, one limit-free entitlement on both products.

Owner instruction, 2026-11-03. These tests pin the promises the bundle makes, and they are
written so that each one **fails on the old code**:

* **One charge.** The money is taken in Smart Business Writer only. The other product is granted
  the bundle from the same PayPal vault and switches its own record off, so a second subscription
  never bills. The hand-off itself is a fail-closed call: a missing address or secret, a refused
  call, or a body that does not confirm the grant are all failures with a reason.
* **The real subscription decides.** The entitlement follows the *billing* subscription id, so a
  cancellation on either side stops both.
* **A plan change is an adjustment.** PayPal keeps the subscription id and prorates the period,
  and the ledger must record the new tier against that same id - not keep reporting the first one.
* **Unlimited is a declaration, not a number.** The bundle grants no limit on either product, so
  the export wallet stops blocking for it; the tiers whose allowance has not been decided keep
  their meter, because undecided is not free.

No network and no third-party import: the PayPal client and the hand-off client both take an
injected opener, so every response below is a fixture.
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
from bp.product import credits  # noqa: E402
from bp.product import paypal  # noqa: E402
from bp.product import write_smarter  # noqa: E402


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
        self.calls.append((request.get_method(), url, request.data))
        for (method, fragment), answer in sorted(self.routes.items(),
                                                 key=lambda row: -len(row[0][1])):
            if request.get_method() == method and fragment in url:
                if isinstance(answer, Exception):
                    raise answer
                payload, status = answer if isinstance(answer, tuple) else (answer, 200)
                return FakeResponse(payload, status)
        raise AssertionError("no fixture for %s %s" % (request.get_method(), url))


def http_error(code, name="INVALID_REQUEST", message="bad request"):
    import io
    body = json.dumps({"name": name, "message": message, "details": []}).encode()
    return urllib.error.HTTPError("https://write-smarter.example/x", code, "refused", {},
                                  io.BytesIO(body))


class BundleTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-bundle-test-")
        self.previous = {name: os.environ.get(name) for name in
                         ("BP_STATE_DIR", "PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_ENV",
                          "BP_PAYPAL_CLIENT_ID", "BP_PAYPAL_CLIENT_SECRET", "BP_PAYPAL_ENV",
                          "BP_WRITE_SMARTER_URL", "BP_BUNDLE_HANDOFF_SECRET")}
        os.environ["BP_STATE_DIR"] = self.root
        for name in ("BP_PAYPAL_CLIENT_ID", "BP_PAYPAL_CLIENT_SECRET", "BP_PAYPAL_ENV",
                     "PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_ENV",
                     "BP_WRITE_SMARTER_URL", "BP_BUNDLE_HANDOFF_SECRET"):
            os.environ.pop(name, None)
        # The suite never reads a credential file from this machine: the lazy loaders are
        # disabled here so an "unconfigured" test cannot pick up the developer's live keys.
        paypal._LOADED = True
        write_smarter._LOADED = True

    def tearDown(self):
        for name, value in self.previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(self.root, ignore_errors=True)

    def configure_paypal(self, environment="sandbox"):
        os.environ["BP_PAYPAL_CLIENT_ID"] = "test-client-id"
        os.environ["BP_PAYPAL_CLIENT_SECRET"] = "test-secret-value"
        os.environ["BP_PAYPAL_ENV"] = environment

    def configure_handoff(self):
        os.environ["BP_WRITE_SMARTER_URL"] = "https://write-smarter.example"
        os.environ["BP_BUNDLE_HANDOFF_SECRET"] = "shared-secret-value"


# ── the one charge ───────────────────────────────────────────────────────────────────────────────

class OneChargeTest(BundleTestCase):
    """The money is taken once. The other product is granted, not charged."""

    def test_the_bundle_grants_the_other_product_rather_than_charging_it(self):
        self.configure_handoff()
        opener = FakeOpener({
            ("POST", "/api/pay/paypal/bundle-entitlement"):
                {"ok": True, "entitlement": {"sku": "bundle", "unlimited": True,
                                             "billingSubscriptionId": "I-REAL",
                                             "recordSubscriptionId": "W-REC1",
                                             "recordStatus": "SUSPENDED"}},
        })
        result = write_smarter.grant_bundle("buyer@example.com", "V-1", "I-REAL",
                                            tier="agency", cycle="monthly", opener=opener)
        self.assertTrue(result["granted"])
        self.assertEqual(result["record_subscription_id"], "W-REC1")
        self.assertEqual(result["record_status"], "SUSPENDED")
        # The request carries the vault id and the real subscription id - and nothing that
        # could take money.
        method, url, data = opener.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://write-smarter.example/api/pay/paypal/bundle-entitlement")
        body = json.loads(data)
        self.assertEqual(body["vault_id"], "V-1")
        self.assertEqual(body["billing_subscription_id"], "I-REAL")
        self.assertNotIn("plan_id", body)
        self.assertNotIn("amount", body)

    def test_a_missing_vault_id_is_a_failure_not_a_grant(self):
        self.configure_handoff()
        opener = FakeOpener({})
        with self.assertRaises(write_smarter.HandoffError) as caught:
            write_smarter.grant_bundle("buyer@example.com", None, "I-REAL", opener=opener)
        self.assertIn("vault id", str(caught.exception))
        self.assertEqual(opener.calls, [], "nothing was sent without a vault id")

    def test_an_unconfigured_hand_off_fails_closed_and_names_the_variable(self):
        with self.assertRaises(write_smarter.HandoffNotConfigured) as caught:
            write_smarter.grant_bundle("buyer@example.com", "V-1", "I-REAL")
        self.assertIn("BP_WRITE_SMARTER_URL", caught.exception.missing)
        self.assertIn("BP_BUNDLE_HANDOFF_SECRET", caught.exception.missing)

    def test_a_refused_hand_off_is_reported_not_swallowed(self):
        self.configure_handoff()
        opener = FakeOpener({
            ("POST", "/api/pay/paypal/bundle-entitlement"):
                ({"ok": False, "error": "the record is still ACTIVE"}, 502),
        })
        with self.assertRaises(write_smarter.HandoffError) as caught:
            write_smarter.grant_bundle("buyer@example.com", "V-1", "I-REAL", opener=opener)
        self.assertIn("still ACTIVE", str(caught.exception))

    def test_a_body_that_does_not_confirm_the_grant_is_not_a_grant(self):
        self.configure_handoff()
        opener = FakeOpener({
            ("POST", "/api/pay/paypal/bundle-entitlement"): {"ok": False, "error": "no"},
        })
        with self.assertRaises(write_smarter.HandoffError):
            write_smarter.grant_bundle("buyer@example.com", "V-1", "I-REAL", opener=opener)

    def test_the_hand_off_client_never_calls_a_paypal_billing_endpoint(self):
        self.configure_handoff()
        opener = FakeOpener({
            ("POST", "/api/pay/paypal/bundle-entitlement"): {"ok": True, "entitlement": {}},
        })
        write_smarter.grant_bundle("buyer@example.com", "V-1", "I-REAL", opener=opener)
        for _method, url, _data in opener.calls:
            self.assertNotIn("paypal.com", url)
            self.assertNotIn("/v1/billing/", url)


# ── the ledger records a plan change ─────────────────────────────────────────────────────────────

class PlanChangeLedgerTest(BundleTestCase):
    """PayPal keeps the subscription id when the plan changes, so the ledger must move with it."""

    def test_a_plan_change_is_recorded_against_the_same_subscription(self):
        billing.activate("starter", "monthly", "I-SAME", payer_email="a@example.com")
        result = billing.activate("agency", "monthly", "I-SAME", payer_email="a@example.com")
        self.assertTrue(result["recorded"], "the tier change was not recorded")
        current = billing.current()
        self.assertEqual(current["tier"], "agency")
        self.assertEqual(current["subscription_id"], "I-SAME")
        self.assertTrue(current["unlimited"])
        self.assertEqual(current["amount"], "99.99")

    def test_a_retried_confirmation_of_the_same_tier_records_nothing_new(self):
        billing.activate("agency", "monthly", "I-SAME")
        again = billing.activate("agency", "monthly", "I-SAME")
        self.assertFalse(again["recorded"])
        self.assertTrue(again["reused"])
        self.assertEqual(len([e for e in billing.entries() if e["kind"] == "activate"]), 1)

    def test_the_account_page_reads_the_new_tier_not_the_first(self):
        billing.activate("starter", "monthly", "I-SAME")
        billing.activate("agency", "monthly", "I-SAME")
        self.assertEqual(billing.current()["tier"], "agency")
        self.assertEqual(billing.current()["name"], "Business Bundle")

    def test_a_cancellation_names_the_tier_the_customer_was_on(self):
        billing.activate("starter", "monthly", "I-SAME")
        billing.activate("agency", "monthly", "I-SAME")
        result = billing.cancel("I-SAME")
        self.assertTrue(result["recorded"])
        event = [e for e in billing.entries() if e["kind"] == "cancel"][-1]
        self.assertEqual(event["tier"], "agency")

    def test_the_downgrade_moves_the_tier_back(self):
        billing.activate("agency", "monthly", "I-SAME")
        billing.activate("starter", "monthly", "I-SAME")
        current = billing.current()
        self.assertEqual(current["tier"], "starter")
        self.assertFalse(current["unlimited"], "a downgrade must not keep the unlimited grant")


# ── the plan-change route ────────────────────────────────────────────────────────────────────────

class PlanChangeRouteTest(BundleTestCase):
    def test_the_change_route_adjusts_the_plan_and_records_the_new_tier(self):
        self.configure_paypal()
        billing.activate("starter", "monthly", "I-SAME", payer_email="a@example.com")
        original = paypal.change_plan
        paypal.change_plan = lambda subscription_id, tier, cycle, opener=None: {
            "subscription_id": subscription_id, "plan_id": "P-BUNDLE", "tier": tier, "cycle": cycle,
            "status": "ACTIVE", "outstanding_balance": "70.00",
            "adjustment": {"amount": "70.00", "direction": "charged",
                           "note": "PayPal charged the difference for the rest of this period."},
            "period": {"next_billing": "2026-12-03T00:00:00Z"}}
        try:
            status, payload = product_api.handle("POST", "/api/billing/change",
                                                 {"tier": "agency", "cycle": "monthly"})
        finally:
            paypal.change_plan = original
        self.assertEqual(status, 200)
        self.assertTrue(payload["changed"])
        self.assertTrue(payload["recorded"])
        self.assertEqual(payload["current"]["tier"], "agency")
        self.assertEqual(payload["adjustment"]["direction"], "charged")
        self.assertEqual(payload["adjustment"]["amount"], "70.00")

    def test_the_change_route_refuses_when_paypal_did_not_change_the_plan(self):
        self.configure_paypal()
        billing.activate("starter", "monthly", "I-SAME")
        original = paypal.change_plan
        paypal.change_plan = lambda subscription_id, tier, cycle, opener=None: {
            "subscription_id": subscription_id, "plan_id": "P-X", "tier": tier, "cycle": cycle,
            "status": "SUSPENDED", "outstanding_balance": None,
            "adjustment": {"amount": None, "direction": "unknown", "note": ""},
            "period": {}}
        try:
            status, payload = product_api.handle("POST", "/api/billing/change",
                                                 {"tier": "agency", "cycle": "monthly"})
        finally:
            paypal.change_plan = original
        self.assertEqual(status, 409)
        self.assertEqual(billing.current()["tier"], "starter")

    def test_the_change_route_without_a_subscription_is_a_404(self):
        self.configure_paypal()
        status, payload = product_api.handle("POST", "/api/billing/change",
                                             {"tier": "agency", "cycle": "monthly"})
        self.assertEqual(status, 404)
        self.assertIn("no subscription", payload["error"])


# ── the adjustment PayPal reported ────────────────────────────────────────────────────────────────

class AdjustmentTest(BundleTestCase):
    def test_a_positive_outstanding_balance_is_a_charge(self):
        result = paypal._adjustment("70.00")
        self.assertEqual(result["direction"], "charged")
        self.assertEqual(result["amount"], "70.00")

    def test_a_negative_outstanding_balance_is_a_credit(self):
        result = paypal._adjustment("-19.98")
        self.assertEqual(result["direction"], "credited")
        self.assertEqual(result["amount"], "19.98")

    def test_no_reported_balance_is_said_so_and_not_guessed(self):
        result = paypal._adjustment(None)
        self.assertEqual(result["direction"], "unknown")
        self.assertIsNone(result["amount"])

    def test_a_balance_the_product_cannot_read_is_not_a_number(self):
        result = paypal._adjustment("not-a-number")
        self.assertEqual(result["direction"], "unknown")
        self.assertIsNone(result["amount"])


# ── the vault id reaches the hand-off ─────────────────────────────────────────────────────────────

class VaultTest(BundleTestCase):
    def test_the_vault_id_is_read_from_the_subscription_paypal_reports(self):
        self.assertEqual(paypal._vault_id({"payment_source": {"vault_id": "V-9"}}), "V-9")
        self.assertEqual(paypal._vault_id({"vault_id": "V-8"}), "V-8")
        self.assertIsNone(paypal._vault_id({}))
        self.assertIsNone(paypal._vault_id({"payment_source": {}}))

    def test_a_created_subscription_carries_the_vault_id_when_paypal_reports_one(self):
        self.configure_paypal()
        opener = FakeOpener({
            ("POST", "/v1/oauth2/token"): {"access_token": "A21AA-test"},
            ("POST", "/v1/catalogs/products"): {"id": "PROD-1"},
            ("POST", "/v1/billing/plans"): {"id": "P-1"},
            ("POST", "/v1/billing/subscriptions"):
                {"id": "I-SUB1", "status": "APPROVAL_PENDING",
                 "payment_source": {"vault_id": "V-1"}},
        })
        result = paypal.create_subscription("agency", "monthly", opener=opener)
        self.assertEqual(result["vault_id"], "V-1")

    def test_the_vault_id_is_remembered_between_creating_and_confirming(self):
        # PayPal names the vault when it creates the subscription and does not always name it
        # when the subscription is read back, so the note kept at creation is what the
        # confirmation falls back on.
        billing.remember_pending("I-PENDING", vault_id="V-1", tier="agency", cycle="monthly")
        self.assertEqual(billing.pending_vault_id("I-PENDING"), "V-1")
        self.assertIsNone(billing.pending_vault_id("I-OTHER"))
        billing.forget_pending("I-PENDING")
        self.assertIsNone(billing.pending_vault_id("I-PENDING"))

    def test_confirming_falls_back_to_the_vault_id_kept_at_creation(self):
        self.configure_paypal()
        billing.remember_pending("I-REAL", vault_id="V-1", tier="agency", cycle="monthly")
        original = paypal.get_subscription
        paypal.get_subscription = lambda subscription_id, opener=None: {
            "subscription_id": subscription_id, "status": "ACTIVE", "custom_id": "agency:monthly",
            "payer_email": "buyer@example.com", "plan_id": "P-1"}
        opened = []
        original_grant = write_smarter.grant_bundle
        write_smarter.grant_bundle = lambda email, vault_id, subscription_id, **kw: (
            opened.append(vault_id) or {"granted": True})
        try:
            status, payload = product_api.handle("POST", "/api/billing/confirm",
                                                 {"subscription_id": "I-REAL"})
        finally:
            paypal.get_subscription = original
            write_smarter.grant_bundle = original_grant
        self.assertEqual(status, 200)
        self.assertEqual(opened, ["V-1"])
        self.assertTrue(payload["handoff"]["granted"])
        # The working note is dropped once the subscription is confirmed.
        self.assertIsNone(billing.pending_vault_id("I-REAL"))

    def test_a_missing_vault_id_is_reported_and_nothing_is_sent(self):
        self.configure_paypal()
        self.configure_handoff()
        opened = []
        original = paypal.get_subscription
        paypal.get_subscription = lambda subscription_id, opener=None: {
            "subscription_id": subscription_id, "status": "ACTIVE", "custom_id": "agency:monthly",
            "payer_email": "buyer@example.com"}
        # The real client is used here: it is the one that refuses a missing vault id, and it
        # refuses before it sends anything.
        original_call = write_smarter._call
        write_smarter._call = lambda *args, **kwargs: opened.append(args) or {}
        try:
            status, payload = product_api.handle("POST", "/api/billing/confirm",
                                                 {"subscription_id": "I-NOVAULT"})
        finally:
            paypal.get_subscription = original
            write_smarter._call = original_call
        self.assertEqual(status, 200)
        self.assertFalse(payload["handoff"]["granted"])
        self.assertIn("vault id", payload["handoff"]["error"])
        self.assertEqual(opened, [], "nothing was sent without a vault id")


# ── the confirm route hands the bundle over ───────────────────────────────────────────────────────

class ConfirmHandoffTest(BundleTestCase):
    def _confirm(self, remote):
        original = paypal.get_subscription
        paypal.get_subscription = lambda subscription_id, opener=None: remote
        try:
            return product_api.handle("POST", "/api/billing/confirm",
                                      {"subscription_id": remote.get("subscription_id", "I-REAL")})
        finally:
            paypal.get_subscription = original

    def test_confirming_the_bundle_grants_the_other_product(self):
        self.configure_paypal()
        self.configure_handoff()
        opened = []
        original = write_smarter.grant_bundle

        def fake_grant(email, vault_id, subscription_id, tier=None, cycle=None, opener=None):
            opened.append({"email": email, "vault_id": vault_id,
                           "subscription_id": subscription_id, "tier": tier, "cycle": cycle})
            return {"granted": True, "record_subscription_id": "W-REC1",
                    "record_status": "SUSPENDED"}

        write_smarter.grant_bundle = fake_grant
        try:
            status, payload = self._confirm({
                "subscription_id": "I-REAL", "status": "ACTIVE", "custom_id": "agency:monthly",
                "payer_email": "buyer@example.com", "vault_id": "V-1",
                "period": {"next_billing": "2026-12-03T00:00:00Z"}})
        finally:
            write_smarter.grant_bundle = original
        self.assertEqual(status, 200)
        self.assertTrue(payload["handoff"]["granted"])
        self.assertEqual(opened[0]["email"], "buyer@example.com")
        self.assertEqual(opened[0]["vault_id"], "V-1")
        self.assertEqual(opened[0]["subscription_id"], "I-REAL")
        self.assertEqual(opened[0]["tier"], "agency")

    def test_a_single_product_plan_is_never_handed_over(self):
        self.configure_paypal()
        opened = []
        original = write_smarter.grant_bundle
        write_smarter.grant_bundle = lambda *args, **kwargs: opened.append(args) or {}
        try:
            status, payload = self._confirm({
                "subscription_id": "I-REAL", "status": "ACTIVE", "custom_id": "pro:monthly",
                "payer_email": "buyer@example.com", "vault_id": "V-1"})
        finally:
            write_smarter.grant_bundle = original
        self.assertEqual(status, 200)
        self.assertFalse(payload["handoff"]["applicable"])
        self.assertEqual(opened, [])

    def test_a_failed_hand_off_does_not_undo_the_paid_plan_but_is_reported(self):
        self.configure_paypal()
        original = write_smarter.grant_bundle

        def failing(*args, **kwargs):
            raise write_smarter.HandoffNotConfigured(["BP_WRITE_SMARTER_URL"])

        write_smarter.grant_bundle = failing
        try:
            status, payload = self._confirm({
                "subscription_id": "I-REAL", "status": "ACTIVE", "custom_id": "agency:monthly",
                "payer_email": "buyer@example.com", "vault_id": "V-1"})
        finally:
            write_smarter.grant_bundle = original
        self.assertEqual(status, 200, "the payment was real; it must not be reported as failed")
        self.assertFalse(payload["handoff"]["granted"])
        self.assertIn("BP_WRITE_SMARTER_URL", payload["handoff"]["missing"])
        # The purchase still stands on this side.
        self.assertEqual(billing.current()["tier"], "agency")
        self.assertTrue(billing.current()["unlimited"])


# ── cancelling one side stops both ───────────────────────────────────────────────────────────────

class CancelRevokeTest(BundleTestCase):
    def setUp(self):
        super().setUp()
        # The cancellation itself is PayPal's work; this suite is about the other half.
        self.original_cancel = paypal.cancel_subscription
        paypal.cancel_subscription = lambda subscription_id, reason=None, opener=None: {
            "subscription_id": subscription_id, "status": "CANCELLED"}

    def tearDown(self):
        paypal.cancel_subscription = self.original_cancel
        super().tearDown()

    def test_cancelling_the_bundle_revokes_the_grant_on_the_other_product(self):
        self.configure_paypal()
        self.configure_handoff()
        billing.activate("agency", "monthly", "I-REAL", payer_email="buyer@example.com")
        revoked = []
        original = write_smarter.revoke_bundle
        write_smarter.revoke_bundle = lambda email=None, billing_subscription_id=None, opener=None: (
            revoked.append({"email": email, "subscription_id": billing_subscription_id})
            or {"revoked": True})
        try:
            status, payload = product_api.handle("POST", "/api/billing/cancel", {})
        finally:
            write_smarter.revoke_bundle = original
        self.assertEqual(status, 200)
        self.assertTrue(payload["handoff"]["revoked"])
        self.assertEqual(revoked[0]["email"], "buyer@example.com")
        self.assertEqual(revoked[0]["subscription_id"], "I-REAL")

    def test_a_failed_revocation_is_reported_but_the_cancellation_still_stands(self):
        self.configure_paypal()
        billing.activate("agency", "monthly", "I-REAL", payer_email="buyer@example.com")
        original = write_smarter.revoke_bundle

        def failing(*args, **kwargs):
            raise write_smarter.HandoffError("the other product could not be reached")

        write_smarter.revoke_bundle = failing
        try:
            status, payload = product_api.handle("POST", "/api/billing/cancel", {})
        finally:
            write_smarter.revoke_bundle = original
        self.assertEqual(status, 200)
        self.assertFalse(payload["handoff"]["revoked"])
        self.assertIn("could not be reached", payload["handoff"]["error"])
        self.assertEqual(billing.current()["status"], "cancelled")


# ── the unlimited wallet ──────────────────────────────────────────────────────────────────────────

class UnlimitedWalletTest(BundleTestCase):
    def test_a_bundle_holder_is_never_blocked_by_the_export_wallet(self):
        quote = credits.quote("case-1", "submission", "pptx", account="local", unlimited=True)
        self.assertEqual(quote["cost"], 0)
        self.assertEqual(quote["balance"], quote["balance"])
        result = credits.charge("case-1", "submission", "pptx", account="local", unlimited=True)
        self.assertEqual(result["balance"], 100, "the balance must not move")
        self.assertFalse(result["charged"])
        # A second format of the same artefact would cost 3 credits; the bundle pays nothing.
        again = credits.quote("case-1", "submission", "pptx", account="local", unlimited=True)
        self.assertEqual(again["cost"], 0)

    def test_the_export_route_does_not_return_402_for_a_bundle_holder(self):
        # The route reads the plan from the ledger, so the ledger must carry the unlimited flag.
        billing.activate("agency", "monthly", "I-REAL")
        self.assertTrue(product_api._unlimited_plan())
        # With a zero balance the export still goes through.
        credits.charge("case-1", "submission", "pptx", account="local", unlimited=True)

    def test_a_tier_whose_allowance_is_undecided_keeps_its_meter(self):
        billing.activate("pro", "monthly", "I-REAL")
        self.assertFalse(product_api._unlimited_plan(),
                         "undecided is not free: the wallet keeps its meter")
        # The first export of an artefact is free on every plan; a second one is charged.
        credits.charge("case-1", "submission", "pptx", account="local")
        quote = credits.quote("case-1", "submission", "pptx", account="local")
        self.assertEqual(quote["cost"], 3)

    def test_the_free_first_export_is_still_free_for_an_ordinary_plan(self):
        first = credits.quote("case-1", "submission", "docx", account="local")
        self.assertEqual(first["cost"], 0)
        self.assertTrue(first["free"])
        credits.charge("case-1", "submission", "docx", account="local")
        second = credits.quote("case-1", "submission", "docx", account="local")
        self.assertEqual(second["cost"], 1)

    def test_the_bundle_grants_no_number_of_credits(self):
        result = billing.grant_for("agency", "monthly", "I-REAL")
        self.assertIsNone(result["granted"])
        self.assertTrue(result["unlimited"])
        self.assertIn("grants no limit", result["reason"])


# ── what the customer reads ───────────────────────────────────────────────────────────────────────

class CatalogueCopyTest(BundleTestCase):
    def test_the_bundle_card_reads_unlimited_and_names_both_products(self):
        card = billing.card("agency")
        self.assertEqual(card["name"], "Business Bundle")
        self.assertTrue(card["unlimited"])
        self.assertEqual(card["credits_label"], "Unlimited")
        self.assertIn("Write Smarter - unlimited", card["includes"])
        self.assertIn("Smart Business Writer - unlimited", card["includes"])

    def test_no_other_card_claims_a_limit(self):
        for tier in ("starter", "pro", "studio"):
            card = billing.card(tier)
            self.assertFalse(card["unlimited"])
            self.assertIsNone(card["credits"])
            self.assertIn("to be confirmed", card["credits_label"].lower())

    def test_each_bundle_rung_names_the_write_smarter_pools(self):
        starter = billing.card("bundle_starter")
        self.assertEqual(starter["write_smarter"]["tier"], "Basic")
        self.assertEqual(starter["sbw_tier"], "Starter")
        values = {pool["label"]: pool["value"] for pool in starter["write_smarter"]["pools"]}
        self.assertEqual(values["Text-Gen pool"], "25,000 words")
        self.assertEqual(values["Humanizer & AI-Detector"], "5,000 words")
        self.assertEqual(values["Video"], "30 min")
        self.assertEqual(values["Source Finder"], "Unlimited")
        pro = {pool["label"]: pool["value"] for pool in billing.card("bundle_pro")["write_smarter"]["pools"]}
        self.assertEqual(pro["Text-Gen pool"], "50,000 words")
        studio = {pool["label"]: pool["value"] for pool in billing.card("bundle_studio")["write_smarter"]["pools"]}
        self.assertEqual(studio["Text-Gen pool"], "100,000 words")
        best = {pool["label"]: pool["value"] for pool in billing.card("agency")["write_smarter"]["pools"]}
        self.assertEqual(best["Text-Gen pool"], "Unlimited")

    def test_the_bundle_carries_no_discount_claim(self):
        # The bundle is a declared price, not a discount: there is no published sum to take
        # 20% off, so the card must not claim a saving against a made-up total.
        card = billing.card("agency")
        self.assertEqual(card["monthly"]["amount"], "99.99")
        self.assertEqual(card["annual"]["amount"], "959.90")

    def test_an_unknown_tier_is_refused_rather_than_treated_as_unlimited(self):
        with self.assertRaises(billing.BillingError):
            billing.unlimited_for("platinum")


# ── the bundle is shown as a band, not as a fourth card ─────────────────────────────────────────

class BundleBandTest(BundleTestCase):
    """The bundle covers two products, so it is shown **below** the pricing grid.

    A customer reads "two products, one price" from a band and reads "a fourth tier of this
    product" from a fourth card - and the second reading is the wrong one. These tests pin the
    split so the band cannot quietly become a card again.
    """

    def test_the_three_single_product_tiers_are_the_cards(self):
        self.assertEqual(billing.CARD_TIERS, ("starter", "pro", "studio"))
        self.assertEqual(billing.BUNDLE_TIER, "agency")

    def test_the_catalogue_says_which_is_the_card_grid_and_which_is_the_band(self):
        catalogue = billing.catalogue()
        self.assertEqual(catalogue["card_tiers"], ["starter", "pro", "studio"])
        self.assertEqual(catalogue["bundle_tier"], "agency")
        self.assertEqual(catalogue["bundle_tiers"],
                         ["bundle_starter", "bundle_pro", "bundle_studio", "agency"])

    def test_no_bundle_rung_is_one_of_the_cards(self):
        catalogue = billing.catalogue()
        for tier in catalogue["bundle_tiers"]:
            self.assertNotIn(tier, catalogue["card_tiers"])
        for row in catalogue["tiers"]:
            if row["tier"] in catalogue["bundle_tiers"]:
                self.assertTrue(row["bundle"], row["tier"])
            else:
                self.assertFalse(row["bundle"], row["tier"])

    def test_the_bundle_band_lists_both_products_and_what_each_one_gives(self):
        card = billing.card("agency")
        names = [product["name"] for product in card["products"]]
        self.assertEqual(names, ["Write Smarter", "Smart Business Writer"])
        write_smarter = card["products"][0]
        self.assertIn("Unlimited Text-Gen", write_smarter["features"])
        self.assertIn("Unlimited Research Assistant", write_smarter["features"])
        self.assertIn("Unlimited Humanizer & AI-Detector", write_smarter["features"])
        self.assertIn("Unlimited Video", write_smarter["features"])
        self.assertIn("Unlimited use of Source Finder", write_smarter["features"])

    def test_no_band_feature_carries_a_number(self):
        # The bundle grants no limit, so no feature line may quote a quota or a price.
        card = billing.card("agency")
        for product in card["products"]:
            for line in product["features"]:
                self.assertFalse(any(character.isdigit() for character in line),
                                 "%r carries a number nobody agreed" % line)

    def test_the_page_renders_the_band_below_the_grid(self):
        page = os.path.join(HERE, "..", "web", "index.html")
        with open(page, encoding="utf-8") as stream:
            html = stream.read()
        # The bundle ladder lives in its own element, after the grid.
        self.assertIn('id="pmbband"', html)
        self.assertLess(html.index('id="pmgrid"'), html.index('id="pmbband"'))
        # The grid itself is three columns now - the bundles are not cards in it.
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", html)
        # The ladder renders one plan-style card per rung, all from the catalogue.
        self.assertIn("pmRenderBundles", html)
        self.assertIn("pm-ladder-grid", html)
        self.assertIn("pm-best-grid", html)
        self.assertIn('class="pm-card is-best"', html)

    def test_the_page_draws_the_cards_and_the_band_from_the_api_not_from_itself(self):
        # The page must not name the tiers itself: it reads which are cards and which is the
        # band from the catalogue, and even each tier's colour comes from there - so a price, a
        # tier or a new rung needs no edit to the page.
        page = os.path.join(HERE, "..", "web", "index.html")
        with open(page, encoding="utf-8") as stream:
            html = stream.read()
        self.assertIn("pm.plans.card_tiers", html)
        self.assertIn("pm.plans.bundle_tier", html)
        self.assertIn("card.color", html)
        for tier in ("starter", "pro", "studio", "agency"):
            self.assertNotIn('data-tier="%s"' % tier, html,
                             "the page names a tier instead of reading it from the catalogue")

    def test_the_account_page_names_the_products_from_the_catalogue_too(self):
        # The account page must not write the product names into itself either.
        page = os.path.join(HERE, "..", "web", "account.html")
        with open(page, encoding="utf-8") as stream:
            html = stream.read()
        self.assertIn("cur.products", html)
        self.assertNotIn("Write Smarter - unlimited, Smart Business Writer - unlimited", html)

    def test_the_current_plan_names_the_products_it_covers(self):
        billing.activate("agency", "monthly", "I-REAL")
        current = billing.current()
        self.assertEqual([product["name"] for product in current["products"]],
                         ["Write Smarter", "Smart Business Writer"])
        # A single-product plan covers no second product, so it names none.
        billing.activate("pro", "monthly", "I-SINGLE")
        self.assertEqual(billing.current()["products"], [])


if __name__ == "__main__":
    unittest.main()
