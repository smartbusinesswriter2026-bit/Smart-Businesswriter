"""The corpus build tools: the contracts that must not break.

    python corpus-db/build/test_corpus_build.py

Stdlib only, and no test may touch the real corpus database or the network:
every test builds its own throwaway SQLite file in a temporary directory.

Five defects are pinned here. Each was found by running the code, not by
reading it, and each failed silently rather than loudly:

    1. `days_ago()` raised NameError, because `timedelta` was never imported.
    2. The 30-day window compared the stored `...T...Z` timestamps against
       SQLite's own `datetime('now', ?)`, which returns a space separator.
       'T' sorts above ' ', so a row exactly `days` old still counted as
       inside the window.
    3. The admin service bound the name `handle` to a file object inside
       `do_GET`, shadowing the module's `handle()` function: every API GET
       raised UnboundLocalError and the admin page could not load its data.
    4. The admin service dropped the query string, so `?status=all` and
       `?limit=` were ignored and the enrichment queue showed only 'new'.
    5. `stats()["bytes"]` returned a page count, not bytes.

Ten more pin the no-duplication guarantees (D-25): the same file twice, another
copy of the same work, a different book not refused, one refusal recorded once,
the database itself refusing a second row with the same bytes, the same paper
seen with a DOI and with only a URL staying one candidate, a candidate for a
work already held not being downloaded, a lost file being put back, and a work
that returns in a later year remaining its own document.
"""

import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import corpus_lib as lib
import corpus_service as service
import enrich


class TempCorpusTest(unittest.TestCase):
    """A throwaway corpus: its own database file, its own directory."""

    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="corpus-test-")
        self.db_path = os.path.join(self.directory, "corpus.sqlite")
        self.connection = lib.connect(self.db_path)
        lib.apply_schema(self.connection)

    def tearDown(self):
        self.connection.close()
        shutil.rmtree(self.directory, ignore_errors=True)


