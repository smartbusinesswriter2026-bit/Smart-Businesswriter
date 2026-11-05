import sys, os, json, sqlite3
from datetime import datetime, timezone

# Add heal_log table to the schema
_HEAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS heal_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_type TEXT,
    proposal_json TEXT,
    outcome TEXT,  -- 'applied', 'rejected', 'reverted'
    reason TEXT,
    problems_tested INTEGER,
    problems_passed INTEGER,
    created_at TEXT NOT NULL
);
"""

def _ensure_heal_table():
    c = _conn()
    c.execute(_HEAL_SCHEMA)
    c.commit()
    c.close()

def log_heal(proposal_type, proposal, outcome, reason, tested=0, passed=0):
    """Record a healing attempt. Append-only."""
    try:
        _ensure_heal_table()
        c = _conn()
        c.execute(
            "INSERT INTO heal_log (proposal_type, proposal_json, outcome, reason, "
            "problems_tested, problems_passed, created_at) VALUES (?,?,?,?,?,?,?)",
            (proposal_type, json.dumps(proposal, default=str), outcome, reason,
             tested, passed, datetime.now(timezone.utc).isoformat()))
        c.commit()
        c.close()
    except Exception:
        pass

def heal_history(limit=50):
    """Return recent healing attempts."""
    try:
        _ensure_heal_table()
        c = _conn()
        rows = c.execute(
            "SELECT id, proposal_type, outcome, reason, problems_tested, problems_passed, created_at "
            "FROM heal_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        c.close()
        return [{"id": r[0], "type": r[1], "outcome": r[2], "reason": r[3],
                 "tested": r[4], "passed": r[5], "at": r[6]} for r in rows]
    except Exception:
        return []

def pending_proposals():
    """Return proposals from gap_report that haven't been applied yet."""
    report = gap_report()
    return report.get("proposals", [])
PYEOF
python qa/manual/heal_lib.py 2>&1 | Select-Object -Last 3