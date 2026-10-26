import sys, json, threading, unittest, urllib.request
from decimal import Decimal as D
sys.path.insert(0, "src")
from http.server import ThreadingHTTPServer
from bp import currency, accounts, server
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline

YES = lambda s: True
CONV = {"amount": "1000", "from_currency": "USD", "to_currency": "EUR", "rate": "0.92", "rate_provenance": "user", "rate_date": "2026-10-20"}


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class Registry(unittest.TestCase):
    def test_major_and_minor_units(self):
        self.assertEqual([currency.minor_units(c) for c in ("USD", "EUR", "CNY", "GBP", "PHP")], [2, 2, 2, 2, 2])
        self.assertEqual([currency.minor_units(c) for c in ("JPY", "KRW", "VND", "ISK")], [0, 0, 0, 0])
        self.assertEqual([currency.minor_units(c) for c in ("KWD", "BHD", "OMR")], [3, 3, 3])
        self.assertEqual(currency.minor_units("CLF"), 4)

    def test_world_coverage_and_catalog(self):
        self.assertGreater(len(currency.codes()), 140)
        for c in ("USD", "EUR", "CNY", "JPY", "GBP", "INR", "BRL", "ZAR", "PHP", "AED", "KWD"):
            self.assertIn(c, currency.codes())
        cat = currency.catalog(); self.assertEqual([r["code"] for r in cat], sorted(currency.codes()))
        self.assertEqual(cat[0]["code"], "AED"); self.assertTrue(all(set(r) == {"code", "name", "minor_units"} for r in cat))

    def test_normalisation_and_unknown_codes(self):
        self.assertEqual(currency.normalize(" eur "), "EUR")
        for bad in ("XYZ", "", None, "US"):
            with self.assertRaises(currency.CurrencyError): currency.minor_units(bad)


class Conversion(unittest.TestCase):
    def test_declared_rate_arithmetic(self):
        out = currency.convert("1000", "USD", "EUR", "0.92")
        self.assertEqual(out["amount"], D("920.00")); self.assertEqual((out["from_currency"], out["to_currency"]), ("USD", "EUR"))
        self.assertEqual(currency.convert("1000", "EUR", "CNY", "7.8")["amount"], D("7800.0"))
        self.assertEqual(currency.convert("100", "CNY", "JPY", "20.4")["amount"], D("2040.0"))

    def test_same_currency_requires_rate_one(self):
        self.assertEqual(currency.convert("5", "USD", "usd", "1")["amount"], D(5))
        with self.assertRaises(currency.CurrencyError): currency.convert("5", "USD", "USD", "2")

    def test_provenance_rules(self):
        out = currency.convert("1", "USD", "EUR", "0.9", rate_provenance="assumption")
        self.assertEqual(out["rate_provenance"], "assumption"); self.assertIn("not retrieved or verified", out["provenance_note"])
        with self.assertRaises(currency.CurrencyError): currency.convert("1", "USD", "EUR", "0.9", rate_provenance="sourced")
        self.assertEqual(currency.convert("1", "USD", "EUR", "0.9", rate_provenance="sourced", rate_source="ECB reference")["rate_source"], "ECB reference")
        with self.assertRaises(currency.CurrencyError): currency.convert("1", "USD", "EUR", "0.9", rate_provenance="guess")

    def test_invalid_amounts_rates_and_codes_are_refused(self):
        for args in (("1", "USD", "XYZ", "0.9"), ("1", "USD", "EUR", "0"), ("1", "USD", "EUR", "-2"), ("abc", "USD", "EUR", "0.9")):
            with self.assertRaises(currency.CurrencyError): currency.convert(*args)


class InPipeline(unittest.TestCase):
    def test_delivery_reports_the_conversion_and_the_declared_rate(self):
        d = delivered({"objective": "Convert the invoice", "method": "currency_convert", "currency": "EUR", "period": "cross_section", "inputs": CONV})
        self.assertIn("converts to", d.report); self.assertIn("not retrieved or verified", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 3)
        ap = d.appendix["accounts"]
        self.assertEqual((ap["from_currency"], ap["to_currency"], ap["rate"], ap["rate_provenance"]), ("USD", "EUR", "0.92", "user"))
        self.assertEqual(ap["converted"], "920.00")
        self.assertTrue(all(ok for ok in d.appendix["tests"]))

    def test_currency_precision_follows_the_currency(self):
        req = {"objective": "Invest?", "method": "npv", "period": "annual", "inputs": {"rate": "0.10", "cashflows": ["-1000", "400", "400", "400"]}}
        jpy = delivered({**req, "currency": "JPY"}); kwd = delivered({**req, "currency": "KWD"}); usd = delivered({**req, "currency": "USD"})
        self.assertIn("JPY (5)", jpy.report)          # no minor units: rounded to a whole yen
        self.assertIn("KWD (5.259)", kwd.report)      # three minor units
        self.assertIn("USD (5.26)", usd.report)       # two minor units

    def test_unknown_currency_is_refused_at_intake(self):
        d = Pipeline().run({"objective": "Invest?", "method": "npv", "currency": "XYZ",
                            "inputs": {"rate": "0.10", "cashflows": ["-1000", "400", "400", "400"]}}, YES)
        self.assertEqual(d.status, "blocked"); self.assertIn("unknown currency", d.blocked_reason)

    def test_accounts_places_default_from_the_currency(self):
        self.assertEqual(accounts._default_places({"currency": "JPY"}), 0)
        self.assertEqual(accounts._default_places({"currency": "KWD"}), 3)
        self.assertEqual(accounts._default_places({"currency": "USD"}), 2)
        bad = accounts.validate_spec({"currency": "XYZ"})
        self.assertTrue(any("unknown currency" in e for e in bad))


class CurrencyApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H); cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown(); cls.srv.server_close()

    def test_catalog_endpoint_lists_world_currencies_and_no_rate_service(self):
        with urllib.request.urlopen(self.base + "/api/currencies") as r: b = json.loads(r.read())
        codes = [c["code"] for c in b["currencies"]]
        for c in ("USD", "EUR", "CNY", "JPY", "KWD"): self.assertIn(c, codes)
        self.assertEqual(b["currencies"][[c["code"] for c in b["currencies"]].index("JPY")]["minor_units"], 0)
        self.assertIn("No exchange rates are provided", b["note"])


class Contract(unittest.TestCase):
    def test_registration_and_preset(self):
        m = LIBRARY["currency_convert"]
        self.assertEqual((m.tier, m.claim_ceiling, m.metric, m.unit), ("T1", "descriptive", "amount", "currency"))
        self.assertIn("currency", server.PRESETS); self.assertEqual(server.PRESETS["currency"]["method"], "currency_convert")
        self.assertEqual(server.PRESETS["currency"]["currency"], "EUR")

    def test_deterministic(self):
        m = LIBRARY["currency_convert"]
        self.assertEqual({k: str(v) for k, v in m.impl(CONV).items() if not k.startswith("_")},
                         {k: str(v) for k, v in m.impl(CONV).items() if not k.startswith("_")})


if __name__ == "__main__":
    unittest.main()
