"""Tracked-instrument price store and routes: record, dedupe, returns, readiness, fail-closed."""

import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import instruments, api, marketdata  # noqa: E402


def quote(value, as_of, previous=None):
    payload = {"kind": "quote", "symbol": "AAPL", "value": value, "as_of": as_of,
               "source": "Alpha Vantage (free tier)", "source_url": "https://www.alphavantage.co/query",
               "response_sha256": "deadbeef"}
    if previous is not None:
        payload["previous_close"] = previous
    return payload


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.patch = mock.patch.dict(os.environ, {"BP_CASES_DIR": self.folder.name})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.folder.cleanup()

    def test_create_stores_a_twelve_hex_id_and_persists(self):
        document = instruments.create("aapl", label="Apple", kind="equity", sector="tech")
        self.assertRegex(document["id"], r"^[0-9a-f]{12}$")
        self.assertEqual(document["symbol"], "AAPL")
        self.assertEqual(document["snapshots"], [])
        reloaded = instruments.load(document["id"])
        self.assertEqual(reloaded["label"], "Apple")
        self.assertEqual(reloaded["sector"], "tech")

    def test_record_appends_and_dedupes_by_as_of(self):
        document = instruments.create("AAPL")
        first = instruments.record(document["id"], quote=quote("100.00", "2026-10-01", "99.00"))
        self.assertEqual(len(first["snapshots"]), 1)
        self.assertEqual(first["snapshots"][0]["price"], "100.00")
        self.assertEqual(first["snapshots"][0]["previous_close"], "99.00")
        same_day = instruments.record(document["id"], quote=quote("105.00", "2026-10-01"))
        self.assertEqual(len(same_day["snapshots"]), 1)
        self.assertEqual(same_day["snapshots"][0]["price"], "105.00")
        next_day = instruments.record(document["id"], quote=quote("110.00", "2026-10-02"))
        self.assertEqual(len(next_day["snapshots"]), 2)

    def test_returns_series_uses_consecutive_recorded_prices(self):
        document = instruments.create("AAPL")
        for value, day in (("100", "2026-10-01"), ("110", "2026-10-02"), ("121", "2026-10-03")):
            document = instruments.record(document["id"], quote=quote(value, day))
        self.assertEqual(instruments.returns_series(document), ["0.1", "0.1"])

    def test_readiness_names_the_gaps_until_three_returns(self):
        document = instruments.create("AAPL")
        empty = instruments.readiness(document)
        self.assertFalse(empty["risk_ready"])
        self.assertEqual(len(empty["gaps"]), 2)
        for value, day in (("100", "2026-10-01"), ("110", "2026-10-02"), ("121", "2026-10-03")):
            document = instruments.record(document["id"], quote=quote(value, day))
        partial = instruments.readiness(document)
        self.assertEqual(partial["returns"], 2)
        self.assertFalse(partial["risk_ready"])
        document = instruments.record(document["id"], quote=quote("133.1", "2026-10-04"))
        ready = instruments.readiness(document)
        self.assertEqual(ready["returns"], 3)
        self.assertTrue(ready["risk_ready"])
        self.assertEqual(ready["gaps"], [])


    def test_fail_closed_on_bad_inputs(self):
        with self.assertRaises(ValueError):
            instruments.load("NOTHEX")
        with self.assertRaises(ValueError):
            instruments.load("../../etc/passwd")
        document = instruments.create("AAPL")
        with self.assertRaises(instruments.InstrumentError):
            instruments.record(document["id"], quote={"value": "0", "as_of": "2026-10-01"})
        with self.assertRaises(instruments.InstrumentError):
            instruments.record(document["id"], quote={"value": "100", "as_of": ""})

        def boom(_symbol):
            raise marketdata.MarketDataError("an Alpha Vantage key is required")

        with self.assertRaises(instruments.InstrumentError):
            instruments.record(document["id"], fetch=boom)

    def test_a_corrupt_file_is_refused(self):
        document = instruments.create("AAPL")
        path = instruments.instruments_dir() / (document["id"] + ".json")
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(instruments.InstrumentCorrupt):
            instruments.load(document["id"])


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.patch = mock.patch.dict(os.environ, {"BP_CASES_DIR": self.folder.name})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.folder.cleanup()

    def test_create_list_record_and_get(self):
        status, created = api.handle("POST", "/api/cases/instruments", {"symbol": "MSFT"})
        self.assertEqual(status, 201)
        instrument_id = created["id"]
        status, listing = api.handle("GET", "/api/cases/instruments")
        self.assertEqual(status, 200)
        self.assertEqual(len(listing["instruments"]), 1)
        status, recorded = api.handle("POST", "/api/cases/instruments/%s/record" % instrument_id,
                                      {"quote": quote("330.00", "2026-10-01")})
        self.assertEqual(status, 200)
        self.assertEqual(recorded["readiness"]["snapshots"], 1)
        status, shown = api.handle("GET", "/api/cases/instruments/%s" % instrument_id)
        self.assertEqual(status, 200)
        self.assertEqual(shown["instrument"]["symbol"], "MSFT")
        status, removed = api.handle("DELETE", "/api/cases/instruments/%s" % instrument_id)
        self.assertEqual(status, 200)
        self.assertEqual(removed["deleted"], instrument_id)

    def test_unknown_instrument_is_404(self):
        status, _payload = api.handle("GET", "/api/cases/instruments/0123456789ab")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()

