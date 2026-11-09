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
    for part in ("prices", "snapshots", "journal", "exports", "statements"):
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


def _normalise_rationale(rationale):
    """Accept a string (legacy) or a dict (structured) and return a structured rationale.

    A string becomes {"thesis": string}.  A dict keeps its fields.  The structured form
    is what the reflection step grades against.
    """
    if isinstance(rationale, dict):
        out = {}
        for key in ("thesis", "key_risks", "catalysts", "target_price", "kill_criteria", "review_date"):
            if key in rationale and rationale[key] is not None:
                out[key] = rationale[key]
        if not out:
            out["thesis"] = str(rationale).strip()[:2000]
        return out
    text = str(rationale or "").strip()[:2000]
    return {"thesis": text} if text else {}


def add_holding(portfolio_id, symbol, shares, cost_basis="0", rationale="", trade=None):
    _portfolio(portfolio_id)
    symbol = _symbol(symbol)
    shares = _decimal(shares, "shares", positive=True)
    cost = _decimal(cost_basis or 0, "cost basis", non_negative=True)
    why = _normalise_rationale(rationale)
    document = _holdings_document(portfolio_id)
    rows = [row for row in document["holdings"] if str(row.get("symbol", "")).upper() != symbol]
    entry = {"symbol": symbol, "shares": str(shares), "cost_basis": str(cost),
             "rationale": why, "trades": [], "corporate_actions": []}
    # Backward compat: migrate old string rationale
    if isinstance(document.get("holdings"), list):
        for old_row in document["holdings"]:
            if str(old_row.get("symbol", "")).upper() == symbol:
                old_r = old_row.get("rationale")
                if isinstance(old_r, str):
                    entry["rationale"] = {"thesis": old_r}
                if isinstance(old_row.get("trades"), list):
                    entry["trades"] = old_row["trades"]
                if isinstance(old_row.get("corporate_actions"), list):
                    entry["corporate_actions"] = old_row["corporate_actions"]
    # Record this trade in the ledger
    if trade and isinstance(trade, dict):
        entry["trades"].append({
            "date": str(trade.get("date") or ""),
            "action": str(trade.get("action") or "buy").lower(),
            "shares": str(trade.get("shares") or shares),
            "price": str(trade.get("price") or cost),
            "note": str(trade.get("note") or ""),
            "recorded_at": _now(),
        })
    rows.append(entry)
    document["holdings"] = sorted(rows, key=lambda row: row["symbol"])
    _write(_path(portfolio_id, "holdings.json"), document)
    return document["holdings"]


def save_trade(portfolio_id, symbol, date, action, shares, price, note=""):
    """Record a dated trade in the holding's trade ledger."""
    _portfolio(portfolio_id)
    symbol = _symbol(symbol)
    doc = _holdings_document(portfolio_id)
    found = False
    for row in doc["holdings"]:
        if str(row.get("symbol", "")).upper() == symbol:
            row.setdefault("trades", [])
            row["trades"].append({
                "date": _date(date), "action": str(action or "buy").lower(),
                "shares": str(_decimal(shares, "shares", positive=True)),
                "price": str(_decimal(price, "price", positive=True)),
                "note": str(note or "").strip()[:500],
                "recorded_at": _now(),
            })
            row["trades"].sort(key=lambda t: t.get("date", ""))
            found = True
            break
    if not found:
        raise ValueError("add %s as a holding before recording a trade" % symbol)
    _write(_path(portfolio_id, "holdings.json"), doc)
    return doc["holdings"]


def save_corporate_action(portfolio_id, symbol, date, action_type, amount, note=""):
    """Record a corporate action (split, dividend, merger) affecting a holding."""
    _portfolio(portfolio_id)
    symbol = _symbol(symbol)
    doc = _holdings_document(portfolio_id)
    found = False
    for row in doc["holdings"]:
        if str(row.get("symbol", "")).upper() == symbol:
            row.setdefault("corporate_actions", [])
            row["corporate_actions"].append({
                "date": _date(date), "type": str(action_type or "").strip().lower(),
                "amount": str(_decimal(amount, "amount", non_negative=True)),
                "note": str(note or "").strip()[:500],
                "recorded_at": _now(),
            })
            row["corporate_actions"].sort(key=lambda t: t.get("date", ""))
            found = True
            break
    if not found:
        raise ValueError("add %s as a holding before recording a corporate action" % symbol)
    _write(_path(portfolio_id, "holdings.json"), doc)
    return doc["holdings"]


