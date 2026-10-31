"""Shared library for the corpus database: schema, extraction, ingest, search.

Every build tool imports this one module:

    ingest.py          one PDF -> corpus (the owner's upload, and the harvest)
    enrich.py          one enrichment pass: learning log -> candidates -> corpus
    corpus_service.py  the admin API that admin.html talks to

Stdlib only, except the optional PDF packages used at ingest time (`pypdf`, and
`pypdfium2` + `pytesseract` + a local Tesseract for scanned pages).

The database is the system of record. Meilisearch is a derived index and can be
rebuilt from SQLite at any time with `index_pages()`.
"""

import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.dirname(BUILD_DIR)
SCHEMA_PATH = os.path.join(BUILD_DIR, "schema.sql")
SETTINGS_PATH = os.path.join(BUILD_DIR, "meili_settings.json")

#: The corpus database. Override with BP_CORPUS_DB (the VPS path).
DB_PATH = os.environ.get("BP_CORPUS_DB") or os.path.join(CORPUS_DIR, "corpus.sqlite")
#: Working copies of the PDFs.
PDF_DIR = os.environ.get("BP_CORPUS_PDFS") or os.path.join(CORPUS_DIR, "pdfs")

MEILI_URL = os.environ.get("CORPUS_MEILI_URL", "http://127.0.0.1:7700").rstrip("/")
MEILI_KEY = os.environ.get("CORPUS_MEILI_KEY", "")
INDEX = os.environ.get("CORPUS_INDEX", "pages")

MIN_PAGE_CHARS = 20      # fewer characters than this on a page means "scan me"
KIND_PREFIX = {"book": "bk", "journal-article": "ja"}


# ── small helpers ───────────────────────────────────────────────────────────

