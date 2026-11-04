"""Free market-data lookups for the product layer (B-106, B-109).

Read-only services from a fixed allowlist of public sources:

* **FX** - Frankfurter (``api.frankfurter.dev``), central-bank and official reference rates.
  No API key, no quota, daily and historical.
* **Risk-free yield** - the U.S. Treasury daily par yield curve CSV (``home.treasury.gov``).
  No API key.
* **Equity quote** - a declared chain: Alpha Vantage (``www.alphavantage.co``, primary, the
  user's own free key in ``BP_ALPHAVANTAGE_KEY``, 25 requests/day), then Massive
  (``api.massive.com``, ``BP_MASSIVE_KEY``, 5 requests/minute), then QVeris
  (``qveris.ai``, ``BP_QVERIS_KEY`` plus a declared tool and price path, credits per call).
  Each provider has an internal ceiling; when one is reached the next is tried.
* **Equity fundamentals** - the U.S. SEC EDGAR XBRL facts (``data.sec.gov``). No key.
* **Filings** - U.S. SEC EDGAR's public Atom feed (``www.sec.gov``). No key.
* **Macro** - the World Bank Open Data API (``api.worldbank.org``), CC BY 4.0. No key.

Nothing here computes a business number and nothing here enters a method by itself.
A lookup returns the value *with its source, date, URL and a SHA-256 of the response*;
the user must confirm and type it into the tool.  That is the boundary the rest of the
product keeps: retrieved data is labelled and confirmed, never silently substituted.
A market the free sources do not cover (a private company, or an exchange with no free
official feed) stays a manual entry.

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
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

FORMAT = "bp-marketdata/1"

FRANKFURTER = "https://api.frankfurter.dev/v2/rate/{base}/{quote}"
MASSIVE = "https://api.massive.com"
QVERIS = "https://qveris.ai/api/v1"
TREASURY = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            "daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
            "&field_tdr_date_value={year}&page&_format=csv")
ALPHAVANTAGE = "https://www.alphavantage.co/query"
SEC_EDGAR = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&ticker={ticker}"
             "&type={form}&dateb=&owner=include&count={count}&output=atom")
WORLDBANK = ("https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
             "?format=json&per_page={count}")

ALLOWED_HOSTS = {"api.frankfurter.dev", "home.treasury.gov", "www.alphavantage.co",
                 "api.massive.com", "qveris.ai",
                 "www.sec.gov", "data.sec.gov", "api.worldbank.org"}
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

#: XBRL concepts for a compact fundamentals snapshot, with fallbacks where companies differ.
SEC_CONCEPTS = {
    "Revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "Net income": ("NetIncomeLoss",),
    "Total assets": ("Assets",),
    "Total liabilities": ("Liabilities",),
    "Shareholders' equity": ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
    "Diluted EPS": ("EarningsPerShareDiluted", "EarningsPerShareBasic"),
}

_CACHE = {}


class MarketDataError(Exception):
    """The lookup could not be completed; no value is returned."""


class MarketDataQuota(MarketDataError):
    """The free equity source's daily quota or rate limit is exhausted."""


def _cache_get(key):
    hit = _CACHE.get(key)
    if hit and hit[0] > time.time(): return hit[1]
    return None


def _cache_put(key, value, seconds=CACHE_SECONDS):
    _CACHE[key] = (time.time() + seconds, value)


def _public_url(url):
    """A source URL safe to show: an API key in the query string is redacted."""
    return re.sub(r"((?:api_?key)=)[^&]+", r"\1***", url, flags=re.I)


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


