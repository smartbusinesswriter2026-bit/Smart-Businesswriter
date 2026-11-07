p = "src/bp/product/portfolios.py"
src = open(p, encoding="utf-8").read()

# P1: Upgrade add_holding to support structured rationale and trade ledger
old_add = '''def add_holding(portfolio_id, symbol, shares, cost_basis="0", rationale=""):
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
    return document["holdings"]'''

new_add = '''def _normalise_rationale(rationale):
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
'''

assert old_add in src
src = src.replace(old_add, new_add, 1)
open(p, "w", encoding="utf-8").write(src)
print("P1 patched: structured rationale + trade ledger + corporate actions + benchmark series + reflection")