def now():
    """UTC, ISO-8601, Zulu. One format everywhere, so string comparison in SQL
    compares correctly against strftime('...Z')."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def days_ago(days):
    """The same format, `days` in the past. Used as a SQL bound.

    Bind this into a `searched_at >= ?` comparison rather than using SQLite's
    own `datetime('now', ?)`: that returns `YYYY-MM-DD HH:MM:SS`, a space
    separator, and string-comparing it against the `...T...Z` timestamps in
    this database puts 'T' (0x54) above ' ' (0x20), so a row that is exactly
    `days` old still counts as inside the window.
    """
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean(text):
    """Strip control characters and normalise line endings. Never adds content."""
    text = (text or "").replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(ch for ch in text if ch in "\n\t" or ord(ch) >= 32)
    return text.strip()


def doc_id_for(kind, digest):
    return "%s-%s" % (KIND_PREFIX.get(kind, "doc"), digest[:12])


# ── identity: the keys that stop the corpus duplicating itself ──────────────
#
# Two different things can be duplicated, and they need two different keys.
#
#   the FILE  the same bytes. sha256 names it exactly.
#   the WORK  the same book or paper from another copy, a re-download or a
#             different scan. A DOI names it exactly; without one, the title,
#             the first author's family name and the year do.
#
# The work key is what catches the paper the harvester fetched and the owner
# then uploaded by hand, and the book the owner downloaded twice under two
# names.

DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/",
                "http://dx.doi.org/", "doi:")


def norm_doi(value):
    """A DOI as one canonical string: no prefix, no case, no surrounding space."""
    text = (value or "").strip().lower()
    if not text:
        return ""
    for prefix in DOI_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.strip()


def norm_url(value):
    """A URL as one canonical string: lowercase scheme and host, no fragment."""
    text = (value or "").strip()
    if not text:
        return ""
    try:
        parts = urllib.parse.urlsplit(text)
    except ValueError:
        return text.lower()
    if not parts.scheme and not parts.netloc:
        return text.lower().rstrip("/")
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                                    parts.path.rstrip("/"), parts.query, ""))


def norm_title(value):
    """A title as one canonical string: lowercase, no punctuation, single spaces."""
    text = re.sub(r"[^a-z0-9]+", " ", (value or "").lower())
    return " ".join(text.split())


def first_author_key(authors):
    """The family name of the first author. `; ` separates authors, family first."""
    first = (authors or "").split(";")[0].strip()
    if not first:
        return ""
    if "," in first:
        return norm_title(first.split(",")[0])
    words = first.split()
    return norm_title(words[-1]) if words else ""


def _isbn13_check(core12):
    """The 13th digit of an ISBN-13, from its first twelve."""
    total = sum(int(digit) * (1 if index % 2 == 0 else 3)
                for index, digit in enumerate(core12))
    return str((10 - total % 10) % 10)


def _isbn13_ok(digits):
    return len(digits) == 13 and digits.isdigit() and digits[-1] == _isbn13_check(digits[:12])


def _isbn10_ok(digits):
    if len(digits) != 10 or not digits[:9].isdigit():
        return False
    total = sum((10 - index) * (10 if ch in "Xx" else int(ch))
                for index, ch in enumerate(digits))
    return total % 11 == 0


def norm_isbn(value):
    """One ISBN-13 for one book, from either the ISBN-10 or the ISBN-13 spelling.

    '978-0-13-235088-4' and '0132350882' name the same book, so both become
    '9780132350884' and a second scan of that book is recognised as the same
    work even when its title was typed differently.

    The checksum is verified, and anything that fails it returns '' — because a
    key built on a mistyped number would refuse a genuinely different book,
    which is worse than failing to notice a duplicate. An unknown ISBN is a gap,
    not a guess.
    """
    digits = re.sub(r"[^0-9Xx]", "", value or "").upper()
    if len(digits) == 13:
        return digits if _isbn13_ok(digits) else ""
    if len(digits) == 10 and _isbn10_ok(digits):
        core = "978" + digits[:9]
        return core + _isbn13_check(core)
    return ""


def work_key_for(meta):
    """The identity of a WORK, or None when the metadata cannot name one.

    A DOI is the strongest name a work has, so it wins when it is known.
    An ISBN is the strongest name a *book* has, so it is second: two scans of
    one book then match even when their titles were typed differently, which the
    title rule cannot do.
    Otherwise the key is the title, the first author's family name and the
    year. A work with too little to tell it apart from another work is given
    no key at all: a key that is too weak would merge two different books and
    lose one of them, which is worse than a duplicate slipping through.
    """
    doi = norm_doi(meta.get("doi"))
    if doi:
        return "doi:" + doi
    isbn = norm_isbn(meta.get("isbn"))
    if isbn:
        return "isbn:" + isbn
    title = norm_title(meta.get("title"))
    if len(title) < 12:
        return None
    author = first_author_key(meta.get("authors"))
    year = meta.get("year")
    if not author and not year:
        return None
    return "t:%s|%s|%s" % (title, author, year if year else "")


def candidate_key(item):
    """The identity of a candidate work, or None when it cannot name one."""
    doi = norm_doi(item.get("doi"))
    if doi:
        return "doi:" + doi
    url = norm_url(item.get("url"))
    if url:
        return "url:" + url
    title = norm_title(item.get("title"))
    if len(title) < 12:
        return None
    return "t:%s|%s" % (title, item.get("year") if item.get("year") else "")


# ── the database ────────────────────────────────────────────────────────────

def connect(path=None):
    """Open the corpus database. Foreign keys are ON on every connection."""
    connection = sqlite3.connect(path or DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    register_functions(connection)
    return connection


def register_functions(connection):
    """Teach SQLite the normalisation rules, so a query can compare with them.

    A row written before the rules existed is then compared with the same
    rules as a row written now, which is what lets a duplicate be found
    across both.
    """
    connection.create_function("norm_doi", 1, norm_doi, deterministic=True)
    connection.create_function("norm_url", 1, norm_url, deterministic=True)
    connection.create_function("norm_title", 1, norm_title, deterministic=True)


#: Columns an older database may not have. The tables are created with
#: CREATE TABLE IF NOT EXISTS, so an existing database keeps its old shape and
#: a new column has to be added to it.
MIGRATIONS = {
    "documents": {"work_key": "TEXT", "added_by": "TEXT", "enrichen_at": "TEXT",
                  "owner_approved_at": "TEXT"},
    "candidates": {"work_key": "TEXT"},
    "ingest_log": {"reason": "TEXT"},
}


def migrate(connection):
    """Bring an older database up to the current shape. Safe to run repeatedly.

    It adds the columns the new constraints refer to, and gives the rows that
    predate the work key one, so the first duplicate check after the upgrade
    sees them.
    """
    tables = {row["name"] for row in
              connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, columns in MIGRATIONS.items():
        if table not in tables:
            continue
        existing = {row["name"] for row in connection.execute("PRAGMA table_info(%s)" % table)}
        for column, kind in columns.items():
            if column not in existing:
                connection.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, column, kind))
    connection.commit()
    backfill_work_keys(connection)


def backfill_work_keys(connection):
    """Give every row the key the current rule would give it.

    Not only the rows that predate the column: when the rule itself improves
    (an ISBN now names a book, where before only the title could), a row keyed
    under the old rule would keep a key that no longer matches the rule, and the
    better identity would never be used for it. Re-keying is therefore done
    whenever the stored key differs from the computed one.

    Two documents that now look like one work are **not** merged. Merging would
    destroy one of them; the second is left without a key instead, which makes it
    fall back to the file check and leaves the decision to the owner.
    """
    tables = {row["name"] for row in
              connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "documents" in tables:
        rows = connection.execute(
            "SELECT doc_id, title, authors, year, doi, isbn, work_key FROM documents").fetchall()
        for row in rows:
            key = work_key_for({"title": row["title"], "authors": row["authors"],
                                "year": row["year"], "doi": row["doi"], "isbn": row["isbn"]})
            if key == row["work_key"]:
                continue
            try:
                connection.execute("UPDATE documents SET work_key = ? WHERE doc_id = ?",
                                   (key, row["doc_id"]))
            except sqlite3.IntegrityError:
                connection.execute("UPDATE documents SET work_key = NULL WHERE doc_id = ?",
                                   (row["doc_id"],))
    if "candidates" in tables:
        rows = connection.execute(
            "SELECT candidate_id, title, doi, url, year FROM candidates WHERE work_key IS NULL").fetchall()
        for row in rows:
            key = candidate_key({"title": row["title"], "doi": row["doi"],
                                 "url": row["url"], "year": row["year"]})
            if key:
                connection.execute("UPDATE candidates SET work_key = ? WHERE candidate_id = ?",
                                   (key, row["candidate_id"]))
    connection.commit()


def apply_schema(connection=None):
    """Create or update the schema. Safe to run repeatedly."""
    own = connection is None
    connection = connection or connect()
    script = open(SCHEMA_PATH, encoding="utf-8").read()
    migrate(connection)
    try:
        connection.executescript(script)
    except sqlite3.OperationalError:
        # An older database: the script creates the tables it needs, but the
        # unique constraints refer to columns that only exist after the
        # migration above. Add them, then run the script again.
        migrate(connection)
        try:
            connection.executescript(script)
        except sqlite3.OperationalError as error:
            raise RuntimeError(
                "the schema could not be applied (%s). A database from an earlier build may "
                "hold two rows with the same work key, and the unique constraints refuse to "
                "be created until that is resolved." % error)
    connection.commit()
    if own:
        connection.close()


# ── PDF extraction ──────────────────────────────────────────────────────────

def tesseract_cmd():
    """The local Tesseract binary: env var, then the usual Windows paths, then PATH."""
    candidates = [
        os.environ.get("BP_TESSERACT_CMD"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
        shutil.which("tesseract"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def ocr_page(document, index):
    """Render one page with pdfium and OCR it with the local Tesseract."""
    import pypdfium2 as pdfium
    import pytesseract
    page = document[index]
    try:
        bitmap = page.render(scale=2.0)
        try:
            return pytesseract.image_to_string(bitmap.to_pil()) or ""
        finally:
            bitmap.close()
    finally:
        page.close()


def extract_pages(raw):
    """Return [(page_number, text, method)]. Exactly one entry per PDF page.

    `documents.extract_pdf()` in the pipeline returns the whole document as one
    string. The corpus needs the pages apart, so this does its own extraction
    and keeps the same idea: pypdf for the text layer, pdfium + Tesseract for
    pages that have none.
    """
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(raw))
    count = len(reader.pages)
    pages = []
    for index in range(count):
        try:
            text = clean(reader.pages[index].extract_text() or "")
        except Exception:
            text = ""
        pages.append([index + 1, text, "pdf_text_layer"])
    sparse = [page for page in pages if len(page[1]) < MIN_PAGE_CHARS]
    if sparse:
        if not tesseract_cmd():
            print("WARNING: %d page(s) have no text layer and no Tesseract was found; "
                  "their text will be empty" % len(sparse), file=sys.stderr)
            return [(number, text, method) for number, text, method in pages]
        import pypdfium2 as pdfium
        document = pdfium.PdfDocument(raw)
        try:
            for page in sparse:
                try:
                    page[1] = clean(ocr_page(document, page[0] - 1))
                except Exception:
                    page[1] = ""
                page[2] = "ocr"
        finally:
            document.close()
    return [(number, text, method) for number, text, method in pages]


# ── ingest ──────────────────────────────────────────────────────────────────

def find_duplicate(connection, digest, meta):
    """The document this file would duplicate, why, and how it matched.

    (doc_id, reason, kind) where kind is 'file' when the bytes are the same
    and 'work' when the work is the same but the bytes are not. (None, None,
    None) when the file is new.
    """
    row = connection.execute(
        "SELECT doc_id FROM documents WHERE sha256 = ?", (digest,)).fetchone()
    if row:
        return row["doc_id"], "the same file is already in the corpus as %s" % row["doc_id"], "file"
    key = work_key_for(meta)
    if key:
        row = connection.execute(
            "SELECT doc_id FROM documents WHERE work_key = ?", (key,)).fetchone()
        if row:
            return row["doc_id"], ("the same work is already in the corpus as %s "
                                   "(a different copy of it)" % row["doc_id"]), "work"
    return None, None, None


def restore_missing_file(connection, doc_id, raw, filename):
    """Put the file back for a document whose file is gone.

    The corpus holds one document per work. When the same file arrives again
    and the document's own copy has been lost, the right answer is to put the
    file back: not to refuse the file, and not to make a second document.
    Returns the path it was written to, or None when there was nothing to do.
    """
    if not filename:
        return None
    row = connection.execute(
        "SELECT local_path FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    if not row:
        return None
    path = row["local_path"]
    if path and os.path.exists(path):
        return None
    saved = save_pdf(raw, filename)
    connection.execute("UPDATE documents SET local_path = ? WHERE doc_id = ?", (saved, doc_id))
    connection.commit()
    return saved


def find_document_for(connection, doi=None, url=None, title=None, year=None):
    """The document that already holds this work, or None.

    A DOI names one work exactly, so it is matched first. A title and a year
    are matched next, and only when the title is specific enough to name one
    work - the corpus is not allowed to merge two books because they happen to
    share a short title.
    """
    doi_key = norm_doi(doi)
    if doi_key:
        row = connection.execute(
            "SELECT doc_id FROM documents WHERE doi IS NOT NULL AND norm_doi(doi) = ? LIMIT 1",
            (doi_key,)).fetchone()
        if row:
            return row["doc_id"]
    url_key = norm_url(url)
    if url_key:
        row = connection.execute(
            "SELECT doc_id FROM documents WHERE source_url IS NOT NULL AND norm_url(source_url) = ?"
            " LIMIT 1", (url_key,)).fetchone()
        if row:
            return row["doc_id"]
    title_key = norm_title(title)
    if len(title_key) >= 12 and year:
        row = connection.execute(
            "SELECT doc_id FROM documents WHERE title IS NOT NULL AND norm_title(title) = ?"
            " AND year = ? LIMIT 1", (title_key, year)).fetchone()
        if row:
            return row["doc_id"]
    return None


def record_refusal(connection, digest, doc_id, reason):
    """Write one 'skipped' row for a refused file: the audit of a duplicate.

    Only once per file. A file the owner uploads twice is refused twice, but
    the refusal is recorded once, so the log is a record of what is in the
    corpus and not a count of how many times the owner pressed the button.
    """
    row = connection.execute(
        "SELECT 1 FROM ingest_log WHERE sha256 = ? AND status = 'skipped' LIMIT 1",
        (digest,)).fetchone()
    if row:
        return
    connection.execute(
        "INSERT INTO ingest_log (ingested_at, doc_id, sha256, method, pages, status, reason)"
        " VALUES (?,?,?,?,?,?,?)",
        (now(), doc_id, digest, "none", 0, "skipped", reason))
    connection.commit()


def ingest_pdf(connection, raw, meta, local_path=None, filename=None, pages=None,
               added_by="owner"):
    """Put one PDF into the corpus. Returns (status, doc_id, message).

    status is 'ingested', 'duplicate' or 'failed'. A file that is already in
    the corpus is not ingested twice, and neither is another copy of a work the
    corpus already holds: the re-ingest policy (Q-15) is still open, so this
    refuses rather than guessing. A refused file is written to the ingest log
    with the reason, and no copy of it is written to disk.

    `added_by` is 'owner' (immediately citable), 'student' (awaits owner
    approval before it can be cited) or 'harvest' (immediately citable).
    Student uploads carry `added_by = 'student'` with `enrichen_at` and
    `owner_approved_at` NULL until the owner approves them in the admin UI.

    `pages` may carry pages that were extracted already, by a caller reading
    several PDFs at once. Reading a scanned page is the slow part of an import,
    so a bulk importer does it in parallel and passes the result in; the
    database itself is still written by one connection, in order.
    """
    digest = sha256_bytes(raw)
    existing, reason, kind = find_duplicate(connection, digest, meta)
    if existing:
        restored = None
        if kind == "file":
            # The same bytes, so the document is the same document. If its file
            # has been lost, this is the file that puts it back.
            restored = restore_missing_file(connection, existing, raw, filename)
        record_refusal(connection, digest, existing, reason)
        if restored:
            reason = reason + "; its file was put back"
        return "duplicate", existing, reason
    kind = meta.get("kind") or meta.get("source_kind") or "book"
    doc_id = doc_id_for(kind, digest)
    if pages is None:
        try:
            pages = extract_pages(raw)
        except Exception as error:
            return "failed", None, "the PDF could not be read (%s)" % type(error).__name__
    if not pages:
        return "failed", None, "the PDF has no pages"
    method = "ocr" if any(page[2] == "ocr" for page in pages) else "pdf_text_layer"
    if local_path is None and filename:
        local_path = save_pdf(raw, filename)
    # Student uploads are private and not citable until the owner approves them.
    enrichen_at = None
    owner_approved_at = None
    if added_by in ("owner", "harvest"):
        enrichen_at = now()
        owner_approved_at = now()
    connection.execute(
        "INSERT INTO documents (doc_id, title, authors, year, publisher, edition, isbn, doi, venue,"
        " volume, issue, source_kind, subject, local_path, r2_key, source_url, sha256, pages_total,"
        " text_method, licence, licence_verified, metadata_source, metadata_verified, added_at,"
        " work_key, added_by, enrichen_at, owner_approved_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (doc_id, meta.get("title") or "Untitled", meta.get("authors") or "",
         meta.get("year"), meta.get("publisher"), meta.get("edition"), meta.get("isbn"),
         meta.get("doi"), meta.get("venue"), meta.get("volume"), meta.get("issue"), kind,
         meta.get("subject"), local_path or meta.get("local_path") or "", None,
         meta.get("source_url"), digest, len(pages), method, meta.get("licence"),
         1 if meta.get("licence_verified") else 0, meta.get("metadata_source") or "manual",
         1 if meta.get("metadata_verified") else 0, now(), work_key_for(meta),
         added_by, enrichen_at, owner_approved_at))
    connection.executemany(
        "INSERT INTO pages (doc_id, doc_version, pdf_page, printed_page, section_path, text,"
        " text_sha256, chars, text_method) VALUES (?,?,?,?,?,?,?,?,?)",
        [(doc_id, 1, number, None, None, text, sha256_text(text), len(text), page_method)
         for number, text, page_method in pages])
    connection.execute(
        "INSERT INTO ingest_log (ingested_at, doc_id, sha256, method, pages, status, reason)"
        " VALUES (?,?,?,?,?,?,?)",
        (now(), doc_id, digest, method, len(pages),
         "ok" if method == "pdf_text_layer" else "ocr", None))
    connection.commit()
    return "ingested", doc_id, "%d pages, method=%s" % (len(pages), method)


def save_pdf(raw, filename):
    """Write the PDF into the working directory under a stable name."""
    os.makedirs(PDF_DIR, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", filename or "document.pdf")
    path = os.path.join(PDF_DIR, stem)
    counter = 1
    while os.path.exists(path):
        path = os.path.join(PDF_DIR, "%s.%d" % (stem, counter))
        counter += 1
    with open(path, "wb") as handle:
        handle.write(raw)
    return path


# ── Meilisearch ─────────────────────────────────────────────────────────────

def meili_call(method, path, payload=None, timeout=60):
    """One Meilisearch REST call. Raises on a transport or HTTP error."""
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if MEILI_KEY:
        headers["Authorization"] = "Bearer " + MEILI_KEY
    request = urllib.request.Request(MEILI_URL + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def meili_available():
    try:
        return meili_call("GET", "/health", timeout=3).get("status") == "available"
    except Exception:
        return False


def meili_task(uid, timeout=120):
    """Wait for a Meilisearch task to finish, and return it."""
    deadline = time.time() + timeout
    task = {}
    while time.time() < deadline:
        task = meili_call("GET", "/tasks/%d" % uid, timeout=10)
        if task.get("status") in ("succeeded", "failed", "canceled"):
            return task
        time.sleep(0.2)
    return task


def ensure_index():
    """Make sure the index exists, with `id` as its primary key.

    The primary key belongs to the index, not to its settings, so it is set
    here and is never patched: Meilisearch refuses the whole settings patch
    when it meets a field it does not know.
    """
    try:
        info = meili_call("GET", "/indexes/%s" % INDEX, timeout=10)
    except urllib.error.HTTPError:
        info = None
    if info is None:
        task = meili_call("POST", "/indexes", {"uid": INDEX, "primaryKey": "id"})
        finished = meili_task(task.get("taskUid", 0))
        if finished.get("status") != "succeeded":
            raise RuntimeError("the index %s could not be created: %s"
                               % (INDEX, finished.get("error")))
        return
    if not info.get("primaryKey"):
        task = meili_call("PATCH", "/indexes/%s" % INDEX, {"primaryKey": "id"})
        finished = meili_task(task.get("taskUid", 0))
        if finished.get("status") != "succeeded":
            raise RuntimeError("the primary key of the index %s could not be set: %s"
                               % (INDEX, finished.get("error")))


def apply_settings(settings):
    """Put the index settings on the server. Returns (settings_applied, warning).

    `typoTolerance.disableOnNumbers` needs Meilisearch v1.15 or newer. On an
    older server the whole patch is refused with HTTP 400 — and the corpus
    would then never index at all, which is a far worse outcome than losing one
    setting. So the field is dropped, and the loss is named rather than
    accepted quietly: on such a server a search for `2024` may match `2025`.
    """
    try:
        meili_call("PATCH", "/indexes/%s/settings" % INDEX, settings)
        return settings, None
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        if "disableOnNumbers" not in body:
            raise
        reduced = json.loads(json.dumps(settings))
        reduced.get("typoTolerance", {}).pop("disableOnNumbers", None)
        meili_call("PATCH", "/indexes/%s/settings" % INDEX, reduced)
        return reduced, ("this Meilisearch is older than v1.15 and refused "
                         "`typoTolerance.disableOnNumbers`; the setting was left off, so a "
                         "search for `2024` may match `2025`. Upgrade the server to turn it on.")


def index_pages(connection, rebuild=False):
    """Push every page into Meilisearch. Settings first, then documents.

    `rebuild=True` empties the index first, so that the index holds exactly
    the pages the database holds. That matters: an index that keeps documents
    the database no longer has can return the same page twice.
    """
    rows = connection.execute(
        "SELECT p.doc_id, p.pdf_page, p.printed_page, p.section_path, p.text, p.text_method,"
        "       d.title, d.authors, d.year, d.publisher, d.edition, d.doi, d.venue, d.volume,"
        "       d.issue, d.subject, d.source_kind, d.source_url"
        "  FROM pages p JOIN documents d ON d.doc_id = p.doc_id"
        " WHERE d.enrichen_at IS NOT NULL"
        " ORDER BY d.doc_id, p.pdf_page").fetchall()
    if not rows:
        return 0
    ensure_index()
    if rebuild:
        # Empty the index before it is refilled, so that it holds exactly the
        # pages the database holds and not a page twice.
        task = meili_call("DELETE", "/indexes/%s/documents" % INDEX)
        finished = meili_task(task.get("taskUid", 0))
        if finished.get("status") != "succeeded":
            raise RuntimeError("the index could not be emptied: %s" % finished.get("error"))
    settings = json.load(open(SETTINGS_PATH, encoding="utf-8"))
    applied, warning = apply_settings(settings)
    if warning:
        print("WARNING: %s" % warning, file=sys.stderr)
    documents = [{
        "id": "%s-%d" % (row["doc_id"], row["pdf_page"]),
        "doc_id": row["doc_id"], "pdf_page": row["pdf_page"],
        "printed_page": row["printed_page"], "section_path": row["section_path"],
        "text": row["text"], "text_method": row["text_method"],
        "title": row["title"], "authors": row["authors"], "year": row["year"],
        "publisher": row["publisher"], "edition": row["edition"], "doi": row["doi"],
        "venue": row["venue"], "volume": row["volume"], "issue": row["issue"],
        "subject": row["subject"], "source_kind": row["source_kind"],
        "url": row["source_url"],
    } for row in rows]
    for start in range(0, len(documents), 500):
        task = meili_call("POST", "/indexes/%s/documents" % INDEX, documents[start:start + 500])
        finished = meili_task(task.get("taskUid", 0))
        if finished.get("status") != "succeeded":
            raise RuntimeError("the pages could not be indexed: %s" % finished.get("error"))
    return len(documents)


def search_pages(query, limit=20):
    """Search the corpus. Returns a list of hits; an empty list when it is down."""
    try:
        body = json.dumps({"q": query, "limit": limit}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if MEILI_KEY:
            headers["Authorization"] = "Bearer " + MEILI_KEY
        request = urllib.request.Request(
            "%s/indexes/%s/search" % (MEILI_URL, INDEX), data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=3.0) as response:
            return json.loads(response.read().decode("utf-8")).get("hits", [])
    except Exception:
        return []


# ── the learning loop ───────────────────────────────────────────────────────

def record_search(connection, query, subject=None, dimension=None, case_id=None,
                  corpus_hits=0, live_hits=0, corpus_status="ok", sources=None):
    """Write one retrieval into the learning log. Fail-soft: never raise."""
    try:
        search_id = hashlib.sha1(
            ("%s|%s|%s" % (query, subject, now())).encode("utf-8")).hexdigest()[:16]
        connection.execute(
            "INSERT OR REPLACE INTO search_log (search_id, searched_at, query, subject, dimension,"
            " case_id, corpus_hits, live_hits, corpus_status) VALUES (?,?,?,?,?,?,?,?,?)",
            (search_id, now(), query or "", subject, dimension, case_id,
             int(corpus_hits or 0), int(live_hits or 0), corpus_status or "ok"))
        for source in sources or []:
            # The same source, seen twice in one search, is one row. The key is
            # the work it names, not the string it arrived as, so a DOI and a
            # landing page for the same paper do not become two rows.
            key = (norm_doi(source.get("doi")) or norm_url(source.get("url"))
                   or norm_title(source.get("title")))
            if not key:
                continue
            seen_id = hashlib.sha1(
                ("%s|%s|%s" % (search_id, source.get("source") or "unknown", key)).encode("utf-8")
            ).hexdigest()[:16]
            connection.execute(
                "INSERT OR IGNORE INTO seen_sources (seen_id, search_id, source, title, doi, url,"
                " venue, year, abstract, used) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (seen_id, search_id, source.get("source") or "unknown", source.get("title"),
                 norm_doi(source.get("doi")) or None, norm_url(source.get("url")) or None,
                 source.get("venue"), source.get("year"), source.get("abstract"),
                 1 if source.get("used") else 0))
            if source.get("used"):
                # A source the paper used stays used, whichever copy said so.
                connection.execute("UPDATE seen_sources SET used = 1 WHERE seen_id = ?", (seen_id,))
        connection.commit()
        return search_id
    except Exception:
        return None


def record_web_source(connection, source):
    """Note that the web tier saw a page. Fail-soft: never raise.

    The web tier is not the corpus: the corpus is books and papers. This is the
    rolling record of what the web layer saw, so the same site is not fetched
    and re-read for every student. `snapshot` holds the summary the tier
    already retrieved; the full text is never stored here.
    """
    try:
        # The URL is stored canonically, so the same page is one row however
        # it was written down.
        url = norm_url(source.get("url"))
        if not url:
            return None
        domain = source.get("domain")
        if not domain:
            domain = urllib.parse.urlparse(url).hostname or ""
            domain = domain[4:] if domain.startswith("www.") else domain
        existing = connection.execute(
            "SELECT url, seen_count FROM web_sources WHERE url = ?", (url,)).fetchone()
        if existing:
            connection.execute(
                "UPDATE web_sources SET last_seen_at = ?, seen_count = seen_count + 1,"
                " title = COALESCE(?, title), summary = COALESCE(?, summary) WHERE url = ?",
                (now(), source.get("title"), source.get("summary"), url))
            connection.commit()
            return url
        connection.execute(
            "INSERT INTO web_sources (url, first_seen_at, last_seen_at, title, domain, summary,"
            " seen_count, snapshot) VALUES (?,?,?,?,?,?,1,?)",
            (url, now(), now(), source.get("title"), domain or None,
             source.get("summary"), source.get("snapshot")))
        connection.commit()
        return url
    except Exception:
        return None


def find_candidate(connection, item):
    """The candidate row for this work, or None.

    The match is on the work, not on the row: the same paper seen once with a
    DOI and once with only a landing-page URL is one candidate, not two.
    """
    doi = norm_doi(item.get("doi"))
    url = norm_url(item.get("url"))
    title = norm_title(item.get("title"))
    year = item.get("year")
    if doi:
        row = connection.execute(
            "SELECT candidate_id FROM candidates WHERE doi IS NOT NULL AND norm_doi(doi) = ? LIMIT 1",
            (doi,)).fetchone()
        if row:
            return row["candidate_id"]
    if url:
        row = connection.execute(
            "SELECT candidate_id FROM candidates WHERE url IS NOT NULL AND norm_url(url) = ? LIMIT 1",
            (url,)).fetchone()
        if row:
            return row["candidate_id"]
    if title and len(title) >= 12:
        row = connection.execute(
            "SELECT candidate_id FROM candidates WHERE title IS NOT NULL AND norm_title(title) = ?"
            " AND year IS ? LIMIT 1", (title, year)).fetchone()
        if row:
            return row["candidate_id"]
    return None


def upsert_candidate(connection, item):
    """Record a work the corpus does not have. One row per work.

    A source seen twice is one candidate with a higher seen_count, never two
    candidates. The row is found by the work itself, so the same paper seen
    with a DOI in one search and with only a URL in another is still one
    candidate, and the DOI is kept on the row when it arrives later.
    """
    try:
        key = candidate_key(item)
        if not key:
            return None
        existing = find_candidate(connection, item)
        if existing:
            connection.execute(
                "UPDATE candidates SET last_seen_at = ?, seen_count = seen_count + 1,"
                " doi = COALESCE(doi, ?), url = COALESCE(url, ?),"
                " title = COALESCE(title, ?), year = COALESCE(year, ?)"
                " WHERE candidate_id = ?",
                (now(), norm_doi(item.get("doi")) or None, norm_url(item.get("url")) or None,
                 item.get("title"), item.get("year"), existing))
            connection.commit()
            return existing
        candidate_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        connection.execute(
            "INSERT INTO candidates (candidate_id, first_seen_at, last_seen_at, title, doi, url,"
            " source, year, venue, seen_count, priority, status, reason, work_key)"
            " VALUES (?,?,?,?,?,?,?,?,?,1,0,'new',?,?)",
            (candidate_id, now(), now(), item.get("title"), norm_doi(item.get("doi")) or None,
             norm_url(item.get("url")) or None, item.get("source"), item.get("year"),
             item.get("venue"), "seen in a pipeline search", key))
        connection.commit()
        return candidate_id
    except Exception:
        return None


def record_upload(connection, filename, digest, size, status, doc_id, message):
    """One row per uploaded file.

    The same file uploaded twice is one row, updated: the uploads table is a
    list of the files the owner has brought in, not a count of how many times
    the button was pressed.
    """
    try:
        upload_id = hashlib.sha1(digest.encode("utf-8")).hexdigest()[:16]
        connection.execute(
            "INSERT OR REPLACE INTO uploads (upload_id, uploaded_at, filename, sha256, bytes,"
            " status, doc_id, message) VALUES (?,?,?,?,?,?,?,?)",
            (upload_id, now(), filename, digest, size, status, doc_id, message))
        connection.commit()
        return upload_id
    except Exception:
        return None


def thin_subjects(connection, since_days=30, min_searches=3):
    """Subjects the corpus answers badly. 0.5 means "half the searches found nothing"."""
    rows = connection.execute(
        "SELECT subject, COUNT(*) AS searches,"
        "       SUM(CASE WHEN corpus_hits > 0 THEN 1 ELSE 0 END) AS answered"
        "  FROM search_log WHERE subject IS NOT NULL AND subject != ''"
        "   AND searched_at >= ? GROUP BY subject",
        (days_ago(since_days),)).fetchall()
    thin = {}
    for row in rows:
        searches = row["searches"] or 0
        if searches < min_searches:
            continue
        answered = row["answered"] or 0
        ratio = answered / searches
        if ratio < 0.5:
            thin[row["subject"]] = round(1.0 - ratio, 3)
    return thin


def rescore_candidates(connection):
    """Priority = how often it was seen, times how badly the corpus needs that subject."""
    thin = thin_subjects(connection)
    rows = connection.execute(
        "SELECT candidate_id, seen_count, source, title FROM candidates WHERE status = 'new'").fetchall()
    for row in rows:
        subject = classify_subject(row["title"] or "", row["source"] or "")
        need = thin.get(subject, 0.0)
        priority = row["seen_count"] * (1.0 + 2.0 * need)
        connection.execute(
            "UPDATE candidates SET priority = ? WHERE candidate_id = ?",
            (int(priority * 100), row["candidate_id"]))
    connection.commit()
    return len(rows)


#: A rough subject guess for a candidate. It is a hint for the admin, never a
#: fact: the owner confirms the subject before the document is ingested.
SUBJECT_HINTS = {
    "accounting": ["accounting", "ledger", "journal entry", "depreciation", "gaap", "ifrs"],
    "finance": ["finance", "valuation", "wacc", "capital budget", "portfolio", "derivatives"],
    "economics": ["economics", "elasticity", "gdp", "monetary", "fiscal", "inflation"],
    "management": ["strategy", "strategic", "management", "governance", "leadership",
                   "organisational", "porter", "five forces", "competitive advantage",
                   "competitive strategy", "swot", "industry analysis", "firm performance",
                   "business model", "case study"],
    "marketing": ["marketing", "brand", "consumer behaviour", "consumer behavior",
                  "segmentation", "pricing", "advertising", "customer", "retail", "promotion"],
    "operations": ["operations", "supply chain", "inventory", "logistics", "lean", "quality"],
    # `research` used to own "analysis", "study", "method" and "theory", which appear
    # in almost every academic title and therefore pulled every paper into this shelf.
    # It now holds only words that name research *as a subject*.
    "research": ["research design", "research method", "methodology", "literature review",
                 "systematic review", "meta-analysis", "bibliometric"],
    "entrepreneurship": ["entrepreneur", "venture", "startup", "msme", "sme"],
    "people": ["human resource", "organisational behaviour", "organizational behavior",
               "motivation", "employee", "workforce"],
    "supply-chain": ["supply chain", "procurement", "supplier", "logistics"],
    "project-management": ["project management", "pmbok", "project schedule", "risk register"],
}


def classify_subject(text, source=""):
    """The best-matching pipeline subject id for a candidate title. A hint only."""
    lowered = (text or "").lower()
    best, score = None, 0
    for subject, words in SUBJECT_HINTS.items():
        hits = sum(1 for word in words if word in lowered)
        if hits > score:
            best, score = subject, hits
    return best


def stats(connection):
    """The numbers the admin page shows."""
    def scalar(sql, args=()):
        row = connection.execute(sql, args).fetchone()
        return row[0] if row else 0

    by_subject = connection.execute(
        "SELECT subject, COUNT(*) AS documents FROM documents GROUP BY subject ORDER BY documents DESC"
    ).fetchall()
    searches = scalar("SELECT COUNT(*) FROM search_log")
    answered = scalar("SELECT COUNT(*) FROM search_log WHERE corpus_hits > 0")
    # The size on disk, not a page count. The 10 GB ceiling (C-01) is measured
    # in bytes, so a number under a "bytes" key has to be bytes.
    stored = 0
    for row in connection.execute("SELECT local_path FROM documents"):
        try:
            stored += os.path.getsize(row[0])
        except OSError:
            pass          # a document whose file is gone contributes its gap, not a guess
    return {
        "documents": scalar("SELECT COUNT(*) FROM documents"),
        "pages": scalar("SELECT COUNT(*) FROM pages"),
        "bytes": stored,
        "candidates": scalar("SELECT COUNT(*) FROM candidates WHERE status = 'new'"),
        "searches": searches,
        "searches_answered": answered,
        "hit_rate": round(answered / searches, 3) if searches else None,
        "by_subject": [{"subject": row["subject"], "documents": row["documents"]} for row in by_subject],
        "thin_subjects": thin_subjects(connection),
        "meili": meili_available(),
        "database": DB_PATH,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Corpus database utilities.")
    parser.add_argument("--init", action="store_true", help="create or update the schema")
    parser.add_argument("--status", action="store_true", help="print the corpus statistics")
    parser.add_argument("--index", action="store_true",
                        help="load the pages into the search index, emptying it first")
    args = parser.parse_args()
    if args.init:
        apply_schema()
        print("schema applied:", DB_PATH)
    if args.index:
        connection = connect()
        apply_schema(connection)
        print("indexed %d pages" % index_pages(connection, rebuild=True))
        connection.close()
    if args.status:
        connection = connect()
        apply_schema(connection)
        print(json.dumps(stats(connection), indent=2))
        connection.close()
