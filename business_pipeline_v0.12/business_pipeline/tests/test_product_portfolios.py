"""Portfolio store, snapshot integration and the Portfolio Lab routes."""

import base64
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
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


if __name__ == "__main__":
    unittest.main()