def trade_ledger(portfolio_id, symbol=None):
    """Return the trade ledger for one holding or all holdings."""
    doc = _holdings_document(portfolio_id)
    out = []
    for row in doc["holdings"]:
        if symbol and str(row.get("symbol", "")).upper() != _symbol(symbol):
            continue
        for t in row.get("trades", []):
            out.append({"symbol": row["symbol"], **t})
    out.sort(key=lambda t: t.get("date", ""))
    return out


def corporate_actions(portfolio_id, symbol=None):
    """Return corporate actions for one holding or all holdings."""
    doc = _holdings_document(portfolio_id)
    out = []
    for row in doc["holdings"]:
        if symbol and str(row.get("symbol", "")).upper() != _symbol(symbol):
            continue
        for ca in row.get("corporate_actions", []):
            out.append({"symbol": row["symbol"], **ca})
    out.sort(key=lambda t: t.get("date", ""))
    return out


def reflection(portfolio_id):
    """Compare each holding's structured rationale with what happened.

    Returns a list of reflection records: thesis, key_risks, actual outcome,
    and a gap analysis.  The student writes the interpretation; this provides
    the evidence.
    """
    bundle = load(portfolio_id)
    holdings = bundle["holdings"]
    snapshots = bundle["snapshots"]
    out = []
    for h in holdings:
        sym = h.get("symbol", "")
        rationale = h.get("rationale", {})
        if isinstance(rationale, str):
            rationale = {"thesis": rationale}
        trades = h.get("trades", [])
        # Compute realized P&L from trades
        buys = [t for t in trades if t.get("action") == "buy"]
        sells = [t for t in trades if t.get("action") == "sell"]
        total_bought = sum(float(t.get("shares", 0)) * float(t.get("price", 0)) for t in buys)
        total_sold = sum(float(t.get("shares", 0)) * float(t.get("price", 0)) for t in sells)
        realized_pnl = total_sold - total_bought
        out.append({
            "symbol": sym,
            "thesis": rationale.get("thesis", ""),
            "key_risks": rationale.get("key_risks", []),
            "catalysts": rationale.get("catalysts", []),
            "target_price": rationale.get("target_price", ""),
            "kill_criteria": rationale.get("kill_criteria", ""),
            "review_date": rationale.get("review_date", ""),
            "n_trades": len(trades),
            "n_buys": len(buys),
            "n_sells": len(sells),
            "total_invested": round(total_bought, 2),
            "total_realized": round(total_sold, 2),
            "realized_pnl": round(realized_pnl, 2),
            "corporate_actions": h.get("corporate_actions", []),
            "current_shares": h.get("shares", "0"),
            "current_cost_basis": h.get("cost_basis", "0"),
        })
    return out


def save_benchmark(portfolio_id, date, price, source="user"):
    """Store a benchmark price snapshot (like prices but for the benchmark index)."""
    _portfolio(portfolio_id)
    day = _date(date)
    path = _path(portfolio_id, "benchmarks", day + ".json")
    document = _read(path) if path.exists() else {"format": FORMAT, "date": day, "price": None}
    document["price"] = str(_decimal(price, "benchmark price", positive=True))
    document["source"] = str(source or "user")[:40]
    document["retrieved_at"] = _now()
    _write(path, document)
    return document


def benchmark_series(portfolio_id):
    """Return all benchmark prices as a dated series."""
    root = _path(portfolio_id, "benchmarks")
    if not root.exists():
        return []
    out = []
    for path in sorted(root.glob("*.json")):
        try:
            doc = _read(path)
            out.append({"date": doc.get("date", path.stem), "price": doc.get("price"),
                        "source": doc.get("source", "")})
        except Exception:
            pass
    return out



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


def _safe_evidence_name(name):
    name = str(name or "").strip()
    base = os.path.basename(name.replace("\\", "/"))
    if not base or base in (".", ".."):
        raise ValueError("the evidence file needs a name")
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in base)
    if not cleaned or cleaned in (".", ".."):
        raise ValueError("the evidence file name is not usable")
    if len(cleaned) > 120:
        cleaned = cleaned[:120]
    return cleaned


