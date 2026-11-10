"""RRA append-only JSONL storage under state/relevance/.

Mirrors the ops_log pattern: one JSON object per line, append-only, never
the source of truth for code.  All paths are confined to state/relevance/
and qa/relevance/ (AC3).
"""
import json
import os
from pathlib import Path

from .schemas import EvidenceRecord, CoverageRow, GapSpec, WatchItem, RunRecord

# ── Path confinement (AC3) ─────────────────────────────────────────────────────

_ALLOWED_ROOTS = None  # resolved lazily


def _repo_root():
    return Path(__file__).resolve().parents[4]


def _state_root():
    override = os.environ.get("BP_STATE_DIR")
    if override:
        return Path(override).expanduser()
    return _repo_root() / "state"


def state_dir():
    """The RRA state directory: state/relevance/.  Created on demand."""
    d = _state_root() / "relevance"
    d.mkdir(parents=True, exist_ok=True)
    return d


def qa_dir():
    """The RRA reviewable registry directory: qa/relevance/.  Created on demand."""
    d = _repo_root() / "qa" / "relevance"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _confined_path(name):
    """Return a path inside state/relevance/, rejecting traversal."""
    d = state_dir()
    # strip any directory components
    safe = Path(name).name
    if not safe or safe in (".", ".."):
        raise ValueError("invalid file name: %r" % name)
    candidate = (d / safe).resolve()
    if not str(candidate).startswith(str(d.resolve())):
        raise ValueError("path escapes state/relevance/: %r" % name)
    return candidate


def runs_path():
    return _confined_path("runs.jsonl")


def evidence_path():
    return _confined_path("evidence.jsonl")


def gaps_path():
    return _confined_path("gaps.jsonl")


def watchlist_path():
    return _confined_path("watchlist.jsonl")


def coverage_path():
    return _confined_path("coverage.jsonl")


def _append_jsonl(path, record):
    """Append one record (dict or dataclass) as a JSON line.  Returns True on success."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(record, "to_dict"):
            record = record.to_dict()
        line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        with open(path, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
        return True
    except (OSError, TypeError, ValueError):
        return False


def _read_jsonl(path, limit=100000):
    """Read JSONL records, newest last, capped at limit.  Malformed lines skipped."""
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
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if len(rows) >= limit:
                    break
    except OSError:
        return []
    return rows


def _write_jsonl(path, records):
    """Overwrite a JSONL file (for rebuild).  Returns True on success."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            for r in records:
                if hasattr(r, "to_dict"):
                    r = r.to_dict()
                stream.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
        return True
    except (OSError, TypeError, ValueError):
        return False


# ── Append helpers ─────────────────────────────────────────────────────────────

def append_run(record):
    if isinstance(record, RunRecord):
        record = record.to_dict()
    return _append_jsonl(runs_path(), record)


def append_evidence(record):
    if isinstance(record, EvidenceRecord):
        record = record.to_dict()
    return _append_jsonl(evidence_path(), record)


def append_gap(record):
    if isinstance(record, GapSpec):
        record = record.to_dict()
    return _append_jsonl(gaps_path(), record)


def append_watchitem(record):
    if isinstance(record, WatchItem):
        record = record.to_dict()
    return _append_jsonl(watchlist_path(), record)


def append_coverage(record):
    if isinstance(record, CoverageRow):
        record = record.to_dict()
    return _append_jsonl(coverage_path(), record)


# ── Read helpers ───────────────────────────────────────────────────────────────

def read_runs(limit=1000):
    return _read_jsonl(runs_path(), limit=limit)


def read_evidence(limit=100000):
    return _read_jsonl(evidence_path(), limit=limit)


def read_gaps(limit=100000):
    return _read_jsonl(gaps_path(), limit=limit)


def read_watchlist(limit=100000):
    return _read_jsonl(watchlist_path(), limit=limit)


def read_coverage(limit=100000):
    return _read_jsonl(coverage_path(), limit=limit)


def read_latest_gap(gap_id):
    """Return the latest record for a gap id, or None."""
    for r in reversed(read_gaps()):
        if r.get("id") == gap_id or r.get("gap_id") == gap_id:
            return r
    return None


def read_latest_gaps():
    """One record per gap id (the latest wins), oldest first.

    The log is append-only, so a second sweep writes the same gap id again.
    This is the view the admin panel and the decision queue use: a gap
    appears once, with its latest state.
    """
    latest = {}
    order = []
    for r in read_gaps():
        gid = r.get("id") or r.get("gap_id")
        if not gid:
            continue
        if gid not in latest:
            order.append(gid)
        latest[gid] = r
    return [latest[gid] for gid in order]


def read_latest_evidence(evidence_id):
    """Return the latest record for an evidence id, or None."""
    for r in reversed(read_evidence()):
        if r.get("id") == evidence_id:
            return r
    return None


def is_confined_path(path):
    """Check whether a path is inside state/relevance/ or qa/relevance/ (AC3)."""
    try:
        p = Path(path).resolve()
    except (OSError, ValueError):
        return False
    roots = [state_dir().resolve(), qa_dir().resolve()]
    for root in roots:
        try:
            p.relative_to(root)
            return True
        except ValueError:
            continue
    return False
