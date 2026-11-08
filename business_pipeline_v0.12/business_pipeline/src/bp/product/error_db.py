"""A searchable database of mistakes and the durable fixes that closed them.

The repair loop learns a **cause**; this module is where that learning is kept
so the growth loop starts with it instead of rediscovering it:

* `qa/errors/error_registry.jsonl` is the reviewable record.  One line per
  mistake: the symptom, the trigger, the fix, the artifact it wrote, the files
  and tests that pin it, and the shapes to **avoid** next time.
* `state/error_db.sqlite3` is built from that registry plus the live error log,
  the cause ledger and the golden regression cases.  It is a cache, never the
  source: `rebuild()` can always regenerate it.

The growth loop asks `growth_brief(subject, tile, text)` before it scaffolds a
new capability, so a method it writes is checked against the mistakes already
paid for.
"""
import json
import os
import sqlite3
from pathlib import Path

REGISTRY_FORMAT = "bp-error-registry/1"


def _root():
    return Path(__file__).resolve().parents[3]


def registry_path():
    return _root() / "qa" / "errors" / "error_registry.jsonl"


def db_path():
    override = os.environ.get("BP_ERROR_DB")
    if override:
        return Path(override)
    return _root() / "state" / "error_db.sqlite3"


def registry():
    """The canonical records, newest first.  A malformed line is skipped, never fatal."""
    path = registry_path()
    if not path.is_file():
        return []
    rows = []
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rows.sort(key=lambda row: str(row.get("date") or ""), reverse=True)
    return rows


def _connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _have_fts(conn):
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts_probe USING fts5(x)")
        conn.execute("DROP TABLE IF EXISTS _fts_probe")
        return True
    except sqlite3.OperationalError:
        return False


def rebuild():
    """Rebuild the SQLite cache from the registry, the error log and the golden cases."""
    from . import cause_ledger, ops_log, regression_cases
    lessons = registry()
    errors = ops_log.list_errors(limit=100000, status="all")
    ledger = cause_ledger.summary()
    goldens = regression_cases.list_cases()
    fts = True
    conn = _connect()
    try:
        conn.executescript(
            """
            DROP TABLE IF EXISTS lessons;
            DROP TABLE IF EXISTS errors;
            DROP TABLE IF EXISTS causes;
            DROP TABLE IF EXISTS golden_cases;
            DROP TABLE IF EXISTS lesson_fts;
            CREATE TABLE lessons (
                id TEXT PRIMARY KEY, date TEXT, scope TEXT, cause TEXT,
                symptom TEXT, trigger TEXT, fix TEXT, artifact TEXT,
                files TEXT, tests TEXT, avoid TEXT, subject TEXT, tile TEXT
            );
            CREATE TABLE errors (
                error_id TEXT, ts TEXT, lane TEXT, cause TEXT, scope TEXT,
                severity TEXT, message TEXT, count INTEGER, status TEXT, artifact TEXT
            );
            CREATE TABLE causes (
                cause TEXT PRIMARY KEY, title TEXT, scope TEXT, remedy TEXT,
                required_artifact TEXT, occurrences INTEGER, recurrences INTEGER,
                status TEXT, fixed_at TEXT
            );
            CREATE TABLE golden_cases (
                id TEXT, cause TEXT, original TEXT, normalized TEXT, notes TEXT,
                verified_by TEXT, deterministic_ok INTEGER
            );
            """
        )
        for row in lessons:
            conn.execute(
                "INSERT OR REPLACE INTO lessons VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (str(row.get("id") or ""), str(row.get("date") or ""),
                 str(row.get("scope") or ""), str(row.get("cause") or ""),
                 str(row.get("symptom") or ""), str(row.get("trigger") or ""),
                 str(row.get("fix") or ""), str(row.get("artifact") or ""),
                 json.dumps(row.get("files") or [], ensure_ascii=False),
                 json.dumps(row.get("tests") or [], ensure_ascii=False),
                 json.dumps(row.get("avoid") or [], ensure_ascii=False),
                 str(row.get("subject") or ""), str(row.get("tile") or "")))
        for row in errors:
            conn.execute(
                "INSERT INTO errors VALUES (?,?,?,?,?,?,?,?,?,?)",
                (str(row.get("error_id") or ""), str(row.get("ts") or ""),
                 str(row.get("lane") or ""), str(row.get("cause") or ""),
                 str(row.get("scope") or ""), str(row.get("severity") or ""),
                 str(row.get("error") or ""), int(row.get("count") or 1),
                 ("closed" if (row.get("resolved") or row.get("invalid")
                               or row.get("dismissed")) else
                  ("attended" if row.get("attended") else "open")),
                 str(row.get("artifact") or "")))
        for row in ledger.get("causes") or []:
            conn.execute(
                "INSERT OR REPLACE INTO causes VALUES (?,?,?,?,?,?,?,?,?)",
                (str(row.get("cause") or ""), str(row.get("title") or ""),
                 str(row.get("scope") or ""), str(row.get("remedy") or ""),
                 str(row.get("required_artifact") or ""),
                 int(row.get("occurrences") or 0), int(row.get("recurrences") or 0),
                 str(row.get("status") or ""), str(row.get("fixed_at") or "")))
        for index, row in enumerate(goldens):
            conn.execute(
                "INSERT INTO golden_cases VALUES (?,?,?,?,?,?,?)",
                ("golden_%04d" % (index + 1), str(row.get("category") or ""),
                 str(row.get("original") or ""), str(row.get("normalized") or ""),
                 json.dumps(row.get("notes") or [], ensure_ascii=False),
                 str(row.get("verified_by") or ""), int(bool(row.get("deterministic_ok")))))
        if fts:
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE lesson_fts USING fts5("
                    "id, symptom, trigger, fix, avoid, tokenize='unicode61')")
                for row in lessons:
                    conn.execute(
                        "INSERT INTO lesson_fts VALUES (?,?,?,?,?)",
                        (str(row.get("id") or ""), str(row.get("symptom") or ""),
                         str(row.get("trigger") or ""), str(row.get("fix") or ""),
                         " ".join(str(x) for x in (row.get("avoid") or []))))
            except sqlite3.OperationalError:
                fts = False
        conn.commit()
    finally:
        conn.close()
    return {"lessons": len(lessons), "errors": len(errors),
            "causes": len(ledger.get("causes") or []), "golden_cases": len(goldens),
            "fts": fts, "db": str(db_path())}


