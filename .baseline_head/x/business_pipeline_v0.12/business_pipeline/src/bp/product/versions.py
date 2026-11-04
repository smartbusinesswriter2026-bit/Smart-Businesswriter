"""Immutable case versions (product layer, standard library only).

A case can grow: the same analysis re-run with corrected data, a later period,
or an upgraded method version.  Each save is an immutable **version** appended
to the case's chain; an older version is never rewritten.

Storage layout (under the same directory as the flat case store):

    <BP_CASES_DIR>/<case id>/v001.json
    <BP_CASES_DIR>/<case id>/v002.json
    ...

A version document is an envelope around the opaque bundle the frozen core
recorded:

    {"format": "bp-case-version/1", "case_id": "<12 hex>", "version": 2,
     "created_at": "<ISO-8601 UTC>", "bundle_hash": "<sha256 of the bundle>",
     "spec_hash": str, "outputs_hash": str, "method": id,
     "method_version": str, "tier": str, "title": str, "bundle": {...}}

`bundle_hash` is computed from the canonical JSON of the bundle, so a
sign-off or a comparison can prove which bytes it was built from.  Nothing
here computes a business number: the bundle is stored as given.
"""

import datetime
import json
import re
import shutil
import uuid
from pathlib import Path

from . import cases as case_store

FORMAT = "bp-case-version/1"
ID_RE = re.compile(r"[0-9a-f]{12}")
REQUIRED_KEYS = ("title", "method", "tier", "spec_hash", "outputs_hash", "session", "delivery")
_META_KEYS = ("format", "case_id", "version", "created_at", "bundle_hash",
              "spec_hash", "outputs_hash", "method", "method_version", "tier", "title", "bundle")


class VersionError(Exception):
    """Base class for version-store failures."""


class VersionNotFound(VersionError):
    """The case or the requested version does not exist."""


class VersionCorrupt(VersionError, ValueError):
    """A stored version cannot be read or does not match its envelope."""


def _root():
    return case_store.cases_dir()


def _check_id(case_id):
    if not isinstance(case_id, str) or not ID_RE.fullmatch(case_id):
        raise ValueError("case id must be 12 lowercase hex characters")
    return case_id


def _case_dir(case_id):
    checked = _check_id(case_id)
    root = _root().resolve()
    path = (root / checked).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("case id resolves outside the case store")
    return path


def _version_path(case_id, version):
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError("version must be a positive integer")
    return _case_dir(case_id) / ("v%03d.json" % version)


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _canonical(bundle):
    return json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def bundle_hash(bundle):
    """The SHA-256 of the bundle's canonical JSON."""
    import hashlib
    return hashlib.sha256(_canonical(bundle).encode("utf-8")).hexdigest()


def _validate_bundle(bundle):
    if not isinstance(bundle, dict):
        raise ValueError("case bundle must be an object")
    missing = [key for key in REQUIRED_KEYS if key not in bundle]
    if missing:
        raise ValueError("case bundle is missing required key(s): " + ", ".join(missing))
    if not isinstance(bundle["session"], dict):
        raise ValueError("case bundle 'session' must be an object")
    delivery = bundle["delivery"]
    if not isinstance(delivery, dict):
        raise ValueError("case bundle 'delivery' must be an object")
    if not isinstance(delivery.get("report"), str):
        raise ValueError("case bundle 'delivery' must carry a 'report' string")
    if not isinstance(delivery.get("appendix"), dict):
        raise ValueError("case bundle 'delivery' must carry an 'appendix' object")
    for key in ("title", "method", "tier", "spec_hash", "outputs_hash"):
        if not isinstance(bundle[key], str):
            raise ValueError("case bundle %r must be a string" % key)
    return bundle


def _method_version(bundle):
    appendix = bundle["delivery"]["appendix"]
    method = appendix.get("method") if isinstance(appendix, dict) else None
    if isinstance(method, dict) and isinstance(method.get("version"), str):
        return method["version"]
    return "not recorded"


def _existing_versions(case_id):
    folder = _case_dir(case_id)
    if not folder.is_dir():
        return []
    versions = []
    for path in sorted(folder.glob("v*.json")):
        try:
            versions.append(int(path.stem[1:]))
        except ValueError:
            continue
    return versions