def _post_json(url, payload, key):
    """POST an allowlisted JSON endpoint with a bearer key; the key never enters the URL."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise MarketDataError("this lookup may only read from the declared public sources over HTTPS")
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST", headers={
        "User-Agent": "SmartBusinessWriter/0.83 (local educational app)",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
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
    """Drop the in-memory cache and the internal ceilings (tests and a manual refresh)."""
    _CACHE.clear()
    with _LIMIT_LOCK:
        _LIMIT_WINDOWS.clear()


def status():
    """Which sources are configured, without making a network call.

    Equity quotes use a chain: Alpha Vantage first, then Massive, then QVeris.
    FX, Treasury, SEC and World Bank need no key. The UI uses this to explain a
    disabled button before it is clicked.
    """
    providers = _equity_providers()
    equity = any(row["configured"] for row in providers)
    return {"format": FORMAT,
            "sources": {"fx": True, "riskfree": True, "equity": equity, "fundamentals": True,
                        "filings": True, "macro": True},
            "equity_providers": [{"name": row["name"], "configured": row["configured"],
                                  "key_env": row["key_env"], "per_minute": row["per_minute"],
                                  "per_day": row["per_day"]} for row in providers],
            "alpha_key_env": "BP_ALPHAVANTAGE_KEY",
            "note": ("Equity quotes try Alpha Vantage first, then Massive, then QVeris. Each provider "
                     "has an internal ceiling; when one is reached the next is tried. Fundamentals come "
                     "from SEC EDGAR and need no key. Markets the free sources do not cover are "
                     "manual entries.")}


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
            message = str(data[field])
            if re.search(r"rate limit|requests per (day|minute)|premium plan|call frequency|"
                         r"daily limit|exceeded", message, re.I):
                raise MarketDataQuota("the free equity source's limit is reached: " + message[:300])
            raise MarketDataError("the equity source refused the request: " + message[:300])
    return data, raw, final


_LIMIT_LOCK = threading.Lock()
_LIMIT_WINDOWS = {}


def _int_env(name, default):
    try:
        return max(1, int(str(os.environ.get(name) or default)))
    except (TypeError, ValueError):
        return default


def _limit_ok(name, per_minute=None, per_day=None):
    """May this provider be called now? The ceiling is internal, not the vendor's."""
    now = time.time()
    with _LIMIT_LOCK:
        state = _LIMIT_WINDOWS.setdefault(name, {"minute": [], "day": [None, 0]})
        if per_minute:
            state["minute"] = [stamp for stamp in state["minute"] if now - stamp < 60]
            if len(state["minute"]) >= per_minute:
                return False
        if per_day:
            today = datetime.date.today().isoformat()
            if state["day"][0] != today:
                state["day"] = [today, 0]
            if state["day"][1] >= per_day:
                return False
        return True


def _limit_spend(name):
    now = time.time()
    with _LIMIT_LOCK:
        state = _LIMIT_WINDOWS.setdefault(name, {"minute": [], "day": [None, 0]})
        state["minute"].append(now)
        today = datetime.date.today().isoformat()
        if state["day"][0] != today:
            state["day"] = [today, 0]
        state["day"][1] += 1


def _equity_providers():
    """The declared order. A provider without its key is skipped, not guessed."""
    alpha = bool((os.environ.get("BP_ALPHAVANTAGE_KEY") or "").strip())
    massive = bool((os.environ.get("BP_MASSIVE_KEY") or "").strip())
    qveris = bool((os.environ.get("BP_QVERIS_KEY") or "").strip()
                  and (os.environ.get("BP_QVERIS_TOOL_ID") or "").strip()
                  and (os.environ.get("BP_QVERIS_PRICE_PATH") or "").strip())
    return [
        {"name": "Alpha Vantage", "configured": alpha, "fetch": _alpha_quote,
         "per_minute": _int_env("BP_ALPHA_PER_MINUTE_CEILING", 5),
         "per_day": _int_env("BP_ALPHA_DAILY_CEILING", 25),
         "key_env": "BP_ALPHAVANTAGE_KEY"},
        {"name": "Massive", "configured": massive, "fetch": _massive_quote,
         "per_minute": _int_env("BP_MASSIVE_PER_MINUTE_CEILING", 5), "per_day": None,
         "key_env": "BP_MASSIVE_KEY"},
        {"name": "QVeris", "configured": qveris, "fetch": _qveris_quote,
         "per_minute": _int_env("BP_QVERIS_PER_MINUTE_CEILING", 60), "per_day": None,
         "key_env": "BP_QVERIS_KEY"},
    ]


def _attempt_text(attempts):
    return "; ".join("%s: %s" % (row["provider"], row["error"]) for row in attempts)