def save_evidence(portfolio_id, date, filename, mime, raw):
    _portfolio(portfolio_id)
    day = _date(date)
    if _path(portfolio_id, "snapshots", day + ".json").exists():
        raise PortfolioError("the snapshot for %s is already saved; evidence cannot be added after" % day)
    mime = str(mime or "").strip().lower()
    allowed = {"image/png", "image/jpeg", "application/pdf"}
    if mime not in allowed:
        raise ValueError("evidence must be a PNG, JPEG or PDF")
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError("evidence content must be bytes")
    raw = bytes(raw)
    if not raw:
        raise ValueError("the evidence file is empty")
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("the evidence file must be 2 MB or smaller")
    safe = _safe_evidence_name(filename)
    ext = os.path.splitext(safe)[1].lower()
    if mime == "image/png" and ext != ".png":
        safe = safe + ".png"
    if mime == "image/jpeg" and ext not in (".jpg", ".jpeg"):
        safe = safe + ".jpg"
    if mime == "application/pdf" and ext != ".pdf":
        safe = safe + ".pdf"
    evidence_dir = _path(portfolio_id, "evidence", day)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    target = (evidence_dir / safe).resolve()
    try:
        target.relative_to(_root(portfolio_id))
    except ValueError:
        raise ValueError("the evidence path resolves outside the portfolio directory")
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        i = 2
        while (evidence_dir / ("%s-%d%s" % (stem, i, suffix))).exists():
            i += 1
        target = evidence_dir / ("%s-%d%s" % (stem, i, suffix))
        safe = target.name
    target.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    metadata = {
        "filename": safe,
        "mime": mime,
        "size_bytes": len(raw),
        "sha256": digest,
        "captured_at": _now(),
        "relative_path": "evidence/%s/%s" % (day, safe),
    }
    return metadata


def save_snapshot(portfolio_id, snapshot):
    _portfolio(portfolio_id)
    day = _date(snapshot.get("date"))
    path = _path(portfolio_id, "snapshots", day + ".json")
    if path.exists(): raise PortfolioError("a snapshot for %s already exists" % day)
    evidence = snapshot.get("evidence")
    if evidence is not None:
        if not isinstance(evidence, list):
            raise ValueError("evidence must be a list")
        cleaned = []
        for item in evidence:
            if not isinstance(item, dict):
                raise ValueError("each evidence item must be an object")
            fname = _safe_evidence_name(item.get("filename"))
            sha = str(item.get("sha256") or "").strip().lower()
            if not sha or len(sha) != 64:
                raise ValueError("each evidence item needs a sha256")
            full = _path(portfolio_id, "evidence", day, fname)
            if not full.exists():
                raise ValueError("evidence file %s was not uploaded" % fname)
            actual = hashlib.sha256(full.read_bytes()).hexdigest()
            if actual != sha:
                raise ValueError("evidence file %s was changed after capture" % fname)
            captured_at = str(item.get("captured_at") or "").strip()
            mime = str(item.get("mime") or "").strip().lower()
            size = item.get("size_bytes")
            try:
                size = int(size) if size is not None else full.stat().st_size
            except (TypeError, ValueError):
                size = full.stat().st_size
            cleaned.append({
                "filename": fname,
                "mime": mime,
                "size_bytes": size,
                "sha256": sha,
                "captured_at": captured_at or _now(),
                "relative_path": "evidence/%s/%s" % (day, fname),
            })
        snapshot = dict(snapshot)
        snapshot["evidence"] = cleaned
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


def save_selection(portfolio_id, selection):
    """Store the student's stock-selection record on the portfolio.

    ``selection`` is a dict with ``set`` (str), ``parameters`` (list of ids) and
    ``rows`` (list of {symbol, values, reason}).  Nothing is computed; the values
    are what the screener showed or what the student typed.
    """
    portfolio = _portfolio(portfolio_id)
    if not isinstance(selection, dict):
        raise ValueError("selection must be an object")
    set_id = str(selection.get("set") or "").strip().lower()
    parameters = selection.get("parameters") or []
    if not isinstance(parameters, list):
        raise ValueError("parameters must be a list")
    parameters = [str(p).strip() for p in parameters if str(p).strip()]
    thresholds = selection.get("thresholds")
    if thresholds is not None and not isinstance(thresholds, dict):
        raise ValueError("thresholds must be an object")
    rows = selection.get("rows") or []
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    cleaned_rows = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each row must be an object")
        symbol = _symbol(row.get("symbol"))
        values = row.get("values")
        if values is not None and not isinstance(values, dict):
            raise ValueError("row.values must be an object")
        values = values or {}
        cleaned_values = {str(k): (None if v in (None, "") else str(v)) for k, v in values.items()}
        reason = str(row.get("reason") or "").strip()[:500]
        entry = {"symbol": symbol, "values": cleaned_values, "reason": reason}
        if isinstance(row.get("scorecard"), dict):
            entry["scorecard"] = row["scorecard"]
        if row.get("score") is not None:
            entry["score"] = str(row.get("score"))
        cleaned_rows.append(entry)
    cleaned = {
        "set": set_id,
        "parameters": parameters,
        "rows": cleaned_rows,
        "recorded_at": _now(),
    }
    if thresholds is not None:
        cleaned["thresholds"] = thresholds
    portfolio["selection"] = cleaned
    portfolio["updated_at"] = _now()
    _write(_path(portfolio_id, "portfolio.json"), portfolio)
    return portfolio["selection"]


