"""Market-data lookups: parsing, provenance and fail-closed behaviour, with no network."""

import io
import json
import os
import pathlib
import sys
import unittest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import marketdata  # noqa: E402

FX_JSON = b'{"date":"2026-10-28","base":"USD","quote":"PHP","rate":63.986}'
TREASURY_CSV = (b'Date,"1 Mo","2 Mo","3 Mo","4 Mo","6 Mo","1 Yr","2 Yr","3 Yr","5 Yr","7 Yr","10 Yr","20 Yr","30 Yr"\n'
                b'10/27/2026,4.10,4.05,4.00,3.98,3.95,3.90,3.85,3.88,3.95,4.15,4.99,5.20,5.05\n'
                b'10/26/2026,4.09,4.04,3.99,3.97,3.94,3.89,3.84,3.87,3.94,4.14,4.98,5.19,5.04\n')


class FakeFetch:
    def __init__(self, raw, final="https://api.frankfurter.dev/v2/rate/USD/PHP"):
        self.raw, self.final, self.calls = raw, final, 0

    def __call__(self, url):
        self.calls += 1
        return self.raw, self.final


class FxTest(unittest.TestCase):
    def setUp(self):
        marketdata.clear_cache()
        self.real = marketdata._fetch

    def tearDown(self):
        marketdata._fetch = self.real
        marketdata.clear_cache()

    def test_a_lookup_records_the_value_source_date_and_response_hash(self):
        fake = FakeFetch(FX_JSON)
        marketdata._fetch = fake
        out = marketdata.fx_rate("usd", "php")
        self.assertEqual(out["format"], "bp-marketdata/1")
        self.assertEqual(out["value"], "63.986")
        self.assertEqual(out["base"], "USD")
        self.assertEqual(out["quote"], "PHP")
        self.assertEqual(out["as_of"], "2026-10-28")
        self.assertEqual(out["response_sha256"], __import__("hashlib").sha256(FX_JSON).hexdigest())
        self.assertIn("not independently verified", out["verification"])
        self.assertIn("does not fill a method silently", out["note"])

    def test_a_repeated_lookup_is_cached_and_one_call_is_made(self):
        fake = FakeFetch(FX_JSON)
        marketdata._fetch = fake
        first = marketdata.fx_rate("USD", "PHP")
        second = marketdata.fx_rate("USD", "PHP")
        self.assertEqual(first, second)
        self.assertEqual(fake.calls, 1)

    def test_bad_codes_and_dates_are_refused_before_any_fetch(self):
        fake = FakeFetch(FX_JSON)
        marketdata._fetch = fake
        with self.assertRaises(marketdata.MarketDataError): marketdata.fx_rate("US", "PHP")
        with self.assertRaises(marketdata.MarketDataError): marketdata.fx_rate("USD", "PHP", "2026-13-01")
        self.assertEqual(fake.calls, 0)

    def test_a_response_without_a_positive_rate_is_refused(self):
        marketdata._fetch = FakeFetch(b'{"date":"2026-10-28","base":"USD","quote":"PHP","rate":0}')
        with self.assertRaises(marketdata.MarketDataError): marketdata.fx_rate("USD", "PHP")

    def test_only_the_allowlisted_hosts_can_be_read(self):
        with self.assertRaises(marketdata.MarketDataError):
            marketdata._fetch("https://example.com/steal")
        with self.assertRaises(marketdata.MarketDataError):
            marketdata._fetch("http://api.frankfurter.dev/v2/rate/USD/PHP")