def equity_quote(symbol):
    """The first quote from Alpha Vantage, Massive or QVeris, with provenance.

    Alpha is primary. A provider at its internal ceiling, or one the vendor
    rate-limits, is skipped; the next is tried. Every attempt is recorded in
    ``attempts`` so the report can say which source answered and why the others
    did not. Nothing is invented and no key appears in the URL.
    """
    symbol = _symbol(symbol)
    cache_key = ("quote", symbol)
    cached = _cache_get(cache_key)
    if cached: return cached
    attempts, configured, limited = [], 0, 0
    for provider in _equity_providers():
        if not provider["configured"]:
            continue
        configured += 1
        if not _limit_ok(provider["name"], provider["per_minute"], provider["per_day"]):
            limited += 1
            attempts.append({"provider": provider["name"], "error": "internal ceiling reached"})
            continue
        _limit_spend(provider["name"])
        try:
            payload = provider["fetch"](symbol)
        except MarketDataQuota as error:
            limited += 1
            attempts.append({"provider": provider["name"], "error": str(error)})
            continue
        except MarketDataError as error:
            attempts.append({"provider": provider["name"], "error": str(error)})
            continue
        payload["provider"] = provider["name"]
        payload["attempts"] = attempts
        _cache_put(cache_key, payload, DAY_SECONDS)
        return payload
    if configured and limited == configured:
        raise MarketDataQuota("every configured equity source is at its limit: " + _attempt_text(attempts))
    if configured:
        raise MarketDataError("no equity source returned a quote: " + _attempt_text(attempts))
    raise MarketDataError("equity quotes need a key: set BP_ALPHAVANTAGE_KEY (primary), "
                          "BP_MASSIVE_KEY, or BP_QVERIS_KEY with BP_QVERIS_TOOL_ID and "
                          "BP_QVERIS_PRICE_PATH")


def _alpha_quote(symbol):
    """Latest quote from Alpha Vantage's free tier (the primary source)."""
    key = _alpha_key()
    data, raw, final = _alpha_json("GLOBAL_QUOTE", symbol, key)
    quote = data.get("Global Quote") or {}
    try:
        price = Decimal(str(quote["05. price"]))
    except (KeyError, InvalidOperation, TypeError):
        raise MarketDataError("the equity source returned no quote for " + symbol)
    return _payload("quote", price, str(quote.get("07. latest trading day") or ""),
                    "Alpha Vantage (free tier)", _public_url(final), raw,
                    {"symbol": symbol, "change_percent": str(quote.get("10. change percent") or "").strip(),
                     "volume": str(quote.get("06. volume") or "").strip(),
                     "previous_close": str(quote.get("08. previous close") or "").strip()})