class TimestampTest(TempCorpusTest):
    def test_days_ago_returns_the_stored_format(self):
        value = lib.days_ago(30)
        self.assertTrue(value.endswith("Z"), value)
        self.assertIn("T", value, value)

    def test_a_row_exactly_at_the_window_edge_is_outside_it(self):
        """The defect: 'T' (0x54) sorts above ' ' (0x20), so the old
        `datetime('now', ?)` comparison let an expired row back in.

        The row is one second *older* than the boundary, because the bound
        is recomputed at query time and a row landing on the same second as
        the bound is inside the window (`>=`), which is correct."""
        edge = (datetime.now(timezone.utc) - timedelta(days=30, seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.connection.execute(
            "INSERT INTO search_log (search_id, searched_at, query, subject, corpus_hits)"
            " VALUES ('edge', ?, 'q', 'accounting', 0)", (edge,))
        self.connection.commit()
        thin = lib.thin_subjects(self.connection, since_days=30, min_searches=1)
        self.assertNotIn("accounting", thin,
                         "a row older than 30 days must be outside the 30-day window")

    def test_a_row_inside_the_window_is_counted(self):
        inside = lib.days_ago(1)
        self.connection.execute(
            "INSERT INTO search_log (search_id, searched_at, query, subject, corpus_hits)"
            " VALUES ('inside', ?, 'q', 'accounting', 0)", (inside,))
        self.connection.commit()
        thin = lib.thin_subjects(self.connection, since_days=30, min_searches=1)
        self.assertIn("accounting", thin,
                      "a row from yesterday is inside the 30-day window")

    def test_unanswered_queries_respects_the_window(self):
        edge = (datetime.now(timezone.utc) - timedelta(days=30, seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.connection.execute(
            "INSERT INTO search_log (search_id, searched_at, query, subject, corpus_hits)"
            " VALUES ('edge', ?, 'stale question', 'accounting', 0)", (edge,))
        self.connection.commit()
        gaps = enrich.unanswered_queries(self.connection, since_days=30, min_times=1)
        self.assertEqual(gaps, [], "an expired row is not an unanswered question")


class CandidateTest(TempCorpusTest):
    def test_a_candidate_seen_twice_rises_and_keeps_one_row(self):
        item = {"title": "Pricing in emerging markets", "doi": "10.1234/emerging.1",
                "source": "openalex"}
        lib.upsert_candidate(self.connection, item)
        lib.upsert_candidate(self.connection, item)
        rows = self.connection.execute("SELECT * FROM candidates").fetchall()
        self.assertEqual(len(rows), 1, "one candidate, however often it is seen")
        self.assertEqual(rows[0]["seen_count"], 2)
        self.assertEqual(rows[0]["status"], "new")

    def test_collect_turns_a_seen_source_into_a_candidate(self):
        search_id = lib.record_search(
            self.connection, "pricing strategy", subject="marketing",
            sources=[{"source": "openalex", "title": "Pricing in emerging markets",
                      "doi": "10.1234/emerging.1", "url": "https://doi.org/10.1234/emerging.1"}])
        self.assertIsNotNone(search_id)
        seen, added = enrich.collect(self.connection)
        self.assertEqual(seen, 1)
        self.assertEqual(added, 1)
        rows = self.connection.execute("SELECT * FROM candidates").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["doi"], "10.1234/emerging.1")

    def test_record_search_never_raises(self):
        """A learning-log failure must never break a retrieval."""
        broken = lib.connect(self.db_path)
        broken.execute("DROP TABLE IF EXISTS search_log")
        broken.commit()
        self.assertIsNone(lib.record_search(broken, "q", subject="marketing"))
        broken.close()


class WebSourceTest(TempCorpusTest):
    def test_a_web_page_is_recorded_once_and_counted_afterwards(self):
        source = {"url": "https://example.org/a-study", "title": "A study",
                  "summary": "A short summary."}
        self.assertEqual(lib.record_web_source(self.connection, source),
                         "https://example.org/a-study")
        lib.record_web_source(self.connection, source)
        row = self.connection.execute(
            "SELECT * FROM web_sources WHERE url = ?", ("https://example.org/a-study",)).fetchone()
        self.assertEqual(row["seen_count"], 2)
        self.assertEqual(row["domain"], "example.org")

    def test_a_web_page_without_a_url_is_not_recorded(self):
        self.assertIsNone(lib.record_web_source(self.connection, {"title": "no url"}))
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM web_sources").fetchone()[0], 0)


class StatsTest(TempCorpusTest):
    def test_bytes_is_bytes_not_a_page_count(self):
        self.connection.execute(
            "INSERT INTO documents (doc_id, title, authors, source_kind, local_path, sha256,"
            " pages_total, text_method, added_at) VALUES"
            " ('bk-1', 'T', 'A', 'book', ?, 'abc', 42, 'pdf_text_layer', ?)",
            (os.path.join(self.directory, "book.pdf"), lib.now()))
        self.connection.commit()
        with open(os.path.join(self.directory, "book.pdf"), "wb") as handle:
            handle.write(b"x" * 1234)
        stats = lib.stats(self.connection)
        self.assertEqual(stats["bytes"], 1234)
        self.assertNotEqual(stats["bytes"], 42,
                            "the page count must not be reported as bytes")


class AdminServiceTest(unittest.TestCase):
    """The admin API, served for real. The name-shadowing defect only
    appeared at request time, so the test makes actual requests."""

    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="corpus-admin-")
        self.original_db = lib.DB_PATH
        self.original_pdf_dir = lib.PDF_DIR
        self.db_path = os.path.join(self.directory, "corpus.sqlite")
        lib.DB_PATH = self.db_path
        lib.PDF_DIR = os.path.join(self.directory, "pdfs")
        connection = lib.connect(self.db_path)
        lib.apply_schema(connection)
        connection.execute(
            "INSERT INTO candidates (candidate_id, first_seen_at, last_seen_at, title, doi,"
            " url, source, seen_count, priority, status, reason) VALUES"
            " ('c1', ?, ?, 'New one', '10.1/a', 'https://doi.org/10.1/a', 'openalex', 1, 10, 'new', '')",
            (lib.now(), lib.now()))
        connection.execute(
            "INSERT INTO candidates (candidate_id, first_seen_at, last_seen_at, title, doi,"
            " url, source, seen_count, priority, status, reason) VALUES"
            " ('c2', ?, ?, 'Done one', '10.1/b', 'https://doi.org/10.1/b', 'openalex', 1, 10, 'ingested', '')",
            (lib.now(), lib.now()))
        connection.commit()
        connection.close()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), service.Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.2)

    def tearDown(self):
        self.server.shutdown()
        lib.DB_PATH = self.original_db
        lib.PDF_DIR = self.original_pdf_dir
        shutil.rmtree(self.directory, ignore_errors=True)

    def get(self, path):
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.port, path), timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_stats_is_served(self):
        """The defect: `with open(...) as handle:` shadowed the module's
        `handle()`, so every API GET raised UnboundLocalError."""
        payload = self.get("/api/corpus/stats")
        self.assertIn("documents", payload)

    def test_the_candidates_query_string_is_honoured(self):
        """The defect: the query string was dropped, so `?status=all` was
        ignored and the queue showed only 'new'."""
        everything = self.get("/api/corpus/candidates?status=all")["candidates"]
        self.assertEqual(len(everything), 2, "status=all returns both candidates")
        only_new = self.get("/api/corpus/candidates?status=new")["candidates"]
        self.assertEqual(len(only_new), 1)
        self.assertEqual(only_new[0]["title"], "New one")

    def test_the_limit_is_honoured(self):
        payload = self.get("/api/corpus/candidates?status=all&limit=1")
        self.assertEqual(len(payload["candidates"]), 1)

    def test_the_admin_page_is_served(self):
        with urllib.request.urlopen("http://127.0.0.1:%d/" % self.port, timeout=10) as response:
            body = response.read().decode("utf-8")
        self.assertIn("Corpus admin", body)

    def test_the_pipeline_can_write_the_learning_log(self):
        """The route the pipeline's learning hook calls."""
        payload = {
            "query": "depreciation schedule straight line",
            "subject": "accounting",
            "dimension": "analysis",
            "case_id": "case-1",
            "corpus_hits": 1,
            "live_hits": 3,
            "sources": [{"source": "openalex", "title": "Pricing in emerging markets",
                         "doi": "10.1234/emerging.1",
                         "url": "https://doi.org/10.1234/emerging.1"}],
            "web_sources": [{"url": "https://example.org/page", "title": "A page"}],
        }
        request = urllib.request.Request(
            "http://127.0.0.1:%d/api/corpus/log" % self.port,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
        self.assertIn("search_id", body)

        connection = lib.connect(self.db_path)
        try:
            row = connection.execute(
                "SELECT * FROM search_log WHERE search_id = ?", (body["search_id"],)).fetchone()
            self.assertEqual(row["query"], "depreciation schedule straight line")
            self.assertEqual(row["corpus_hits"], 1)
            self.assertEqual(row["live_hits"], 3)
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM seen_sources WHERE search_id = ?",
                (body["search_id"],)).fetchone()[0], 1)
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM web_sources").fetchone()[0], 1)
        finally:
            connection.close()