class RiskfreeTest(unittest.TestCase):
    def setUp(self):
        marketdata.clear_cache()
        self.real = marketdata._fetch

    def tearDown(self):
        marketdata._fetch = self.real
        marketdata.clear_cache()

    def test_the_latest_observation_is_converted_from_percent_to_decimal(self):
        marketdata._fetch = FakeFetch(TREASURY_CSV, "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all")
        out = marketdata.riskfree_rate("10Y", year=2026)
        self.assertEqual(out["value"], "0.0499")
        self.assertEqual(out["maturity"], "10Y")
        self.assertEqual(out["as_of"], "2026-10-27")
        self.assertIn("Treasury", out["source"])

    def test_an_unknown_maturity_is_refused(self):
        with self.assertRaises(marketdata.MarketDataError):
            marketdata.riskfree_rate("15Y")

    def test_a_year_without_the_column_is_refused(self):
        marketdata._fetch = FakeFetch(b'Date,"1 Yr"\n10/27/2026,3.90\n')
        with self.assertRaises(marketdata.MarketDataError):
            marketdata.riskfree_rate("10Y", year=2026)


AV_QUOTE = b'{"Global Quote":{"01. symbol":"AAPL","05. price":"230.50","06. volume":"1234567","07. latest trading day":"2026-10-27","08. previous close":"229.00","09. change":"1.50","10. change percent":"0.6550%"}}'
AV_OVERVIEW = (b'{"Symbol":"AAPL","Name":"Apple Inc","MarketCapitalization":"3500000000000","PERatio":"35.2",'
               b'"PEGRatio":"2.1","PriceToBookRatio":"55.0","EVToEBITDA":"26.4","ProfitMargin":"0.24",'
               b'"ReturnOnEquity":"1.50","RevenueTTM":"400000000000","EBITDA":"130000000000",'
               b'"QuarterlyEarningsGrowthYOY":"0.12","LatestQuarter":"2026-06-30","Currency":"USD"}')
SEC_ATOM = b"""<?xml version="1.0" encoding="ISO-8859-1" ?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <company-info><cik>0000320193</cik><conformed-name>Apple Inc.</conformed-name></company-info>
  <entry><content type="text/xml">
    <filing-date>2025-10-31</filing-date>
    <filing-href>https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.htm</filing-href>
    <filing-type>10-K</filing-type><form-name>Annual report</form-name>
  </content></entry>
  <entry><content type="text/xml">
    <filing-date>2025-07-31</filing-date>
    <filing-href>https://www.sec.gov/Archives/edgar/data/320193/000032019325000050/0000320193-25-000050-index.htm</filing-href>
    <filing-type>10-Q</filing-type><form-name>Quarterly report</form-name>
  </content></entry>
</feed>"""
WB_JSON = b""" [{"page":1,"pages":1,"per_page":5,"total":2,"sourceid":"2","lastupdated":"2026-10-08"},
[{"indicator":{"id":"NY.GDP.MKTP.KD.ZG","value":"GDP growth (annual %)"},"country":{"id":"KE","value":"Kenya"},"countryiso3code":"KEN","date":"2025","value":4.4024,"unit":"","obs_status":"","decimal":1},
 {"indicator":{"id":"NY.GDP.MKTP.KD.ZG","value":"GDP growth (annual %)"},"country":{"id":"KE","value":"Kenya"},"countryiso3code":"KEN","date":"2024","value":5.7147,"unit":"","obs_status":"","decimal":1}]]"""