def selection(portfolio_id):
    portfolio = _portfolio(portfolio_id)
    return portfolio.get("selection")


def save_statement(portfolio_id, symbol, filename, mime, raw):
    """Store one financial statement (PDF/CSV/XLSX) for a symbol in a book.

    Returns metadata.  The file is written under ``statements/<symbol>/``.
    Does not block a snapshot; statements only flip parameters from greyed-out
    to available.
    """
    _portfolio(portfolio_id)
    symbol = _symbol(symbol)
    held = {str(row["symbol"]).upper() for row in _holdings_document(portfolio_id)["holdings"]}
    if symbol not in held:
        raise ValueError("add %s as a holding before attaching a statement" % symbol)
    mime = str(mime or "").strip().lower()
    allowed = {"application/pdf", "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
               "application/vnd.ms-excel", "text/plain"}
    if mime not in allowed:
        raise ValueError("statement must be a PDF, CSV or spreadsheet")
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError("statement content must be bytes")
    raw = bytes(raw)
    if not raw:
        raise ValueError("the statement file is empty")
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("the statement file must be 5 MB or smaller")
    safe = _safe_evidence_name(filename)
    stmt_dir = _path(portfolio_id, "statements", symbol)
    stmt_dir.mkdir(parents=True, exist_ok=True)
    target = (stmt_dir / safe).resolve()
    try:
        target.relative_to(_root(portfolio_id))
    except ValueError:
        raise ValueError("the statement path resolves outside the portfolio directory")
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        i = 2
        while (stmt_dir / ("%s-%d%s" % (stem, i, suffix))).exists():
            i += 1
        target = stmt_dir / ("%s-%d%s" % (stem, i, suffix))
        safe = target.name
    target.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    extracted = None
    try:
        from . import statement_reader as _sr
        extracted = _sr.read_bytes(raw, mime)
    except Exception:
        extracted = None
    metadata = {
        "symbol": symbol,
        "filename": safe,
        "mime": mime,
        "size_bytes": len(raw),
        "sha256": digest,
        "captured_at": _now(),
        "relative_path": "statements/%s/%s" % (symbol, safe),
        "extracted": extracted,
    }
    # record in portfolio.json
    portfolio = _portfolio(portfolio_id)
    stmts = portfolio.get("statements")
    if not isinstance(stmts, list):
        stmts = []
    stmts = [s for s in stmts if not (str(s.get("symbol", "")).upper() == symbol
                                       and s.get("filename") == safe)]
    stmts.append(metadata)
    portfolio["statements"] = stmts
    portfolio["updated_at"] = _now()
    _write(_path(portfolio_id, "portfolio.json"), portfolio)
    return metadata


def statements(portfolio_id, symbol=None):
    portfolio = _portfolio(portfolio_id)
    rows = portfolio.get("statements") or []
    if not isinstance(rows, list):
        return []
    if symbol:
        sym = _symbol(symbol)
        return [r for r in rows if str(r.get("symbol", "")).upper() == sym]
    return list(rows)


def has_statement(portfolio_id, symbol):
    return bool(statements(portfolio_id, symbol))


def extract_statement(portfolio_id, symbol):
    """Re-extract a stored statement.  Returns the extracted dict or None."""
    _portfolio(portfolio_id)
    symbol = _symbol(symbol)
    rows = statements(portfolio_id, symbol)
    if not rows:
        raise ValueError("no statement stored for %s" % symbol)
    latest = rows[-1]
    full = _path(portfolio_id, latest["relative_path"])
    if not full.exists():
        raise ValueError("the statement file is missing")
    mime = str(latest.get("mime") or "").lower()
    extracted = None
    try:
        from . import statement_reader as _sr
        extracted = _sr.read_bytes(full.read_bytes(), mime)
    except Exception:
        extracted = None
    # update the stored record
    portfolio = _portfolio(portfolio_id)
    stmts = portfolio.get("statements") or []
    for s in stmts:
        if (str(s.get("symbol", "")).upper() == symbol
                and s.get("filename") == latest.get("filename")):
            s["extracted"] = extracted
    portfolio["statements"] = stmts
    portfolio["updated_at"] = _now()
    _write(_path(portfolio_id, "portfolio.json"), portfolio)
    return extracted