def _massive_quote(symbol):
    """Previous close from Massive's Stocks Basic plan (5 requests/minute)."""
    key = (os.environ.get("BP_MASSIVE_KEY") or "").strip()
    if not key:
        raise MarketDataError("a Massive key is required: set BP_MASSIVE_KEY")
    url = (MASSIVE + "/v2/aggs/ticker/" + urllib.parse.quote(symbol) +
           "/prev?adjusted=true&apiKey=" + urllib.parse.quote(key))
    raw, final = _fetch(url)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise MarketDataError("Massive returned a response this app cannot read")
    if data.get("status") not in ("OK", "DELAYED"):
        raise MarketDataError("Massive refused the request: " + str(data.get("status") or "")[:120])
    results = data.get("results") or []
    if not results:
        raise MarketDataError("Massive returned no previous close for " + symbol)
    row = results[0]
    try:
        price = Decimal(str(row["c"]))
    except (KeyError, InvalidOperation, TypeError):
        raise MarketDataError("Massive returned no usable close for " + symbol)
    try:
        as_of = datetime.datetime.fromtimestamp(int(row.get("t")) / 1000,
                                                tz=datetime.timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        as_of = ""
    return _payload("quote", price, as_of, "Massive (previous close)", _public_url(final), raw,
                    {"symbol": symbol, "volume": str(row.get("v") or "")})


def _dig(data, path):
    node = data
    for part in str(path or "").split("."):
        if not part:
            continue
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            raise MarketDataError("the QVeris result did not carry the configured field")
    return node


def _qveris_quote(symbol):
    """Call one declared QVeris capability. Credits are spent, so it is the last resort."""
    key = (os.environ.get("BP_QVERIS_KEY") or "").strip()
    tool = (os.environ.get("BP_QVERIS_TOOL_ID") or "").strip()
    price_path = (os.environ.get("BP_QVERIS_PRICE_PATH") or "").strip()
    if not (key and tool and price_path):
        raise MarketDataError("QVeris needs BP_QVERIS_KEY, BP_QVERIS_TOOL_ID and BP_QVERIS_PRICE_PATH")
    param = (os.environ.get("BP_QVERIS_SYMBOL_PARAM") or "symbol").strip()
    url = QVERIS + "/tools/execute?tool_id=" + urllib.parse.quote(tool, safe="")
    body = {"parameters": {param: symbol},
            "model": (os.environ.get("BP_QVERIS_MODEL") or "smart-businesswriter").strip()}
    raw, final = _post_json(url, body, key)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise MarketDataError("QVeris returned a response this app cannot read")
    if data.get("success") is False:
        raise MarketDataError("QVeris refused the call: " + str(data.get("error_message") or "")[:300])
    try:
        price = Decimal(str(_dig(data, price_path)))
    except (InvalidOperation, TypeError, ValueError):
        raise MarketDataError("QVeris returned no usable price for " + symbol)
    as_of_path = (os.environ.get("BP_QVERIS_ASOF_PATH") or "").strip()
    as_of = datetime.date.today().isoformat()
    if as_of_path:
        raw_as_of = _dig(data, as_of_path)
        text = str(raw_as_of).strip()
        if isinstance(raw_as_of, (int, float)) or (text.isdigit() and len(text) >= 9):
            try:
                stamp = float(text)
                if stamp > 1e12: stamp /= 1000
                as_of = datetime.datetime.fromtimestamp(stamp, tz=datetime.timezone.utc).date().isoformat()
            except (TypeError, ValueError, OSError):
                pass
        elif text:
            as_of = text
    return _payload("quote", price, as_of, "QVeris (" + tool + ")", _public_url(final), raw,
                    {"symbol": symbol})


def _sec_concept(cik, tags):
    """The latest annual (10-K/FY) fact for the first available XBRL concept."""
    last_error = None
    for tag in tags:
        url = ("https://data.sec.gov/api/xbrl/companyconcept/CIK" + cik +
               "/us-gaap/" + tag + ".json")
        try:
            raw, final = _fetch(url)
        except MarketDataError as exc:
            last_error = exc
            continue
        try:
            data = json.loads(raw.decode("utf-8"))
            units = data.get("units") or {}
            unit = ("USD/shares" if "USD/shares" in units else
                    ("USD" if "USD" in units else next(iter(units), None)))
            facts = [f for f in units.get(unit, []) if isinstance(f, dict) and f.get("val") is not None]
        except (ValueError, UnicodeDecodeError, AttributeError):
            last_error = MarketDataError("an SEC concept could not be read")
            continue
        annual = [f for f in facts if f.get("form") == "10-K" and f.get("fp") == "FY"]
        pool = annual or facts
        if not pool:
            continue
        pool.sort(key=lambda f: (str(f.get("end") or ""), str(f.get("filed") or "")))
        fact = pool[-1]
        try:
            value = Decimal(str(fact["val"]))
        except (InvalidOperation, KeyError, TypeError):
            continue
        return value, str(fact.get("end") or ""), raw, final, str(data.get("tag") or tag)
    raise last_error or MarketDataError("SEC EDGAR has no usable concept for this company")


def sec_fundamentals(ticker):
    """A compact US-company fundamentals snapshot from SEC XBRL company facts (no key)."""
    ticker = _symbol(ticker)
    cache_key = ("sec_fundamentals", ticker)
    cached = _cache_get(cache_key)
    if cached: return cached
    filings = sec_filings(ticker, "", 1)
    cik = str(filings.get("cik") or "").strip()
    if not cik:
        raise MarketDataError("SEC EDGAR returned no CIK for " + ticker + "; this source covers US registrants only")
    cik = cik.zfill(10)
    values, ends, chunks, last_url = {}, [], [], ""
    for label, tags in SEC_CONCEPTS.items():
        try:
            value, end, raw, final, _tag = _sec_concept(cik, tags)
        except MarketDataError:
            continue
        values[label] = str(value)
        if end: ends.append(end)
        chunks.append(raw)
        last_url = final
    if not values:
        raise MarketDataError("SEC EDGAR has no XBRL fundamentals for " + ticker)
    market_value = values.get("Total assets") or values.get("Revenue") or "0"
    payload = _payload("fundamentals", Decimal(market_value), max(ends) if ends else "",
                       "U.S. SEC EDGAR XBRL company facts", last_url, b"".join(chunks),
                       {"symbol": ticker, "company": filings.get("company") or "", "cik": cik,
                        "values": values, "currency": "USD"})
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

# ---- Massive bars/history, overviews and derived fundamentals (ported, B-184) ----

def _massive_key():
    key = (os.environ.get("BP_MASSIVE_KEY") or os.environ.get("BP_MASSIVE_API_KEY") or "").strip()
    if not key:
        raise MarketDataError("a Massive key is required for this provider: set BP_MASSIVE_KEY")
    return key


def massive_quote(symbol):
    """Latest daily close for one symbol from Massive aggregate bars (Custom Bars).

    Uses the daily-bar endpoint, which is available on every Massive stocks plan
    (including Basic), so a quote needs no premium snapshot entitlement.  The
    response is returned with its source, date, URL and SHA-256, like every other
    lookup; nothing is written into a method automatically.
    """
    symbol = _symbol(symbol)
    key = _massive_key()
    cache_key = ("massive_quote", symbol)
    cached = _cache_get(cache_key)
    if cached:
        return cached
    today = datetime.datetime.now(datetime.timezone.utc).date()
    start = today - datetime.timedelta(days=10)
    url = (MASSIVE + "/v2/aggs/ticker/" + urllib.parse.quote(symbol) +
           "/range/1/day/" + start.isoformat() + "/" + today.isoformat() +
           "?adjusted=true&sort=desc&limit=2&apiKey=" + urllib.parse.quote(key))
    raw, final = _fetch(url)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise MarketDataError("the Massive source returned a response this app cannot read")
    if not isinstance(data, dict) or str(data.get("status") or "").upper() not in ("OK", "DELAYED"):
        raise MarketDataError("the Massive source refused the request: " +
                              str(data.get("error") or data.get("status") or "no status")[:300])
    results = data.get("results") or []
    if not results:
        raise MarketDataError("the Massive source has no recent daily bar for " + symbol)
    latest = results[0]
    try:
        price = Decimal(str(latest["c"]))
    except (KeyError, InvalidOperation, TypeError):
        raise MarketDataError("the Massive bar carries no usable close price")
    as_of = ""
    stamp = latest.get("t")
    if isinstance(stamp, (int, float)):
        as_of = datetime.datetime.fromtimestamp(stamp / 1000, datetime.timezone.utc).date().isoformat()
    extra = {"symbol": symbol, "provider": "massive"}
    if len(results) > 1:
        try:
            previous = Decimal(str(results[1]["c"]))
            if previous > 0:
                extra["previous_close"] = str(previous)
        except (KeyError, InvalidOperation, TypeError):
            pass
    if latest.get("v") is not None:
        extra["volume"] = str(latest.get("v"))
    payload = _payload("quote", price, as_of, "Massive (api.massive.com)", _public_url(final), raw, extra)
    _cache_put(cache_key, payload, DAY_SECONDS)
    return payload


def massive_history(symbol, days=30):
    """Recent daily closes for one symbol from Massive aggregate bars (all plans)."""
    symbol = _symbol(symbol)
    key = _massive_key()
    try:
        days = int(days)
    except (TypeError, ValueError):
        raise MarketDataError("days must be a whole number between 2 and 120")
    if not (2 <= days <= 120):
        raise MarketDataError("days must be between 2 and 120")
    cache_key = ("massive_history", symbol, days)
    cached = _cache_get(cache_key)
    if cached:
        return cached
    today = datetime.datetime.now(datetime.timezone.utc).date()
    start = today - datetime.timedelta(days=days + 7)
    url = (MASSIVE + "/v2/aggs/ticker/" + urllib.parse.quote(symbol) + "/range/1/day/" +
           start.isoformat() + "/" + today.isoformat() +
           "?adjusted=true&sort=asc&limit=120&apiKey=" + urllib.parse.quote(key))
    raw, final = _fetch(url)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise MarketDataError("the Massive source returned a response this app cannot read")
    if not isinstance(data, dict) or str(data.get("status") or "").upper() not in ("OK", "DELAYED"):
        raise MarketDataError("the Massive source refused the request: " +
                              str(data.get("error") or data.get("status") or "no status")[:300])
    bars = []
    for bar in data.get("results") or []:
        try:
            close = Decimal(str(bar["c"]))
        except (KeyError, InvalidOperation, TypeError):
            continue
        stamp = bar.get("t")
        if not isinstance(stamp, (int, float)) or close <= 0:
            continue
        bars.append({"as_of": datetime.datetime.fromtimestamp(stamp / 1000, datetime.timezone.utc).date().isoformat(),
                     "close": str(close)})
    bars.sort(key=lambda b: b["as_of"])
    bars = bars[-days:]
    if len(bars) < 2:
        raise MarketDataError("the Massive source returned fewer than two daily bars for " + symbol)
    payload = _payload("history", Decimal(len(bars)), bars[-1]["as_of"],
                       "Massive (api.massive.com)", _public_url(final), raw,
                       {"symbol": symbol, "provider": "massive", "bars": bars})
    _cache_put(cache_key, payload, DAY_SECONDS)
    return payload


#: Alpha Vantage OVERVIEW fields mapped to the names the screener uses.
AV_OVERVIEW_FIELDS = {
    "MarketCapitalization": "market_cap", "PERatio": "pe_ratio", "PEGRatio": "peg_ratio",
    "PriceToBookRatio": "price_to_book", "EVToEBITDA": "ev_to_ebitda", "ProfitMargin": "profit_margin",
    "ReturnOnEquity": "roe", "RevenueTTM": "revenue_ttm", "EBITDA": "ebitda",
    "QuarterlyEarningsGrowthYOY": "earnings_growth_yoy", "Currency": "currency",
    "LatestQuarter": "latest_quarter", "Name": "company", "Sector": "sector",
}


def alpha_overview(symbol):
    """Company overview from Alpha Vantage OVERVIEW (P/E, ROE, P/B, market cap).

    On the free tier this endpoint is premium and returns no data; the lookup then
    fails closed with a clear message rather than inventing a ratio.
    """
    symbol = _symbol(symbol)
    key = _alpha_key()
    cache_key = ("av_overview", symbol)
    cached = _cache_get(cache_key)
    if cached:
        return cached
    data, raw, final = _alpha_json("OVERVIEW", symbol, key)
    if not isinstance(data, dict) or not data.get("Symbol"):
        raise MarketDataError("Alpha Vantage returned no OVERVIEW for " + symbol +
                              " (OVERVIEW is a premium endpoint; free tier returns nothing)")
    out = {"symbol": str(data.get("Symbol") or symbol), "provider": "alphavantage"}
    for source, target in AV_OVERVIEW_FIELDS.items():
        value = data.get(source)
        if value not in (None, "", "None", "-", "0"):
            out[target] = str(value)
    out = {k: v for k, v in out.items() if v not in (None, "")}
    as_of = out.get("latest_quarter") or ""
    try:
        value = Decimal(str(out.get("market_cap") or "0"))
    except InvalidOperation:
        value = Decimal(0)
    payload = _payload("fundamentals", value, as_of, "Alpha Vantage (OVERVIEW)", _public_url(final), raw, out)
    _cache_put(cache_key, payload, DAY_SECONDS)
    return payload


def massive_overview(symbol):
    """Ticker overview from Massive (market cap, shares outstanding, name, sector)."""
    symbol = _symbol(symbol)
    key = _massive_key()
    cache_key = ("massive_overview", symbol)
    cached = _cache_get(cache_key)
    if cached:
        return cached
    url = MASSIVE + "/v3/reference/tickers/" + urllib.parse.quote(symbol) + "?apiKey=" + urllib.parse.quote(key)
    raw, final = _fetch(url)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise MarketDataError("the Massive source returned a response this app cannot read")
    if not isinstance(data, dict) or str(data.get("status") or "").upper() not in ("OK", "DELAYED"):
        raise MarketDataError("the Massive source refused the request: " +
                              str(data.get("error") or data.get("status") or "no status")[:300])
    results = data.get("results") or {}
    if not results:
        raise MarketDataError("the Massive source returned no ticker overview for " + symbol)
    out = {"symbol": results.get("ticker") or symbol, "provider": "massive",
           "company": results.get("name"), "sector": results.get("sic_description"),
           "cik": results.get("cik")}
    if results.get("market_cap") is not None:
        out["market_cap"] = str(results.get("market_cap"))
    if results.get("weighted_shares_outstanding") is not None:
        out["shares_outstanding"] = str(results.get("weighted_shares_outstanding"))
    out = {k: v for k, v in out.items() if v not in (None, "")}
    try:
        value = Decimal(str(out.get("market_cap") or "0"))
    except InvalidOperation:
        value = Decimal(0)
    payload = _payload("fundamentals", value, "", "Massive ticker overview (api.massive.com)",
                       _public_url(final), raw, out)
    _cache_put(cache_key, payload, DAY_SECONDS)
    return payload


#: Fundamentals provider id -> marketdata function name.
FUNDAMENTALS_PROVIDERS = {"alphavantage": "alpha_overview", "massive": "massive_overview",
                          "derived": "derived_ratios", "auto": "fundamentals_chain",
                          "chain": "fundamentals_chain"}

#: The order the fallback chain tries: the US path first, then international Alpha Vantage.
FUNDAMENTALS_CHAIN = ("derived", "alphavantage", "massive")

#: Metric keys the chain merges, each keeping the source that supplied it.
_METRIC_KEYS = ("company", "sector", "market_cap", "pe_ratio", "roe", "price_to_book",
                "profit_margin", "net_income", "shareholders_equity", "diluted_eps", "shares_outstanding")


def fundamentals(symbol, provider="alphavantage"):
    """Dispatch a fundamentals lookup to the chosen provider (Alpha Vantage or Massive)."""
    name = (provider or "alphavantage").strip().lower()
    if name not in FUNDAMENTALS_PROVIDERS:
        raise MarketDataError("unknown fundamentals provider %r; choose one of: %s"
                              % (provider, ", ".join(sorted(FUNDAMENTALS_PROVIDERS))))
    return globals()[FUNDAMENTALS_PROVIDERS[name]](symbol)


def _num(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def derived_ratios(symbol):
    """Free-tier P/E and ROE derived from SEC XBRL facts and Massive market cap.

    ROE = SEC net income / SEC shareholders' equity; P/E = Massive market cap / SEC
    net income.  Every input is a sourced value and the ratios are pure arithmetic
    on them; a missing input is a named gap, never an estimate.  SEC covers US
    registrants only, so a non-US ticker keeps these as gaps.
    """
    symbol = _symbol(symbol)
    cache_key = ("derived_ratios", symbol)
    cached = _cache_get(cache_key)
    if cached:
        return cached
    gaps = []
    facts, overview = {}, {}
    try:
        facts = sec_fundamentals(symbol)
    except MarketDataError as error:
        gaps.append("SEC fundamentals unavailable: " + str(error))
    try:
        overview = massive_overview(symbol)
    except MarketDataError as error:
        gaps.append("market cap unavailable: " + str(error))
    if not facts and not overview:
        raise MarketDataError("no SEC fundamentals and no Massive overview for " + symbol)
    values = facts.get("values") or {}
    net_income = _num(values.get("Net income"))
    equity = _num(values.get("Shareholders' equity"))
    eps = _num(values.get("Diluted EPS"))
    market_cap = _num(overview.get("market_cap"))
    out = {"symbol": symbol, "provider": "derived",
           "company": facts.get("company") or overview.get("company"),
           "sector": overview.get("sector")}
    if market_cap is not None:
        out["market_cap"] = str(market_cap)
    if net_income is not None:
        out["net_income"] = str(net_income)
    if equity is not None:
        out["shareholders_equity"] = str(equity)
    if eps is not None:
        out["diluted_eps"] = str(eps)
    if net_income is not None and equity is not None and equity > 0:
        out["roe"] = str(net_income / equity)
    else:
        gaps.append("ROE needs net income and positive shareholders' equity from SEC XBRL (US registrants)")
    if market_cap is not None and net_income is not None and net_income > 0:
        out["pe_ratio"] = str(market_cap / net_income)
    else:
        gaps.append("P/E needs market cap (Massive) and positive net income (SEC XBRL)")
    out = {k: v for k, v in out.items() if v not in (None, "")}
    combined = (str(facts.get("response_sha256") or "") + "|" +
                str(overview.get("response_sha256") or "")).encode("utf-8")
    payload = {"format": FORMAT, "kind": "fundamentals", "value": str(market_cap or net_income or 0),
               "as_of": facts.get("as_of") or "",
               "source": "Derived: SEC XBRL facts and Massive market cap (not independently verified)",
               "source_url": facts.get("source_url") or overview.get("source_url") or "",
               "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               "response_sha256": hashlib.sha256(combined).hexdigest(),
               "verification": "net income, equity and EPS are SEC XBRL facts; market cap is Massive's; "
                               "the two ratios are arithmetic on them, not independently verified by this app",
               "note": "Confirm these values; the app does not fill a method silently.",
               "sources": {"sec": facts.get("source_url"), "massive": overview.get("source_url")},
               "gaps": gaps}
    payload.update(out)
    _cache_put(cache_key, payload, DAY_SECONDS)
    return payload


def fundamentals_chain(symbol, providers=None):
    """Try several fundamentals providers and merge what each one supplies.

    Useful for a non-US ticker: the SEC/Massive path covers US registrants, then
    Alpha Vantage OVERVIEW (which accepts international exchange suffixes such as
    ``TSCO.LON``) is tried next.  Each metric keeps the source that supplied it, and
    a metric no provider returns stays a named gap.
    """
    symbol = _symbol(symbol)
    names = tuple(providers or FUNDAMENTALS_CHAIN)
    cache_key = ("fundamentals_chain", symbol, names)
    cached = _cache_get(cache_key)
    if cached:
        return cached
    merged = {"symbol": symbol, "provider": "chain", "metric_sources": {}, "contributors": [],
              "gaps": [], "source_urls": [], "response_sha256s": []}
    for name in names:
        try:
            data = fundamentals(symbol, name)
        except MarketDataError as error:
            merged["gaps"].append("%s: %s" % (name, str(error)))
            continue
        merged["contributors"].append(name)
        if data.get("source_url"):
            merged["source_urls"].append(data["source_url"])
        if data.get("response_sha256"):
            merged["response_sha256s"].append(data["response_sha256"])
        for key in _METRIC_KEYS:
            if merged.get(key) in (None, "") and data.get(key) not in (None, ""):
                merged[key] = data[key]
                merged["metric_sources"][key] = name
        for gap in (data.get("gaps") or []):
            if gap not in merged["gaps"]:
                merged["gaps"].append(gap)
    if not merged["contributors"]:
        raise MarketDataError("no fundamentals provider returned data for " + symbol + ": " +
                              "; ".join(merged["gaps"]))
    for key in ("market_cap", "pe_ratio", "roe"):
        if merged.get(key) in (None, "") and not any(key in gap for gap in merged["gaps"]):
            merged["gaps"].append("%s is not available from any configured fundamentals source" % key)
    merged["format"] = FORMAT
    merged["kind"] = "fundamentals"
    merged["value"] = str(merged.get("market_cap") or merged.get("net_income") or 0)
    merged["as_of"] = ""
    merged["source"] = "Fallback chain (" + ", ".join(merged["contributors"]) + "); not independently verified"
    merged["source_url"] = merged["source_urls"][0] if merged["source_urls"] else ""
    merged["response_sha256"] = (hashlib.sha256("|".join(merged["response_sha256s"]).encode("utf-8")).hexdigest()
                                 if merged["response_sha256s"] else "")
    merged["verification"] = "each metric is shown with the source that supplied it; the app does not invent a ratio"
    merged["note"] = "Confirm these values; the app does not fill a method silently."
    _cache_put(cache_key, merged, DAY_SECONDS)
    return merged
