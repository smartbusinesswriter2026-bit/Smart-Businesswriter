"""Operational surface for the local product server (product layer, standard library only).

Phase 2b of `docs/PRODUCT_BACKEND_PLAN.md`: health, a request log that
**never records case content**, and backup/restore of the case directory.
Standard library only, no frozen-core imports (the boundary test enforces it).

Environment:

    BP_CASES_DIR    the case store (default <repo>/cases)
    BP_STATE_DIR    logs and backups (default <repo>/state)
    BP_REQUEST_LOG  the request log path; unset or "" keeps the log OFF (opt-in)
"""

import datetime
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from . import cases as case_store
from . import versions as version_store
from .. import build as build_info

FORMAT = "bp-ops/1"
MAX_LOG_PATH = 200


def repo_root():
    """The project directory (the product package lives at `<repo>/src/bp/product`)."""
    return Path(__file__).resolve().parents[3]


def state_dir():
    configured = os.environ.get("BP_STATE_DIR")
    if configured:
        return Path(configured).expanduser()
    return repo_root() / "state"


def request_log_path():
    """The request-log file, or None when logging is not configured.

    The log is **off by default**: set `BP_REQUEST_LOG` to a path to enable it,
    or to `""` to keep it off explicitly.  (Off by default keeps a fresh run
    from writing operational files into the project, and keeps test runs clean.)
    """
    configured = os.environ.get("BP_REQUEST_LOG")
    if not configured:
        return None
    return Path(configured).expanduser()


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _safe_path(path):
    """A request path without its query string, capped, and nothing else."""
    text = str(path or "")
    text = text.split("?", 1)[0].split("#", 1)[0]
    return text[:MAX_LOG_PATH]


def log_request(method, path, status, duration_ms, error=None):
    """Append one request line to the log. Returns True when written.

    Only the method, the query-free path, the status and the duration are
    recorded - never a body, a case title, an input value or a report.  Logging
    is best-effort: a failure is reported to stderr and never fails the request.
    """
    target = request_log_path()
    if target is None:
        return False
    line = {"ts": _now_iso(), "method": str(method or "")[:12], "path": _safe_path(path),
            "status": int(status), "ms": round(float(duration_ms), 3)}
    if error:
        line["error"] = str(error)[:120]
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(line, ensure_ascii=False) + "\n")
        return True
    except OSError as problem:
        import sys
        print("warning: request log not written: %s" % problem, file=sys.stderr)
        return False


def _case_counts():
    root = case_store.cases_dir()
    summary = {"dir": str(root), "cases": 0, "versions": 0, "signoffs": 0}
    if not root.is_dir():
        return summary
    counted = set()
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        case_id = folder.name
        try:
            versions = version_store.list_versions(case_id)
        except (ValueError, version_store.VersionError):
            continue
        counted.add(case_id)
        summary["cases"] += 1
        summary["versions"] += len(versions)
        signoff_dir = folder / "signoff"
        if signoff_dir.is_dir():
            summary["signoffs"] += len(list(signoff_dir.glob("*.json")))
    for path in sorted(root.glob("*.json")):
        if path.stem in counted:
            continue
        summary["cases"] += 1
        summary["versions"] += 1
    return summary


def health(extra=None):
    """A JSON-serialisable health report. `extra` carries server facts from the core."""
    problems = []
    try:
        store = _case_counts()
        checks = [{"name": "case_store", "ok": True, "detail": store["dir"]}]
    except (OSError, ValueError) as problem:
        store = {"dir": str(case_store.cases_dir()), "cases": None, "versions": None, "signoffs": None}
        problems.append(str(problem))
        checks = [{"name": "case_store", "ok": False, "detail": str(problem)}]
    log_path = request_log_path()
    report = {"format": FORMAT, "status": "ok" if not problems else "degraded",
              # The build the tree actually is, so the page's pill cannot state a
              # different one.  `bp.build.VERSION` is pinned to the newest changelog
              # build by tests/test_docs_sync.py (D-PM-07).
              "build": build_info.VERSION,
              "checked_at": _now_iso(), "product": {"state_dir": str(state_dir())},
              "case_store": store,
              "request_log": {"enabled": log_path is not None, "path": str(log_path) if log_path else None},
              "checks": checks, "problems": problems}
    if isinstance(extra, dict):
        report.update(extra)
    return report


