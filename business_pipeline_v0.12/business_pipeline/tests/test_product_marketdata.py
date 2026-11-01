"""Market-data lookups: parsing, provenance and fail-closed behaviour, with no network."""

import io
import json
import os
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
[{"indicator":{"id":"NY.GDP.MKTP.KD.ZG","value":"GDP growth (annual %)"},"country":{"id":"PH","value":"Philippines"},"countryiso3code":"PHL","date":"2025","value":4.4024,"unit":"","obs_status":"","decimal":1},
 {"indicator":{"id":"NY.GDP.MKTP.KD.ZG","value":"GDP growth (annual %)"},"country":{"id":"PH","value":"Philippines"},"countryiso3code":"PHL","date":"2024","value":5.7147,"unit":"","obs_status":"","decimal":1}]]"""


class EquityTest(unittest.TestCase):
    def setUp(self):
        marketdata.clear_cache()
        self.real = marketdata._fetch
        self.previous = os.environ.get("BP_ALPHAVANTAGE_KEY")
        os.environ["BP_ALPHAVANTAGE_KEY"] = "secret123"

    def tearDown(self):
        marketdata._fetch = self.real
        if self.previous is None: os.environ.pop("BP_ALPHAVANTAGE_KEY", None)
        else: os.environ["BP_ALPHAVANTAGE_KEY"] = self.previous
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
        marketdata._fetch = FakeFetch(WB_JSON, "https://api.worldbank.org/v2/country/PH/indicator/NY.GDP.MKTP.KD.ZG?format=json")
        out = marketdata.worldbank_indicator("ph", "gdp_growth")
        self.assertEqual(out["value"], "4.4024")
        self.assertEqual(out["as_of"], "2025")
        self.assertEqual(out["unit"], "%")
        self.assertEqual(out["country"], "Philippines")

    def test_an_unknown_indicator_or_country_is_refused(self):
        with self.assertRaises(marketdata.MarketDataError):
            marketdata.worldbank_indicator("PH", "not_an_indicator")
        with self.assertRaises(marketdata.MarketDataError):
            marketdata.worldbank_indicator("PHILIPPINES", "gdp_growth")



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



MASSIVE_JSON = (b'{"status":"OK","request_id":"r1","ticker":"AAPL","results":['
                b'{"c":230.50,"h":231,"l":229,"o":230,"v":1000,"t":1793001600000},'
                b'{"c":229.00,"h":230,"l":228,"o":229,"v":900,"t":1792915200000}],'
                b'"resultsCount":2,"queryCount":2,"adjusted":true}')


class MassiveQuoteTest(unittest.TestCase):
    def setUp(self):
        marketdata.clear_cache()
        self.real = marketdata._fetch
        self.previous = os.environ.get("BP_MASSIVE_API_KEY")
        os.environ["BP_MASSIVE_API_KEY"] = "massive-secret"

    def tearDown(self):
        marketdata._fetch = self.real
        if self.previous is None: os.environ.pop("BP_MASSIVE_API_KEY", None)
        else: os.environ["BP_MASSIVE_API_KEY"] = self.previous
        marketdata.clear_cache()

    def test_a_massive_quote_records_close_previous_and_redacts_key(self):
        marketdata._fetch = FakeFetch(
            MASSIVE_JSON,
            "https://api.massive.com/v2/aggs/ticker/AAPL/range/1/day/2026-10-20/2026-10-30"
            "?adjusted=true&sort=desc&limit=2&apiKey=massive-secret")
        out = marketdata.massive_quote("aapl")
        self.assertEqual(Decimal(out["value"]), Decimal("230.5"))
        self.assertEqual(out["symbol"], "AAPL")
        self.assertEqual(out["provider"], "massive")
        self.assertEqual(Decimal(out["previous_close"]), Decimal("229"))
        import datetime as _dt
        self.assertEqual(out["as_of"], _dt.datetime.fromtimestamp(1793001600, _dt.timezone.utc).date().isoformat())
        self.assertNotIn("massive-secret", out["source_url"])
        self.assertIn("apiKey=***", out["source_url"])

    def test_massive_without_a_key_refuses_before_any_fetch(self):
        os.environ.pop("BP_MASSIVE_API_KEY", None)
        fake = FakeFetch(MASSIVE_JSON)
        marketdata._fetch = fake
        with self.assertRaises(marketdata.MarketDataError) as caught:
            marketdata.massive_quote("AAPL")
        self.assertIn("BP_MASSIVE_API_KEY", str(caught.exception))
        self.assertEqual(fake.calls, 0)

    def test_massive_refusal_status_is_not_read_as_data(self):
        marketdata._fetch = FakeFetch(b'{"status":"ERROR","error":"invalid api key"}')
        with self.assertRaises(marketdata.MarketDataError):
            marketdata.massive_quote("AAPL")


HISTORY_JSON = (b'{"status":"OK","ticker":"AAPL","results":['
                b'{"c":100,"t":1792915200000},{"c":110,"t":1793001600000}]}')
MASSIVE_OVERVIEW_JSON = (b'{"status":"OK","results":{"ticker":"AAPL","name":"Apple Inc.",'
                         b'"market_cap":3500000000000,"weighted_shares_outstanding":16000000000,'
                         b'"sic_description":"ELECTRONIC COMPUTERS","cik":"0000320193","currency_name":"usd"}}')


class HistoryOverviewTest(unittest.TestCase):
    def setUp(self):
        marketdata.clear_cache()
        self.real = marketdata._fetch
        self.prev_m = os.environ.get("BP_MASSIVE_API_KEY")
        self.prev_a = os.environ.get("BP_ALPHAVANTAGE_KEY")
        os.environ["BP_MASSIVE_API_KEY"] = "massive-secret"
        os.environ["BP_ALPHAVANTAGE_KEY"] = "alpha-secret"

    def tearDown(self):
        marketdata._fetch = self.real
        for name, prev in (("BP_MASSIVE_API_KEY", self.prev_m), ("BP_ALPHAVANTAGE_KEY", self.prev_a)):
            if prev is None: os.environ.pop(name, None)
            else: os.environ[name] = prev
        marketdata.clear_cache()

    def test_massive_history_returns_sorted_daily_closes(self):
        marketdata._fetch = FakeFetch(HISTORY_JSON, "https://api.massive.com/v2/aggs/ticker/AAPL/range/1/day/x/y?apiKey=massive-secret")
        out = marketdata.massive_history("aapl", days=5)
        self.assertEqual(out["kind"], "history")
        self.assertEqual(len(out["bars"]), 2)
        self.assertEqual(Decimal(out["bars"][0]["close"]), Decimal("100"))
        self.assertEqual(Decimal(out["bars"][1]["close"]), Decimal("110"))
        self.assertNotIn("massive-secret", out["source_url"])

    def test_alpha_overview_parses_ratios(self):
        marketdata._fetch = FakeFetch(AV_OVERVIEW, "https://www.alphavantage.co/query?function=OVERVIEW&symbol=AAPL&apikey=alpha-secret")
        out = marketdata.alpha_overview("aapl")
        self.assertEqual(Decimal(out["pe_ratio"]), Decimal("35.2"))
        self.assertEqual(Decimal(out["roe"]), Decimal("1.50"))
        self.assertEqual(Decimal(out["market_cap"]), Decimal("3500000000000"))
        self.assertNotIn("alpha-secret", out["source_url"])

    def test_massive_overview_parses_market_cap(self):
        marketdata._fetch = FakeFetch(MASSIVE_OVERVIEW_JSON, "https://api.massive.com/v3/reference/tickers/AAPL?apiKey=massive-secret")
        out = marketdata.massive_overview("AAPL")
        self.assertEqual(out["company"], "Apple Inc.")
        self.assertEqual(Decimal(out["market_cap"]), Decimal("3500000000000"))
        self.assertEqual(out["provider"], "massive")

    def test_fundamentals_dispatch_and_unknown_provider(self):
        marketdata._fetch = FakeFetch(AV_OVERVIEW, "https://www.alphavantage.co/query?function=OVERVIEW&symbol=AAPL&apikey=alpha-secret")
        out = marketdata.fundamentals("AAPL", "alphavantage")
        self.assertEqual(Decimal(out["pe_ratio"]), Decimal("35.2"))
        with self.assertRaises(marketdata.MarketDataError):
            marketdata.fundamentals("AAPL", "wibble")


if __name__ == "__main__":
    unittest.main()
