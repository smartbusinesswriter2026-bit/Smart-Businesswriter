"""The student's papers on disk (product layer, standard library only).

Every generated paper is written to ``documents/`` next to a small index record,
so the Home page can list it and the browser can download it again. The shipped
sample papers in ``samples/`` are listed beside them, which means the page is
never empty and the student can inspect a finished paper before writing one.

Nothing here recomputes a paper: the bytes that were generated are the bytes
that are served. An id is either a twelve-character hex string from the index or
``sample-<slug>`` for a shipped sample; anything else is refused.
"""

import hashlib
import json
import os
import re
import time

MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ZIP_MIME = "application/zip"
#: A shipped sample is a Word file, or a ZIP holding the paper and its explainer
#: exactly as the export route produces them.
MIME_BY_EXT = {".docx": MIME, ".zip": ZIP_MIME}

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
STORE = os.path.join(ROOT, "documents")
SAMPLES = os.path.join(ROOT, "samples")
INDEX = os.path.join(STORE, "index.json")

ID = re.compile(r"^[0-9a-f]{12}$")
SAMPLE_ID = re.compile(r"^sample-[a-z0-9-]{1,90}$")

SAMPLE_TITLES = {
    "apple-iran-pestel-apa7.docx": ("Apple's Prospective Entry into Iran: A PESTEL Analysis", "PESTEL", "APA 7"),
    "five-forces-full-paper.docx": ("Porter's Five Forces: Apple's Entry into Iran's Smartphone Industry",
                                    "Five Forces", "Full paper"),
    "five-forces-completion-draft.docx": ("Porter's Five Forces: Apple's Entry into Iran's Smartphone Industry",
                                          "Five Forces", "Draft"),
    # One framework and one computation, in the three length options the product
    # offers, each with the companion that explains it.  Word files, so a
    # double-click opens them.
    "pestel-and-break-even-tehran-device-store-short.docx": (
        "PESTEL and Break-even: A Tehran Device Store - Short (600-1,200 words)",
        "PESTEL + break-even", "Short paper"),
    "pestel-and-break-even-tehran-device-store-short-explainer.docx": (
        "How the Short Paper Was Solved", "PESTEL + break-even", "Explainer"),
    "pestel-and-break-even-tehran-device-store-mid.docx": (
        "PESTEL and Break-even: A Tehran Device Store - Mid (1,200-2,500 words)",
        "PESTEL + break-even", "Mid report"),
    "pestel-and-break-even-tehran-device-store-mid-explainer.docx": (
        "How the Mid Report Was Solved", "PESTEL + break-even", "Explainer"),
    "pestel-and-break-even-tehran-device-store-long.docx": (
        "PESTEL and Break-even: A Tehran Device Store - Long (2,500-5,000 words)",
        "PESTEL + break-even", "Long report"),
    "pestel-and-break-even-tehran-device-store-long-explainer.docx": (
        "How the Long Report Was Solved", "PESTEL + break-even", "Explainer"),
}


class NotFound(Exception):
    pass


def _ensure():
    if not os.path.isdir(STORE):
        os.makedirs(STORE, exist_ok=True)


def _index():
    try:
        with open(INDEX, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _write_index(rows):
    _ensure()
    tmp = INDEX + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(rows[:200], handle, indent=1)
    os.replace(tmp, INDEX)


def _slug(name):
    base = os.path.basename(str(name or "paper.docx"))
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-").lower()
    if not base.endswith(".docx"):
        base += ".docx"
    return base or "paper.docx"


def save(data, filename, title, framework="Five Forces", version="draft", words=0, length=""):
    """Store one generated paper and return its record."""
    _ensure()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    seed = hashlib.sha256((str(time.time()) + str(len(data)) + str(title)).encode("utf-8")).hexdigest()
    doc_id = seed[:12]
    name = _slug(filename)
    with open(os.path.join(STORE, doc_id + ".docx"), "wb") as handle:
        handle.write(data)
    record = {"id": doc_id, "title": str(title or "Paper"), "framework": str(framework or ""),
              "version": str(version or ""), "created": stamp, "size": len(data),
              "words": int(words or 0), "length": str(length or ""), "filename": name,
              "download": "/api/cases/documents/" + doc_id}
    rows = [row for row in _index() if row.get("id") != doc_id]
    rows.insert(0, record)
    _write_index(rows)
    return record


def _samples():
    rows = []
    try:
        names = sorted(os.listdir(SAMPLES))
    except OSError:
        return rows
    for name in names:
        extension = os.path.splitext(name)[1].lower()
        mime = MIME_BY_EXT.get(extension)
        if mime is None:
            continue
        path = os.path.join(SAMPLES, name)
        try:
            size = os.path.getsize(path)
            created = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(path)))
        except OSError:
            continue
        title, framework, version = SAMPLE_TITLES.get(
            name, (re.sub(r"[-_]+", " ", os.path.splitext(name)[0]).strip().title(), "Sample", "Sample"))
        doc_id = "sample-" + re.sub(r"[^a-z0-9]+", "-", os.path.splitext(name)[0].lower()).strip("-")
        rows.append({"id": doc_id, "title": title, "framework": framework, "version": version,
                     "created": created, "size": size, "words": 0, "filename": name,
                     "download": "/api/cases/documents/" + doc_id, "sample": True, "mime": mime})
    return rows


LABELS = {"full": "Full paper", "draft": "Draft"}


def listing():
    """Newest first: the student's papers, then the shipped samples."""
    rows = []
    for row in _index():
        if not row.get("id"):
            continue
        row = dict(row)
        row["version"] = LABELS.get(str(row.get("version") or "").lower(), row.get("version") or "")
        rows.append(row)
    return {"documents": rows + _samples()}


def read(doc_id):
    """Return (record, bytes) for one document id."""
    doc_id = str(doc_id or "")
    if SAMPLE_ID.match(doc_id):
        for row in _samples():
            if row["id"] == doc_id:
                path = os.path.join(SAMPLES, row["filename"])
                root = os.path.realpath(SAMPLES)
                target = os.path.realpath(path)
                if not target.startswith(root + os.sep):
                    raise NotFound("no such document")
                with open(target, "rb") as handle:
                    return row, handle.read()
        raise NotFound("no such document")
    if not ID.match(doc_id):
        raise NotFound("no such document")
    for row in _index():
        if row.get("id") == doc_id:
            path = os.path.join(STORE, doc_id + ".docx")
            if not os.path.isfile(path):
                raise NotFound("no such document")
            with open(path, "rb") as handle:
                return row, handle.read()
    raise NotFound("no such document")
