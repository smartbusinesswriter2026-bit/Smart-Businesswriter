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


def record(instrument_id, quote=None, fetch=None):
    """Append (or update same-day) a price snapshot and return the document.

    When ``quote`` is omitted the instrument's live quote is fetched through the
    market-data layer; the ``fetch`` seam lets a test supply the payload without
    a network call.  A provider failure is re-raised as ``InstrumentError``.
    """
    document = load(instrument_id)
    if quote is None:
        fetcher = fetch or marketdata.equity_quote
        try:
            quote = fetcher(document["symbol"])
        except marketdata.MarketDataError as error:
            raise InstrumentError(str(error))
    snapshot = _snapshot_from_quote(quote)
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


def delete(instrument_id):
    """Remove an instrument record and return the deletion result."""
    path = _path(instrument_id)
    if not path.exists():
        raise InstrumentNotFound("no instrument is stored with id %s" % instrument_id)
    os.unlink(path)
    return {"deleted": instrument_id}