class NoDuplicationTest(TempCorpusTest):
    """The corpus must not hold the same file, or the same work, twice.

    These are the guarantees the owner asked for: an upload or an addition
    that repeats something the corpus already holds is refused, and nothing
    is written.
    """

    def setUp(self):
        super().setUp()
        self.original_pdf_dir = lib.PDF_DIR
        lib.PDF_DIR = os.path.join(self.directory, "pdfs")

    def tearDown(self):
        lib.PDF_DIR = self.original_pdf_dir
        super().tearDown()

    def minimal_pdf(self, marker=""):
        """A one-page PDF, built by hand so the tests stay stdlib-only.

        Two calls with different markers are two files with different bytes
        and the same content: another copy of the same work.
        """
        stream = "BT /F1 12 Tf 20 100 Td (Corpus test page) Tj ET"
        objects = [
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>",
            "<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
        out = "%PDF-1.4\n%% " + marker + "\n"
        offsets = []
        for number, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += "%d 0 obj\n%s\nendobj\n" % (number, body)
        start = len(out)
        out += "xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
        for offset in offsets:
            out += "%010d 00000 n \n" % offset
        out += "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            len(objects) + 1, start)
        return out.encode("latin-1")

    def book(self, title="A Book About Leadership", author="Nguyen, Tuan", year=2024):
        return {"title": title, "authors": author, "year": year, "kind": "book"}

    def count(self, table):
        return self.connection.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]

    def test_the_same_file_is_not_ingested_twice(self):
        raw = self.minimal_pdf("one copy")
        status, doc_id, message = lib.ingest_pdf(self.connection, raw, self.book())
        self.assertEqual("ingested", status)

        status, again, message = lib.ingest_pdf(self.connection, raw, self.book())
        self.assertEqual("duplicate", status)
        self.assertEqual(doc_id, again)
        self.assertIn("same file", message)
        self.assertEqual(1, self.count("documents"))
        self.assertEqual(1, self.count("pages"), "the pages must not be written twice")

    def test_another_copy_of_the_same_work_is_refused(self):
        first = self.minimal_pdf("first copy")
        second = self.minimal_pdf("second copy")
        self.assertNotEqual(lib.sha256_bytes(first), lib.sha256_bytes(second))

        self.assertEqual("ingested", lib.ingest_pdf(self.connection, first, self.book())[0])
        status, doc_id, message = lib.ingest_pdf(self.connection, second, self.book())
        self.assertEqual("duplicate", status)
        self.assertIn("same work", message)
        self.assertEqual(1, self.count("documents"))

    def test_a_different_book_is_not_refused(self):
        self.assertEqual("ingested", lib.ingest_pdf(
            self.connection, self.minimal_pdf("one"), self.book())[0])
        self.assertEqual("ingested", lib.ingest_pdf(
            self.connection, self.minimal_pdf("two"),
            self.book(title="A Book About Marketing"))[0])
        self.assertEqual(2, self.count("documents"))

    def test_a_refused_file_is_recorded_once_in_the_log(self):
        raw = self.minimal_pdf("one copy")
        lib.ingest_pdf(self.connection, raw, self.book())
        lib.ingest_pdf(self.connection, raw, self.book())
        lib.ingest_pdf(self.connection, raw, self.book())
        skipped = self.connection.execute(
            "SELECT COUNT(*) FROM ingest_log WHERE status = 'skipped'").fetchone()[0]
        self.assertEqual(1, skipped, "a refusal is recorded once, not once per attempt")
        reason = self.connection.execute(
            "SELECT reason FROM ingest_log WHERE status = 'skipped'").fetchone()["reason"]
        self.assertIn("already in the corpus", reason)

    def test_the_database_refuses_a_second_row_with_the_same_bytes(self):
        raw = self.minimal_pdf("one copy")
        lib.ingest_pdf(self.connection, raw, self.book())
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO documents (doc_id, title, authors, source_kind, local_path, sha256,"
                " text_method, added_at) VALUES"
                " ('bk-second', 'T', 'A', 'book', 'p', ?, 'pdf_text_layer', ?)",
                (lib.sha256_bytes(raw), lib.now()))

    def test_the_same_paper_seen_with_a_doi_and_with_only_a_url_is_one_candidate(self):
        first = {"title": "Leadership in Complex Disease Outbreak Management",
                 "doi": "https://doi.org/10.1000/abc", "url": "https://example.org/a",
                 "year": 2024, "source": "openalex"}
        second = {"title": "Leadership in Complex Disease Outbreak Management",
                  "url": "https://example.org/a", "year": 2024, "source": "crossref"}
        one = lib.upsert_candidate(self.connection, first)
        two = lib.upsert_candidate(self.connection, second)
        self.assertEqual(one, two)
        self.assertEqual(1, self.count("candidates"))
        row = self.connection.execute("SELECT seen_count, doi FROM candidates").fetchone()
        self.assertEqual(2, row["seen_count"])
        self.assertEqual("10.1000/abc", row["doi"], "the DOI is kept when it arrives")

    def test_a_candidate_for_a_work_the_corpus_holds_is_not_fetched_again(self):
        raw = self.minimal_pdf("one copy")
        meta = self.book(title="Leadership in Complex Disease Outbreak Management")
        meta.update({"doi": "10.1000/abc", "kind": "journal-article", "authors": "Tran, Binh"})
        lib.ingest_pdf(self.connection, raw, meta)

        self.connection.execute(
            "INSERT INTO candidates (candidate_id, first_seen_at, last_seen_at, title, doi, url,"
            " source, year, venue, seen_count, priority, status, reason)"
            " VALUES ('c1', ?, ?, ?, ?, ?, 'openalex', 2024, 'V', 1, 0, 'new', '')",
            (lib.now(), lib.now(), meta["title"], meta["doi"], "https://doi.org/" + meta["doi"]))
        self.connection.commit()
        row = self.connection.execute("SELECT * FROM candidates WHERE candidate_id = 'c1'").fetchone()

        called = []

        def refuse_to_download(url):
            called.append(url)
            raise AssertionError("a work the corpus already holds must not be downloaded")

        original = enrich._get_bytes
        enrich._get_bytes = refuse_to_download
        try:
            outcome = enrich.fetch_one(self.connection, row)
        finally:
            enrich._get_bytes = original
        self.assertEqual("duplicate", outcome)
        self.assertEqual([], called, "nothing may be downloaded for a work already held")
        after = self.connection.execute(
            "SELECT status, doc_id FROM candidates WHERE candidate_id = 'c1'").fetchone()
        self.assertEqual("ingested", after["status"])
        self.assertIsNotNone(after["doc_id"])

    def test_a_duplicate_puts_a_lost_file_back(self):
        raw = self.minimal_pdf("one copy")
        status, doc_id, message = lib.ingest_pdf(self.connection, raw, self.book(),
                                                 filename="the-book.pdf")
        self.assertEqual("ingested", status)
        path = self.connection.execute(
            "SELECT local_path FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()["local_path"]
        self.assertTrue(os.path.exists(path))
        os.remove(path)          # the document's own file is lost

        status, again, message = lib.ingest_pdf(self.connection, raw, self.book(),
                                                filename="the-book.pdf")
        self.assertEqual("duplicate", status)
        self.assertIn("put back", message)
        restored = self.connection.execute(
            "SELECT local_path FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()["local_path"]
        self.assertTrue(os.path.exists(restored), "the file must be put back")
        self.assertEqual(1, self.count("documents"), "and still only one document")

    def test_a_work_that_comes_back_in_another_year_is_its_own_document(self):
        # The re-ingest policy (Q-15) is still open. A work that comes back in a
        # later year is a separate document today. This pins that rule, so the
        # behaviour is a decision and not an accident.
        self.assertEqual("ingested", lib.ingest_pdf(
            self.connection, self.minimal_pdf("one"), self.book(year=2024))[0])
        self.assertEqual("ingested", lib.ingest_pdf(
            self.connection, self.minimal_pdf("two"), self.book(year=2025))[0])
        self.assertEqual(2, self.count("documents"))


class OwnerUploadTest(unittest.TestCase):
    """The owner's upload path: the same file twice must not become two documents."""

    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="corpus-upload-")
        self.original_db = lib.DB_PATH
        self.original_pdf_dir = lib.PDF_DIR
        lib.DB_PATH = os.path.join(self.directory, "corpus.sqlite")
        lib.PDF_DIR = os.path.join(self.directory, "pdfs")
        connection = lib.connect(lib.DB_PATH)
        lib.apply_schema(connection)
        connection.close()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), service.Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.2)

    def tearDown(self):
        self.server.shutdown()
        lib.DB_PATH = self.original_db
        lib.PDF_DIR = self.original_pdf_dir
        shutil.rmtree(self.directory, ignore_errors=True)

    def upload(self, raw, filename="the-book.pdf", title="A Book About Leadership"):
        import base64
        payload = {"filename": filename, "title": title, "authors": "Nguyen, Tuan",
                   "year": 2024, "data": base64.b64encode(raw).decode("ascii")}
        request = urllib.request.Request(
            "http://127.0.0.1:%d/api/corpus/upload" % self.port,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_uploading_the_same_file_twice_keeps_one_document(self):
        raw = NoDuplicationTest.minimal_pdf(self, "one copy")
        first = self.upload(raw)
        self.assertEqual("ingested", first["status"])

        second = self.upload(raw)
        self.assertEqual("duplicate", second["status"])
        self.assertEqual(first["doc_id"], second["doc_id"])

        connection = lib.connect(lib.DB_PATH)
        try:
            self.assertEqual(1, connection.execute(
                "SELECT COUNT(*) FROM documents").fetchone()[0])
            self.assertEqual(1, connection.execute(
                "SELECT COUNT(*) FROM uploads").fetchone()[0],
                "the same file uploaded twice is one row in the upload log")
            row = connection.execute("SELECT status FROM uploads").fetchone()
            self.assertEqual("duplicate", row["status"])
        finally:
            connection.close()

        written = os.listdir(lib.PDF_DIR) if os.path.isdir(lib.PDF_DIR) else []
        self.assertEqual(1, len(written), "no second copy of the file may be written")


class SettingsTest(TempCorpusTest):
    """The index settings must be fields Meilisearch actually accepts.

    The settings file once carried three fields that no current Meilisearch
    accepts, and the whole patch was refused with HTTP 400 - so the corpus
    could never be indexed at all. The defect was silent: the ingest looked
    successful and the index stayed empty.
    """

    #: The fields a Meilisearch settings patch accepts, as the server itself
    #: reports them ("expected one of ...").
    ACCEPTED = {
        "displayedAttributes", "searchableAttributes", "filterableAttributes",
        "sortableAttributes", "rankingRules", "stopWords", "nonSeparatorTokens",
        "separatorTokens", "dictionary", "synonyms", "distinctAttribute",
        "proximityPrecision", "typoTolerance", "faceting", "pagination",
        "embedders", "searchCutoffMs", "localizedAttributes", "facetSearch",
        "prefixSearch",
    }

    def settings(self):
        with open(lib.SETTINGS_PATH, encoding="utf-8") as handle:
            return json.load(handle)

    def test_every_settings_field_is_one_meilisearch_accepts(self):
        unknown = set(self.settings()) - self.ACCEPTED
        self.assertEqual(set(), unknown,
                         "Meilisearch refuses the whole patch when it meets a field it does "
                         "not know, so the corpus would never index")

    def test_the_primary_key_is_not_patched(self):
        self.assertNotIn("primaryKey", self.settings(),
                         "the primary key belongs to the index, not to its settings")

    def test_the_page_identifier_is_one_meilisearch_accepts(self):
        # A document identifier may hold alphanumerics, a hyphen and an
        # underscore - and nothing else. A colon is refused.
        row = {"doc_id": "ja-5ccf4308e484", "pdf_page": 1}
        identifier = "%s-%d" % (row["doc_id"], row["pdf_page"])
        self.assertTrue(identifier.replace("-", "").replace("_", "").isalnum())

    def test_an_older_server_loses_only_the_numbers_setting(self):
        calls = []

        def fake_call(method, path, payload=None, timeout=60):
            calls.append(payload)
            if payload and "disableOnNumbers" in json.dumps(payload):
                raise urllib.error.HTTPError(
                    "http://localhost", 400, "Bad Request", {},
                    io.BytesIO(json.dumps(
                        {"message": "Unknown field `disableOnNumbers` inside `.typoTolerance`"}
                    ).encode("utf-8")))
            return {"taskUid": 1}

        original = lib.meili_call
        lib.meili_call = fake_call
        try:
            applied, warning = lib.apply_settings(self.settings())
        finally:
            lib.meili_call = original
        self.assertNotIn("disableOnNumbers", applied["typoTolerance"])
        self.assertIn("v1.15", warning, "the loss must be named, not accepted quietly")
        self.assertEqual(2, len(calls))

    def test_a_refusal_for_another_reason_is_not_swallowed(self):
        def fake_call(method, path, payload=None, timeout=60):
            raise urllib.error.HTTPError(
                "http://localhost", 400, "Bad Request", {},
                io.BytesIO(json.dumps(
                    {"message": "Unknown field `maxQueryTerms`"}
                ).encode("utf-8")))

        original = lib.meili_call
        lib.meili_call = fake_call
        try:
            with self.assertRaises(urllib.error.HTTPError):
                lib.apply_settings(self.settings())
        finally:
            lib.meili_call = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
