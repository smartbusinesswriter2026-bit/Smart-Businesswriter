"""The Portfolio Lab's instrument guide and chooser (B-178).

The owner asked for guidance on choosing what to hold, with the system offering
choices and prefilling - without the app recommending an investment. These tests
pin four things: the reference list is neutral and sourced, the example books are
labelled examples, the served page carries the guide, the chooser and the reason
field, and the create flow never reports a missing name without the field.
"""

import json
import pathlib
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp import server  # noqa: E402
from bp.product import instruments  # noqa: E402

PAGE = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

ADVICE_WORDS = ("best", "should buy", "will rise", "outperform", "guaranteed",
                "expected return", "target price", "recommend", "must buy",
                "sure thing", "top pick", "buy now")
GLOBAL_WORDS = ("PSE", "Philippines", "Philippine", "Filipino", "PHP", "peso")


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=15) as response:
        return response.status, json.loads(response.read().decode())


def _post(base, path, body):
    request = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode() or "{}")


class CatalogueTest(unittest.TestCase):
    def test_the_catalogue_is_complete_and_unique(self):
        rows = instruments.catalogue()
        self.assertGreaterEqual(len(rows), 12)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        self.assertEqual(len({row["symbol"] for row in rows}), len(rows))
        for row in rows:
            self.assertIn(row["asset_class"], ("etf", "equity"), row["symbol"])
            self.assertEqual(row["currency"], "USD", row["symbol"])
            self.assertRegex(row["symbol"], r"^[A-Z0-9.\-]{1,12}$")
            self.assertTrue(row["name"].strip(), row["symbol"])
            self.assertTrue(row["description"].strip(), row["symbol"])
            self.assertTrue(row["teaching_note"].strip(), row["symbol"])
            self.assertIsInstance(row["quote_supported"], bool, row["symbol"])

    def test_every_instrument_names_a_source(self):
        for row in instruments.catalogue():
            self.assertTrue(row["source_url"].startswith("https://"), row["symbol"])

    def test_no_instrument_carries_advice_or_a_forecast(self):
        text = json.dumps(instruments.catalogue()).lower()
        for word in ADVICE_WORDS:
            self.assertNotIn(word, text, "the reference list must stay neutral: " + word)

    def test_find_resolves_a_known_symbol_and_refuses_an_unknown_one(self):
        self.assertEqual(instruments.find("voo")["symbol"], "VOO")
        self.assertIsNone(instruments.find("NOT-A-LISTING"))

    def test_sample_books_use_only_catalogued_symbols(self):
        known = {row["symbol"] for row in instruments.catalogue()}
        books = instruments.sample_books()
        self.assertGreaterEqual(len(books), 3)
        for book in books:
            self.assertTrue(book["holdings"], book["id"])
            for holding in book["holdings"]:
                self.assertIn(holding["symbol"], known, book["id"])
                self.assertGreater(float(holding["shares"]), 0, book["id"])
            self.assertGreaterEqual(float(book["cash"]), 0, book["id"])

    def test_example_books_are_labelled_examples_not_advice(self):
        for book in instruments.sample_books():
            note = book["note"].lower()
            self.assertIn("example only", note, book["id"])
            self.assertIn("not advice", note, book["id"])
        text = json.dumps(instruments.sample_books()).lower()
        for word in ADVICE_WORDS:
            self.assertNotIn(word, text, "an example book must not read as advice: " + word)

    def test_the_guide_is_a_decision_aid_with_ordered_steps(self):
        guide = instruments.guidance()
        self.assertTrue(guide["intro"].strip())
        self.assertGreaterEqual(len(guide["steps"]), 5)
        for step in guide["steps"]:
            self.assertTrue(step["title"].strip())
            self.assertTrue(step["text"].strip())
        self.assertTrue(guide["principles"])
        self.assertTrue(guide["limits"])
        combined = (guide["intro"] + " ".join(step["text"] for step in guide["steps"])).lower()
        self.assertIn("does not recommend", combined)

    def test_the_whole_bundle_stays_global(self):
        text = json.dumps(instruments.bundle(), ensure_ascii=False)
        for word in GLOBAL_WORDS:
            self.assertNotIn(word, text, "the portfolio guide must stay global: " + word)


class BundleRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join(timeout=5)

    def test_the_route_serves_the_guide_the_list_and_the_books(self):
        status, payload = _get(self.base, "/api/portfolios/instruments")
        self.assertEqual(status, 200)
        self.assertEqual(payload["format"], "bp-instruments/1")
        self.assertTrue(payload["guidance"]["steps"])
        self.assertGreaterEqual(len(payload["instruments"]), 12)
        self.assertGreaterEqual(len(payload["sample_books"]), 3)

    def test_the_route_is_read_only(self):
        status, _ = _post(self.base, "/api/portfolios/instruments", {})
        self.assertEqual(status, 405)


class PageCarriesTheGuideTest(unittest.TestCase):
    def test_the_page_carries_the_guide_and_the_chooser(self):
        # The B-185 redesign put the reference list behind a collapsible card, so the
        # chooser is reached through "Browse the reference list" instead of a bare heading.
        for marker in ("pfGuidanceCard", "Browse the reference list",
                       "data-pfinstrument", "data-pfsample", "pfInstrumentRows",
                       "/api/portfolios/instruments"):
            self.assertIn(marker, PAGE)

    def test_the_page_collects_a_reason_for_each_holding(self):
        self.assertIn('id="pfhwhy"', PAGE)
        self.assertIn("Why you hold it", PAGE)
        self.assertIn("rationale: rationale", PAGE)
        self.assertIn("Holdings and rationale", PAGE)

    def test_the_create_flow_never_reports_a_missing_name_without_the_field(self):
        self.assertIn('id="pfname"', PAGE)
        self.assertIn("pfcreate", PAGE)
        self.assertIn("The portfolio name field is highlighted above", PAGE)
        self.assertIn('field.scrollIntoView({ block: "center", behavior: "smooth" });', PAGE)
        self.assertIn("The form is not on screen", PAGE)

    def test_the_page_offers_the_example_books_as_examples(self):
        self.assertIn("These are examples, not advice", PAGE)
        self.assertIn("Nothing is saved until you click Import holdings", PAGE)


if __name__ == "__main__":
    unittest.main()
