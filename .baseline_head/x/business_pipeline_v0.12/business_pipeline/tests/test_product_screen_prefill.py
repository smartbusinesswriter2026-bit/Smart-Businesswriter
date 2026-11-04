"""Screening (Phase 3) and prefill (Phase 4): sourced shortlist and frozen-input builders."""

import os
import sys
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import instruments, screener, prefill, api, marketdata  # noqa: E402


def quote(value, as_of, previous=None):
    payload = {"kind": "quote", "symbol": "X", "value": value, "as_of": as_of,
               "source": "Test source", "source_url": "https://example/quote",
               "response_sha256": "deadbeef"}
    if previous is not None:
        payload["previous_close"] = previous
    return payload


def make(symbol, pairs):
    document = instruments.create(symbol)
    for day, price in pairs:
        document = instruments.record(document["id"], quote=quote(price, day))
    return document


def stub_quote(symbol):
    value = "110" if symbol == "AAA" else "90"
    return {"symbol": symbol, "value": value, "previous_close": "100",
            "as_of": "2026-10-10", "source": "Test source", "source_url": "u",
            "response_sha256": "h", "provider": "massive"}


class ScreenerTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.patch = mock.patch.dict(os.environ, {"BP_CASES_DIR": self.folder.name})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.folder.cleanup()

    def test_screen_ranks_by_one_day_return_and_names_gaps(self):
        out = screener.screen(["BBB", "AAA"], criteria={"sort": "one_day_return", "order": "desc"},
                              fetch=stub_quote, provider="massive")
        self.assertEqual(out["count"], 2)
        self.assertEqual(out["rows"][0]["symbol"], "AAA")
        self.assertEqual(Decimal(out["rows"][0]["one_day_return"]), Decimal("0.1"))
        self.assertTrue(any("fundamentals" in gap for gap in out["rows"][0]["gaps"]))

    def test_screen_filters_and_records_a_per_symbol_error(self):
        kept = screener.screen(["AAA", "BBB"], criteria={"filters": [{"metric": "price", "min": "100"}]},
                               fetch=stub_quote)
        self.assertEqual([row["symbol"] for row in kept["rows"]], ["AAA"])

        def boom(_symbol):
            raise marketdata.MarketDataError("no key")

        failed = screener.screen(["AAA"], fetch=boom)
        self.assertEqual(failed["rows"][0]["error"], "no key")
        with self.assertRaises(screener.ScreenerError):
            screener.screen(["S%d" % i for i in range(30)], fetch=stub_quote)

    def test_screen_uses_recorded_history_when_present(self):
        make("AAA", [("2026-10-01", "100"), ("2026-10-02", "110"),
                     ("2026-10-03", "121"), ("2026-10-04", "133.1")])
        out = screener.screen(["AAA"], fetch=stub_quote)
        row = out["rows"][0]
        self.assertEqual(row["n_returns"], 3)
        self.assertIn("mean_return", row)
        self.assertIn("sd", row)
        self.assertIn("cumulative_return", row)


    def test_screen_can_include_fundamentals(self):
        def fund(symbol):
            return {"source": "Alpha Vantage (OVERVIEW)", "as_of": "2026-06-30", "response_sha256": "f",
                    "market_cap": "3000000000000", "pe_ratio": "30.5", "roe": "1.4", "price_to_book": "50"}
        out = screener.screen(["AAA"], fetch=stub_quote, include_fundamentals=True, fetch_fundamentals=fund)
        row = out["rows"][0]
        self.assertEqual(Decimal(row["pe_ratio"]), Decimal("30.5"))
        self.assertEqual(row["market_cap"], "3000000000000")
        self.assertEqual(Decimal(row["roe"]), Decimal("1.4"))
        self.assertFalse(any("fundamentals are not wired" in gap for gap in row["gaps"]))


    def test_screen_derived_fundamentals(self):
        original = marketdata.derived_ratios
        marketdata.derived_ratios = lambda symbol: {
            "source": "Derived: SEC XBRL and Massive", "as_of": "", "response_sha256": "d",
            "market_cap": "20000", "pe_ratio": "20", "roe": "0.2", "gaps": []}
        try:
            out = screener.screen(["AAA"], fetch=stub_quote, include_fundamentals=True,
                                  fundamentals_provider="derived")
        finally:
            marketdata.derived_ratios = original
        row = out["rows"][0]
        self.assertEqual(Decimal(row["pe_ratio"]), Decimal("20"))
        self.assertEqual(Decimal(row["roe"]), Decimal("0.2"))


class PrefillTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.patch = mock.patch.dict(os.environ, {"BP_CASES_DIR": self.folder.name})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.folder.cleanup()

    def test_risk_inputs_from_recorded_returns(self):
        document = make("AAA", [("2026-10-01", "100"), ("2026-10-02", "105"), ("2026-10-03", "110")])
        out = prefill.risk_inputs(document, confidence="0.95")
        self.assertEqual(len(out["inputs"]["returns"]), 2)
        self.assertEqual(out["inputs"]["confidence"], "0.95")
        self.assertTrue(out["ready"])

    def test_portfolio_inputs_align_and_require_a_market_and_rate(self):
        dates = [("2026-10-01", "100"), ("2026-10-02", "101"),
                 ("2026-10-03", "102"), ("2026-10-04", "103")]
        asset_a = make("AAA", dates)
        asset_b = make("BBB", [("2026-10-01", "50"), ("2026-10-02", "51"),
                               ("2026-10-03", "52"), ("2026-10-04", "53")])
        market = make("SPY", [("2026-10-01", "400"), ("2026-10-02", "402"),
                              ("2026-10-03", "404"), ("2026-10-04", "406")])
        ready = prefill.portfolio_inputs(asset_a, asset_b, market=market, risk_free_rate="0.02")
        self.assertTrue(ready["ready"])
        self.assertEqual(len(ready["inputs"]["returns_a"]), 3)
        self.assertEqual(len(ready["inputs"]["returns_market"]), 3)
        self.assertEqual(ready["inputs"]["risk_free_rate"], "0.02")
        missing = prefill.portfolio_inputs(asset_a, asset_b)
        self.assertFalse(missing["ready"])
        self.assertTrue(any("returns_market" in gap for gap in missing["gaps"]))
        self.assertTrue(any("risk_free_rate" in gap for gap in missing["gaps"]))

    def test_capm_inputs_honour_a_declared_beta(self):
        document = make("AAA", [("2026-10-01", "100"), ("2026-10-02", "105")])
        out = prefill.capm_inputs(document, risk_free_rate="0.04", market_return="0.10", beta="1.2")
        self.assertTrue(out["ready"])
        self.assertEqual(out["inputs"]["beta"], "1.2")
        self.assertEqual(out["inputs"]["market_return"], "0.10")


    def test_seed_fills_and_dedupes_history(self):
        document = instruments.create("AAA")
        def hist(symbol, days):
            return {"kind": "history", "source": "Massive (api.massive.com)", "source_url": "u", "response_sha256": "h",
                    "bars": [{"as_of": "2026-10-01", "close": "100"}, {"as_of": "2026-10-02", "close": "110"},
                             {"as_of": "2026-10-03", "close": "121"}, {"as_of": "2026-10-04", "close": "133.1"}]}
        seeded = instruments.seed(document["id"], days=5, fetch=hist)
        self.assertEqual(len(seeded["snapshots"]), 4)
        self.assertTrue(instruments.readiness(seeded)["risk_ready"])
        again = instruments.seed(document["id"], days=5, fetch=hist)
        self.assertEqual(len(again["snapshots"]), 4)


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.patch = mock.patch.dict(os.environ, {"BP_CASES_DIR": self.folder.name})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.folder.cleanup()

    def test_screen_route(self):
        original = marketdata.equity_quote
        marketdata.equity_quote = stub_quote
        try:
            status, out = api.handle("POST", "/api/cases/screen", {"symbols": ["AAA", "BBB"]})
        finally:
            marketdata.equity_quote = original
        self.assertEqual(status, 200)
        self.assertEqual(out["count"], 2)

    def test_prefill_route(self):
        document = make("AAA", [("2026-10-01", "100"), ("2026-10-02", "105"), ("2026-10-03", "110")])
        status, out = api.handle("POST", "/api/cases/prefill", {"target": "risk", "id": document["id"]})
        self.assertEqual(status, 200)
        self.assertEqual(out["target"], "risk")
        self.assertTrue(out["ready"])

    def test_prefill_route_rejects_unknown_target(self):
        status, _payload = api.handle("POST", "/api/cases/prefill", {"target": "wibble"})
        self.assertEqual(status, 422)


    def test_seed_route(self):
        document = instruments.create("AAA")
        original = marketdata.massive_history
        marketdata.massive_history = lambda symbol, days: {
            "bars": [{"as_of": "2026-10-01", "close": "100"}, {"as_of": "2026-10-02", "close": "110"},
                     {"as_of": "2026-10-03", "close": "121"}, {"as_of": "2026-10-04", "close": "133.1"}],
            "source": "Massive", "source_url": "u", "response_sha256": "h"}
        try:
            status, out = api.handle("POST", "/api/cases/instruments/%s/seed" % document["id"], {"days": 5})
        finally:
            marketdata.massive_history = original
        self.assertEqual(status, 200)
        self.assertEqual(out["readiness"]["snapshots"], 4)

    def test_screen_route_with_fundamentals(self):
        original_q, original_f = marketdata.equity_quote, marketdata.fundamentals
        marketdata.equity_quote = stub_quote
        marketdata.fundamentals = lambda symbol, provider="alphavantage": {
            "source": "Alpha Vantage (OVERVIEW)", "as_of": "", "response_sha256": "f",
            "market_cap": "1000", "pe_ratio": "20", "roe": "1.1"}
        try:
            status, out = api.handle("POST", "/api/cases/screen", {"symbols": ["AAA"], "include_fundamentals": True})
        finally:
            marketdata.equity_quote = original_q
            marketdata.fundamentals = original_f
        self.assertEqual(status, 200)
        self.assertEqual(out["rows"][0]["pe_ratio"], "20")


if __name__ == "__main__":
    unittest.main()

