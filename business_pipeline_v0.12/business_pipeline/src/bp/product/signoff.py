"""Reviewer sign-off records (product layer, standard library only).

A sign-off is an **append-only** record attached to one immutable case
version.  It records who reviewed which exact bytes and under what wording -
it never changes the bundle, and recording a later sign-off never edits an
earlier one.

Storage:

    <BP_CASES_DIR>/<case id>/signoff/v002-001.json
    <BP_CASES_DIR>/<case id>/signoff/v002-002.json

The signature text is fixed by the owner (B-084, Option A): it records the
review, not the truth of the inputs or the correctness of the analysis.  The
record carries the version's `spec_hash`, `outputs_hash` and `bundle_hash` so
that a later tamper check can tell whether the signed bytes are still the
stored bytes.  Nothing here computes a business number.
"""

import datetime
import json
import os
import tempfile
from pathlib import Path

from . import versions

FORMAT = "bp-signoff/1"
DECISIONS = ("reviewed", "not_reviewed")
SIGNATURE_TEXT = ("I reviewed the named case bundle and its disclosed limitations. This signature records "
                  "that review; it does not assert that the inputs are true or that the analysis is correct.")
REQUIRED_KEYS = ("format", "case_id", "version", "reviewer", "scope", "decision", "signed_at",
                 "spec_hash", "outputs_hash", "bundle_hash", "signature_text")


class SignoffError(Exception):
    """Base class for sign-off failures."""


class SignoffNotFound(SignoffError):
    """No sign-off is stored for that case/version."""


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _folder(case_id, version):
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError("version must be a positive integer")
    return versions._case_dir(case_id) / "signoff"


def _next_sequence(folder, version):
    prefix = "v%03d-" % version
    highest = 0
    if folder.is_dir():
        for path in folder.glob(prefix + "*.json"):
            try:
                highest = max(highest, int(path.stem.split("-")[-1]))
            except ValueError:
                continue
    return highest + 1


def _write(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-signoff-", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return path


def record(case_id, version, reviewer, role=None, scope=None, decision="reviewed"):
    """Record one reviewer sign-off on one stored version. Returns the record.

    The version must exist and its bytes must still match the recorded hashes;
    a blank reviewer, an unknown decision or a tampered bundle is refused.
    """
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("reviewer must be a non-empty name")
    if decision not in DECISIONS:
        raise ValueError("decision must be one of: " + ", ".join(DECISIONS))
    if role is not None and not isinstance(role, str):
        raise ValueError("role must be text when supplied")
    if scope is not None and not isinstance(scope, str):
        raise ValueError("scope must be text when supplied")
    document = versions.get(case_id, version)
    if versions.bundle_hash(document["bundle"]) != document["bundle_hash"]:
        raise ValueError("the stored bundle no longer matches its recorded hash; sign-off refused")
    record = {"format": FORMAT, "case_id": case_id, "version": version,
              "reviewer": {"name": reviewer.strip(), "role": role.strip() if isinstance(role, str) else None},
              "scope": scope.strip() if isinstance(scope, str) else None,
              "decision": decision, "signed_at": _now_iso(),
              "spec_hash": document["spec_hash"], "outputs_hash": document["outputs_hash"],
              "bundle_hash": document["bundle_hash"], "signature_text": SIGNATURE_TEXT}
    folder = _folder(case_id, version)
    path = folder / ("v%03d-%03d.json" % (version, _next_sequence(folder, version)))
    _write(path, record)
    return record


def list_for(case_id, version=None):
    """Stored sign-offs for one version (or all versions), oldest first.

    Each entry carries an `integrity` block: whether the signed hashes still
    match the stored version, so a tampered bundle is visible rather than
    silently signed.
    """
    versions._check_id(case_id)
    folder = versions._case_dir(case_id) / "signoff"
    if not folder.is_dir():
        return []
    wanted = None if version is None else version
    records = []
    for path in sorted(folder.glob("v*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as error:
            records.append({"file": path.name, "corrupt": True, "error": str(error)})
            continue
        if not isinstance(document, dict) or document.get("format") != FORMAT:
            records.append({"file": path.name, "corrupt": True, "error": "not a sign-off record"})
            continue
        if wanted is not None and document.get("version") != wanted:
            continue
        integrity = {"checked": False, "matches": None}
        try:
            current = versions.get(case_id, document["version"])
            integrity = {"checked": True,
                         "matches": (current["bundle_hash"] == document["bundle_hash"]
                                     and current["spec_hash"] == document["spec_hash"]
                                     and current["outputs_hash"] == document["outputs_hash"])}
        except versions.VersionError as error:
            integrity = {"checked": True, "matches": False, "error": str(error)}
        records.append({**document, "integrity": integrity})
    return records


def summary(case_id):
    """One line per case version: number of sign-offs and whether they still match."""
    out = []
    for entry in versions.list_versions(case_id):
        if entry.get("corrupt"):
            continue
        records = list_for(case_id, entry["version"])
        out.append({"version": entry["version"],
                    "signoffs": len(records),
                    "reviewed": any(r.get("decision") == "reviewed" and not r.get("corrupt") for r in records),
                    "all_match": all(r.get("integrity", {}).get("matches") is not False for r in records)})
    return out
