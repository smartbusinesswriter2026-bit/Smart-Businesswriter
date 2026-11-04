"""Durable portfolio store for the Portfolio Lab (product layer, standard library only).

One directory per portfolio under ``BP_PORTFOLIOS_DIR`` (default ``<repo>/portfolios``):

    portfolios/<id>/
      portfolio.json          metadata, mode, mandate, benchmark, constraints
      holdings.json           current positions and target weights
      prices/<date>.json      dated price snapshot with provenance
      snapshots/<date>.json   immutable valuation snapshots
      exports/                generated documents

This module stores and validates documents; it computes no business number and imports no
frozen core module.  The snapshot endpoint in the server calls the frozen method library and
hands the result here as an opaque document.  Writes are atomic; a snapshot for a date is
written once and refused on a second write.
"""

import datetime
import csv
import hashlib
import io
import json
import os
import re
import tempfile
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

FORMAT = "bp-portfolio/1"
ID_RE = re.compile(r"[0-9a-f]{12}")
SYMBOL_RE = re.compile(r"[A-Z0-9.\-]{1,12}")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
CURRENCY_RE = re.compile(r"[A-Z]{3}")
MODES = ("paper", "fund")
STATUSES = ("draft", "active", "closed")


class PortfolioError(Exception):
    """Base class for portfolio-store failures."""


class PortfolioNotFound(PortfolioError):
    """No portfolio is stored under that id."""


class PortfolioCorrupt(PortfolioError, ValueError):
    """A stored document cannot be read (bad JSON, wrong shape or missing keys)."""