def _ensure_case(case_id):
    """Create the case directory, migrating a legacy flat case as version 1 if present."""
    folder = _case_dir(case_id)
    if folder.is_dir():
        return
    legacy = case_store.cases_dir() / (case_id + ".json")
    if legacy.exists():
        # A case saved by the original flat store becomes version 1; the legacy
        # file stays where it is, untouched, and the chain starts above it.
        document = case_store.load(case_id)
        envelope = _envelope(document, 1, document.get("created_at"))
        envelope["case_id"] = case_id
        folder.mkdir(parents=True, exist_ok=True)
        _write(folder / "v001.json", envelope)
        return
    folder.mkdir(parents=True, exist_ok=True)


def _envelope(bundle, version, created_at=None):
    return {"format": FORMAT, "case_id": None, "version": version,
            "created_at": created_at or _now_iso(), "bundle_hash": bundle_hash(bundle),
            "spec_hash": bundle["spec_hash"], "outputs_hash": bundle["outputs_hash"],
            "method": bundle["method"], "method_version": _method_version(bundle),
            "tier": bundle["tier"], "title": bundle["title"], "bundle": bundle}


def _write(path, document):
    import os
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-version-", suffix=".json")
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


def append(bundle, case_id=None):
    """Append one immutable version. Returns `(case_id, version)`.

    With no `case_id` a new case is created at version 1.  With a `case_id`
    the next version is appended to that case (a legacy flat case is adopted
    as version 1 first).  Nothing is overwritten.
    """
    _validate_bundle(bundle)
    if case_id is None:
        case_id = uuid.uuid4().hex[:12]
        version = 1
    else:
        _check_id(case_id)
        _ensure_case(case_id)
        versions = _existing_versions(case_id)
        version = (versions[-1] + 1) if versions else 1
    document = _envelope(bundle, version)
    document["case_id"] = case_id
    _write(_version_path(case_id, version), document)
    return case_id, version


def get(case_id, version):
    """One stored version document, or `VersionNotFound`."""
    path = _version_path(case_id, version)
    if not path.exists():
        raise VersionNotFound("case %s has no version %s" % (case_id, version))
    try:
        text = path.read_text(encoding="utf-8")
        document = json.loads(text)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise VersionCorrupt("version %s of case %s cannot be read: %s" % (version, case_id, error))
    if not isinstance(document, dict):
        raise VersionCorrupt("version %s of case %s is not an object" % (version, case_id))
    absent = [key for key in _META_KEYS if key not in document]
    if absent:
        raise VersionCorrupt("version %s of case %s is missing key(s): %s" % (version, case_id, ", ".join(absent)))
    if document["case_id"] != case_id or document["version"] != version:
        raise VersionCorrupt("version %s of case %s records a different identity" % (version, case_id))
    if bundle_hash(document["bundle"]) != document["bundle_hash"]:
        raise VersionCorrupt("version %s of case %s does not match its recorded bundle hash" % (version, case_id))
    return document


def latest(case_id):
    """The newest stored version, or `VersionNotFound`."""
    versions = _existing_versions(_check_id(case_id))
    if not versions:
        raise VersionNotFound("no versions are stored for case %s" % case_id)
    return get(case_id, versions[-1])


def list_versions(case_id):
    """Summaries of the stored versions, oldest first. A corrupt version is reported, not hidden."""
    summaries = []
    for version in _existing_versions(_check_id(case_id)):
        try:
            document = get(case_id, version)
        except VersionCorrupt as error:
            summaries.append({"version": version, "corrupt": True, "error": str(error)})
            continue
        summaries.append({"version": version, "created_at": document["created_at"],
                          "spec_hash": document["spec_hash"], "outputs_hash": document["outputs_hash"],
                          "method": document["method"], "method_version": document["method_version"],
                          "tier": document["tier"], "title": document["title"],
                          "bundle_hash": document["bundle_hash"], "corrupt": False})
    return summaries


def delete_case(case_id):
    """Remove every version (and any sign-off) of a case. Refuses a missing case."""
    _check_id(case_id)
    folder = _case_dir(case_id)
    if folder.is_dir():
        shutil.rmtree(folder)
        return True
    if (case_store.cases_dir() / (case_id + ".json")).exists():
        case_store.delete(case_id)
        return True
    raise VersionNotFound("no case is stored with id %s" % case_id)
