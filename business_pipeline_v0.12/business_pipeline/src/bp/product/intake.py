"""Intake store for files a user attaches on Home (product layer, standard library only).

The store does one job: keep the bytes exactly as they arrived, hash them, and
record what kind of file it is.  It does **not** read, parse or summarise
anything:

* a structured file (CSV/TSV/TXT/XLSX/XLSM) is stored with status `stored`
  and is read by the frozen `bp.ingest` module through `POST /api/intake`;
* every other file is stored with status `reference_only` and is never read -
  PDF, DOCX, scans, images and legacy `.xls` have no reader on this server,
  and pretending otherwise would be invention.

One JSON record per file under `BP_INTAKE_DIR` (default `<repo>/intake/`):

    {"format": "bp-intake/1", "id": "<12 lowercase hex>", "filename": str,
     "ext": str, "bytes": int, "sha256": str, "uploaded_at": "<ISO-8601 UTC>",
     "kind": "structured" | "reference", "status": "stored" | "ingested" |
     "reference_only", "note": str, "error": str | null, "table": object | null}

The payload bytes live beside it as `<id><ext>` and are never rewritten.  A
corrupt record refuses to load; it is listed as corrupt instead of being
silently skipped.  Nothing here computes a business number and nothing here
imports the frozen core.
"""

import datetime
import hashlib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

FORMAT = "bp-intake/1"

#: A file id is exactly twelve lowercase hex characters.
ID_RE = re.compile(r"[0-9a-f]{12}")

#: Extensions the frozen ingest module can read into a typed table.
STRUCTURED_EXT = (".csv", ".tsv", ".txt", ".xlsx", ".xlsm")

#: Extensions accepted for storage but never read (explicit notes below).
LEGACY_NOTE = "Legacy .xls is not read; save the workbook as .xlsx to ingest it."
REFERENCE_NOTE = "No reader is implemented for this file type on this server; it is stored only."

#: The same 5 MB limit the ingestion route applies (decode_request).
MAX_BYTES = 5_000_000

STATUSES = ("stored", "ingested", "reference_only")


class IntakeError(Exception):
    """Base class for intake-store failures."""


class IntakeNotFound(IntakeError):
    """No file is stored under that id."""


class IntakeCorrupt(IntakeError, ValueError):
    """A stored record cannot be read (bad JSON, wrong shape or missing keys)."""


