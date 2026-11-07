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


def _findings_path():
    return _log_dir() / "findings.jsonl"


def finding_key(rule, subject="", feature="", section=""):
    """Stable identity of a validation finding: rule+subject+feature+section."""
    raw = "|".join(str(x or "") for x in (rule, subject, feature, section))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


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


def log_error(lane, error, problem_text=None, gap_label=None, count=1, case_id=None):
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
        # Kept locally so "Resolve" can replay the exact failing problem;
        # never shown as evidence and never leaves the state directory.
        record["problem"] = str(problem_text)[:2000]
    if case_id:
        # A stored tile case is replayed by code, not by a model, so a case
        # failure costs no tokens to re-check.
        record["case_id"] = str(case_id)[:200]
    if gap_label:
        record["gap_label"] = str(gap_label)[:160]
    return _append_jsonl(_errors_path(), record)


def classify_severity(error_text):
    """Classify an error as light/moderate/severe based on keywords.

    Returns 'light', 'moderate', or 'severe'.
    """
    text = str(error_text or "").lower()
    severe_keywords = ["crash", "exception", "traceback", "500", "fatal", "refused", "cannot", "unable", "hallucination", "invented"]
    moderate_keywords = ["fail", "missing", "invalid", "wrong", "incorrect", "mismatch", "refusal", "untraceable", "irrelevant"]
    if any(kw in text for kw in severe_keywords):
        return "severe"
    if any(kw in text for kw in moderate_keywords):
        return "moderate"
    return "light"


def log_hallucination(lane, finding, problem_text=None):
    """Log a hallucination finding as an error.

    Returns True when written.
    """
    error_text = "[hallucination:%s] %s" % (finding.get('type', 'unknown'), finding.get('reason', ''))
    return log_error(lane, error_text, problem_text=problem_text,
                     gap_label=finding.get('type'), count=1)


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
    """Return recent error records, newest first.

    Only records that actually carry an error message are returned; resolution,
    attendance, invalid and attempt records live in the same append-only file
    and must never appear as errors themselves.
    """
    def filt(rec):
        if not rec.get("error"):
            return False
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


def get_error(error_id):
    """Return one error record by id (with its stored replay problem), or None."""
    for rec in _read_jsonl(_errors_path(), limit=100000):
        if rec.get("error_id") == error_id and rec.get("error"):
            return rec
    return None


def mark_error_verified(error_id, note=""):
    """Mark an error resolved *because a replay passed*, recording the proof.

    This is the only path that sets `verified: true`; a plain resolve never does.
    """
    record = {
        "ts": _now_iso(),
        "error_id": error_id,
        "resolved": True,
        "verified": True,
        "resolution_ts": _now_iso(),
        "note": str(note)[:200],
    }
    _append_jsonl(_errors_path(), record)
    return True


def log_resolution_attempt(error_id, category, steps, outcome):
    """Append one in-pipeline resolution attempt (kept even when it fails)."""
    record = {
        "ts": _now_iso(),
        "error_id": error_id,
        "attempt": True,
        "category": str(category or "unknown")[:40],
        "outcome": str(outcome or "unknown")[:40],
        "steps": [
            {"strategy": str(s.get("strategy", ""))[:80],
             "model": str(s.get("model", ""))[:60],
             "outcome": str(s.get("outcome", ""))[:40],
             "detail": str(s.get("detail", ""))[:200]}
            for s in (steps or [])
        ],
    }
    return _append_jsonl(_errors_path(), record)


def is_error_resolved(error_id):
    """Check if an error has been marked resolved."""
    errors = list_errors(limit=10000)
    for e in errors:
        if e.get("error_id") == error_id and e.get("resolved"):
            return True
    return False


def mark_error_attended(error_id):
    """Mark an error as attended (the owner is working on it).

    The autoresearch loop only picks up errors left unattended, so an error the
    owner has opened in the Self-Healing panel is skipped until it resolves.

    Returns True if the error was found and marked.
    """
    errors = list_errors(limit=10000)
    for e in errors:
        if e.get("error_id") == error_id:
            record = {
                "ts": _now_iso(),
                "error_id": error_id,
                "attended": True,
                "attended_ts": _now_iso(),
            }
            _append_jsonl(_errors_path(), record)
            return True
    return False


def mark_error_dismissed(error_id, reason=""):
    """Dismiss an error that cannot be verified (no replayable problem stored).

    Distinct from solved: it is labelled "dismissed (unverified)" and never
    claims the failure is gone.
    """
    record = {
        "ts": _now_iso(),
        "error_id": error_id,
        "dismissed": True,
        "reason": str(reason)[:200],
    }
    _append_jsonl(_errors_path(), record)
    return True