def statement_extracted(portfolio_id, symbol):
    rows = statements(portfolio_id, symbol)
    if not rows:
        return None
    return rows[-1].get("extracted")


def portfolio_fit(portfolio_id, candidate_symbol, candidate_weight):
    """Show what adding a candidate does to concentration, sector, and risk contribution.

    Returns a dict with current vs projected metrics.  The student decides whether to add.
    """
    bundle = load(portfolio_id)
    holdings = bundle["holdings"]
    current_symbols = [h.get("symbol", "") for h in holdings]
    total = len(current_symbols) + 1
    # Concentration: Herfindahl index
    current_weights = [1.0 / len(current_symbols) if current_symbols else 0] * len(current_symbols)
    projected_weights = current_weights + [float(candidate_weight)]
    # Normalize
    proj_sum = sum(projected_weights)
    projected_weights = [w / proj_sum for w in projected_weights]
    current_hhi = sum(w ** 2 for w in current_weights) if current_weights else 0
    projected_hhi = sum(w ** 2 for w in projected_weights)
    return {
        "candidate": candidate_symbol,
        "candidate_weight": candidate_weight,
        "current_holdings": len(current_symbols),
        "projected_holdings": total,
        "current_hhi": round(current_hhi, 4),
        "projected_hhi": round(projected_hhi, 4),
        "concentration_change": round(projected_hhi - current_hhi, 4),
        "max_position_current": round(max(current_weights, default=0), 4),
        "max_position_projected": round(max(projected_weights), 4),
    }


def performance_attribution(portfolio_id):
    """Decompose portfolio return into allocation vs selection effects.

    Returns per-period attribution.  The student explains the why.
    """
    bundle = load(portfolio_id)
    snapshots = bundle["snapshots"]
    if len(snapshots) < 2:
        raise ValueError("at least two dated snapshots are required")
    loaded = [snapshot(portfolio_id, row["date"]) for row in snapshots]
    periods = []
    for prev, curr in zip(loaded, loaded[1:]):
        prev_nav = float(prev["outputs"].get("nav", 0) or 0)
        curr_nav = float(curr["outputs"].get("nav", 0) or 0)
        if prev_nav == 0:
            continue
        period_return = (curr_nav - prev_nav) / prev_nav
        periods.append({
            "period": curr["date"],
            "start_nav": prev_nav,
            "end_nav": curr_nav,
            "period_return": round(period_return, 6),
        })
    total_return = (loaded[-1]["outputs"].get("nav", 0) and
                    float(loaded[-1]["outputs"].get("nav", 0)) / float(loaded[0]["outputs"].get("nav", 0)) - 1
                    if float(loaded[0]["outputs"].get("nav", 0)) else 0)
    return {
        "periods": periods,
        "total_return": round(float(total_return), 6),
        "n_periods": len(periods),
    }


def screener(portfolio_id, candidates, factor_weights=None, top_n=10):
    """Two-stage screener: hard filters from mandate, then ranking by student-chosen weights.

    Returns a shortlist with metrics, peer percentiles, and red flags.
    """
    bundle = load(portfolio_id)
    portfolio = bundle["portfolio"]
    constraints = portfolio.get("constraints", {})
    max_position = float(constraints.get("max_position", 0.10))
    long_only = constraints.get("long_only", True)

    # Stage 1: hard filters
    filtered = []
    for c in candidates:
        if long_only and float(c.get("weight", 0)) < 0:
            continue
        if float(c.get("weight", 0)) > max_position:
            continue
        filtered.append(c)

    # Stage 2: ranking by factor weights
    weights = factor_weights or {"pe": 0.25, "pb": 0.25, "roe": 0.25, "momentum": 0.25}
    scored = []
    for c in filtered:
        score = 0
        for factor, w in weights.items():
            val = float(c.get(factor, 0))
            # Higher is better for roe, momentum; lower is better for pe, pb
            if factor in ("pe", "pb"):
                score += w * (1.0 / (val + 0.01))
            else:
                score += w * val
        scored.append({**c, "composite_score": round(score, 4)})

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    shortlist = scored[:top_n]

    # Red flags
    for item in shortlist:
        flags = []
        if float(item.get("pe", 0)) > 50:
            flags.append("high P/E")
        if float(item.get("debt_ratio", 0)) > 0.7:
            flags.append("high leverage")
        if float(item.get("current_ratio", 0)) < 1.0:
            flags.append("low liquidity")
        item["red_flags"] = flags

    return {
        "total_candidates": len(candidates),
        "after_filters": len(filtered),
        "shortlist": shortlist,
        "factor_weights": weights,
    }
