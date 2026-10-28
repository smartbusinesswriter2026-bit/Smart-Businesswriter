"""Free market-data lookups for the product layer (B-106, B-109).

Read-only services from a fixed allowlist of public sources:

* **FX** - Frankfurter (``api.frankfurter.dev``), central-bank and official reference rates.
  No API key, no quota, daily and historical.
* **Risk-free yield** - the U.S. Treasury daily par yield curve CSV (``home.treasury.gov``).
  No API key.
* **Equity quote and fundamentals** - Alpha Vantage (``www.alphavantage.co``) with the user's
  own free key in ``BP_ALPHAVANTAGE_KEY``; 25 requests/day on the free tier.
* **Filings** - U.S. SEC EDGAR's public Atom feed (``www.sec.gov``). No key.
* **Macro** - the World Bank Open Data API (``api.worldbank.org``), CC BY 4.0. No key.

Nothing here computes a business number and nothing here enters a method by itself.
A lookup returns the value *with its source, date, URL and a SHA-256 of the response*;
the user must confirm and type it into the tool.  That is the boundary the rest of the
product keeps: retrieved data is labelled and confirmed, never silently substituted.
An uncovered market (PSE, private companies) stays a manual entry.

The module is standard library only.  Network failures raise ``MarketDataError`` and no
value is invented.  Hosts are fixed, responses are capped, redirects are checked against
the allowlist, API keys are redacted from returned URLs, and a short cache limits traffic.
"""

import csv
import datetime
import hashlib
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

FORMAT = "bp-marketdata/1"

FRANKFURTER = "https://api.frankfurter.dev/v2/rate/{base}/{quote}"
TREASURY = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            "daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
            "&field_tdr_date_value={year}&page&_format=csv")
ALPHAVANTAGE = "https://www.alphavantage.co/query"
SEC_EDGAR = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&ticker={ticker}"
             "&type={form}&dateb=&owner=include&count={count}&output=atom")
WORLDBANK = ("https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
             "?format=json&per_page={count}")

ALLOWED_HOSTS = {"api.frankfurter.dev", "home.treasury.gov", "www.alphavantage.co",
                 "www.sec.gov", "api.worldbank.org"}
MAX_BYTES = 1_000_000
TIMEOUT = 20
CACHE_SECONDS = 300
DAY_SECONDS = 86_400

#: The maturities the Treasury CSV carries, keyed by the label the page uses.
MATURITIES = {
    "1M": "1 Mo", "2M": "2 Mo", "3M": "3 Mo", "4M": "4 Mo", "6M": "6 Mo",
    "1Y": "1 Yr", "2Y": "2 Yr", "3Y": "3 Yr", "5Y": "5 Yr", "7Y": "7 Yr",
    "10Y": "10 Yr", "20Y": "20 Yr", "30Y": "30 Yr",
}

#: World Bank indicators a student can select, with the unit the series is published in.
WB_INDICATORS = {
    "gdp_growth": ("NY.GDP.MKTP.KD.ZG", "%", "GDP growth (annual %)"),
    "inflation": ("FP.CPI.TOTL.ZG", "%", "Inflation, consumer prices (annual %)"),
    "unemployment": ("SL.UEM.TOTL.ZS", "%", "Unemployment, total (% of labour force)"),
    "gdp_per_capita": ("NY.GDP.PCAP.CD", "USD", "GDP per capita (current US$)"),
    "population": ("SP.POP.TOTL", "people", "Population, total"),
    "gov_debt": ("GC.DOD.TOTL.GD.ZS", "%", "Central government debt, total (% of GDP)"),
}

#: EDGAR form filters offered by the panel; an empty string means any form.
SEC_FORMS = ("10-K", "10-Q", "8-K", "20-F", "6-K", "DEF 14A", "")

_CACHE = {}


class MarketDataError(Exception):
    """The lookup could not be completed; no value is returned."""


def _cache_get(key):
    hit = _CACHE.get(key)
    if hit and hit[0] > time.time(): return hit[1]
    return None


def _cache_put(key, value, seconds=CACHE_SECONDS):
    _CACHE[key] = (time.time() + seconds, value)


def _public_url(url):
    """A source URL safe to show: an API key in the query string is redacted."""
    return re.sub(r"(apikey=)[^&]+", r"\1***", url, flags=re.I)