def mark_error_invalid(error_id, reason=""):
    """Mark an error as invalid test input (not a pipeline defect).

    It leaves the open list, but it is never labelled solved: invalid input is
    not a pipeline failure, so "fixed" would be a false claim.
    """
    record = {
        "ts": _now_iso(),
        "error_id": error_id,
        "invalid": True,
        "reason": str(reason)[:200],
    }
    _append_jsonl(_errors_path(), record)
    return True


def merge_resolved(errors):
    """Merge resolution records into error list.

    Returns errors with 'resolved', 'verified', 'attended' and 'invalid'
    fields set from the append-only resolution/attendance/invalid records.
    """
    resolved_ids = set()
    attended_ids = set()
    verified_ids = set()
    invalid_ids = set()
    dismissed_ids = set()
    all_records = _read_jsonl(_errors_path(), limit=100000)
    for r in all_records:
        if r.get("resolved") and r.get("error_id"):
            resolved_ids.add(r["error_id"])
            if r.get("verified"):
                verified_ids.add(r["error_id"])
        if r.get("attended") and r.get("error_id"):
            attended_ids.add(r["error_id"])
        if r.get("invalid") and r.get("error_id"):
            invalid_ids.add(r["error_id"])
        if r.get("dismissed") and r.get("error_id"):
            dismissed_ids.add(r["error_id"])
    for e in errors:
        e["resolved"] = e.get("error_id") in resolved_ids
        e["attended"] = e.get("error_id") in attended_ids
        e["verified"] = e.get("error_id") in verified_ids
        e["invalid"] = e.get("error_id") in invalid_ids
        e["dismissed"] = e.get("error_id") in dismissed_ids
        e["replayable"] = bool(e.get("problem"))
    return errors


# ── Validation findings ────────────────────────────────────────────────────
# Findings come from three feeders: the validation harness (manifest.json),
# failing pipeline runs, and the manual "Add finding" form.  Identity is
# rule+subject+feature+section (finding_key); repeats bump first/last_seen.
# Resolution is append-only, same pattern as errors.jsonl.

def log_finding(rule, subject="", feature="", section="", source="manual",
                severity=None, message="", paper="", run_id="", build=""):
    """Append (or update) one validation finding. Returns (finding_key, error)."""
    rule = str(rule or "").strip()
    if not rule:
        return None, "rule is required"
    fkey = finding_key(rule, subject, feature, section)
    existing = {f.get("finding_key"): f for f in _read_jsonl(_findings_path(), limit=100000)}
    prior = existing.get(fkey)
    record = {
        "ts": _now_iso(),
        "finding_key": fkey,
        "rule": str(rule)[:120],
        "subject": str(subject or "")[:60],
        "feature": str(feature or "")[:120],
        "section": str(section or "")[:160],
        "source": str(source or "manual")[:40],
        "message": str(message or "")[:500],
        "paper": str(paper or "")[:80],
        "run_id": str(run_id or "")[:40],
        "build": str(build or "")[:40],
        "severity": severity or classify_severity(message),
    }
    if prior:
        record["first_seen"] = prior.get("first_seen") or prior.get("ts")
        record["occurrences"] = int(prior.get("occurrences") or 1) + 1
    else:
        record["first_seen"] = record["ts"]
        record["occurrences"] = 1
    ok = _append_jsonl(_findings_path(), record)
    return fkey, (None if ok else "could not write findings.jsonl")


def list_findings(limit=200, source=None, status=None):
    """Latest record per finding_key, newest first, with resolution merged."""
    all_records = _read_jsonl(_findings_path(), limit=100000)
    latest = {}
    resolved = set()
    for r in reversed(all_records):  # chronological, so the latest record wins
        fkey = r.get("finding_key")
        if not fkey:
            continue
        if "rule" in r:
            latest[fkey] = r
            resolved.discard(fkey)  # a newer record re-opened it
        elif r.get("resolved"):
            resolved.add(fkey)
    findings = []
    for f in latest.values():
        f = dict(f)
        f["resolved"] = f["finding_key"] in resolved
        if source and f.get("source") != source:
            continue
        if status == "open" and f.get("resolved"):
            continue
        if status == "resolved" and not f.get("resolved"):
            continue
        findings.append(f)
    findings.sort(key=lambda f: f.get("ts") or "", reverse=True)
    return findings[:limit]


def resolve_findings_on_pass(current_keys):
    """Auto-resolve findings that a later harness pass no longer reports.

    `current_keys` is the set of finding_keys found failing in the newest pass.
    Everything previously seen that is absent is marked resolved. Returns the
    number of findings resolved.
    """
    all_records = _read_jsonl(_findings_path(), limit=100000)
    already = {r.get("finding_key") for r in all_records if r.get("resolved")}
    known = {r.get("finding_key"): r for r in all_records
             if r.get("finding_key") and r.get("source") == "validation-harness"}
    to_resolve = (set(known) - set(current_keys)) - already
    for fkey in to_resolve:
        mark_finding_resolved(fkey)
    return len(to_resolve)


