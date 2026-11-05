"""Run log and error log for the admin self-healing monitor (product layer).

Append-only JSONL storage under state/, opt-in via BP_OPS_LOG env var.
Follows the same pattern as ops.request_log_path() but captures pipeline
runs and errors, not just HTTP requests.

Environment:
    BP_OPS_LOG   the log directory; unset or "" keeps logging OFF (opt-in).
                 Default: <repo>/state/ops_log when BP_STATE_DIR is set.
"""
import datetime
import hashlib
import json
import os
import re
from pathlib import Path

from . import ops as ops_mod


def _log_dir():
    configured = os.environ.get("BP_OPS_LOG")
    if configured:
        return Path(configured).expanduser()
    state = ops_mod.state_dir()
    return state / "ops_log"


def _ensure_dir():
    d = _log_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _runs_path():
    return _log_dir() / "runs.jsonl"


def _errors_path():
    return _log_dir() / "errors.jsonl"


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _append_jsonl(path, record):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return True
    except OSError:
        return False


def log_run(lane, kind, status, problem_text=None, error=None, duration_ms=None, gaps=None):
    """Append one run record. Returns True when written."""
    record = {
        "ts": _now_iso(),
        "run_id": hashlib.sha256((_now_iso() + str(lane) + str(kind)).encode()).hexdigest()[:12],
        "lane": str(lane or "unknown"),
        "kind": str(kind or "unknown"),
        "status": str(status or "unknown"),
    }
    if problem_text:
        record["problem_hash"] = hashlib.sha256(str(problem_text).encode("utf-8")).hexdigest()[:16]
    if error:
        record["error"] = str(error)[:300]
    if duration_ms is not None:
        record["duration_ms"] = round(float(duration_ms), 1)
    if gaps:
        record["gaps"] = [str(g)[:120] for g in (gaps if isinstance(gaps, list) else [gaps])]
    return _append_jsonl(_runs_path(), record)


def log_error(lane, error, problem_text=None, gap_label=None, count=1):
    """Append one error record. Returns True when written."""
    record = {
        "ts": _now_iso(),
        "error_id": hashlib.sha256((_now_iso() + str(error)).encode()).hexdigest()[:12],
        "lane": str(lane or "unknown"),
        "error": str(error)[:500],
        "count": int(count),
        "severity": classify_severity(str(error)),
    }
    if problem_text:
        record["problem_hash"] = hashlib.sha256(str(problem_text).encode("utf-8")).hexdigest()[:16]
    if gap_label:
        record["gap_label"] = str(gap_label)[:160]
    return _append_jsonl(_errors_path(), record)


def classify_severity(error_text):
    """Classify an error as light/moderate/severe based on keywords.

    Returns 'light', 'moderate', or 'severe'.
    """
    text = str(error_text or "").lower()
    severe_keywords = ["crash", "exception", "traceback", "500", "fatal", "refused", "cannot", "unable"]
    moderate_keywords = ["fail", "missing", "invalid", "wrong", "incorrect", "mismatch", "refusal"]
    if any(kw in text for kw in severe_keywords):
        return "severe"
    if any(kw in text for kw in moderate_keywords):
        return "moderate"
    return "light"


def severity_count(severity):
    """Return the default problem count for a severity level."""
    return {"light": 3, "moderate": 5, "severe": 10}.get(severity, 5)


def _read_jsonl(path, limit=50, filter_fn=None):
    if not path.is_file():
        return []
    rows = []
    try:
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if filter_fn and not filter_fn(rec):
                    continue
                rows.append(rec)
    except OSError:
        return []
    rows.reverse()  # newest first
    return rows[:limit]


def list_runs(limit=50, lane=None, status=None):
    """Return recent run records, newest first."""
    def filt(rec):
        if lane and rec.get("lane") != lane:
            return False
        if status and rec.get("status") != status:
            return False
        return True
    return _read_jsonl(_runs_path(), limit=limit, filter_fn=filt)


def list_errors(limit=50, lane=None):
    """Return recent error records, newest first."""
    def filt(rec):
        if lane and rec.get("lane") != lane:
            return False
        return True
    return _read_jsonl(_errors_path(), limit=limit, filter_fn=filt)


def run_count():
    """Total number of run records."""
    path = _runs_path()
    if not path.is_file():
        return 0
    try:
        with open(path, encoding="utf-8") as stream:
            return sum(1 for line in stream if line.strip())
    except OSError:
        return 0


def error_count():
    """Total number of error records."""
    path = _errors_path()
    if not path.is_file():
        return 0
    try:
        with open(path, encoding="utf-8") as stream:
            return sum(1 for line in stream if line.strip())
    except OSError:
        return 0


def mark_error_resolved(error_id):
    """Mark an error as resolved by appending a resolution record.

    Returns True if the error was found and marked.
    """
    errors = list_errors(limit=10000)
    for e in errors:
        if e.get("error_id") == error_id:
            record = {
                "ts": _now_iso(),
                "error_id": error_id,
                "resolved": True,
                "resolution_ts": _now_iso(),
            }
            _append_jsonl(_errors_path(), record)
            return True
    return False


def is_error_resolved(error_id):
    """Check if an error has been marked resolved."""
    errors = list_errors(limit=10000)
    for e in errors:
        if e.get("error_id") == error_id and e.get("resolved"):
            return True
    return False


def merge_resolved(errors):
    """Merge resolution records into error list.

    Returns errors with 'resolved' field set based on resolution records.
    """
    resolved_ids = set()
    all_records = _read_jsonl(_errors_path(), limit=100000)
    for r in all_records:
        if r.get("resolved") and r.get("error_id"):
            resolved_ids.add(r["error_id"])
    for e in errors:
        e["resolved"] = e.get("error_id") in resolved_ids
    return errors