def _backup_dir():
    return state_dir() / "backups"


def backup(destination=None):
    """Zip the case directory. Returns metadata about the archive.

    Nothing is written into the case directory, and no file is modified.
    """
    cases_dir = case_store.cases_dir()
    target_dir = Path(destination).expanduser() if destination else _backup_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = target_dir / ("cases-%s.zip" % stamp)
    files = []
    if cases_dir.is_dir():
        # Only the case store's JSON documents are archived; state, logs and
        # previously written archives are never folded into a backup.
        files = sorted(path for path in cases_dir.rglob("*.json") if path.is_file())
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            bundle.write(path, arcname=str(path.relative_to(cases_dir)).replace("\\", "/"))
        bundle.writestr("bp-backup-manifest.json", json.dumps(
            {"format": "bp-backup/1", "created_at": _now_iso(), "files": len(files),
             "cases_dir": str(cases_dir)}, ensure_ascii=False))
    raw = archive.read_bytes()
    return {"format": "bp-backup/1", "archive": str(archive), "files": len(files),
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def list_backups():
    """Existing backups, newest first, with their sizes."""
    folder = _backup_dir()
    if not folder.is_dir():
        return []
    rows = []
    for path in sorted(folder.glob("*.zip"), reverse=True):
        rows.append({"archive": str(path), "bytes": path.stat().st_size})
    return rows


def _safe_member(name):
    """Refuse absolute, parent-traversing, drive-qualified or non-JSON entries (zip-slip defence)."""
    clean = str(name).replace("\\", "/")
    if not clean or clean.startswith("/") or ".." in clean.split("/"):
        raise ValueError("archive entry escapes the case directory: %r" % name)
    if ":" in clean.split("/", 1)[0]:
        raise ValueError("archive entry has a drive-qualified path: %r" % name)
    if not clean.endswith(".json"):
        raise ValueError("archive entry is not a JSON file: %r" % name)
    if clean.count("/") > 3:
        raise ValueError("archive entry is nested too deeply: %r" % name)
    return clean


def restore(archive, overwrite=False):
    """Restore a backup into the case directory.

    The archive is validated first (a readable zip, JSON members only, no
    traversal); nothing is extracted outside the case directory.  A case that
    already exists refuses the restore unless `overwrite=True`.
    """
    source = Path(archive).expanduser()
    if not source.is_file():
        raise ValueError("backup archive not found: %s" % source)
    cases_dir = case_store.cases_dir()
    cases_dir.mkdir(parents=True, exist_ok=True)
    try:
        bundle = zipfile.ZipFile(source)
    except zipfile.BadZipFile:
        raise ValueError("backup archive is not a readable zip: %s" % source)
    members = [member for member in bundle.namelist() if member != "bp-backup-manifest.json"]
    if not members:
        raise ValueError("backup archive contains no case files")
    checked = [(member, _safe_member(member)) for member in members]
    existing = set()
    for member, clean in checked:
        top = clean.split("/", 1)[0]
        if (cases_dir / top).exists():
            existing.add(top)
    if existing and not overwrite:
        raise ValueError("restore refused: these cases already exist: " + ", ".join(sorted(existing)))
    staging = Path(tempfile.mkdtemp(prefix=".bp-restore-", dir=str(cases_dir.parent)))
    try:
        for _, clean in checked:
            destination = (staging / clean).resolve()
            try:
                destination.relative_to(staging.resolve())
            except ValueError:
                raise ValueError("archive entry escapes the restore directory: %r" % clean)
        bundle.extractall(staging)
        restored = 0
        for member, clean in checked:
            source_file = staging / clean
            destination = cases_dir / clean
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, destination)
            restored += 1
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {"format": "bp-backup/1", "restored": restored, "archive": str(source),
            "cases_dir": str(cases_dir), "overwrote_existing": bool(existing)}