def _ensure():
    """Build the cache, or rebuild it when the registry or the error log is newer."""
    target = db_path()
    if not target.is_file():
        rebuild()
        return
    try:
        built = target.stat().st_mtime
        from . import ops_log
        sources = [registry_path(), Path(ops_log._errors_path())]
        if any(path.is_file() and path.stat().st_mtime > built for path in sources):
            rebuild()
    except OSError:
        rebuild()


def search(text, limit=10):
    """Rank the registry by a free-text query; falls back to LIKE when FTS is absent."""
    _ensure()
    query = str(text or "").strip()
    conn = _connect()
    try:
        rows = []
        if query:
            try:
                cursor = conn.execute(
                    "SELECT l.* FROM lesson_fts f JOIN lessons l ON l.id = f.id "
                    "WHERE lesson_fts MATCH ? ORDER BY rank LIMIT ?",
                    (query.replace('"', " "), int(limit)))
                rows = [dict(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                rows = []
            if not rows:
                like = "%" + query + "%"
                cursor = conn.execute(
                    "SELECT * FROM lessons WHERE symptom LIKE ? OR trigger LIKE ? "
                    "OR fix LIKE ? OR avoid LIKE ? OR id LIKE ? LIMIT ?",
                    (like, like, like, like, like, int(limit)))
                rows = [dict(row) for row in cursor.fetchall()]
        else:
            cursor = conn.execute("SELECT * FROM lessons ORDER BY date DESC LIMIT ?", (int(limit),))
            rows = [dict(row) for row in cursor.fetchall()]
        for row in rows:
            for key in ("files", "tests", "avoid"):
                try:
                    row[key] = json.loads(row.get(key) or "[]")
                except (TypeError, ValueError):
                    row[key] = []
        return rows
    finally:
        conn.close()


def lessons_for(subject="", tile="", text="", limit=5):
    """The most relevant lessons for a subject/tile, or for a problem text."""
    rows = search(text, limit=max(limit, 10)) if text else search("", limit=max(limit, 10))
    picked = []
    for row in rows:
        if subject and row.get("subject") and row["subject"] != subject:
            continue
        if tile and row.get("tile") and row["tile"] != tile:
            continue
        picked.append(row)
        if len(picked) >= limit:
            break
    return picked


def growth_brief(subject="", tile="", text="", limit=5):
    """A short text block the growth loop reads before it scaffolds a capability."""
    rows = lessons_for(subject, tile, text, limit)
    lines = ["Known mistakes to avoid (from qa/errors/error_registry.jsonl):"]
    if not rows:
        lines.append("- No prior lesson matched this subject/tile; treat it as new.")
    for row in rows:
        avoid = "; ".join(row.get("avoid") or [])
        lines.append("- %s: %s Avoid: %s" % (row.get("id"), row.get("symptom"), avoid))
    _ensure()
    conn = _connect()
    try:
        open_causes = [dict(r) for r in conn.execute(
            "SELECT cause, status, recurrences FROM causes WHERE status != 'fixed' "
            "ORDER BY recurrences DESC").fetchall()]
    finally:
        conn.close()
    if open_causes:
        lines.append("Causes still open: " + "; ".join(
            "%s (%s, %d recurrence(s))" % (c["cause"], c["status"], c["recurrences"])
            for c in open_causes[:6]))
    return "\n".join(lines)


def summary():
    """Counts for the admin panel and the API."""
    _ensure()
    conn = _connect()
    try:
        def count(sql, args=()):
            row = conn.execute(sql, args).fetchone()
            return int(row[0]) if row else 0
        return {"lessons": count("SELECT COUNT(*) FROM lessons"),
                "errors": count("SELECT COUNT(*) FROM errors"),
                "open_errors": count("SELECT COUNT(*) FROM errors WHERE status = 'open'"),
                "causes": count("SELECT COUNT(*) FROM causes"),
                "fixed_causes": count("SELECT COUNT(*) FROM causes WHERE status = 'fixed'"),
                "golden_cases": count("SELECT COUNT(*) FROM golden_cases"),
                "db": str(db_path())}
    finally:
        conn.close()
