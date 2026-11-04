"""Price-record store for tracked instruments (product layer, standard library only).

One JSON document per tracked stock/ETF/bond/FX instrument under
``<case store>/instruments/``.  A document is an **append-only record of price
snapshots**: each snapshot is the value a provider returned on a given day, with
its source, URL and response hash.  Over several weeks the accumulated snapshots
become the return series a student can evaluate -- the system never invents a
history feed.

The only arithmetic here is a trivial simple return derived from two recorded
prices; the frozen portfolio/risk methods remain the sole evaluators.  Refusals
fail closed: a bad id, a traversal, a corrupt file, a snapshot that is not a
positive price, or a returns request with fewer than two points.

Snapshots are deduplicated by their ``as_of`` date, so recording the same day
twice updates that day rather than adding a duplicate.  This module never
imports the frozen core.
"""

import datetime
import json
import os
import re
import tempfile
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

from . import cases
from . import marketdata

FORMAT = "bp-instrument/1"

#: A stored instrument id is exactly twelve lowercase hex characters.
ID_RE = re.compile(r"[0-9a-f]{12}")

#: Instrument kinds the store understands.
KINDS = ("equity", "etf", "bond", "fx", "other")


class InstrumentError(Exception):
    """Base class for instrument-store failures."""


class InstrumentNotFound(InstrumentError):
    """No instrument is stored under that id."""


class InstrumentCorrupt(InstrumentError, ValueError):
    """A stored instrument cannot be read (bad JSON or wrong shape)."""


def instruments_dir():
    """The directory that holds the instrument records."""
    return cases.cases_dir() / "instruments"


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _check_id(instrument_id):
    """Refuse anything that is not twelve lowercase hex characters."""
    if not isinstance(instrument_id, str) or not ID_RE.fullmatch(instrument_id):
        raise ValueError("instrument id must be 12 lowercase hex characters")
    return instrument_id


def _path(instrument_id):
    """The file that holds an instrument, after refusing traversal."""
    checked = _check_id(instrument_id)
    root = instruments_dir().resolve()
    path = (root / (checked + ".json")).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("instrument id resolves outside the store")
    return path