def mark_finding_resolved(finding_key):
    """Append a resolution record for a finding. Returns True if it was open."""
    all_records = _read_jsonl(_findings_path(), limit=100000)
    if finding_key in {r.get("finding_key") for r in all_records if r.get("resolved")}:
        return False
    if finding_key not in {r.get("finding_key") for r in all_records}:
        return False
    _append_jsonl(_findings_path(), {"ts": _now_iso(), "finding_key": finding_key,
                                     "resolved": True, "resolution_ts": _now_iso()})
    return True


def finding_count():
    """Number of distinct findings ever recorded."""
    keys = {r.get("finding_key") for r in _read_jsonl(_findings_path(), limit=100000) if r.get("finding_key")}
    return len(keys)


def ingest_validation_manifest(manifest_path=None):
    """Feed the validation harness's manifest.json findings into the store.

    Manifest shape (per docs/VALIDATION_HARNESS.md Stage 1): a JSON object with
    "results": a list of {unit, kind, subject, paper, status, failures:[{rule,
    section, message}]}.  A compute deliverable failure without an explicit rule
    is recorded as rule "D-EXPORT".  Findings a later pass no longer reports are
    auto-resolved. Returns (opened, resolved, errors).
    """
    if manifest_path:
        path = Path(manifest_path)
    else:  # default: <business_pipeline repo root>/validation_out/manifest.json
        path = Path(__file__).resolve().parents[3] / "validation_out" / "manifest.json"
    if not path.is_file():
        return 0, 0, ["manifest not found: %s" % path]
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return 0, 0, ["cannot read manifest: %s" % e]
    errs = []
    current_keys = set()
    opened = 0
    # Two accepted shapes:
    #   §10 of the design: {"features": [{subject, kind, id, verdict, findings:[{rule, status, severity, detail, where}]}]}
    #   Stage-1 interim:   {"results": [{unit, subject, paper, failures: [{rule, section, message}]}]}
    results = manifest.get("results") or manifest.get("features") or \
        (manifest if isinstance(manifest, list) else [])
    for res in results:
        paper = str(res.get("paper") or res.get("id") or res.get("unit") or "")
        subject = str(res.get("subject") or "")
        failures = res.get("failures") or res.get("findings") or []
        for f in failures:
            rule = f.get("rule") or res.get("rule")
            if not rule:
                continue  # unattributed issues are not findings
            fkey, err = log_finding(
                rule=rule,
                subject=subject,
                feature=str(f.get("feature") or res.get("kind") or ""),
                section=str(f.get("section") or f.get("where") or ""),
                source="validation-harness",
                message=str(f.get("message") or f.get("detail") or ""),
                paper=paper,
                run_id=str(res.get("run_id") or ""),
                build=str(manifest.get("build") or ""),
            )
            if err:
                errs.append(err)
            elif fkey:
                current_keys.add(fkey)
                opened += 1
    resolved = resolve_findings_on_pass(current_keys)
    return opened, resolved, errs

def _proposals_path():
    return _log_dir() / "proposals.jsonl"


def log_proposal(finding_key, kind, payload, status="pending"):
    """Append one proposal. Returns proposal_id."""
    import uuid
    pid = uuid.uuid4().hex[:12]
    record = {
        "ts": _now_iso(),
        "proposal_id": pid,
        "finding_key": str(finding_key or ""),
        "kind": str(kind or "code"),
        "status": str(status or "pending"),
        "payload": payload if isinstance(payload, dict) else {"text": str(payload)},
    }
    ok = _append_jsonl(_proposals_path(), record)
    return pid if ok else None


def list_proposals(finding_key=None, status=None, limit=100):
    all_records = _read_jsonl(_proposals_path(), limit=100000)
    base = {}
    statuses = {}
    for r in all_records:
        pid = r.get("proposal_id")
        if not pid:
            continue
        if "payload" in r:
            base[pid] = r
        if r.get("status"):
            statuses[pid] = r["status"]
    out = []
    for pid, p in base.items():
        p = dict(p)
        p["status"] = statuses.get(pid, p.get("status", "pending"))
        if finding_key and p.get("finding_key") != finding_key:
            continue
        if status and p.get("status") != status:
            continue
        out.append(p)
    out.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return out[:limit]


def update_proposal_status(proposal_id, status):
    """Append a status update for a proposal."""
    all_records = _read_jsonl(_proposals_path(), limit=100000)
    known = {r.get("proposal_id") for r in all_records if r.get("proposal_id")}
    if proposal_id not in known:
        return False
    _append_jsonl(_proposals_path(), {"ts": _now_iso(), "proposal_id": proposal_id,
                                     "status": str(status)})
    # update in-memory latest record's status by re-reading
    return True
