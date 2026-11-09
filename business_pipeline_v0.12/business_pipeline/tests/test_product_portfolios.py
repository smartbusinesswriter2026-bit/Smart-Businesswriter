"""Portfolio store, snapshot integration and the Portfolio Lab routes."""

import base64
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
import zipfile
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods, server  # noqa: E402
from bp.product import portfolio_docx, portfolios  # noqa: E402


def _post(base, path, body):
    request = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, json.loads(response.read())


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=20) as response:
        return response.status, json.loads(response.read())


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-portfolios-")
        self.previous = os.environ.get("BP_PORTFOLIOS_DIR")
        os.environ["BP_PORTFOLIOS_DIR"] = self.root

    def tearDown(self):
        if self.previous is None: os.environ.pop("BP_PORTFOLIOS_DIR", None)
        else: os.environ["BP_PORTFOLIOS_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_create_add_price_snapshot_and_delete(self):
        portfolio = portfolios.create("Paper portfolio", "USD", "S&P 500", "paper")
        self.assertEqual(portfolio["mode"], "paper")
        self.assertEqual(portfolios.summaries()[0]["name"], "Paper portfolio")
        portfolios.add_holding(portfolio["id"], "AAPL", "10", "150")
        portfolios.add_holding(portfolio["id"], "MSFT", "5", "350")
        portfolios.set_price(portfolio["id"], "AAPL", "2026-10-30", "200")
        portfolios.set_price(portfolio["id"], "MSFT", "2026-10-30", "400")
        inputs = {"holdings": [{"symbol": "AAPL", "shares": "10", "price": "200"},
                                {"symbol": "MSFT", "shares": "5", "price": "400"}], "cash": "1000"}
        method = methods.LIBRARY["portfolio_valuation"]
        outputs = method.impl(inputs)
        appendix = outputs.pop("_appendix")
        outputs.pop("_checks", None)
        snapshot = portfolios.save_snapshot(portfolio["id"], {
            "date": "2026-10-30", "inputs": inputs,
            "outputs": {key: str(value) for key, value in outputs.items()},
            "positions": appendix["positions"], "prices": {}, "checks": [], "method": "portfolio_valuation",
        })
        self.assertEqual(snapshot["outputs"]["nav"], "5000")
        bundle = portfolios.load(portfolio["id"])
        self.assertEqual(bundle["snapshots"][0]["nav"], "5000")
        with self.assertRaises(portfolios.PortfolioError):
            portfolios.save_snapshot(portfolio["id"], {"date": "2026-10-30", "outputs": {}})
        data, filename = portfolio_docx.render(portfolio, snapshot)
        self.assertTrue(data.startswith(b"PK"))
        self.assertTrue(filename.endswith(".docx"))
        portfolios.delete(portfolio["id"])
        self.assertEqual(portfolios.summaries(), [])

    def test_prices_are_refused_for_an_unknown_holding(self):
        portfolio = portfolios.create("Empty")
        with self.assertRaises(ValueError):
            portfolios.set_price(portfolio["id"], "AAPL", "2026-10-30", "200")

    def test_pasted_rows_import_in_one_write(self):
        portfolio = portfolios.create("Imported")
        rows = portfolios.import_holdings(
            portfolio["id"], "Symbol,Shares,Cost basis\nAAPL,10,150\nMSFT,5,350")
        self.assertEqual([row["symbol"] for row in rows], ["AAPL", "MSFT"])
        document = portfolios.import_prices(
            portfolio["id"], "Symbol,Price,Source\nAAPL,200,user\nMSFT,400,user", "2026-10-30")
        self.assertEqual(document["prices"]["AAPL"]["price"], "200")
        self.assertEqual(document["prices"]["MSFT"]["source"], "user")

    def test_tabbed_rows_without_a_header_import(self):
        portfolio = portfolios.create("Tabbed")
        rows = portfolios.import_holdings(portfolio["id"], "AAPL\t10\nMSFT\t5")
        self.assertEqual(len(rows), 2)
        document = portfolios.import_prices(portfolio["id"], "AAPL\t200\nMSFT\t400", "2026-10-30")
        self.assertEqual(set(document["prices"]), {"AAPL", "MSFT"})

    def test_one_bad_row_refuses_the_whole_paste(self):
        portfolio = portfolios.create("Bad paste")
        with self.assertRaises(ValueError):
            portfolios.import_holdings(portfolio["id"], "AAPL,10\nMSFT,oops")
        self.assertEqual(portfolios.load(portfolio["id"])["holdings"], [])
        with self.assertRaises(ValueError):
            portfolios.import_holdings(portfolio["id"], "AAPL,10\nAAPL,5")
        self.assertEqual(portfolios.load(portfolio["id"])["holdings"], [])

    def test_price_import_refuses_an_unknown_symbol_and_a_saved_date(self):
        portfolio = portfolios.create("Price rules")
        portfolios.import_holdings(portfolio["id"], "AAPL,10")
        with self.assertRaises(ValueError):
            portfolios.import_prices(portfolio["id"], "MSFT,400", "2026-10-30")
        portfolios.import_prices(portfolio["id"], "AAPL,200", "2026-10-30")
        portfolios.save_snapshot(portfolio["id"], {"date": "2026-10-30", "outputs": {}})
        with self.assertRaises(portfolios.PortfolioError):
            portfolios.import_prices(portfolio["id"], "AAPL,201", "2026-10-30")


    def test_the_journal_keeps_the_students_words_and_flow(self):
        portfolio = portfolios.create("Fund journal", mode="fund", objective="Learn", roster="A, B")
        entry = portfolios.save_journal(portfolio["id"], "2026-10-31", note="Added cash",
                                        flow="500", benchmark="4300")
        self.assertEqual(entry["flow"], "500")
        self.assertEqual(entry["benchmark"], "4300")
        self.assertEqual(portfolios.load(portfolio["id"])["journal"][0]["note"], "Added cash")
        portfolios.save_journal(portfolio["id"], "2026-10-31", note="Revised", flow="0", benchmark="")
        self.assertEqual(portfolios.journal(portfolio["id"])[0]["note"], "Revised")
        portfolios.remove_journal(portfolio["id"], "2026-10-31")
        self.assertEqual(portfolios.journal(portfolio["id"]), [])
        with self.assertRaises(ValueError):
            portfolios.save_journal(portfolio["id"], "2026-10-31", benchmark="-1")


class RoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="bp-portfolios-routes-")
        cls.previous = os.environ.get("BP_PORTFOLIOS_DIR")
        os.environ["BP_PORTFOLIOS_DIR"] = cls.root
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join(timeout=5)
        if cls.previous is None: os.environ.pop("BP_PORTFOLIOS_DIR", None)
        else: os.environ["BP_PORTFOLIOS_DIR"] = cls.previous
        shutil.rmtree(cls.root, ignore_errors=True)

    def test_create_hold_snapshot_export(self):
        status, portfolio = _post(self.base, "/api/portfolios",
                                  {"name": "Route paper", "base_currency": "USD", "benchmark": "S&P 500"})
        self.assertEqual(status, 201)
        pid = portfolio["id"]
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "AAPL", "shares": "10", "cost_basis": "150"})
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "MSFT", "shares": "5", "cost_basis": "350"})
        status, snapshot = _post(self.base, "/api/portfolios/%s/snapshot" % pid,
                                 {"date": "2026-10-30", "cash": "1000",
                                  "prices": {"AAPL": {"price": "200"}, "MSFT": {"price": "400"}}})
        self.assertEqual(status, 201)
        self.assertEqual(snapshot["outputs"]["nav"], "5000")
        self.assertEqual(len(snapshot["positions"]), 2)
        status, exported = _post(self.base, "/api/portfolios/%s/export" % pid, {"format": "docx"})
        self.assertEqual(status, 200)
        self.assertTrue(base64.b64decode(exported["data"]).startswith(b"PK"))
        status, bundle = _get(self.base, "/api/portfolios/%s" % pid)
        self.assertEqual(status, 200)
        self.assertEqual(bundle["portfolio"]["name"], "Route paper")
        self.assertEqual(len(bundle["snapshots"]), 1)
        status, stored = _get(self.base, "/api/portfolios/%s/snapshot/2026-10-30" % pid)
        self.assertEqual(status, 200)
        self.assertEqual(stored["outputs"]["nav"], "5000")

    def test_a_snapshot_without_every_price_is_refused(self):
        _, portfolio = _post(self.base, "/api/portfolios", {"name": "Missing price"})
        pid = portfolio["id"]
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "AAPL", "shares": "10"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            _post(self.base, "/api/portfolios/%s/snapshot" % pid, {"date": "2026-10-30"})
        self.assertEqual(caught.exception.code, 422)
        body = json.loads(caught.exception.read())
        self.assertIn("missing prices", body["error"])

    def test_paste_import_routes_feed_the_snapshot(self):
        _, portfolio = _post(self.base, "/api/portfolios", {"name": "Imported route"})
        pid = portfolio["id"]
        status, rows = _post(self.base, "/api/portfolios/%s/holdings/import" % pid,
                             {"text": "Symbol,Shares\nAAPL,10\nMSFT,5"})
        self.assertEqual(status, 200)
        self.assertEqual(len(rows["holdings"]), 2)
        status, prices = _post(self.base, "/api/portfolios/%s/prices/import" % pid,
                               {"date": "2026-10-31", "text": "AAPL,200\nMSFT,400"})
        self.assertEqual(status, 200)
        self.assertEqual(set(prices["prices"]), {"AAPL", "MSFT"})
        status, snapshot = _post(self.base, "/api/portfolios/%s/snapshot" % pid,
                                 {"date": "2026-10-31", "cash": "0"})
        self.assertEqual(status, 201)
        self.assertEqual(snapshot["outputs"]["nav"], "4000")

    def test_a_bad_paste_is_refused_with_422(self):
        _, portfolio = _post(self.base, "/api/portfolios", {"name": "Bad paste route"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            _post(self.base, "/api/portfolios/%s/holdings/import" % portfolio["id"],
                  {"text": "AAPL,nope"})
        self.assertEqual(caught.exception.code, 422)
        body = json.loads(caught.exception.read())
        self.assertIn("row 1", body["error"])


    def test_fund_performance_and_journal_routes(self):
        _, portfolio = _post(self.base, "/api/portfolios",
                             {"name": "Fund route", "mode": "fund", "objective": "Learn"})
        pid = portfolio["id"]
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "AAPL", "shares": "10"})
        _post(self.base, "/api/portfolios/%s/prices" % pid,
              {"symbol": "AAPL", "date": "2026-10-24", "price": "200"})
        _post(self.base, "/api/portfolios/%s/snapshot" % pid, {"date": "2026-10-24", "cash": "0"})
        _post(self.base, "/api/portfolios/%s/prices" % pid,
              {"symbol": "AAPL", "date": "2026-10-31", "price": "220"})
        _post(self.base, "/api/portfolios/%s/snapshot" % pid, {"date": "2026-10-31", "cash": "0"})
        _post(self.base, "/api/portfolios/%s/journal" % pid,
              {"date": "2026-10-24", "note": "Start", "flow": "0", "benchmark": "100"})
        _post(self.base, "/api/portfolios/%s/journal" % pid,
              {"date": "2026-10-31", "note": "Held", "flow": "0", "benchmark": "102"})
        status, performance = _get(self.base, "/api/portfolios/%s/performance" % pid)
        self.assertEqual(status, 200)
        self.assertEqual(performance["outputs"]["twr"], "0.1")
        self.assertTrue(performance["benchmark_used"])
        self.assertEqual(performance["outputs"]["benchmark_return"], "0.02")
        status, exported = _post(self.base, "/api/portfolios/%s/export" % pid, {"format": "docx"})
        self.assertEqual(status, 200)
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(exported["data"]))) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("Time-weighted return", xml)
        self.assertIn("Journal of decisions", xml)
        self.assertIn("Held", xml)
        self.assertIn("All 12 checks passed", xml)
        self.assertNotIn("second_implementation_agrees", xml)

    def test_a_missing_benchmark_is_named_not_filled(self):
        _, portfolio = _post(self.base, "/api/portfolios", {"name": "No benchmark", "mode": "fund"})
        pid = portfolio["id"]
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "AAPL", "shares": "10"})
        _post(self.base, "/api/portfolios/%s/prices" % pid,
              {"symbol": "AAPL", "date": "2026-10-24", "price": "200"})
        _post(self.base, "/api/portfolios/%s/snapshot" % pid, {"date": "2026-10-24", "cash": "0"})
        _post(self.base, "/api/portfolios/%s/prices" % pid,
              {"symbol": "AAPL", "date": "2026-10-31", "price": "220"})
        _post(self.base, "/api/portfolios/%s/snapshot" % pid, {"date": "2026-10-31", "cash": "0"})
        status, performance = _get(self.base, "/api/portfolios/%s/performance" % pid)
        self.assertEqual(status, 200)
        self.assertFalse(performance["benchmark_used"])
        self.assertNotIn("benchmark_return", performance["outputs"])

    def test_performance_needs_two_snapshots(self):
        _, portfolio = _post(self.base, "/api/portfolios", {"name": "One snapshot", "mode": "fund"})
        pid = portfolio["id"]
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "AAPL", "shares": "10"})
        _post(self.base, "/api/portfolios/%s/prices" % pid,
              {"symbol": "AAPL", "date": "2026-10-24", "price": "200"})
        _post(self.base, "/api/portfolios/%s/snapshot" % pid, {"date": "2026-10-24", "cash": "0"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            _get(self.base, "/api/portfolios/%s/performance" % pid)
        self.assertEqual(caught.exception.code, 422)

    def test_fetch_prices_uses_the_configured_source_and_names_failures(self):
        from bp.product import marketdata
        _, portfolio = _post(self.base, "/api/portfolios", {"name": "Fetch route"})
        pid = portfolio["id"]
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "AAPL", "shares": "10"})
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "MSFT", "shares": "5"})
        previous = (marketdata.status, marketdata.equity_quote)
        marketdata.status = lambda: {"sources": {"equity": True}, "alpha_key_env": "BP_ALPHAVANTAGE_KEY"}

        def fake_quote(symbol):
            if symbol == "MSFT":
                raise marketdata.MarketDataError("quota exhausted")
            return {"value": "210", "as_of": "2026-10-30", "source": "Alpha Vantage (free tier)"}

        marketdata.equity_quote = fake_quote
        try:
            status, result = _post(self.base, "/api/portfolios/%s/prices/fetch" % pid,
                                   {"date": "2026-10-31"})
        finally:
            marketdata.status, marketdata.equity_quote = previous
        self.assertEqual(status, 200)
        self.assertEqual(result["prices"]["AAPL"]["price"], "210")
        self.assertEqual(result["prices"]["AAPL"]["as_of"], "2026-10-30")
        self.assertEqual(result["failed"][0]["symbol"], "MSFT")
        stored = portfolios.prices(pid, "2026-10-31")
        self.assertEqual(stored["prices"]["AAPL"]["as_of"], "2026-10-30")
        self.assertEqual(stored["prices"]["AAPL"]["source"], "Alpha Vantage (free tier)")

    def test_fetch_prices_without_a_key_is_refused(self):
        from bp.product import marketdata
        _, portfolio = _post(self.base, "/api/portfolios", {"name": "No key"})
        pid = portfolio["id"]
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "AAPL", "shares": "10"})
        previous = marketdata.status
        marketdata.status = lambda: {"sources": {"equity": False}}
        try:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                _post(self.base, "/api/portfolios/%s/prices/fetch" % pid, {"date": "2026-10-31"})
        finally:
            marketdata.status = previous
        self.assertEqual(caught.exception.code, 422)
        self.assertIn("BP_ALPHAVANTAGE_KEY", json.loads(caught.exception.read())["error"])

    def test_fetch_prices_refuses_a_date_with_a_saved_snapshot(self):
        _, portfolio = _post(self.base, "/api/portfolios", {"name": "Saved date"})
        pid = portfolio["id"]
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "AAPL", "shares": "10"})
        _post(self.base, "/api/portfolios/%s/prices" % pid,
              {"symbol": "AAPL", "date": "2026-10-31", "price": "200"})
        _post(self.base, "/api/portfolios/%s/snapshot" % pid, {"date": "2026-10-31", "cash": "0"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            _post(self.base, "/api/portfolios/%s/prices/fetch" % pid, {"date": "2026-10-31"})
        self.assertEqual(caught.exception.code, 422)

    def test_a_daily_quota_returns_429_with_the_manual_fallback(self):
        from bp.product import marketdata
        _, portfolio = _post(self.base, "/api/portfolios", {"name": "Quota"})
        pid = portfolio["id"]
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "AAPL", "shares": "10"})
        previous = (marketdata.status, marketdata.equity_quote)
        marketdata.status = lambda: {"sources": {"equity": True}}

        def quota(symbol):
            raise marketdata.MarketDataQuota("25 requests per day")

        marketdata.equity_quote = quota
        try:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                _post(self.base, "/api/portfolios/%s/prices/fetch" % pid, {"date": "2026-10-31"})
        finally:
            marketdata.status, marketdata.equity_quote = previous
        self.assertEqual(caught.exception.code, 429)
        body = json.loads(caught.exception.read())
        self.assertTrue(body["quota"])
        self.assertIn("manually", body["error"])

    def test_evidence_upload_snapshot_and_export(self):
        _, portfolio = _post(self.base, "/api/portfolios", {"name": "Evidence route"})
        pid = portfolio["id"]
        _post(self.base, "/api/portfolios/%s/holdings" % pid, {"symbol": "AAPL", "shares": "10", "cost_basis": "150"})
        _post(self.base, "/api/portfolios/%s/prices" % pid,
              {"symbol": "AAPL", "date": "2026-11-09", "price": "150", "source": "user"})
        raw = base64.b64encode(b"fake png bytes").decode("ascii")
        status, meta = _post(self.base, "/api/portfolios/%s/evidence" % pid,
                             {"date": "2026-11-09", "filename": "shot.png",
                              "mime": "image/png", "content": raw})
        self.assertEqual(status, 200)
        self.assertEqual(meta["filename"], "shot.png")
        self.assertEqual(len(meta["sha256"]), 64)
        status, snapshot = _post(self.base, "/api/portfolios/%s/snapshot" % pid,
                                 {"date": "2026-11-09", "cash": "0",
                                  "prices": {"AAPL": {"price": "150", "source": "user"}},
                                  "evidence": [{"filename": meta["filename"],
                                                "sha256": meta["sha256"],
                                                "captured_at": meta["captured_at"],
                                                "mime": meta["mime"],
                                                "size_bytes": meta["size_bytes"]}]})
        self.assertEqual(status, 201)
        self.assertEqual(len(snapshot["evidence"]), 1)
        self.assertEqual(snapshot["evidence"][0]["filename"], "shot.png")
        status, exported = _post(self.base, "/api/portfolios/%s/export" % pid, {"format": "docx"})
        self.assertEqual(status, 200)
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(exported["data"]))) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
            names = archive.namelist()
        self.assertIn("Price evidence", xml)
        self.assertIn("shot.png", xml)
        # a swapped evidence hash is refused
        with self.assertRaises(urllib.error.HTTPError) as caught:
            _post(self.base, "/api/portfolios/%s/snapshot" % pid,
                  {"date": "2026-11-10", "cash": "0",
                   "prices": {"AAPL": {"price": "150", "source": "user"}},
                   "evidence": [{"filename": "shot.png", "sha256": "0" * 64,
                                 "captured_at": meta["captured_at"]}]})
        self.assertEqual(caught.exception.code, 422)


if __name__ == "__main__":
    unittest.main()