def _write(path, document):
    """Write one JSON document atomically: temp file, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-instrument-", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return path


def _symbol(value):
    symbol = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9.\-]{1,12}", symbol):
        raise InstrumentError("the symbol must be 1-12 letters, digits, dots or hyphens")
    return symbol


def _snapshot_from_quote(quote):
    """Turn one marketdata quote payload into a stored snapshot."""
    if not isinstance(quote, dict):
        raise InstrumentError("a quote payload is required")
    try:
        price = Decimal(str(quote.get("value")))
    except (InvalidOperation, TypeError):
        raise InstrumentError("the quote carries no usable price")
    if price <= 0:
        raise InstrumentError("the quoted price must be positive")
    as_of = str(quote.get("as_of") or "").strip()
    if not as_of:
        raise InstrumentError("the quote carries no as-of date")
    snapshot = {"as_of": as_of, "price": str(price),
                "source": str(quote.get("source") or "").strip(),
                "source_url": str(quote.get("source_url") or "").strip(),
                "response_sha256": str(quote.get("response_sha256") or "").strip(),
                "recorded_at": _now_iso()}
    previous = quote.get("previous_close")
    if previous not in (None, ""):
        try:
            value = Decimal(str(previous))
            if value > 0:
                snapshot["previous_close"] = str(value)
        except (InvalidOperation, TypeError):
            pass
    return snapshot


def create(symbol, label=None, kind="equity", sector=None):
    """Create an empty instrument record and return the stored document."""
    symbol = _symbol(symbol)
    kind = (kind or "equity").strip().lower()
    if kind not in KINDS:
        raise InstrumentError("kind must be one of: " + ", ".join(KINDS))
    document = {"format": FORMAT, "id": uuid.uuid4().hex[:12], "symbol": symbol,
                "label": (str(label).strip() if label else symbol), "kind": kind,
                "sector": (str(sector).strip() if sector else ""),
                "snapshots": [], "created_at": _now_iso(), "updated_at": _now_iso()}
    _write(_path(document["id"]), document)
    return document


def load(instrument_id):
    """Return the stored instrument document, unchanged, or raise."""
    path = _path(instrument_id)
    if not path.exists():
        raise InstrumentNotFound("no instrument is stored with id %s" % instrument_id)
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise InstrumentCorrupt("instrument %s cannot be read: %s" % (instrument_id, error))
    try:
        document = json.loads(raw)
    except ValueError as error:
        raise InstrumentCorrupt("instrument %s is not readable JSON: %s" % (instrument_id, error))
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise InstrumentCorrupt("instrument %s is not a %s document" % (instrument_id, FORMAT))
    for key in ("id", "symbol", "kind"):
        if key not in document:
            raise InstrumentCorrupt("instrument %s is missing %r" % (instrument_id, key))
    if not isinstance(document.get("snapshots"), list):
        raise InstrumentCorrupt("instrument %s has no snapshot list" % instrument_id)
    return document


#: Provider ids the store can fetch a quote from, mapped to their marketdata function.
QUOTE_PROVIDERS = {"alphavantage": "equity_quote", "massive": "massive_quote"}


def _quote_fetcher(provider):
    name = (provider or "alphavantage").strip().lower()
    if name not in QUOTE_PROVIDERS:
        raise InstrumentError("unknown quote provider %r; choose one of: %s"
                              % (provider, ", ".join(sorted(QUOTE_PROVIDERS))))
    return getattr(marketdata, QUOTE_PROVIDERS[name])


def record(instrument_id, quote=None, fetch=None, provider="alphavantage"):
    """Append (or update same-day) a price snapshot and return the document.

    When ``quote`` is omitted the instrument's live quote is fetched through the
    market-data layer; the ``fetch`` seam lets a test supply the payload without
    a network call.  A provider failure is re-raised as ``InstrumentError``.
    """
    document = load(instrument_id)
    if quote is None:
        fetcher = fetch or _quote_fetcher(provider)
        try:
            quote = fetcher(document["symbol"])
        except marketdata.MarketDataError as error:
            raise InstrumentError(str(error))
    try:
        snapshot = _snapshot_from_quote(quote)
    except InstrumentError as error:
        # Name the symbol and the provider: "the quoted price must be positive" on its own
        # leaves a student guessing which ticker failed and why.
        raise InstrumentError(
            "%s: %s. No price was stored; check the ticker and try again." %
            (document.get("symbol") or "the instrument", error))
    snapshots = [s for s in document.get("snapshots", []) if s.get("as_of") != snapshot["as_of"]]
    snapshots.append(snapshot)
    snapshots.sort(key=lambda s: str(s.get("as_of") or ""))
    document["snapshots"] = snapshots
    document["updated_at"] = _now_iso()
    _write(_path(document["id"]), document)
    return document


def returns_series(document):
    """Simple per-period returns from consecutive recorded prices, oldest first."""
    prices = []
    for snapshot in sorted(document.get("snapshots", []), key=lambda s: str(s.get("as_of") or "")):
        try:
            price = Decimal(str(snapshot.get("price")))
        except (InvalidOperation, TypeError):
            continue
        if price > 0:
            prices.append(price)
    return [str((current - previous) / previous) for previous, current in zip(prices, prices[1:])]


def readiness(document):
    """How far the record is from a usable return/risk series, with named gaps."""
    snapshots = [s for s in document.get("snapshots", []) if s.get("price")]
    returns = returns_series(document)
    gaps = []
    if len(snapshots) < 2:
        gaps.append("record at least two price snapshots before any return can be computed")
    if len(returns) < 3:
        gaps.append("mean, standard deviation and Sharpe need at least three returns; %d so far"
                    % len(returns))
    return {"snapshots": len(snapshots), "returns": len(returns),
            "risk_ready": len(returns) >= 3, "gaps": gaps}


def summary(document):
    """A compact row for the instrument list."""
    last = document["snapshots"][-1] if document.get("snapshots") else {}
    counts = readiness(document)
    return {"id": document["id"], "symbol": document["symbol"], "label": document.get("label"),
            "kind": document.get("kind"), "sector": document.get("sector"),
            "snapshots": counts["snapshots"], "returns": counts["returns"],
            "risk_ready": counts["risk_ready"],
            "last_as_of": last.get("as_of"), "last_price": last.get("price"),
            "updated_at": document.get("updated_at")}


def list_instruments():
    """Every stored instrument as a summary row."""
    root = instruments_dir()
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.glob("*.json")):
        if not ID_RE.fullmatch(path.stem):
            continue
        try:
            rows.append(summary(load(path.stem)))
        except (InstrumentError, ValueError):
            continue
    return rows


def all_documents():
    """Every stored instrument document (corrupt files are skipped)."""
    root = instruments_dir()
    if not root.exists():
        return []
    documents = []
    for path in sorted(root.glob("*.json")):
        if not ID_RE.fullmatch(path.stem):
            continue
        try:
            documents.append(load(path.stem))
        except (InstrumentError, ValueError):
            continue
    return documents


def by_symbol():
    """An index of symbol -> instrument document (first match wins)."""
    index = {}
    for document in all_documents():
        index.setdefault(document.get("symbol"), document)
    return index


def seed(instrument_id, days=30, fetch=None):
    """Fill an instrument's history from a provider's daily bars (default Massive).

    Every bar becomes a dated snapshot (close price, source, URL, SHA), deduped by
    as_of, so the return series is ready immediately instead of waiting for weeks of
    manual recording.  No price is invented: the bars come from the provider, and a
    provider failure is raised as ``InstrumentError``.
    """
    document = load(instrument_id)
    fetcher = fetch or marketdata.massive_history
    try:
        history = fetcher(document["symbol"], days)
    except marketdata.MarketDataError as error:
        raise InstrumentError(str(error))
    bars = (history or {}).get("bars") or []
    if not bars:
        raise InstrumentError("the history source returned no daily bars")
    snapshots = {str(s.get("as_of")): s for s in document.get("snapshots", [])}
    for bar in bars:
        as_of = str(bar.get("as_of") or "").strip()
        try:
            price = Decimal(str(bar.get("close")))
        except (InvalidOperation, TypeError):
            continue
        if not as_of or price <= 0:
            continue
        snapshots[as_of] = {"as_of": as_of, "price": str(price),
                            "source": history.get("source") or "Massive (api.massive.com)",
                            "source_url": history.get("source_url") or "",
                            "response_sha256": history.get("response_sha256") or "",
                            "recorded_at": _now_iso()}
    document["snapshots"] = sorted(snapshots.values(), key=lambda s: str(s.get("as_of") or ""))
    document["updated_at"] = _now_iso()
    _write(_path(document["id"]), document)
    return document


def delete(instrument_id):
    """Remove an instrument record and return the deletion result."""
    path = _path(instrument_id)
    if not path.exists():
        raise InstrumentNotFound("no instrument is stored with id %s" % instrument_id)
    os.unlink(path)
    return {"deleted": instrument_id}

# ---- Guidance, reference list and example books (B-178) --------------------

CATALOGUE_VERSION = 1

GUIDANCE = {
    "title": "How to choose what you hold",
    "intro": ("A portfolio is the collection of holdings you declare. The app does not recommend, "
              "rank or forecast an investment: it helps you make a deliberate choice and record why "
              "you made it, so the report can defend the decision. Work through these steps in order."),
    "steps": [
        {"title": "Write the mandate.",
         "text": ("State the objective, the benchmark you will be measured against and the base "
                  "currency before you look at a single name. A mandate you can restate in one "
                  "sentence is a mandate you can defend.")},
        {"title": "Decide the mix before the names.",
         "text": ("A broad index fund is a diversified core; a sector or thematic fund is a "
                  "deliberate tilt; a single company is a firm-specific view; cash is liquidity. "
                  "Write the target share of each before you pick a ticker.")},
        {"title": "Pick from the list, not from a tip.",
         "text": ("The list below is a fixed reference set of large, widely held listings with a "
                  "one-line description and a source link. It is not ranked and it carries no "
                  "expected return. Read what the instrument is, then add it.")},
        {"title": "Check that it fits the book.",
         "text": ("One base currency: a foreign price must be converted before entry, because the "
                  "app does not convert it for you. Keep the declared limits (by default no single "
                  "position above 10% of NAV and at least 5% cash), and remember a holding you "
                  "cannot price is not a holding yet.")},
        {"title": "Read the evidence, then write the reason.",
         "text": ("Open the fundamentals and filings lookup beside the book, then write one line "
                  "per holding: what you expect it to do in this portfolio and what would make you "
                  "remove it. The report prints it under Holdings and rationale; a blank reason is "
                  "a gap, not a neutral choice.")},
        {"title": "Snapshot, then grade the decision.",
         "text": ("Create the dated snapshot, read the checks, export the report, then compare the "
                  "outcome with the reason you wrote. A defensible decision is one you can explain, "
                  "not one that happened to go up.")},
    ],
    "principles": [
        "The app never recommends, ranks or forecasts an investment.",
        "Diversification is a decision you make; the app only reports the concentration you end up with.",
        "A price is a declared value on a date, not the value of the company.",
        "If you cannot write the reason, you are not ready to hold it.",
    ],
    "limits": [
        "No FX conversion: convert a foreign price before entry.",
        "No fees, tax, dividends or corporate actions.",
        "No forecast, target price or rating.",
        "The list is a fixed reference and is not a complete market; a listing is not an endorsement.",
    ],
}

#: The instrument list. `quote_supported` says whether the optional free quote
#: source is likely to answer for this listing; a manual price always works.
CATALOGUE = [
    {"id": "voo", "symbol": "VOO", "name": "Vanguard S&P 500 ETF", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Tracks the S&P 500: about 500 large US companies in one fund.",
     "teaching_note": ("One fund holds hundreds of companies, so a single company's result moves "
                       "it only a little. A common diversified core."),
     "source_url": "https://investor.vanguard.com/investment-products/etfs/profile/voo"},
    {"id": "vti", "symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Tracks the total US stock market, from the largest to the smallest listed company.",
     "teaching_note": "Broader than a large-cap index: it reaches smaller companies as well.",
     "source_url": "https://investor.vanguard.com/investment-products/etfs/profile/vti"},
    {"id": "vxus", "symbol": "VXUS", "name": "Vanguard Total International Stock ETF",
     "exchange": "NASDAQ", "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds listed companies outside the United States in one fund.",
     "teaching_note": ("Adds countries and currencies a US-only fund misses; the fund's own price "
                       "is quoted in the base currency."),
     "source_url": "https://investor.vanguard.com/investment-products/etfs/profile/vxus"},
    {"id": "vt", "symbol": "VT", "name": "Vanguard Total World Stock ETF", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "A single global fund covering US and non-US listed companies.",
     "teaching_note": "Global diversification in one line, instead of several regional funds.",
     "source_url": "https://investor.vanguard.com/investment-products/etfs/profile/vt"},
    {"id": "qqq", "symbol": "QQQ", "name": "Invesco QQQ Trust", "exchange": "NASDAQ",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Tracks the Nasdaq-100: the largest non-financial companies listed on Nasdaq.",
     "teaching_note": ("Concentrated in large growth companies, so it behaves differently from a "
                       "broad market fund."),
     "source_url": "https://www.invesco.com/qqq-etf/en/home.html"},
    {"id": "iwm", "symbol": "IWM", "name": "iShares Russell 2000 ETF", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Tracks 2,000 smaller US companies.",
     "teaching_note": "Smaller companies can move more than large ones in the same market.",
     "source_url": "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf"},
    {"id": "xle", "symbol": "XLE", "name": "Energy Select Sector SPDR Fund", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds energy-sector companies: oil, gas and energy equipment and services.",
     "teaching_note": ("A sector fund is a deliberate tilt: its result follows one industry, not "
                       "the whole market."),
     "source_url": "https://www.ssga.com/us/en/intermediary/etfs/the-energy-select-sector-spdr-fund-xle"},
    {"id": "xlk", "symbol": "XLK", "name": "Technology Select Sector SPDR Fund",
     "exchange": "NYSE Arca", "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds technology-sector companies.",
     "teaching_note": "A sector tilt means a large share of the book can depend on one industry.",
     "source_url": "https://www.ssga.com/us/en/intermediary/etfs/the-technology-select-sector-spdr-fund-xlk"},
    {"id": "xlv", "symbol": "XLV", "name": "Health Care Select Sector SPDR Fund",
     "exchange": "NYSE Arca", "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds health-care-sector companies: pharmaceuticals, providers and equipment.",
     "teaching_note": "A defensive sector in many market conditions, but still one industry.",
     "source_url": "https://www.ssga.com/us/en/intermediary/etfs/the-health-care-select-sector-spdr-fund-xlv"},
    {"id": "xlf", "symbol": "XLF", "name": "Financial Select Sector SPDR Fund",
     "exchange": "NYSE Arca", "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds banks, insurers and other financial companies.",
     "teaching_note": "A sector whose results are sensitive to interest rates and credit conditions.",
     "source_url": "https://www.ssga.com/us/en/intermediary/etfs/the-financial-select-sector-spdr-fund-xlf"},
    {"id": "vnq", "symbol": "VNQ", "name": "Vanguard Real Estate ETF", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds real-estate investment trusts and related companies.",
     "teaching_note": "Property-linked cash flows and values move for their own reasons.",
     "source_url": "https://investor.vanguard.com/investment-products/etfs/profile/vnq"},
    {"id": "aapl", "symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Consumer electronics, software and services.",
     "teaching_note": "One company: a firm-specific view, not a diversified holding.",
     "source_url": "https://investor.apple.com/"},
    {"id": "msft", "symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Software, cloud computing and hardware.",
     "teaching_note": "One company: its own results drive the holding, not the market average.",
     "source_url": "https://www.microsoft.com/en-us/investor"},
    {"id": "nvda", "symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Graphics processors and accelerated computing.",
     "teaching_note": "A single company whose price has moved sharply; concentration risk shows here.",
     "source_url": "https://investor.nvidia.com/"},
    {"id": "ko", "symbol": "KO", "name": "The Coca-Cola Company", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Beverages, sold in most countries in the world.",
     "teaching_note": "A single, mature company: lower volatility than a small growth company is not diversification.",
     "source_url": "https://investors.coca-colacompany.com/"},
    {"id": "pg", "symbol": "PG", "name": "Procter & Gamble Company", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Household and personal-care products.",
     "teaching_note": "Demand tends to be steady, but this is still one company and one share of the book.",
     "source_url": "https://www.pginvestor.com/"},
    {"id": "jnj", "symbol": "JNJ", "name": "Johnson & Johnson", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Pharmaceuticals, medical devices and consumer health products.",
     "teaching_note": "One company across several health-care segments; not a substitute for a sector fund.",
     "source_url": "https://www.investor.jnj.com/"},
    {"id": "jpm", "symbol": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Banking, payments and asset management.",
     "teaching_note": "A bank's results depend on interest rates, credit and the economy.",
     "source_url": "https://www.jpmorganchase.com/ir"},
    {"id": "xom", "symbol": "XOM", "name": "Exxon Mobil Corporation", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Oil and gas exploration, production and refining.",
     "teaching_note": "Earnings follow energy prices; one commodity cycle can dominate the result.",
     "source_url": "https://investor.exxonmobil.com/"},
    {"id": "wmt", "symbol": "WMT", "name": "Walmart Inc.", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Retail stores and e-commerce, mostly in the United States.",
     "teaching_note": "Retail margins are thin; the reason to hold it must say why it fits the mandate.",
     "source_url": "https://stock.walmart.com/"},
]

#: Composition examples, never advice. Every row is editable before it is saved.
SAMPLE_BOOKS = [
    {"id": "core", "label": "Diversified core",
     "intent": ("A broad-market core with an international sleeve and a small firm-specific "
                "position: the shape a first paper usually starts from."),
     "holdings": [{"symbol": "VOO", "shares": "20", "cost_basis": "0"},
                  {"symbol": "VTI", "shares": "10", "cost_basis": "0"},
                  {"symbol": "VXUS", "shares": "15", "cost_basis": "0"},
                  {"symbol": "AAPL", "shares": "5", "cost_basis": "0"}],
     "cash": "5000",
     "note": ("Example only, not advice: four positions is a starting point, not a rule. Load it, "
              "then replace, resize or remove every row with your own decision.")},
    {"id": "balanced", "label": "Balanced with a cash buffer",
     "intent": ("A core fund plus two sector tilts and a steady single name, held with a larger "
                "cash balance to show how cash changes the concentration arithmetic."),
     "holdings": [{"symbol": "VOO", "shares": "10", "cost_basis": "0"},
                  {"symbol": "XLV", "shares": "5", "cost_basis": "0"},
                  {"symbol": "XLK", "shares": "5", "cost_basis": "0"},
                  {"symbol": "KO", "shares": "20", "cost_basis": "0"}],
     "cash": "8000",
     "note": ("Example only, not advice: sector funds are tilts and add industry risk. Replace them "
              "if your mandate does not call for a tilt.")},
    {"id": "concentrated", "label": "Concentrated growth view",
     "intent": ("A deliberately concentrated book: one growth fund, one technology tilt and two "
                "large single names. It exists to show what a high-concentration result looks like."),
     "holdings": [{"symbol": "QQQ", "shares": "10", "cost_basis": "0"},
                  {"symbol": "XLK", "shares": "8", "cost_basis": "0"},
                  {"symbol": "NVDA", "shares": "3", "cost_basis": "0"},
                  {"symbol": "MSFT", "shares": "2", "cost_basis": "0"}],
     "cash": "1000",
     "note": ("Example only, not advice: this book is concentrated and will breach the default "
              "10% position limit. It is here so you can see why the limits exist.")},
]


def guidance():
    return GUIDANCE


def catalogue():
    return [dict(row) for row in CATALOGUE]


def sample_books():
    return [dict(row) for row in SAMPLE_BOOKS]


def find(symbol):
    wanted = str(symbol or "").strip().upper()
    for row in CATALOGUE:
        if row["symbol"] == wanted:
            return dict(row)
    return None


def bundle():
    """Everything the page needs to render the chooser and the guide, in one payload."""
    return {"format": "bp-instruments/1", "catalogue_version": CATALOGUE_VERSION,
            "guidance": guidance(), "instruments": catalogue(),
            "sample_books": sample_books(),
            "note": ("A fixed reference list of widely held long-only listings. Not ranked, not "
                     "advice and not a forecast; every price is a declared figure the student enters.")}
