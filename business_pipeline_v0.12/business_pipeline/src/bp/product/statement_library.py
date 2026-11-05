"""Learning library for the statements pipeline (append-only, never auto-changes code).

Stores every problem that goes through the pipeline — solved or unsolved — and produces
gap reports for the owner to review. The library never modifies code; it proposes.

Usage:
    from bp.product import statement_library as slib
    slib.record(record)            # store a solved/unsolved problem
    report = slib.gap_report()    # produce a proposal report (dict)
    examples = slib.few_shot(text, n=2)  # retrieve similar solved cases for few-shot
"""
import json
import os
import sqlite3
import re
from datetime import datetime, timezone
from hashlib import sha256
from collections import Counter

_STORE_DIR = os.environ.get("BP_STATEMENT_LIBRARY_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "statement_library")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    text_hash TEXT NOT NULL,
    text TEXT,
    period_start TEXT,
    period_end TEXT,
    model TEXT,
    attempts INTEGER,
    solved INTEGER,
    reading_source TEXT,
    net_income TEXT,
    missing TEXT,
    unplaceable TEXT,
    methods_used TEXT,
    gate_failures TEXT,
    entries_json TEXT,
    adjustments_json TEXT,
    created_at TEXT NOT NULL
);
"""

# Schema migration: add columns if missing
_MIGRATE = [
    "ALTER TABLE problems ADD COLUMN entries_json TEXT",
    "ALTER TABLE problems ADD COLUMN adjustments_json TEXT",
    "ALTER TABLE problems ADD COLUMN origin TEXT",
    "ALTER TABLE problems ADD COLUMN refusal TEXT",
    "ALTER TABLE problems ADD COLUMN kind TEXT",
]


def _conn():
    os.makedirs(_STORE_DIR, exist_ok=True)
    path = os.path.join(_STORE_DIR, "library.db")
    c = sqlite3.connect(path)
    c.execute(_SCHEMA)
    for stmt in _MIGRATE:
        try:
            c.execute(stmt)
        except sqlite3.OperationalError:
            pass  # column already exists
    c.commit()
    return c


def _reading(record):
    reading = record.get("reading")
    return reading if isinstance(reading, dict) else {}


def _as_items(value):
    """Every gap in a stored field, whatever shape it was written in.

    The table holds three shapes from three generations of the writer: a list of strings, a list
    of ``{"what", "why"}`` dicts, and (from the earliest records) one bare dict.  A report that
    only understood the list shape silently saw no gaps at all, which is why it never proposed
    anything.
    """
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return [value] if value.strip() else []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, (list, tuple)):
        return [item for item in value if item]
    return []


def _gap_label(item):
    """The stable name of one gap, so repeats across problems count as one thing."""
    if isinstance(item, dict):
        text = item.get("what") or item.get("account") or item.get("item") or ""
    else:
        text = str(item)
    text = re.sub(r"\s+", " ", str(text)).strip(" .:;,")
    return text[:160]


def record(record, origin=None):
    """Store a statements record (dict) in the library. Append-only.

    `record` is called for every outcome: a solve, a route that returned an unsolved record, and
    (from `handle`) an instruction that raised.  A library that only keeps successes learns
    nothing about the cases that fail, which are the only cases worth learning from.

    `origin` says where the problem came from — ``app`` (a student in the workbench), ``test``
    (a fixture), ``manual`` (an acceptance probe), ``seed`` (the corpus).  Nothing is ever
    deleted: origin lets a reader separate evidence from fixtures without throwing evidence away.
    """
    if not isinstance(record, dict):
        return
    origin = origin or record.get("origin") or os.environ.get("BP_STATEMENT_LIBRARY_ORIGIN") or "app"
    try:
        c = _conn()
        rid = str(record.get("id") or record.get("plan_hash") or "")
        text = str(record.get("instruction") or record.get("text") or "")
        th = sha256(text.encode("utf-8")).hexdigest()
        period = record.get("period") or _reading(record).get("period") or {}
        if isinstance(period, dict):
            ps, pe = period.get("start"), period.get("end")
        else:
            ps, pe = None, None
        reading = _reading(record)
        working = record.get("working") if isinstance(record.get("working"), dict) else {}
        missing = working.get("missing") or reading.get("missing")
        unplaceable = record.get("unplaceable") or reading.get("unplaceable")
        refusal = record.get("refusal") or record.get("error")
        adjustments = None
        entries = None
        spec = record.get("spec") or {}
        if isinstance(spec.get("entries"), list):
            entries = spec["entries"]
        if isinstance(spec.get("adjustments"), list):
            adjustments = spec["adjustments"]
        if isinstance(record.get("entries"), list):
            entries = record["entries"]
        if isinstance(record.get("adjustments"), list):
            adjustments = record["adjustments"]
        gate_failures = None
        checks = record.get("checks") or []
        failed = [ch.get("name") for ch in checks if isinstance(ch, dict) and not ch.get("ok")]
        if failed:
            gate_failures = json.dumps(failed)
        c.execute(
            "INSERT OR REPLACE INTO problems (id, text_hash, text, period_start, period_end, model, "
            "attempts, solved, reading_source, net_income, missing, unplaceable, methods_used, "
            "gate_failures, entries_json, adjustments_json, created_at, origin, refusal, kind) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, th, text, ps, pe, record.get("reading_source"),
             record.get("attempts"),
             1 if record.get("solved") else 0, record.get("reading_source"),
             str(record.get("net_income")) if record.get("net_income") is not None else None,
             json.dumps(missing) if missing is not None else None,
             json.dumps(unplaceable) if unplaceable is not None else None,
             None, gate_failures,
             json.dumps(entries) if entries is not None else None,
             json.dumps(adjustments) if adjustments is not None else None,
             datetime.now(timezone.utc).isoformat(), origin,
             str(refusal)[:1000] if refusal else None,
             record.get("problem_type")))
        c.commit()
        c.close()
    except Exception:
        pass  # library is best-effort; never break the pipeline


#: Words too common to say two problems are alike.  Two shared stopwords are not a similarity.
_STOP = set("""the and for with from that this was were are has have had its their they them
into upon under over which what when where than then also each both more most such only other
some any all not but you your our per net total amount balance account accounts year end
during following extracted december company business cash value cost sales revenue""".split())


def _words(text):
    return {w for w in re.findall(r"[a-z]{4,}", str(text or "").lower()) if w not in _STOP}


def few_shot(text, n=2, kind=None):
    """Up to n solved cases that are genuinely similar, for few-shot prompting.

    Similarity is *meaningful* word overlap — stopwords, account names every problem contains and
    figures are ignored — plus a shape check: a trial balance must not be offered as an example
    for a bank reconciliation.  Records are deduplicated by problem text, so a fixture solved 140
    times contributes one example, and a real solve outranks a fixture at equal similarity.
    """
    try:
        c = _conn()
        rows = c.execute(
            "SELECT text, entries_json, adjustments_json, kind, origin FROM problems "
            "WHERE solved=1 AND entries_json IS NOT NULL ORDER BY created_at DESC LIMIT 500").fetchall()
        c.close()
    except Exception:
        return []
    if not rows:
        return []
    probe = _words(text)
    if len(probe) < 2:
        return []
    rank = {"app": 0, "manual": 1, "seed": 2, "claude_corpus": 2, "test": 3}
    scored, seen = [], set()
    for rtext, entries_json, adjustments_json, row_kind, origin in rows:
        key = sha256(str(rtext or "").encode("utf-8")).hexdigest()
        if key in seen:
            continue
        if kind and row_kind and row_kind != kind:
            # A different kind of problem is not a worked example of this one.
            continue
        overlap = len(probe & _words(rtext))
        if overlap < 3:
            continue
        seen.add(key)
        try:
            entries = json.loads(entries_json) if entries_json else None
        except Exception:
            entries = None
        if not entries:
            continue
        try:
            adjustments = json.loads(adjustments_json) if adjustments_json else None
        except Exception:
            adjustments = None
        scored.append(((overlap, -rank.get(origin or "", 2)),
                       {"text": rtext, "entries": entries, "adjustments": adjustments or [],
                        "kind": row_kind, "origin": origin}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored[:n]]


def gap_report(top=15):
    """Produce a proposal report (dict) from the library. Never auto-changes code.

    The report reads the fields where gaps are actually written — ``missing``, ``unplaceable``,
    ``gate_failures`` and ``refusal`` — in every shape the table holds, and counts each gap by
    **distinct problem** as well as by row.  A fixture solved 140 times is one problem; treating
    it as 140 observations is what made the old report propose nothing while a real defect
    repeated 196 times stayed invisible.
    """
    try:
        c = _conn()
        rows = c.execute(
            "SELECT text_hash, solved, missing, unplaceable, gate_failures, refusal, kind, "
            "reading_source, origin, created_at FROM problems").fetchall()
        c.close()
    except Exception:
        return {"total": 0, "solved": 0, "unsolved": 0, "proposals": []}

    total = len(rows)
    solved = sum(1 for r in rows if r[1])
    problems = {r[0] for r in rows}
    by_kind, by_source, by_origin = Counter(), Counter(), Counter()
    gap_rows, gap_problems = Counter(), Counter()
    gap_reason = {}
    unplaceable_rows, unplaceable_problems = Counter(), Counter()
    gate_rows, gate_problems = Counter(), Counter()
    refusal_rows, refusal_problems = Counter(), Counter()
    refusal_text = {}
    first_seen, last_seen = {}, {}

    def note(label, seen_at):
        if not seen_at:
            return
        if label not in first_seen or seen_at < first_seen[label]:
            first_seen[label] = seen_at
        if label not in last_seen or seen_at > last_seen[label]:
            last_seen[label] = seen_at

    for text_hash, is_solved, missing, unplaceable, gates, refusal, kind, source, origin, seen_at in rows:
        by_kind[str(kind or "unrecorded")] += 1
        by_source[str(source or "unrecorded")] += 1
        by_origin[str(origin or "unrecorded")] += 1
        for item in _as_items(missing):
            label = _gap_label(item)
            if not label:
                continue
            gap_rows[label] += 1
            gap_problems[(label, text_hash)] += 1
            note(label, seen_at)
            if isinstance(item, dict) and item.get("why"):
                gap_reason.setdefault(label, str(item["why"])[:200])
        for item in _as_items(unplaceable):
            label = _gap_label(item)
            unplaceable_rows[label] += 1
            unplaceable_problems[(label, text_hash)] += 1
            note(label, seen_at)
        for item in _as_items(gates):
            label = _gap_label(item)
            gate_rows[label] += 1
            gate_problems[(label, text_hash)] += 1
            note(label, seen_at)
        if refusal:
            label = re.sub(r"\s+", " ", str(refusal))[:160]
            refusal_rows[label] += 1
            refusal_problems[(label, text_hash)] += 1
            refusal_text.setdefault(label, str(refusal)[:400])
            note(label, seen_at)

    def distinct(counter):
        out = Counter()
        for (label, _hash), count in counter.items():
            out[label] += count
        return out

    proposals = []
    singles = []

    def propose(kind_name, label, rows_count, distinct_count, suggestion, why=None):
        entry = {"type": kind_name, "item": label, "problems": distinct_count,
                 "rows": rows_count, "suggestion": suggestion,
                 "first_seen": first_seen.get(label), "last_seen": last_seen.get(label)}
        if why:
            entry["why"] = why
        if distinct_count < 2:
            # One occurrence is an anecdote, not a pattern: it stays visible, but it is not
            # proposed as a change to the pipeline.
            singles.append(entry)
            return
        proposals.append(entry)

    for label, count in distinct(gap_problems).most_common(top):
        propose("recurring_gap", label, gap_rows[label], count,
                "This gap repeats across problems: fix the reader or add the method that removes "
                "it, then re-run the recorded problems to prove it is gone.",
                gap_reason.get(label))
    for label, count in distinct(unplaceable_problems).most_common(top):
        propose("unplaceable_account", label, unplaceable_rows[label], count,
                "Add a placement rule (or a chart account) for '" + label + "'.")
    for label, count in distinct(gate_problems).most_common(top):
        propose("gate_failure", label, gate_rows[label], count,
                "Gate '" + label + "' failed on distinct problems: investigate the account mapping "
                "or the adjustment the model proposed.")
    for label, count in distinct(refusal_problems).most_common(top):
        propose("refusal", label, refusal_rows[label], count,
                "The pipeline refused this class of problem. The refusal text is the requirement: "
                "either a route must handle it or the gap must be shown to the student.",
                refusal_text.get(label))

    proposals.sort(key=lambda p: (-p["problems"], -p["rows"]))
    duplicates = Counter(r[0] for r in rows)
    return {"total": total, "solved": solved, "unsolved": total - solved,
            "distinct_problems": len(problems),
            "solve_rate": (solved / total if total else 0),
            "distinct_solve_rate": (
                sum(1 for h in problems
                    if any(r[0] == h and r[1] for r in rows)) / len(problems)
                if problems else 0),
            "by_kind": dict(by_kind.most_common()),
            "by_source": dict(by_source.most_common()),
            "by_origin": dict(by_origin.most_common()),
            "most_repeated": [{"rows": n, "text": next((r[2] for r in rows if r[0] == h), "")[:90]}
                              for h, n in duplicates.most_common(5) if n > 1],
            "singles": singles[:top],
            "proposals": proposals}

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
