"""Learning library for the Portfolio Lab (append-only, never auto-changes code).

Stores every portfolio valuation, screening, and reflection outcome — solved or unsolved —
and produces gap reports for the owner to review. Never modifies code; it proposes.

Follows the same pattern as bp.product.statement_library.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from hashlib import sha256
from collections import Counter

_STORE_DIR = os.environ.get("BP_PORTFOLIOS_LIBRARY_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "portfolio_library")
_DB_PATH = os.path.join(_STORE_DIR, "library.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_events (
    id TEXT PRIMARY KEY,
    text_hash TEXT NOT NULL,
    portfolio_id TEXT,
    event_type TEXT,
    symbol TEXT,
    solved INTEGER,
    missing TEXT,
    refusal TEXT,
    origin TEXT,
    created_at TEXT NOT NULL
);
"""


def _conn():
    os.makedirs(_STORE_DIR, exist_ok=True)
    c = sqlite3.connect(_DB_PATH)
    c.execute(_SCHEMA)
    c.commit()
    return c


def record(event_type, portfolio_id="", symbol="", solved=True, missing=None, refusal=None, origin="app"):
    """Store a portfolio event. Append-only."""
    try:
        c = _conn()
        text = "%s:%s:%s" % (event_type, portfolio_id, symbol)
        th = sha256(text.encode("utf-8")).hexdigest()
        rid = "%s_%s_%s" % (event_type, portfolio_id, symbol) if symbol else "%s_%s" % (event_type, portfolio_id)
        c.execute(
            "INSERT OR REPLACE INTO portfolio_events (id, text_hash, portfolio_id, event_type, symbol, "
            "solved, missing, refusal, origin, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (rid, th, portfolio_id, event_type, symbol, 1 if solved else 0,
             json.dumps(missing) if missing is not None else None,
             str(refusal)[:500] if refusal else None, origin,
             datetime.now(timezone.utc).isoformat()))
        c.commit()
        c.close()
    except Exception:
        pass


def gap_report():
    """Produce a proposal report from the library. Never auto-changes code."""
    try:
        c = _conn()
        rows = c.execute("SELECT event_type, solved, missing, refusal FROM portfolio_events").fetchall()
        c.close()
    except Exception:
        return {"total": 0, "solved": 0, "unsolved": 0, "proposals": []}
    total = len(rows)
    solved = sum(1 for r in rows if r[1])
    gap_counter = Counter()
    refusal_counter = Counter()
    for et, sol, missing, refusal in rows:
        if missing:
            try:
                items = json.loads(missing)
                if isinstance(items, list):
                    for it in items:
                        gap_counter[str(it)] += 1
            except Exception:
                gap_counter[str(missing)] += 1
        if refusal:
            refusal_counter[str(refusal)[:100]] += 1
    proposals = []
    for item, count in gap_counter.most_common(10):
        if count >= 2:
            proposals.append({"type": "recurring_gap", "item": item, "count": count,
                              "suggestion": "Fix the data or add the method that removes it."})
    for item, count in refusal_counter.most_common(10):
        if count >= 2:
            proposals.append({"type": "refusal", "item": item, "count": count,
                              "suggestion": "The pipeline refused this class of problem."})
    return {"total": total, "solved": solved, "unsolved": total - solved,
            "solve_rate": (solved / total if total else 0), "proposals": proposals}


def heal_history(limit=50):
    try:
        c = _conn()
        rows = c.execute("SELECT event_type, solved, portfolio_id, symbol, created_at "
                         "FROM portfolio_events ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        c.close()
        return [{"type": r[0], "solved": bool(r[1]), "portfolio": r[2], "symbol": r[3], "at": r[4]}
                for r in rows]
    except Exception:
        return []
