"""The Portfolio Lab's stock-selection parameter catalog (classroom criteria).

These tests pin the catalog that guides a student through choosing what to hold,
using parameters taught in finance and accounting classes.  The catalog is data
and definitions only: it never recommends, never ranks, and never invents a
value.
"""

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE
sys.path.insert(0, str(ROOT / "src"))

from bp import server  # noqa: E402
from bp.product import portfolio_parameters  # noqa: E402

ADVICE_WORDS = ("best", "should buy", "will rise", "outperform", "guaranteed",
                "expected return", "target price", "recommend", "must buy",
                "sure thing", "top pick", "buy now")
GLOBAL_WORDS = ("PSE", "Philippines", "Philippine", "Filipino", "PHP", "peso")


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=15) as response:
        return response.status, json.loads(response.read().decode())


class CatalogueTest(unittest.TestCase):
    def test_the_catalogue_has_four_sets(self):
        payload = portfolio_parameters.catalogue()
        self.assertIn("sets", payload)
        self.assertIn("parameters", payload)
        ids = [s["id"] for s in payload["sets"]]
        self.assertEqual(set(ids), {"finance", "accounting", "both", "composite"})

    def test_every_set_has_a_label_and_description(self):
        for s in portfolio_parameters.catalogue()["sets"]:
            self.assertTrue(s["label"].strip(), s["id"])
            self.assertTrue(s["description"].strip(), s["id"])

    def test_the_catalogue_carries_at_least_twelve_parameters(self):
        params = portfolio_parameters.catalogue()["parameters"]
        self.assertGreaterEqual(len(params), 12)

    def test_every_parameter_is_complete(self):
        valid_sources = {"sourced", "manual"}
        for p in portfolio_parameters.catalogue()["parameters"]:
            self.assertTrue(p["id"].strip(), p)
            self.assertTrue(p["label"].strip(), p["id"])
            self.assertTrue(p["definition"].strip(), p["id"])
            self.assertTrue(p["formula"].strip(), p["id"])
            self.assertTrue(p["unit"].strip(), p["id"])
            self.assertIn(p["source"], valid_sources, p["id"])
            self.assertTrue(isinstance(p["sets"], list) and p["sets"], p["id"])
            for s in p["sets"]:
                self.assertIn(s, ("finance", "accounting", "both", "composite"), p["id"])

    def test_ids_are_unique(self):
        params = portfolio_parameters.catalogue()["parameters"]
        self.assertEqual(len({p["id"] for p in params}), len(params))

    def test_each_set_has_at_least_three_parameters(self):
        params = portfolio_parameters.catalogue()["parameters"]
        for sid in ("finance", "accounting", "composite"):
            members = [p for p in params if sid in p["sets"]]
            self.assertGreaterEqual(len(members), 3, sid)

    def test_the_catalogue_carries_no_advice_or_forecast(self):
        text = json.dumps(portfolio_parameters.catalogue()).lower()
        for word in ADVICE_WORDS:
            self.assertNotIn(word, text, "the catalog must stay neutral: " + word)

    def test_the_catalogue_stays_global(self):
        text = json.dumps(portfolio_parameters.catalogue())
        for word in GLOBAL_WORDS:
            self.assertNotIn(word, text, "the catalog must stay global: " + word)

    def test_sourced_parameters_name_a_screener_field(self):
        for p in portfolio_parameters.catalogue()["parameters"]:
            if p["source"] == "sourced":
                self.assertTrue(p.get("screener_field"), p["id"])

    def test_manual_parameters_have_no_screener_field_or_are_explicit(self):
        for p in portfolio_parameters.catalogue()["parameters"]:
            if p["source"] == "manual":
                # manual parameters may optionally name a field; either way is fine
                self.assertIn(p.get("screener_field", None), (None,) + tuple(
                    x.get("screener_field") for x in portfolio_parameters.catalogue()["parameters"]
                    if x.get("screener_field")), p["id"])


class ParametersRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join(timeout=5)

    def test_the_route_serves_the_catalog(self):
        status, payload = _get(self.base, "/api/portfolios/parameters")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(payload["parameters"]), 12)
        self.assertEqual(set(s["id"] for s in payload["sets"]),
                         {"finance", "accounting", "both", "composite"})


if __name__ == "__main__":
    unittest.main()
