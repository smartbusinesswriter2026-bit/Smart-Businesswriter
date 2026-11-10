"""The growth loop — a capability gap becomes a reviewable scaffold.

The **repair loop** detects breakage and protects what works.  The **growth
loop** creates something that does not exist yet: when a capability gap is
logged, it writes a **PROVISIONAL skeleton** — a method stub, a capability
entry, a preset, a test sketch and a README that says what the gap is and
what the system already knows about it.

The boundary is the owner's, and it is not moved here:

- the scaffold is a **draft**: it is marked PROVISIONAL and nothing in it is
  imported by the running system;
- a **human writes the method logic** and runs the suite;
- only then is the capability committed and a case seeded, and the repair
  loop takes over protecting it.

The loop never commits, never wires, and never resolves the finding it
worked on: the finding stays open for the owner to review.
"""
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import ops_log as _ops_log
from . import scaffold as _scaffold

#: How long the loop waits between passes.
DEFAULT_INTERVAL = 300
#: How many gaps one pass may scaffold.
DEFAULT_BATCH = 3

_lock = threading.Lock()

_state = {
    "running": False,
    "stopped": False,
    "thread": None,
    "passes": 0,
    "scaffolded": 0,
    "last_pass": None,
    "last_error": "",
    "status_message": "idle",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _repo_root():
    return Path(__file__).resolve().parents[3]


def _ledger_path():
    state = os.environ.get("BP_STATE_DIR")
    base = Path(state) if state else (_repo_root() / "state")
    return base / "growth_loop.jsonl"


def _read_ledger():
    path = _ledger_path()
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
    except OSError:
        return []
    return rows


def _append_ledger(record):
    path = _ledger_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return True
    except OSError:
        return False


def _already_scaffolded(finding_key):
    for row in _read_ledger():
        if row.get("finding_key") == finding_key:
            return True
    return False


def _subject_and_tile(finding):
    """Read a subject and a tile out of a capability-gap finding.

    The finding carries the subject in `subject` and the gap's title in
    `feature`.  A tile is a slug of the title when the finding names no
    subject, because a scaffold needs a folder to live in.
    """
    subject = str(finding.get("subject") or "").strip()
    feature = str(finding.get("feature") or "").strip()
    if not subject or subject.lower() in ("a", "b", "c", "d", "e", "f", "g", "h", "i", "j"):
        subject = "general"
    tile = _scaffold._safe(feature) or "newtile"
    return subject, tile


def pending_gaps():
    """The capability-gap findings that are open and not yet scaffolded.

    The filter is on the finding's **rule**, not its source: a capability gap
    arrives from the chat (`source="capability_gap"`) and from the Relevance
    Research Agent (`source="relevance"`), and both are the same kind of gap.
    """
    try:
        findings = _ops_log.list_findings(limit=500, status="open")
    except Exception:
        findings = []
    out = []
    for finding in findings:
        if finding.get("rule") != "capability_gap":
            continue
        if _already_scaffolded(finding.get("finding_key", "")):
            continue
        out.append(finding)
    return out


def run_pass(limit=None):
    """One pass: scaffold the open gaps that are not scaffolded yet.

    Returns {scaffolded, skipped, folders}.
    """
    if limit is None:
        limit = int(os.environ.get("BP_GROWTH_BATCH", str(DEFAULT_BATCH)))
    gaps = pending_gaps()
    scaffolded = []
    folders = []
    for finding in gaps[:max(0, limit)]:
        subject, tile = _subject_and_tile(finding)
        instruction = str(finding.get("message") or finding.get("feature") or "").strip()
        try:
            result = _scaffold.generate(subject, tile, instruction)
        except Exception as error:
            _append_ledger({"ts": _now_iso(), "finding_key": finding.get("finding_key", ""),
                            "status": "failed", "error": str(error)[:200]})
            continue
        _append_ledger({
            "ts": _now_iso(),
            "finding_key": finding.get("finding_key", ""),
            "status": "scaffolded",
            "subject": subject,
            "tile": tile,
            "folder": result.get("folder", ""),
            "paths": result.get("paths", []),
            "source": finding.get("source", ""),
        })
        scaffolded.append(finding.get("finding_key", ""))
        folders.append(result.get("folder", ""))
    with _lock:
        _state["passes"] += 1
        _state["scaffolded"] += len(scaffolded)
        _state["last_pass"] = _now_iso()
    return {"scaffolded": len(scaffolded), "keys": scaffolded, "folders": folders,
            "pending": len(gaps)}


def status():
    """The growth loop's status for the console."""
    with _lock:
        state = dict(_state)
    try:
        state["pending_gaps"] = len(pending_gaps())
    except Exception:
        state["pending_gaps"] = 0
    state["interval"] = int(os.environ.get("BP_GROWTH_INTERVAL", str(DEFAULT_INTERVAL)))
    state["scaffolded_total"] = len([r for r in _read_ledger() if r.get("status") == "scaffolded"])
    return state


def start():
    """Start the loop.  Returns (ok, message).  It works from the first pass."""
    with _lock:
        if _state["running"]:
            return False, "the growth loop is already running"
        _state["running"] = True
        _state["stopped"] = False
        _state["last_error"] = ""
        _state["status_message"] = "starting"
        thread = threading.Thread(target=_loop, daemon=True)
        _state["thread"] = thread
    thread.start()
    return True, "the growth loop has started"


def stop():
    """Stop the loop after the current pass."""
    with _lock:
        if not _state["running"]:
            return False, "the growth loop is not running"
        _state["stopped"] = True
        _state["status_message"] = "stopping"
    return True, "the growth loop will stop after the current pass"


def _loop():
    interval = int(os.environ.get("BP_GROWTH_INTERVAL", str(DEFAULT_INTERVAL)))
    try:
        while True:
            with _lock:
                if _state["stopped"]:
                    _state["running"] = False
                    _state["status_message"] = "idle"
                    return
                _state["status_message"] = "working"
            try:
                run_pass()
            except Exception as error:
                with _lock:
                    _state["last_error"] = str(error)[:200]
            with _lock:
                if _state["stopped"]:
                    _state["running"] = False
                    _state["status_message"] = "idle"
                    return
                _state["status_message"] = "idle"
            # Sleep in short steps so a stop is honoured quickly.
            waited = 0
            while waited < interval:
                with _lock:
                    if _state["stopped"]:
                        _state["running"] = False
                        _state["status_message"] = "idle"
                        return
                time.sleep(min(2, max(0, interval - waited)))
                waited += 2
    finally:
        with _lock:
            _state["running"] = False
            _state["status_message"] = "idle"
