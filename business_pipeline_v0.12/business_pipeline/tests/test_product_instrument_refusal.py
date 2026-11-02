"""A refused price names the symbol and the provider (B-185 follow-up).

Recording a price for a ticker the provider cannot price used to fail with
"the quoted price must be positive", which a student cannot act on: it names
neither the ticker nor the provider. The refusal now names both. Nothing is
stored on a refusal, so the watch list cannot carry an empty price.
"""

import json
import os
import pathlib
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bp.product import instruments  # noqa: E402


def _post(base, path, body):
    request = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode() or "{}")


class RefusedPriceTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.patch = mock.patch.dict(os.environ, {"BP_CASES_DIR": self.folder.name})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.folder.cleanup()

    def test_an_unpriced_ticker_refusal_names_the_symbol_and_the_provider(self):
        document = instruments.create("ZZZZINVALID")
        with self.assertRaises(instruments.InstrumentError) as caught:
            instruments.record(document["id"], quote={"value": "0", "as_of": "2026-11-02"},
                               provider="alphavantage")
        message = str(caught.exception)
        self.assertEqual(caught.exception.__class__, instruments.InstrumentError)
        self.assertIn("ZZZZINVALID", message)
        self.assertIn("No price was stored", message)
        # A student is never told to configure a key or an environment variable.
        lowered = message.lower()
        for burden in ("key", "bp_", "environment", "configure", "server"):
            self.assertNotIn(burden, lowered, message)

    def test_a_refused_price_is_not_stored(self):
        document = instruments.create("ZZZZINVALID")
        with self.assertRaises(instruments.InstrumentError):
            instruments.record(document["id"], quote={"value": "0", "as_of": "2026-11-02"},
                               provider="alphavantage")
        stored = instruments.load(document["id"])
        self.assertEqual(stored.get("snapshots", []), [])
        self.assertFalse(instruments.readiness(stored)["risk_ready"])


class AtomicAddRouteTest(unittest.TestCase):
    """POST {symbol, record: true} is one action: no half-added watch-list row.

    The page adds a symbol with `record: true`, so a symbol whose first price cannot
    be sourced must not survive the request as an empty row the student then has to
    remove by hand.
    """

    @classmethod
    def setUpClass(cls):
        from bp import server
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join(timeout=5)

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.patch = mock.patch.dict(os.environ, {"BP_CASES_DIR": self.folder.name})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.folder.cleanup()

    def test_a_failed_record_leaves_no_symbol_behind(self):
        symbols_before = {row["symbol"] for row in instruments.list_instruments()}
        with mock.patch.object(instruments, "record",
                               side_effect=instruments.InstrumentError("no sourced price")):
            status, payload = _post(self.base, "/api/cases/instruments",
                                    {"symbol": "ZZZZINVALID", "record": True})
        self.assertEqual(status, 422)
        self.assertIn("no sourced price", payload["error"])
        symbols_after = {row["symbol"] for row in instruments.list_instruments()}
        self.assertEqual(symbols_after - symbols_before, set())
        self.assertNotIn("ZZZZINVALID", symbols_after)


if __name__ == "__main__":
    unittest.main()
