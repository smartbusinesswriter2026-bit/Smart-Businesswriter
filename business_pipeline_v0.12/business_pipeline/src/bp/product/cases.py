"""Local durable case store (product layer, standard library only).

One JSON document per case, written atomically under the case directory:

    BP_CASES_DIR   if set, else <repo>/cases/

A case bundle is an **opaque document**.  This module stores it, lists it and
hands it back unchanged: it never reinterprets, recomputes, re-rounds or
"fixes" anything inside it, and it never imports the frozen core.  The
document shape is the one the product layer records:

    {"format": "bp-case/1", "id": "<12 lowercase hex>", "title": str,
     "created_at": "<ISO-8601 UTC>", "method": id, "tier": str,
     "spec_hash": str, "outputs_hash": str, "session": <session.to_dict()>,
     "delivery": {"report": str, "appendix": <appendix>},
     "reperform": <appendix["reperform"]>}

Refusals (all clear, all fail closed):

* an id that is not 12 lowercase hex characters is refused;
* a path that would leave the case directory is refused;
* a corrupt file (unreadable JSON, or missing a required key) refuses to load;
* a bundle missing a required key is refused when it is saved.
"""

import datetime
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

FORMAT = "bp-case/1"

#: A case id is exactly twelve lowercase hex characters.
ID_RE = re.compile(r"[0-9a-f]{12}")

#: Keys a stored bundle must carry.
REQUIRED_KEYS = ("title", "method", "tier", "spec_hash", "outputs_hash", "session", "delivery")

#: Keys a stored bundle must carry, envelope included.
STORED_KEYS = ("format", "id", "created_at", "reperform") + REQUIRED_KEYS


class CaseError(Exception):
    """Base class for case-store failures."""


class CaseNotFound(CaseError):
    """No bundle is stored under that id."""


class CaseCorrupt(CaseError, ValueError):
    """A stored bundle cannot be read (bad JSON, wrong shape or missing keys)."""


def cases_dir():
    """The directory that holds the case bundles.

    `BP_CASES_DIR` when it is set, otherwise `<repo>/cases/`.
    """
    configured = os.environ.get("BP_CASES_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[3] / "cases"


def _now_iso():
    """The current UTC time as an ISO-8601 string."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _check_id(case_id):
    """Refuse anything that is not 12 lowercase hex characters."""
    if not isinstance(case_id, str) or not ID_RE.fullmatch(case_id):
        raise ValueError("case id must be 12 lowercase hex characters")
    return case_id


def _path(case_id):
    """The file that holds a case, after refusing traversal."""
    checked = _check_id(case_id)
    root = cases_dir().resolve()
    path = (root / (checked + ".json")).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("case id resolves outside the case store")
    return path


def _text(value):
    """A stored value as text, without changing it."""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _write(path, document):
    """Write one JSON document atomically: temp file, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-case-", suffix=".json")
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


def save(bundle):
    """Store one case bundle and return its id.

    The envelope keys are the product layer's: `format` is fixed, `id` is
    generated when the caller does not supply a valid one, `created_at` is
    stamped when absent, and `reperform` is copied from the delivery appendix
    when the caller does not supply it.  Everything else is stored exactly as
    given.  Nothing here computes a business number.
    """
    if not isinstance(bundle, dict):
        raise ValueError("case bundle must be an object")
    found_format = bundle.get("format", FORMAT)
    if found_format != FORMAT:
        raise ValueError("unsupported case bundle format %r, expected %r" % (found_format, FORMAT))

    missing = [key for key in REQUIRED_KEYS if key not in bundle]
    if missing:
        raise ValueError("case bundle is missing required key(s): " + ", ".join(missing))

    session = bundle["session"]
    delivery = bundle["delivery"]
    if not isinstance(session, dict):
        raise ValueError("case bundle 'session' must be an object")
    if not isinstance(delivery, dict):
        raise ValueError("case bundle 'delivery' must be an object")
    if not isinstance(delivery.get("report"), str):
        raise ValueError("case bundle 'delivery' must carry a 'report' string")
    if not isinstance(delivery.get("appendix"), dict):
        raise ValueError("case bundle 'delivery' must carry an 'appendix' object")
    for key in ("title", "method", "tier", "spec_hash", "outputs_hash"):
        if not isinstance(bundle[key], str):
            raise ValueError("case bundle %r must be a string" % key)

    case_id = bundle.get("id")
    if case_id is None:
        case_id = uuid.uuid4().hex[:12]
    else:
        _check_id(case_id)
    created_at = bundle.get("created_at") or _now_iso()
    if not isinstance(created_at, str):
        raise ValueError("case bundle 'created_at' must be a string")

    reperform = bundle.get("reperform")
    if reperform is None:
        reperform = delivery["appendix"].get("reperform")
    if reperform is None:
        raise ValueError("case bundle is missing required key: reperform")

    document = dict(bundle)
    document["format"] = FORMAT
    document["id"] = case_id
    document["created_at"] = created_at
    document["reperform"] = reperform
    _write(_path(case_id), document)
    return case_id


def load(case_id):
    """Return the stored bundle, unchanged.

    Raises `CaseNotFound` when nothing is stored under that id and
    `CaseCorrupt` (a `ValueError`) when the file cannot be read as a bundle.
    """
    path = _path(case_id)
    if not path.exists():
        raise CaseNotFound("no case is stored with id %s" % case_id)
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CaseCorrupt("case %s cannot be read: %s" % (case_id, error))
    try:
        document = json.loads(raw)
    except ValueError as error:
        raise CaseCorrupt("case %s is not readable JSON: %s" % (case_id, error))
    if not isinstance(document, dict):
        raise CaseCorrupt("case %s is not a bundle object" % case_id)
    absent = [key for key in STORED_KEYS if key not in document]
    if absent:
        raise CaseCorrupt("case %s is missing required key(s): %s" % (case_id, ", ".join(absent)))
    if document["id"] != case_id:
        raise CaseCorrupt("case %s records a different id (%s)" % (case_id, document["id"]))
    return document


def list_cases():
    """Summaries of the stored cases, newest first.

    A file that cannot be read is listed with `corrupt: True` and the reason,
    so that a broken bundle is visible instead of silently missing.
    """
    root = cases_dir()
    if not root.exists():
        return []
    summaries = []
    for path in sorted(root.glob("*.json")):
        case_id = path.stem
        try:
            document = load(case_id)
        except CaseNotFound:
            continue
        except ValueError as error:
            summaries.append({"id": case_id, "corrupt": True, "error": str(error)})
            continue
        summaries.append({
            "id": document["id"],
            "title": document["title"],
            "created_at": document["created_at"],
            "method": document["method"],
            "tier": document["tier"],
            "spec_hash": document["spec_hash"],
            "outputs_hash": document["outputs_hash"],
            "corrupt": False,
        })
    summaries.sort(key=lambda item: (item.get("created_at") or "", item.get("id") or ""))
    return summaries


def delete(case_id):
    """Remove a stored case. Returns True; raises `CaseNotFound` if absent."""
    path = _path(case_id)
    if not path.exists():
        raise CaseNotFound("no case is stored with id %s" % case_id)
    path.unlink()
    return True
