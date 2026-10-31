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


# ── the database ────────────────────────────────────────────────────────────

def connect(path=None):
    """Open the corpus database. Foreign keys are ON on every connection."""
    connection = sqlite3.connect(path or DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def apply_schema(connection=None):
    """Create or update the schema. Safe to run repeatedly."""
    own = connection is None
    connection = connection or connect()
    connection.executescript(open(SCHEMA_PATH, encoding="utf-8").read())
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

def ingest_pdf(connection, raw, meta, local_path=None):
    """Put one PDF into the corpus. Returns (status, doc_id, message).

    status is 'ingested', 'duplicate' or 'failed'. A PDF that is already in the
    corpus is not ingested twice: the re-ingest policy (Q-15) is still open, so
    this refuses rather than guessing.
    """
    digest = sha256_bytes(raw)
    existing = connection.execute(
        "SELECT doc_id FROM documents WHERE sha256 = ?", (digest,)).fetchone()
    if existing:
        return "duplicate", existing["doc_id"], "already in the corpus as %s" % existing["doc_id"]
    kind = meta.get("kind") or meta.get("source_kind") or "book"
    doc_id = doc_id_for(kind, digest)
    try:
        pages = extract_pages(raw)
    except Exception as error:
        return "failed", None, "the PDF could not be read (%s)" % type(error).__name__
    if not pages:
        return "failed", None, "the PDF has no pages"
    method = "ocr" if any(page[2] == "ocr" for page in pages) else "pdf_text_layer"
    connection.execute(
        "INSERT INTO documents (doc_id, title, authors, year, publisher, edition, isbn, doi, venue,"
        " volume, issue, source_kind, subject, local_path, r2_key, source_url, sha256, pages_total,"
        " text_method, licence, licence_verified, metadata_source, metadata_verified, added_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (doc_id, meta.get("title") or "Untitled", meta.get("authors") or "",
         meta.get("year"), meta.get("publisher"), meta.get("edition"), meta.get("isbn"),
         meta.get("doi"), meta.get("venue"), meta.get("volume"), meta.get("issue"), kind,
         meta.get("subject"), local_path or meta.get("local_path") or "", None,
         meta.get("source_url"), digest, len(pages), method, meta.get("licence"),
         1 if meta.get("licence_verified") else 0, meta.get("metadata_source") or "manual",
         1 if meta.get("metadata_verified") else 0, now()))
    connection.executemany(
        "INSERT INTO pages (doc_id, doc_version, pdf_page, printed_page, section_path, text,"
        " text_sha256, chars, text_method) VALUES (?,?,?,?,?,?,?,?,?)",
        [(doc_id, 1, number, None, None, text, sha256_text(text), len(text), page_method)
         for number, text, page_method in pages])
    connection.execute(
        "INSERT INTO ingest_log (ingested_at, doc_id, sha256, method, pages, status)"
        " VALUES (?,?,?,?,?,?)",
        (now(), doc_id, digest, method, len(pages), "ok" if method == "pdf_text_layer" else "ocr"))
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


def index_pages(connection):
    """Push every page into Meilisearch. Settings first, then documents.

    Changing searchable/filterable/sortable attributes, stop words, synonyms or
    typo tolerance triggers a full reindex of every document, so the settings go
    first, on an empty index.
    """
    rows = connection.execute(
        "SELECT p.doc_id, p.pdf_page, p.printed_page, p.section_path, p.text, p.text_method,"
        "       d.title, d.authors, d.year, d.publisher, d.edition, d.doi, d.venue, d.volume,"
        "       d.issue, d.subject, d.source_kind, d.source_url"
        "  FROM pages p JOIN documents d ON d.doc_id = p.doc_id"
        " ORDER BY d.doc_id, p.pdf_page").fetchall()
    if not rows:
        return 0
    settings = json.load(open(SETTINGS_PATH, encoding="utf-8"))
    settings["primaryKey"] = "id"
    meili_call("PATCH", "/indexes/%s/settings" % INDEX, settings)
    documents = [{
        "id": "%s:%d" % (row["doc_id"], row["pdf_page"]),
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
        meili_call("POST", "/indexes/%s/documents" % INDEX, documents[start:start + 500])
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
            seen_id = hashlib.sha1(
                ("%s|%s|%s" % (search_id, source.get("source"), source.get("doi") or source.get("url") or source.get("title"))).encode("utf-8")
            ).hexdigest()[:16]
            connection.execute(
                "INSERT OR REPLACE INTO seen_sources (seen_id, search_id, source, title, doi, url,"
                " venue, year, abstract, used) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (seen_id, search_id, source.get("source") or "unknown", source.get("title"),
                 source.get("doi"), source.get("url"), source.get("venue"), source.get("year"),
                 source.get("abstract"), 1 if source.get("used") else 0))
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
        url = (source.get("url") or "").strip()
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


def upsert_candidate(connection, item):
    try:
        key = (item.get("doi") or item.get("url") or item.get("title") or "").strip().lower()
        if not key:
            return None
        candidate_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        existing = connection.execute(
            "SELECT candidate_id, seen_count FROM candidates WHERE candidate_id = ?",
            (candidate_id,)).fetchone()
        if existing:
            connection.execute(
                "UPDATE candidates SET last_seen_at = ?, seen_count = seen_count + 1 WHERE candidate_id = ?",
                (now(), candidate_id))
            connection.commit()
            return candidate_id
        connection.execute(
            "INSERT INTO candidates (candidate_id, first_seen_at, last_seen_at, title, doi, url,"
            " source, year, venue, seen_count, priority, status, reason)"
            " VALUES (?,?,?,?,?,?,?,?,?,1,0,'new',?)",
            (candidate_id, now(), now(), item.get("title"), item.get("doi"), item.get("url"),
             item.get("source"), item.get("year"), item.get("venue"),
             "seen in a pipeline search"))
        connection.commit()
        return candidate_id
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
    "management": ["strategy", "management", "governance", "leadership", "organisational"],
    "marketing": ["marketing", "brand", "consumer behaviour", "segmentation", "pricing"],
    "operations": ["operations", "supply chain", "inventory", "logistics", "lean", "quality"],
    "research": ["research", "method", "study", "analysis", "theory"],
    "entrepreneurship": ["entrepreneur", "venture", "startup", "business model"],
    "people": ["human resource", "organisational behaviour", "leadership", "motivation"],
    "supply-chain": ["supply chain", "procurement", "supplier"],
    "project-management": ["project", "pmbok", "schedule", "risk register"],
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
    args = parser.parse_args()
    if args.init:
        apply_schema()
        print("schema applied:", DB_PATH)
    if args.status:
        connection = connect()
        apply_schema(connection)
        print(json.dumps(stats(connection), indent=2))
        connection.close()