class EquityTest(unittest.TestCase):
    def setUp(self):
        marketdata.clear_cache()
        self.real = marketdata._fetch
        self.saved = {key: os.environ.get(key) for key in PROVIDER_KEYS}
        for key in PROVIDER_KEYS:
            os.environ.pop(key, None)
        os.environ["BP_ALPHAVANTAGE_KEY"] = "secret123"

    def tearDown(self):
        marketdata._fetch = self.real
        for key, value in self.saved.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        marketdata.clear_cache()

    def test_a_quote_records_the_price_and_redacts_the_key(self):
        marketdata._fetch = FakeFetch(AV_QUOTE, "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=secret123")
        out = marketdata.equity_quote("aapl")
        self.assertEqual(out["value"], "230.50")
        self.assertEqual(out["symbol"], "AAPL")
        self.assertEqual(out["as_of"], "2026-10-27")
        self.assertNotIn("secret123", out["source_url"])
        self.assertIn("apikey=***", out["source_url"])

    def test_sec_fundamentals_reads_xbrl_facts_without_a_key(self):
        original_filings, original_fetch = marketdata.sec_filings, marketdata._fetch
        marketdata.sec_filings = lambda *args, **kwargs: {"cik": "0000320193", "company": "Apple Inc."}
        class Router:
            def __call__(self, url):
                tag = url.rsplit("/", 1)[-1].replace(".json", "")
                unit = "USD/shares" if "EarningsPerShare" in tag else "USD"
                body = ('{"tag":"%s","units":{"%s":[{"end":"2025-09-27","val":1000,'
                        '"form":"10-K","fp":"FY","filed":"2025-10-31"}]}}' % (tag, unit)).encode()
                return body, url
        marketdata._fetch = Router()
        try:
            out = marketdata.sec_fundamentals("AAPL")
            self.assertEqual(out["kind"], "fundamentals")
            self.assertEqual(out["company"], "Apple Inc.")
            self.assertIn("Total assets", out["values"])
            self.assertEqual(out["as_of"], "2025-09-27")
        finally:
            marketdata.sec_filings, marketdata._fetch = original_filings, original_fetch

    def test_without_a_key_the_lookup_refuses_before_any_fetch(self):
        os.environ.pop("BP_ALPHAVANTAGE_KEY", None)
        fake = FakeFetch(AV_QUOTE)
        marketdata._fetch = fake
        with self.assertRaises(marketdata.MarketDataError) as caught:
            marketdata.equity_quote("AAPL")
        self.assertIn("BP_ALPHAVANTAGE_KEY", str(caught.exception))
        self.assertEqual(fake.calls, 0)

    def test_a_rate_limit_note_is_refused_not_read_as_data(self):
        marketdata._fetch = FakeFetch(b'{"Note":"Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."}')
        with self.assertRaises(marketdata.MarketDataError) as caught:
            marketdata.equity_quote("AAPL")
        self.assertIn("rate limit", str(caught.exception))

    def test_the_daily_limit_is_a_distinct_quota_error(self):
        marketdata._fetch = FakeFetch(b'{"Information":"Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day. Please subscribe to a premium plan."}')
        with self.assertRaises(marketdata.MarketDataQuota):
            marketdata.equity_quote("AAPL")


MASSIVE_QUOTE = b"""{"adjusted":true,"queryCount":1,"request_id":"r1",
 "results":[{"T":"AAPL","c":345.67,"h":350,"l":340,"o":344,"t":1761609600000,"v":1000,"vw":345.1}],
 "resultsCount":1,"status":"OK","ticker":"AAPL"}"""

PROVIDER_KEYS = ("BP_ALPHAVANTAGE_KEY", "BP_MASSIVE_KEY", "BP_QVERIS_KEY", "BP_QVERIS_TOOL_ID",
                 "BP_QVERIS_PRICE_PATH", "BP_ALPHA_DAILY_CEILING", "BP_ALPHA_PER_MINUTE_CEILING",
                 "BP_MASSIVE_PER_MINUTE_CEILING", "BP_QVERIS_PER_MINUTE_CEILING")


class Router:
    def __init__(self, alpha_body, massive_body=MASSIVE_QUOTE):
        self.alpha_body, self.massive_body, self.calls = alpha_body, massive_body, []

    def __call__(self, url):
        self.calls.append(url)
        if "alphavantage.co" in url:
            return self.alpha_body, url
        if "api.massive.com" in url:
            return self.massive_body, url
        raise AssertionError("unexpected URL: " + url)