def _fetch(url):
    """Fetch an allowlisted URL, refusing a redirect off the allowlist or an oversized body."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS:
        raise MarketDataError("this lookup may only read from the declared public sources over HTTPS")
    request = urllib.request.Request(url, headers={
        "User-Agent": "SmartBusinessWriter/0.83 (local educational app)",
        "Accept": "application/json, text/csv;q=0.9, text/plain;q=0.8",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            final = urllib.parse.urlparse(response.geturl()).hostname
            if final not in ALLOWED_HOSTS:
                raise MarketDataError("the source redirected to an address outside the allowlist")
            raw = response.read(MAX_BYTES + 1)
            status = response.status
    except MarketDataError:
        raise
    except Exception as exc:
        raise MarketDataError("the source could not be reached: " + type(exc).__name__)
    if status != 200:
        raise MarketDataError("the source answered with status %s" % status)
    if len(raw) > MAX_BYTES:
        raise MarketDataError("the source response is larger than the 1 MB limit")
    return raw, response.geturl()


def _iso_date(value, required=False):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required: raise MarketDataError("a date is required in YYYY-MM-DD form")
        return None
    value = str(value).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise MarketDataError("the date must be in YYYY-MM-DD form")
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise MarketDataError("the date is not a real calendar date")
    return value


def _code(value, what):
    code = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise MarketDataError("the %s currency must be a three-letter ISO code" % what)
    return code


def _iso_asof(value):
    """Normalise a source date to ISO when it is a recognisable month/day/year."""
    value = str(value or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value


def _payload(kind, value, as_of, source, url, raw, extra=None):
    body = {
        "format": FORMAT, "kind": kind, "value": str(value), "as_of": as_of,
        "source": source, "source_url": url,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "verification": "published by the source; not independently verified by this app",
        "note": "Confirm this value and enter it yourself; the app does not fill a method silently.",
    }
    if extra: body.update(extra)
    return body


def fx_rate(base, quote, date=None):
    """The reference rate for one unit of ``base`` in ``quote``, optionally on a date."""
    base, quote = _code(base, "base"), _code(quote, "quote")
    day = _iso_date(date)
    url = FRANKFURTER.format(base=base, quote=quote) + (("?date=" + day) if day else "")
    key = ("fx", base, quote, day)
    cached = _cache_get(key)
    if cached: return cached
    raw, final = _fetch(url)
    try:
        data = json.loads(raw.decode("utf-8"))
        rate = Decimal(str(data["rate"]))
        as_of = str(data.get("date") or day or "")
    except (ValueError, KeyError, InvalidOperation, TypeError):
        raise MarketDataError("the FX source returned a response this app cannot read")
    if rate <= 0: raise MarketDataError("the FX source returned a non-positive rate")
    payload = _payload("fx", rate, as_of, "Frankfurter (official reference rates)", final, raw,
                       {"base": base, "quote": quote})
    _cache_put(key, payload)
    return payload


def riskfree_rate(maturity="10Y", year=None):
    """The latest par yield for a Treasury maturity, as a decimal (4.25% -> 0.0425)."""
    label_key = str(maturity or "10Y").strip().upper()
    if label_key not in MATURITIES:
        raise MarketDataError("maturity must be one of: " + ", ".join(sorted(MATURITIES)))
    if year is not None:
        try: year = int(year)
        except (TypeError, ValueError): raise MarketDataError("the year must be a four-digit number")
        if not (1990 <= year <= datetime.date.today().year):
            raise MarketDataError("the year must be between 1990 and the current year")
    key = ("rf", label_key, year)
    cached = _cache_get(key)
    if cached: return cached
    years = [year] if year else [datetime.date.today().year, datetime.date.today().year - 1]
    last_error = None
    for candidate in years:
        url = TREASURY.format(year=candidate)
        try:
            raw, final = _fetch(url)
        except MarketDataError as exc:
            last_error = exc; continue
        try:
            text = raw.decode("utf-8-sig")
            rows = list(csv.reader(io.StringIO(text)))
        except (UnicodeDecodeError, csv.Error):
            last_error = MarketDataError("the Treasury source returned a response this app cannot read")
            continue
        if not rows: continue
        header = [h.strip() for h in rows[0]]
        column = MATURITIES[label_key]
        if column not in header:
            last_error = MarketDataError("the Treasury source no longer carries the %s maturity" % label_key)
            continue
        index = header.index(column)
        for row in rows[1:]:
            if len(row) <= index or not row[index].strip(): continue
            try:
                rate = Decimal(row[index].strip()) / 100
                as_of = row[0].strip()
            except (InvalidOperation, IndexError):
                continue
            if rate <= 0: continue
            payload = _payload("riskfree", rate, _iso_asof(as_of),
                               "U.S. Department of the Treasury, Daily Treasury Par Yield Curve Rates",
                               final, raw, {"maturity": label_key, "quoted_percent": row[index].strip()})
            _cache_put(key, payload)
            return payload
        last_error = MarketDataError("the Treasury source has no observation for %s in %s" % (label_key, candidate))
    raise last_error or MarketDataError("the risk-free source returned no usable observation")


def clear_cache():
    """Drop the in-memory cache (tests and a manual refresh)."""
    _CACHE.clear()


def _alpha_key():
    key = (os.environ.get("BP_ALPHAVANTAGE_KEY") or "").strip()
    if not key:
        raise MarketDataError("an Alpha Vantage key is required for equity data: register free at "
                              "https://www.alphavantage.co/support/#api-key and set BP_ALPHAVANTAGE_KEY")
    return key


def _symbol(value):
    symbol = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9.\-]{1,12}", symbol):
        raise MarketDataError("the symbol must be 1-12 letters, digits, dots or hyphens")
    return symbol


def _alpha_json(function, symbol, key):
    url = (ALPHAVANTAGE + "?function=" + function + "&symbol=" + urllib.parse.quote(symbol) +
           "&apikey=" + urllib.parse.quote(key))
    raw, final = _fetch(url)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise MarketDataError("the equity source returned a response this app cannot read")
    for field in ("Error Message", "Information", "Note"):
        if field in data:
            raise MarketDataError("the equity source refused the request: " + str(data[field])[:300])
    return data, raw, final


def equity_quote(symbol):
    """Latest quote for one symbol from Alpha Vantage's free tier (the user's own key)."""
    symbol = _symbol(symbol)
    key = _alpha_key()
    cache_key = ("quote", symbol)
    cached = _cache_get(cache_key)
    if cached: return cached
    data, raw, final = _alpha_json("GLOBAL_QUOTE", symbol, key)
    quote = data.get("Global Quote") or {}
    try:
        price = Decimal(str(quote["05. price"]))
    except (KeyError, InvalidOperation, TypeError):
        raise MarketDataError("the equity source returned no quote for " + symbol)
    payload = _payload("quote", price, str(quote.get("07. latest trading day") or ""),
                       "Alpha Vantage (free tier)", _public_url(final), raw,
                       {"symbol": symbol, "change_percent": str(quote.get("10. change percent") or "").strip(),
                        "volume": str(quote.get("06. volume") or "").strip(),
                        "previous_close": str(quote.get("08. previous close") or "").strip()})
    _cache_put(cache_key, payload, DAY_SECONDS)
    return payload


def equity_fundamentals(symbol):
    """A small fundamentals snapshot for one symbol from Alpha Vantage OVERVIEW."""
    symbol = _symbol(symbol)
    key = _alpha_key()
    cache_key = ("fundamentals", symbol)
    cached = _cache_get(cache_key)
    if cached: return cached
    data, raw, final = _alpha_json("OVERVIEW", symbol, key)
    if not data.get("Symbol"):
        raise MarketDataError("the equity source returned no fundamentals for " + symbol)
    fields = {
        "Name": "Name", "MarketCapitalization": "Market capitalisation", "PERatio": "P/E",
        "PEGRatio": "PEG", "PriceToBookRatio": "Price / book", "EVToEBITDA": "EV / EBITDA",
        "ProfitMargin": "Profit margin", "ReturnOnEquity": "Return on equity",
        "RevenueTTM": "Revenue (TTM)", "EBITDA": "EBITDA", "QuarterlyEarningsGrowthYOY": "Earnings growth (YoY)",
    }
    values = {label: str(data.get(key, "") or "").strip() for key, label in fields.items()}
    market_cap = data.get("MarketCapitalization")
    try:
        value = Decimal(str(market_cap)) if market_cap not in (None, "", "None", "-") else Decimal(0)
    except (InvalidOperation, ValueError):
        value = Decimal(0)
    payload = _payload("fundamentals", value, str(data.get("LatestQuarter") or ""),
                       "Alpha Vantage (free tier), company overview", _public_url(final), raw,
                       {"symbol": symbol, "values": values, "currency": str(data.get("Currency") or "").strip()})
    _cache_put(cache_key, payload, DAY_SECONDS)
    return payload


def sec_filings(ticker, form="10-K", count=5):
    """Recent EDGAR filings for a ticker, from the public Atom feed (no key)."""
    ticker = _symbol(ticker)
    form = str(form or "").strip().upper()
    if form and form not in SEC_FORMS:
        raise MarketDataError("form must be one of: " + ", ".join(f for f in SEC_FORMS if f))
    try:
        count = int(count)
    except (TypeError, ValueError):
        raise MarketDataError("count must be a whole number between 1 and 20")
    if not (1 <= count <= 20):
        raise MarketDataError("count must be between 1 and 20")
    cache_key = ("sec", ticker, form, count)
    cached = _cache_get(cache_key)
    if cached: return cached
    url = SEC_EDGAR.format(ticker=urllib.parse.quote(ticker), form=urllib.parse.quote(form), count=count)
    raw, final = _fetch(url)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise MarketDataError("the filings source returned a response this app cannot read")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    company = (root.findtext(".//a:conformed-name", default="", namespaces=ns) or "").strip()
    cik = (root.findtext(".//a:cik", default="", namespaces=ns) or "").strip()
    filings = []
    for entry in root.findall("a:entry", ns):
        content = entry.find("a:content", ns)
        if content is None: continue
        filings.append({
            "form": (content.findtext("a:filing-type", default="", namespaces=ns) or "").strip(),
            "date": (content.findtext("a:filing-date", default="", namespaces=ns) or "").strip(),
            "name": (content.findtext("a:form-name", default="", namespaces=ns) or "").strip(),
            "url": (content.findtext("a:filing-href", default="", namespaces=ns) or "").strip(),
        })
    if not filings:
        raise MarketDataError("no filings were found for %s%s" % (ticker, (" with form " + form) if form else ""))
    filings = filings[:count]
    latest = max((f["date"] for f in filings), default="")
    payload = _payload("filings", Decimal(len(filings)), latest,
                       "U.S. SEC EDGAR (public filings)", final, raw,
                       {"ticker": ticker, "company": company, "cik": cik, "form": form or "any",
                        "filings": filings})
    _cache_put(cache_key, payload, 3600)
    return payload


def worldbank_indicator(country, indicator="gdp_growth", years=5):
    """The latest World Bank observation for one country and indicator (no key)."""
    code = str(country or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{2,3}", code):
        raise MarketDataError("the country must be a two- or three-letter code, e.g. PH or PHL")
    key = str(indicator or "gdp_growth").strip().lower()
    if key not in WB_INDICATORS:
        raise MarketDataError("indicator must be one of: " + ", ".join(sorted(WB_INDICATORS)))
    try:
        years = int(years)
    except (TypeError, ValueError):
        raise MarketDataError("years must be a whole number between 1 and 20")
    if not (1 <= years <= 20):
        raise MarketDataError("years must be between 1 and 20")
    series, unit, label = WB_INDICATORS[key]
    cache_key = ("wb", code, key, years)
    cached = _cache_get(cache_key)
    if cached: return cached
    url = WORLDBANK.format(country=code, indicator=series, count=max(years, 5))
    raw, final = _fetch(url)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise MarketDataError("the macro source returned a response this app cannot read")
    if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
        message = ""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            message = str(data[0].get("message") or "")[:200]
        raise MarketDataError("the macro source returned no series" + (": " + message if message else ""))
    rows = [row for row in data[1] if isinstance(row, dict) and row.get("value") is not None]
    if not rows:
        raise MarketDataError("the macro source has no observation for %s / %s" % (code, label))
    rows.sort(key=lambda row: str(row.get("date") or ""), reverse=True)
    row = rows[0]
    try:
        value = Decimal(str(row["value"]))
    except (InvalidOperation, KeyError, TypeError):
        raise MarketDataError("the macro observation is not a number")
    payload = _payload("macro", value, str(row.get("date") or ""),
                       "World Bank Open Data (CC BY 4.0)", final, raw,
                       {"country": str((row.get("country") or {}).get("value") or code),
                        "country_code": code, "indicator": label, "indicator_id": series, "unit": unit})
    _cache_put(cache_key, payload, DAY_SECONDS)
    return payload