def intake_dir():
    """The directory that holds attached files.

    `BP_INTAKE_DIR` when it is set, otherwise `<repo>/intake/`.
    """
    configured = os.environ.get("BP_INTAKE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[3] / "intake"


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _check_id(file_id):
    if not isinstance(file_id, str) or not ID_RE.fullmatch(file_id):
        raise ValueError("intake id must be 12 lowercase hex characters")
    return file_id


def _path(file_id, suffix=".json"):
    checked = _check_id(file_id)
    root = intake_dir().resolve()
    path = (root / (checked + suffix)).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("intake id resolves outside the intake store")
    return path


def _clean_filename(filename):
    """The bare file name, after refusing paths, control characters and blanks."""
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename is required")
    name = os.path.basename(filename.replace("\\", "/")).strip()
    if name in ("", ".", ".."):
        raise ValueError("a file name is required (a path is not)")
    if len(name) > 255:
        raise ValueError("the file name is longer than 255 characters")
    if any(ord(ch) < 32 or ch == "\x7f" for ch in name):
        raise ValueError("the file name contains control characters")
    return name


def _clean_ext(name):
    ext = os.path.splitext(name)[1].lower()
    return ext if re.fullmatch(r"\.[a-z0-9]{1,10}", ext or "") else ""


def _kind(ext):
    return "structured" if ext in STRUCTURED_EXT else "reference"


def _payload_suffix(ext):
    """The payload extension; `.json` is reserved for the record itself."""
    return ".bin" if ext == ".json" else (ext or "")


def _note(ext, kind):
    if kind == "structured":
        return "Read into a typed table by the frozen ingestion module; nothing is imputed or retyped."
    if ext == ".xls":
        return LEGACY_NOTE
    return REFERENCE_NOTE


def _write_json(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-intake-", suffix=".json")
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


def _write_bytes(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-intake-", suffix=".bin")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(raw)
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


def save(filename, raw, content_type=None):
    """Store one file and return its record.

    The bytes are written first, then the record.  A record that cannot be
    written removes the payload, so a half-stored file is never listed.
    """
    name = _clean_filename(filename)
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError("the file content must be bytes")
    raw = bytes(raw)
    if not raw:
        raise ValueError("the file is empty")
    if len(raw) > MAX_BYTES:
        raise ValueError("the file is over the 5 MB intake limit")
    ext = _clean_ext(name)
    kind = _kind(ext)
    file_id = uuid.uuid4().hex[:12]
    record = {
        "format": FORMAT,
        "id": file_id,
        "filename": name,
        "ext": ext,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "uploaded_at": _now_iso(),
        "kind": kind,
        "status": "stored" if kind == "structured" else "reference_only",
        "note": _note(ext, kind),
        "error": None,
        "table": None,
    }
    if isinstance(content_type, str) and content_type.strip():
        record["content_type"] = content_type.strip()[:120]
    payload_path = _path(file_id, _payload_suffix(ext))
    _write_bytes(payload_path, raw)
    try:
        _write_json(_path(file_id), record)
    except BaseException:
        try:
            payload_path.unlink()
        except OSError:
            pass
        raise
    return record


def _validate(document, file_id):
    if not isinstance(document, dict):
        raise IntakeCorrupt("intake %s is not a record object" % file_id)
    if document.get("format") != FORMAT:
        raise IntakeCorrupt("intake %s has an unknown format %r" % (file_id, document.get("format")))
    if document.get("id") != file_id:
        raise IntakeCorrupt("intake %s records a different id (%s)" % (file_id, document.get("id")))
    for key in ("filename", "kind", "status", "sha256", "uploaded_at"):
        if not isinstance(document.get(key), str):
            raise IntakeCorrupt("intake %s is missing %r" % (file_id, key))
    if document["status"] not in STATUSES:
        raise IntakeCorrupt("intake %s has an unknown status %r" % (file_id, document["status"]))
    return document


def load(file_id):
    """Return the stored record, unchanged."""
    path = _path(file_id)
    if not path.exists():
        raise IntakeNotFound("no file is stored with id %s" % file_id)
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise IntakeCorrupt("intake %s cannot be read: %s" % (file_id, error))
    try:
        document = json.loads(raw)
    except ValueError as error:
        raise IntakeCorrupt("intake %s is not readable JSON: %s" % (file_id, error))
    return _validate(document, file_id)


def payload(file_id):
    """The stored bytes and file name, for the server to hand to ingestion."""
    record = load(file_id)
    path = _path(file_id, _payload_suffix(record.get("ext") or ""))
    if not path.exists():
        raise IntakeNotFound("the payload of intake %s is missing" % file_id)
    try:
        return record["filename"], path.read_bytes()
    except OSError as error:
        raise IntakeCorrupt("the payload of intake %s cannot be read: %s" % (file_id, error))


def attach_table(file_id, table):
    """Record the typed table an ingestion run produced for this file."""
    if not isinstance(table, dict) or not isinstance(table.get("n_rows"), int) or not isinstance(table.get("n_cols"), int):
        raise ValueError("a table summary with n_rows and n_cols is required")
    record = load(file_id)
    record["status"] = "ingested"
    record["table"] = table
    record["error"] = None
    _write_json(_path(file_id), record)
    return record


def fail(file_id, message):
    """Record why an ingestion run failed; the file stays stored, unread."""
    record = load(file_id)
    record["error"] = str(message)
    _write_json(_path(file_id), record)
    return record


def _summary(record):
    table = record.get("table") or {}
    return {
        "id": record["id"],
        "filename": record["filename"],
        "ext": record.get("ext") or "",
        "bytes": record.get("bytes"),
        "sha256": record.get("sha256"),
        "uploaded_at": record.get("uploaded_at"),
        "kind": record.get("kind"),
        "status": record.get("status"),
        "note": record.get("note"),
        "error": record.get("error"),
        "n_rows": table.get("n_rows"),
        "n_cols": table.get("n_cols"),
        "columns": [c.get("name") for c in table.get("columns", []) if isinstance(c, dict)],
    }


def list_files():
    """Summaries of the stored files, newest first; a corrupt record stays visible."""
    root = intake_dir()
    if not root.exists():
        return []
    summaries = []
    for path in sorted(root.glob("*.json")):
        file_id = path.stem
        if not ID_RE.fullmatch(file_id):
            continue  # a temporary file left behind by an interrupted write
        try:
            record = load(file_id)
        except IntakeNotFound:
            continue
        except (IntakeError, ValueError) as error:
            summaries.append({"id": file_id, "corrupt": True, "error": str(error)})
            continue
        summary = _summary(record)
        summary["corrupt"] = False
        summaries.append(summary)
    summaries.sort(key=lambda item: (item.get("uploaded_at") or "", item.get("id") or ""), reverse=True)
    return summaries


def delete(file_id):
    """Remove a stored file and its payload. Returns True; raises when absent."""
    record = load(file_id)
    path = _path(file_id)
    path.unlink()
    try:
        _path(file_id, _payload_suffix(record.get("ext") or "")).unlink()
    except FileNotFoundError:
        pass
    return True