class ProviderChainTest(unittest.TestCase):
    def setUp(self):
        marketdata.clear_cache()
        self.real = marketdata._fetch
        self.saved = {key: os.environ.get(key) for key in PROVIDER_KEYS}
        for key in PROVIDER_KEYS:
            os.environ.pop(key, None)

    def tearDown(self):
        marketdata._fetch = self.real
        for key, value in self.saved.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        marketdata.clear_cache()

    def test_alpha_is_primary_when_it_answers(self):
        os.environ["BP_ALPHAVANTAGE_KEY"] = "a"
        os.environ["BP_MASSIVE_KEY"] = "m"
        marketdata._fetch = Router(AV_QUOTE)
        out = marketdata.equity_quote("AAPL")
        self.assertEqual(out["provider"], "Alpha Vantage")
        self.assertEqual(out["attempts"], [])
        self.assertEqual(out["value"], "230.50")

    def test_massive_is_the_fallback_when_alpha_is_limited(self):
        os.environ["BP_ALPHAVANTAGE_KEY"] = "a"
        os.environ["BP_MASSIVE_KEY"] = "m"
        marketdata._fetch = Router(b'{"Note":"Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."}')
        out = marketdata.equity_quote("AAPL")
        self.assertEqual(out["provider"], "Massive")
        self.assertEqual(out["value"], "345.67")
        self.assertEqual(out["source"], "Massive (previous close)")
        self.assertRegex(out["as_of"], r"\d{4}-\d{2}-\d{2}")
        self.assertIn("rate limit", out["attempts"][0]["error"])
        self.assertNotIn("apiKey=m", out["source_url"])
        self.assertIn("apiKey=***", out["source_url"])

    def test_the_internal_massive_ceiling_skips_to_a_named_limit(self):
        os.environ["BP_ALPHAVANTAGE_KEY"] = "a"
        os.environ["BP_MASSIVE_KEY"] = "m"
        os.environ["BP_MASSIVE_PER_MINUTE_CEILING"] = "1"
        marketdata._fetch = Router(b'{"Note":"alpha rate limit reached"}')
        first = marketdata.equity_quote("AAPL")
        self.assertEqual(first["provider"], "Massive")
        with self.assertRaises(marketdata.MarketDataQuota) as caught:
            marketdata.equity_quote("MSFT")
        self.assertIn("internal ceiling", str(caught.exception))
        self.assertIn("limit", str(caught.exception))

    def test_without_any_key_the_chain_names_the_variables(self):
        with self.assertRaises(marketdata.MarketDataError) as caught:
            marketdata.equity_quote("AAPL")
        self.assertIn("BP_ALPHAVANTAGE_KEY", str(caught.exception))
        self.assertIn("BP_MASSIVE_KEY", str(caught.exception))
        self.assertIn("BP_QVERIS_TOOL_ID", str(caught.exception))

    def test_status_lists_the_chain_in_order(self):
        out = marketdata.status()
        self.assertEqual([row["name"] for row in out["equity_providers"]],
                         ["Alpha Vantage", "Massive", "QVeris"])
        self.assertFalse(out["sources"]["equity"])
        os.environ["BP_MASSIVE_KEY"] = "m"
        out = marketdata.status()
        self.assertTrue(out["sources"]["equity"])
        self.assertTrue([row for row in out["equity_providers"] if row["name"] == "Massive"][0]["configured"])

    def test_qveris_is_skipped_until_its_contract_is_declared(self):
        os.environ["BP_QVERIS_KEY"] = "q"
        self.assertFalse([row for row in marketdata.status()["equity_providers"]
                          if row["name"] == "QVeris"][0]["configured"])
        with self.assertRaises(marketdata.MarketDataError) as caught:
            marketdata.equity_quote("AAPL")
        self.assertIn("BP_QVERIS_TOOL_ID", str(caught.exception))