def portfolios_dir():
    configured = os.environ.get("BP_PORTFOLIOS_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[3] / "portfolios"


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _check_id(portfolio_id):
    if not isinstance(portfolio_id, str) or not ID_RE.fullmatch(portfolio_id):
        raise ValueError("portfolio id must be 12 lowercase hex characters")
    return portfolio_id


def _root(portfolio_id):
    checked = _check_id(portfolio_id)
    root = portfolios_dir().resolve()
    path = (root / checked).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("portfolio id resolves outside the portfolio store")
    return path


def _path(portfolio_id, *parts):
    path = _root(portfolio_id).joinpath(*parts).resolve()
    try:
        path.relative_to(_root(portfolio_id))
    except ValueError:
        raise ValueError("a portfolio path resolves outside the portfolio directory")
    return path


def _write(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-portfolio-", suffix=".json")
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


def _read(path, required=()):
    if not path.exists():
        raise PortfolioNotFound("no portfolio document at %s" % path.name)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise PortfolioCorrupt("%s cannot be read: %s" % (path.name, error))
    if not isinstance(document, dict):
        raise PortfolioCorrupt("%s is not an object" % path.name)
    for key in required:
        if key not in document:
            raise PortfolioCorrupt("%s is missing %r" % (path.name, key))
    return document


def _hash(document):
    return hashlib.sha256(json.dumps(document, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _symbol(value):
    symbol = str(value or "").strip().upper()
    if not SYMBOL_RE.fullmatch(symbol):
        raise ValueError("the symbol must be 1-12 letters, digits, dots or hyphens")
    return symbol


def _date(value):
    value = str(value or "").strip()
    if not DATE_RE.fullmatch(value):
        raise ValueError("the date must be YYYY-MM-DD")
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("the date is not a real calendar date")
    return value


def _decimal(value, what, positive=False, non_negative=False):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("%s must be a number" % what)
    if not number.is_finite():
        raise ValueError("%s must be finite" % what)
    if positive and number <= 0: raise ValueError("%s must be positive" % what)
    if non_negative and number < 0: raise ValueError("%s must be non-negative" % what)
    return number


def create(name, base_currency="USD", benchmark="", mode="paper", constraints=None,
           objective="", roster=""):
    name = str(name or "").strip()
    if not name: raise ValueError("a portfolio name is required")
    if len(name) > 120: raise ValueError("the portfolio name must be at most 120 characters")
    currency = str(base_currency or "USD").strip().upper()
    if not CURRENCY_RE.fullmatch(currency): raise ValueError("the base currency must be a three-letter ISO code")
    mode = str(mode or "paper").strip().lower()
    if mode not in MODES: raise ValueError("mode must be paper or fund")
    portfolio_id = uuid.uuid4().hex[:12]
    root = _root(portfolio_id)
    for part in ("prices", "snapshots", "journal", "exports"):
        (root / part).mkdir(parents=True, exist_ok=True)
    now = _now()
    document = {
        "format": FORMAT, "id": portfolio_id, "name": name, "mode": mode,
        "base_currency": currency, "benchmark": str(benchmark or "").strip(),
        "objective": str(objective or "").strip()[:2000],
        "roster": str(roster or "").strip()[:2000],
        "start_date": datetime.date.today().isoformat(), "status": "draft",
        "cadence": "weekly" if mode == "fund" else "end",
        "constraints": constraints or {"max_position": "0.10", "min_cash": "0.05", "long_only": True},
        "created_at": now, "updated_at": now,
    }
    _write(root / "portfolio.json", document)
    _write(root / "holdings.json", {"format": FORMAT, "id": portfolio_id, "holdings": []})
    return document


def _portfolio(portfolio_id):
    return _read(_path(portfolio_id, "portfolio.json"), ("format", "id", "name", "mode", "base_currency", "status"))


def _holdings_document(portfolio_id):
    document = _read(_path(portfolio_id, "holdings.json"), ("holdings",))
    if not isinstance(document.get("holdings"), list):
        raise PortfolioCorrupt("holdings must be a list")
    return document


def load(portfolio_id):
    portfolio = _portfolio(portfolio_id)
    holdings = _holdings_document(portfolio_id)["holdings"]
    snapshots = [snapshot_summary(portfolio_id, path.stem) for path in sorted(_path(portfolio_id, "snapshots").glob("*.json"))]
    price_dates = [path.stem for path in sorted(_path(portfolio_id, "prices").glob("*.json"))]
    return {"portfolio": portfolio, "holdings": holdings, "snapshots": snapshots,
            "price_dates": price_dates, "journal": journal(portfolio_id)}


def summaries():
    root = portfolios_dir()
    if not root.exists(): return []
    rows = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or not ID_RE.fullmatch(path.name): continue
        try:
            portfolio = _portfolio(path.name)
            holdings = _holdings_document(path.name)["holdings"]
            snapshots = list(_path(path.name, "snapshots").glob("*.json"))
        except (PortfolioError, ValueError):
            rows.append({"id": path.name, "corrupt": True})
            continue
        rows.append({"id": portfolio["id"], "name": portfolio["name"], "mode": portfolio["mode"],
                     "base_currency": portfolio["base_currency"], "benchmark": portfolio.get("benchmark", ""),
                     "status": portfolio["status"], "n_holdings": len(holdings),
                     "n_snapshots": len(snapshots),
                     "latest_snapshot": max((p.stem for p in snapshots), default=""),
                     "updated_at": portfolio.get("updated_at", ""), "corrupt": False})
    return rows


def update(portfolio_id, fields):
    portfolio = _portfolio(portfolio_id)
    allowed = {"name", "benchmark", "status", "cadence", "objective", "roster"}
    for key, value in (fields or {}).items():
        if key not in allowed: raise ValueError("field %r cannot be changed" % key)
        if key == "status" and value not in STATUSES: raise ValueError("status must be draft, active or closed")
        if key == "cadence" and value not in ("weekly", "end"): raise ValueError("cadence must be weekly or end")
        if key == "name":
            value = str(value).strip()
            if not value: raise ValueError("the portfolio name cannot be blank")
        if key in ("objective", "roster"):
            value = str(value or "").strip()[:2000]
        portfolio[key] = value
    portfolio["updated_at"] = _now()
    _write(_path(portfolio_id, "portfolio.json"), portfolio)
    return portfolio


def add_holding(portfolio_id, symbol, shares, cost_basis="0", rationale=""):
    _portfolio(portfolio_id)
    symbol = _symbol(symbol)
    shares = _decimal(shares, "shares", positive=True)
    cost = _decimal(cost_basis or 0, "cost basis", non_negative=True)
    why = str(rationale or "").strip()[:2000]
    document = _holdings_document(portfolio_id)
    rows = [row for row in document["holdings"] if str(row.get("symbol", "")).upper() != symbol]
    rows.append({"symbol": symbol, "shares": str(shares), "cost_basis": str(cost), "rationale": why})
    document["holdings"] = sorted(rows, key=lambda row: row["symbol"])
    _write(_path(portfolio_id, "holdings.json"), document)
    return document["holdings"]


def remove_holding(portfolio_id, symbol):
    _portfolio(portfolio_id)
    symbol = _symbol(symbol)
    document = _holdings_document(portfolio_id)
    document["holdings"] = [row for row in document["holdings"] if str(row.get("symbol", "")).upper() != symbol]
    _write(_path(portfolio_id, "holdings.json"), document)
    return document["holdings"]


def set_price(portfolio_id, symbol, date, price, source="user", as_of=""):
    _portfolio(portfolio_id)
    symbol = _symbol(symbol)
    day = _date(date)
    quoted = _date(as_of) if as_of not in (None, "") else day
    value = _decimal(price, "price", positive=True)
    held = {str(row["symbol"]).upper() for row in _holdings_document(portfolio_id)["holdings"]}
    if symbol not in held: raise ValueError("add %s as a holding before setting its price" % symbol)
    if _path(portfolio_id, "snapshots", day + ".json").exists():
        raise PortfolioError("the snapshot for %s is already saved; its prices are immutable" % day)
    path = _path(portfolio_id, "prices", day + ".json")
    document = _read(path) if path.exists() else {"format": FORMAT, "date": day, "prices": {}}
    document["prices"][symbol] = {"price": str(value), "source": str(source or "user")[:40], "as_of": quoted,
                                  "retrieved_at": _now()}
    document["updated_at"] = _now()
    _write(path, document)
    return document


def prices(portfolio_id, date):
    path = _path(portfolio_id, "prices", _date(date) + ".json")
    if not path.exists(): raise PortfolioNotFound("no prices are stored for %s" % date)
    return _read(path, ("prices",))


# --- paste / CSV import -----------------------------------------------------
# Import parses text the student pasted; it does no arithmetic, fetches nothing
# and writes once.  Every row is validated before anything is stored, so a bad
# row refuses the whole paste rather than importing part of it.

def _delimiter(text):
    for line in str(text or "").splitlines():
        if not line.strip():
            continue
        if "\t" in line:
            return "\t"
        if ";" in line and "," not in line:
            return ";"
        return ","
    return ","


def _table(text, what):
    if not str(text or "").strip():
        raise ValueError("paste at least one %s row first" % what)
    try:
        rows = list(csv.reader(io.StringIO(str(text)), delimiter=_delimiter(text)))
    except csv.Error as error:
        raise ValueError("the pasted %s table cannot be read: %s" % (what, error))
    return [[cell.strip() for cell in row] for row in rows if any(cell.strip() for cell in row)]


#: A first row is a header only when its label is one of these, so a data row
#: with a bad value is refused by name and line rather than skipped as a header.
_HEADER_WORDS = {"symbol", "ticker", "stock", "security", "code", "name", "holding",
                 "asset", "instrument", "shares", "quantity", "qty", "units", "cost",
                 "cost basis", "price", "quote", "close", "source"}


def _is_header(cells):
    first = str(cells[0] if cells else "").strip().lower().replace("_", " ")
    return first in _HEADER_WORDS


def parse_holdings(text):
    """Parse pasted holding rows: symbol, shares, optional cost basis."""
    parsed, seen = [], set()
    for number, cells in enumerate(_table(text, "holding"), 1):
        if number == 1 and _is_header(cells):
            continue  # a labelled header row is accepted and skipped
        if len(cells) < 2:
            raise ValueError("holding row %d needs a symbol and shares" % number)
        symbol = _symbol(cells[0])
        if symbol in seen:
            raise ValueError("holding row %d repeats %s; keep one row per symbol" % (number, symbol))
        seen.add(symbol)
        shares = _decimal(cells[1], "shares on row %d" % number, positive=True)
        cost = _decimal(cells[2] if len(cells) > 2 and cells[2] else 0,
                        "cost basis on row %d" % number, non_negative=True)
        parsed.append({"symbol": symbol, "shares": str(shares), "cost_basis": str(cost)})
    if not parsed:
        raise ValueError("the paste has a header but no holding rows")
    return parsed


def import_holdings(portfolio_id, text):
    """Upsert every pasted holding in one write."""
    rows = parse_holdings(text)
    _portfolio(portfolio_id)
    document = _holdings_document(portfolio_id)
    merged = {str(row["symbol"]).upper(): row for row in document["holdings"]}
    for row in rows:
        merged[row["symbol"]] = row
    document["holdings"] = sorted(merged.values(), key=lambda row: row["symbol"])
    _write(_path(portfolio_id, "holdings.json"), document)
    return document["holdings"]


def parse_prices(text):
    """Parse pasted price rows: symbol, price, optional source."""
    parsed, seen = [], set()
    for number, cells in enumerate(_table(text, "price"), 1):
        if number == 1 and _is_header(cells):
            continue  # a labelled header row is accepted and skipped
        if len(cells) < 2:
            raise ValueError("price row %d needs a symbol and a price" % number)
        symbol = _symbol(cells[0])
        if symbol in seen:
            raise ValueError("price row %d repeats %s; keep one price per symbol" % (number, symbol))
        seen.add(symbol)
        value = _decimal(cells[1], "price on row %d" % number, positive=True)
        parsed.append({"symbol": symbol, "price": str(value),
                       "source": (cells[2] if len(cells) > 2 and cells[2] else "")})
    if not parsed:
        raise ValueError("the paste has a header but no price rows")
    return parsed


def import_prices(portfolio_id, text, date, source="user"):
    """Store every pasted price for one date in one write.

    The date must not already carry a snapshot, and every symbol must already
    be a holding; a wrong symbol refuses the whole paste.
    """
    day = _date(date)
    rows = parse_prices(text)
    _portfolio(portfolio_id)
    if _path(portfolio_id, "snapshots", day + ".json").exists():
        raise PortfolioError("the snapshot for %s is already saved; its prices are immutable" % day)
    held = {str(row["symbol"]).upper() for row in _holdings_document(portfolio_id)["holdings"]}
    unknown = [row["symbol"] for row in rows if row["symbol"] not in held]
    if unknown:
        raise ValueError("add these symbols as holdings first: " + ", ".join(unknown))
    path = _path(portfolio_id, "prices", day + ".json")
    document = _read(path) if path.exists() else {"format": FORMAT, "date": day, "prices": {}}
    for row in rows:
        document["prices"][row["symbol"]] = {
            "price": row["price"], "source": str(row["source"] or source or "user")[:40],
            "as_of": day, "retrieved_at": _now()}
    document["updated_at"] = _now()
    _write(path, document)
    return document


# --- the fund journal -------------------------------------------------------
# One entry per period-ending date: the student's note, that period's external
# flow and, if they use one, the benchmark level at that date.  The store keeps
# the words; it computes nothing.

def journal(portfolio_id):
    rows = []
    for path in sorted(_path(portfolio_id, "journal").glob("*.json")):
        rows.append(_read(path, ("date",)))
    return rows


def journal_entry(portfolio_id, date):
    return _read(_path(portfolio_id, "journal", _date(date) + ".json"), ("date",))


def save_journal(portfolio_id, date, note="", flow="0", benchmark=""):
    _portfolio(portfolio_id)
    day = _date(date)
    flow_value = _decimal(flow if flow not in (None, "") else 0, "flow")
    level = "" if benchmark in (None, "") else str(_decimal(benchmark, "benchmark level", positive=True))
    text = str(note or "").strip()
    if len(text) > 4000: raise ValueError("the note must be at most 4000 characters")
    path = _path(portfolio_id, "journal", day + ".json")
    now = _now()
    created = _read(path).get("created_at", now) if path.exists() else now
    document = {"format": FORMAT, "id": portfolio_id, "date": day, "note": text,
                "flow": str(flow_value), "benchmark": level,
                "created_at": created, "updated_at": now}
    _write(path, document)
    return document


def remove_journal(portfolio_id, date):
    _portfolio(portfolio_id)
    path = _path(portfolio_id, "journal", _date(date) + ".json")
    if not path.exists(): raise PortfolioNotFound("no journal entry for %s" % date)
    path.unlink()
    return True


def save_snapshot(portfolio_id, snapshot):
    _portfolio(portfolio_id)
    day = _date(snapshot.get("date"))
    path = _path(portfolio_id, "snapshots", day + ".json")
    if path.exists(): raise PortfolioError("a snapshot for %s already exists" % day)
    document = {**snapshot, "format": FORMAT, "id": portfolio_id, "date": day, "created_at": _now()}
    document["document_hash"] = _hash(document)
    _write(path, document)
    return document


def snapshot_summary(portfolio_id, date):
    document = _read(_path(portfolio_id, "snapshots", date + ".json"), ("date", "outputs"))
    outputs = document.get("outputs") or {}
    return {"date": document["date"], "nav": outputs.get("nav", ""),
            "invested_value": outputs.get("invested_value", ""), "cash": outputs.get("cash", ""),
            "document_hash": document.get("document_hash", ""), "method": document.get("method", "")}


def snapshot(portfolio_id, date):
    return _read(_path(portfolio_id, "snapshots", _date(date) + ".json"), ("date", "outputs"))


def delete(portfolio_id):
    _portfolio(portfolio_id)
    root = _root(portfolio_id)
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file(): path.unlink()
        elif path.is_dir(): path.rmdir()
    root.rmdir()
    return True