class LocalKeyFileTest(unittest.TestCase):
    def test_the_server_loads_local_keys_and_the_environment_wins(self):
        import json as _json
        import tempfile
        from bp import server
        names = ("BP_ALPHAVANTAGE_KEY", "BP_MASSIVE_KEY", "BP_QVERIS_KEY")
        saved = {name: os.environ.get(name) for name in names}
        for name in names:
            os.environ.pop(name, None)
        os.environ["BP_MASSIVE_KEY"] = "already-set"
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        pathlib.Path(path).write_text(_json.dumps({"alpha_vantage": "a", "massive": "m", "qveris": "q"}),
                                      encoding="utf-8")
        try:
            loaded = server._load_local_keys(path)
            self.assertTrue(loaded.get("BP_ALPHAVANTAGE_KEY"))
            self.assertEqual(os.environ["BP_ALPHAVANTAGE_KEY"], "a")
            self.assertEqual(os.environ["BP_MASSIVE_KEY"], "already-set")
            self.assertNotIn("BP_MASSIVE_KEY", loaded)
            self.assertEqual(os.environ["BP_QVERIS_KEY"], "q")
            self.assertEqual(server._load_local_keys(path + ".missing"), {})
        finally:
            os.unlink(path)
            for name, value in saved.items():
                if value is None: os.environ.pop(name, None)
                else: os.environ[name] = value


class SecTest(unittest.TestCase):
    def setUp(self):
        marketdata.clear_cache(); self.real = marketdata._fetch

    def tearDown(self):
        marketdata._fetch = self.real; marketdata.clear_cache()

    def test_filings_are_parsed_with_company_cik_and_links(self):
        marketdata._fetch = FakeFetch(SEC_ATOM, "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&ticker=AAPL")
        out = marketdata.sec_filings("AAPL", "10-K", 5)
        self.assertEqual(out["kind"], "filings")
        self.assertEqual(out["company"], "Apple Inc.")
        self.assertEqual(out["cik"], "0000320193")
        self.assertEqual(out["as_of"], "2025-10-31")
        self.assertEqual(len(out["filings"]), 2)
        self.assertTrue(out["filings"][0]["url"].startswith("https://www.sec.gov/Archives/"))

    def test_an_unknown_form_is_refused(self):
        with self.assertRaises(marketdata.MarketDataError):
            marketdata.sec_filings("AAPL", "S-99", 5)

    def test_an_empty_feed_is_refused(self):
        marketdata._fetch = FakeFetch(b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>')
        with self.assertRaises(marketdata.MarketDataError):
            marketdata.sec_filings("NONE", "", 5)


class WorldBankTest(unittest.TestCase):
    def setUp(self):
        marketdata.clear_cache(); self.real = marketdata._fetch

    def tearDown(self):
        marketdata._fetch = self.real; marketdata.clear_cache()

    def test_the_latest_observation_is_returned_with_its_year_and_unit(self):
        marketdata._fetch = FakeFetch(WB_JSON, "https://api.worldbank.org/v2/country/KE/indicator/NY.GDP.MKTP.KD.ZG?format=json")
        out = marketdata.worldbank_indicator("ke", "gdp_growth")
        self.assertEqual(out["value"], "4.4024")
        self.assertEqual(out["as_of"], "2025")
        self.assertEqual(out["unit"], "%")
        self.assertEqual(out["country"], "Kenya")

    def test_an_unknown_indicator_or_country_is_refused(self):
        with self.assertRaises(marketdata.MarketDataError):
            marketdata.worldbank_indicator("KE", "not_an_indicator")
        with self.assertRaises(marketdata.MarketDataError):
            marketdata.worldbank_indicator("KENYA", "gdp_growth")



class StatusTest(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("BP_ALPHAVANTAGE_KEY")

    def tearDown(self):
        if self.previous is None: os.environ.pop("BP_ALPHAVANTAGE_KEY", None)
        else: os.environ["BP_ALPHAVANTAGE_KEY"] = self.previous

    def test_equity_is_reported_as_unconfigured_without_a_key(self):
        os.environ.pop("BP_ALPHAVANTAGE_KEY", None)
        out = marketdata.status()
        self.assertFalse(out["sources"]["equity"])
        self.assertTrue(out["sources"]["fx"])
        self.assertTrue(out["sources"]["filings"])
        self.assertTrue(out["sources"]["macro"])

    def test_equity_is_reported_as_configured_with_a_key(self):
        os.environ["BP_ALPHAVANTAGE_KEY"] = "abc123"
        self.assertTrue(marketdata.status()["sources"]["equity"])



if __name__ == "__main__":
    unittest.main()
