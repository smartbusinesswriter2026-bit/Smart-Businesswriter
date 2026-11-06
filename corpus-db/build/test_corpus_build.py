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
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import corpus_lib as lib
import corpus_service as service
import enrich
import bulk_ingest


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

    def test_a_framework_seed_is_not_researched_a_second_time(self):
        for index in range(2):
            self.connection.execute(
                "INSERT INTO search_log (search_id, searched_at, query, subject, dimension,"
                " corpus_hits) VALUES (?, ?, 'PESTEL framework', 'management',"
                " 'framework_seed', 0)", ("seed%d" % index, lib.days_ago(1)))
        self.connection.commit()
        self.assertEqual(enrich.unanswered_queries(self.connection, min_times=1), [])


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

    def test_collect_accepts_a_title_only_source(self):
        # A corpus hit or a web page may carry only a title.  It is still demand
        # the corpus could not answer, so it must enter the queue.
        lib.record_search(
            self.connection, "pricing strategy", subject="marketing",
            sources=[{"source": "OpenAlex", "title": "Pricing in emerging markets"}])
        seen, added = enrich.collect(self.connection)
        self.assertEqual((seen, added), (1, 1))
        row = self.connection.execute("SELECT * FROM candidates").fetchone()
        self.assertEqual(row["title"], "Pricing in emerging markets")
        self.assertIsNone(row["doi"])

    def test_collect_does_not_queue_the_corpus_s_own_pages(self):
        lib.record_search(
            self.connection, "five forces", subject="management",
            sources=[{"source": "Proprietary corpus", "title": "Porter's Five Forces page 1"}])
        seen, added = enrich.collect(self.connection)
        self.assertEqual(seen, 1)
        self.assertEqual(added, 0, "a corpus page is held, not missing")

    def test_collect_does_not_queue_background_reading(self):
        lib.record_search(
            self.connection, "five forces", subject="management",
            sources=[{"source": "orientation web", "title": "Porter's Five Forces",
                      "url": "https://en.wikipedia.org/wiki/Porter%27s_five_forces"}])
        seen, added = enrich.collect(self.connection)
        self.assertEqual(seen, 1)
        self.assertEqual(added, 0, "orientation is not evidence and is never ingested")

    def test_a_title_only_candidate_that_cannot_be_resolved_needs_a_decision(self):
        lib.upsert_candidate(self.connection, {"title": "Porter's Five Forces page 1",
                                                "source": "openalex"})
        candidate = self.connection.execute("SELECT * FROM candidates").fetchone()
        with mock.patch.object(enrich, "work_by_title", return_value=None):
            self.assertEqual(enrich.fetch_one(self.connection, candidate), "needs_decision")
        row = self.connection.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?", (candidate["candidate_id"],)).fetchone()
        self.assertEqual(row["status"], "needs_decision")
        self.assertIsNone(row["doi"], "a title is never turned into a guessed DOI")
        self.assertIn("title only", row["reason"])

    def test_a_rate_limit_is_a_retryable_failure_not_a_rejection(self):
        lib.upsert_candidate(self.connection,
                             {"title": "Pricing in emerging markets",
                              "doi": "10.1234/emerging.1", "source": "openalex"})
        candidate = self.connection.execute("SELECT * FROM candidates").fetchone()
        error = urllib.error.HTTPError("https://api.openalex.org", 429, "Too Many Requests",
                                        {}, io.BytesIO(b""))
        with mock.patch.object(enrich, "work_by_doi", side_effect=error):
            self.assertEqual(enrich.fetch_one(self.connection, candidate), "failed")
        row = self.connection.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?", (candidate["candidate_id"],)).fetchone()
        self.assertEqual(row["status"], "failed")
        self.assertIn("HTTP 429", row["reason"])
        self.assertIn("retry", row["reason"])

    def test_fetch_retries_a_failed_candidate(self):
        lib.upsert_candidate(self.connection,
                             {"title": "Pricing in emerging markets",
                              "doi": "10.1234/emerging.1", "source": "openalex"})
        self.connection.execute("UPDATE candidates SET status = 'failed'")
        self.connection.commit()
        with mock.patch.object(enrich, "fetch_one", return_value="rejected") as fetch_one:
            enrich.fetch(self.connection)
        self.assertEqual(fetch_one.call_count, 1,
                         "a transient failure must be retried next cycle")

    def test_an_unknown_licence_waits_for_the_owner_and_the_owner_can_approve_it(self):
        lib.upsert_candidate(self.connection,
                             {"title": "Pricing in emerging markets",
                              "doi": "10.1234/emerging.1", "source": "openalex"})
        candidate = self.connection.execute("SELECT * FROM candidates").fetchone()
        work = {"id": "https://openalex.org/W1", "title": "Pricing in emerging markets",
                "doi": "https://doi.org/10.1234/emerging.1",
                "publication_year": 2020, "primary_location": {},
                "has_content": {"pdf": True},
                "best_oa_location": {"license": None}}
        with mock.patch.object(enrich, "work_by_doi", return_value=work), \
                mock.patch.object(enrich, "open_access_pdf",
                                  return_value=("https://example.org/paper.pdf", None)):
            self.assertEqual(enrich.fetch_one(self.connection, candidate), "needs_decision")
            row = self.connection.execute(
                "SELECT * FROM candidates WHERE candidate_id = ?",
                (candidate["candidate_id"],)).fetchone()
            self.assertEqual(row["status"], "needs_decision")
            self.assertIn("approve", row["reason"])

        with mock.patch.object(enrich, "work_by_doi", return_value=work), \
                mock.patch.object(enrich, "open_access_pdf",
                                  return_value=("https://example.org/paper.pdf", None)), \
                mock.patch.object(enrich, "_get_bytes", return_value=b"%PDF-1.4 fake"), \
                mock.patch.object(lib, "ingest_pdf",
                                  return_value=("ingested", "doc-1", "ingested")):
            self.assertEqual(enrich.fetch_one(self.connection, candidate, approved=True),
                             "ingested")


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


class IsbnIdentityTest(TempCorpusTest):
    """An ISBN names a book, so two scans of one book are one document.

    The title rule cannot do this: the same book scanned twice can come back
    with its subtitle typed differently, and then the two keys differ and the
    second copy is ingested. The checksum is verified, so a mistyped number
    names nothing rather than naming the wrong book.
    """

    def setUp(self):
        super().setUp()
        self._real_extract = lib.extract_pages
        # The PDF reader is a build-time package and is not installed everywhere;
        # these tests are about identity, not parsing.
        lib.extract_pages = lambda raw: [(1, "page one", "pdf_text_layer")]
        self._real_pdf_dir = lib.PDF_DIR
        lib.PDF_DIR = os.path.join(self.directory, "pdfs")

    def tearDown(self):
        lib.extract_pages = self._real_extract
        lib.PDF_DIR = self._real_pdf_dir
        super().tearDown()

    def test_an_isbn10_and_the_same_book_as_isbn13_name_one_identity(self):
        self.assertEqual(lib.norm_isbn("0132350882"), "9780132350884")
        self.assertEqual(lib.norm_isbn("978-0-13-235088-4"), "9780132350884")

    def test_an_isbn_that_fails_its_checksum_names_nothing(self):
        self.assertEqual(lib.norm_isbn("9780132350885"), "",
                         "one wrong digit is not a different book, it is no book")
        self.assertEqual(lib.norm_isbn("a page range 143-158"), "")

    def test_the_key_prefers_the_isbn_over_the_title(self):
        self.assertEqual(
            lib.work_key_for({"title": "Whatever the scanner typed",
                              "isbn": "0132350882"}),
            "isbn:9780132350884")

    def test_a_doi_still_wins_over_an_isbn(self):
        self.assertEqual(lib.work_key_for({"doi": "10.1000/ABC", "isbn": "0132350882"}),
                         "doi:10.1000/abc")

    def test_the_same_book_scanned_twice_under_different_titles_is_refused(self):
        first = lib.ingest_pdf(
            self.connection, b"%PDF-1.4 scan one",
            {"title": "Competitive Strategy", "authors": "Porter, Michael", "year": 1980,
             "kind": "book", "isbn": "0132350882"})
        second = lib.ingest_pdf(
            self.connection, b"%PDF-1.4 scan two, different bytes",
            {"title": "Competitive Strategy: Techniques for Analysing Industries",
             "authors": "Porter, Michael", "year": 1980, "kind": "book",
             "isbn": "978-0-13-235088-4"})
        self.assertEqual(first[0], "ingested")
        self.assertEqual(second[0], "duplicate")
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 1)

    def test_two_books_with_different_isbns_are_two_documents(self):
        first = lib.ingest_pdf(self.connection, b"%PDF-1.4 a",
                               {"title": "One", "isbn": "0132350882", "kind": "book"})
        second = lib.ingest_pdf(self.connection, b"%PDF-1.4 b",
                                {"title": "Two", "isbn": "9780306406157", "kind": "book"})
        self.assertEqual((first[0], second[0]), ("ingested", "ingested"))

    def test_a_row_keyed_by_title_is_rekeyed_by_its_isbn(self):
        """A row written under the old rule must not keep the weaker key."""
        self.connection.execute(
            "INSERT INTO documents (doc_id, title, authors, source_kind, local_path, sha256,"
            " text_method, licence_verified, metadata_verified, added_at, isbn, work_key)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ("bk-old", "Old Title", "Porter, Michael", "book", "", "aa", "pdf_text_layer",
             0, 0, lib.now(), "0132350882", "t:old title|porter|1980"))
        self.connection.commit()
        lib.apply_schema(self.connection)
        row = self.connection.execute(
            "SELECT work_key FROM documents WHERE doc_id = 'bk-old'").fetchone()
        self.assertEqual(row["work_key"], "isbn:9780132350884")


class BulkIngestTest(TempCorpusTest):
    """Importing a folder reads each PDF once, and never doubles the library."""

    def setUp(self):
        super().setUp()
        self.extractions = 0
        self._real_extract = lib.extract_pages

        def counting(raw):
            self.extractions += 1
            return [(1, "alpha", "pdf_text_layer"), (2, "beta", "pdf_text_layer")]

        lib.extract_pages = counting
        self._real_pdf_dir = lib.PDF_DIR
        lib.PDF_DIR = os.path.join(self.directory, "pdfs")
        self.folder = os.path.join(self.directory, "library")
        os.makedirs(self.folder)

    def tearDown(self):
        lib.extract_pages = self._real_extract
        lib.PDF_DIR = self._real_pdf_dir
        super().tearDown()

    def drop(self, name):
        with open(os.path.join(self.folder, name), "wb") as handle:
            handle.write(b"%PDF-1.4 " + name.encode("utf-8"))

    def test_the_name_gives_the_year_and_a_readable_title(self):
        meta = bulk_ingest.parse_name(
            "A.-Bonini_2024_the-relationship-between-leadership-and-performance.pdf")
        self.assertEqual(meta["year"], 2024)
        self.assertEqual(meta["authors"], "Bonini", "initials are dropped, not guessed")
        self.assertTrue(meta["title"].startswith("The relationship between leadership"))

    def test_no_year_in_the_name_stays_empty(self):
        self.assertIsNone(bulk_ingest.parse_name("some-undated-report.pdf")["year"])

    def test_an_isbn_in_the_name_is_used_only_when_it_is_a_real_one(self):
        found = bulk_ingest.parse_name("Porter_1980_competitive-strategy_0132350882.pdf")
        self.assertEqual(found["isbn"], "9780132350884")
        self.assertIsNone(bulk_ingest.parse_name("Porter_1980_pages-143-158.pdf")["isbn"])

    def test_each_pdf_is_read_once(self):
        self.drop("Smith_2021_first-book.pdf")
        bulk_ingest.import_folder(self.connection, self.folder, subject="management")
        self.assertEqual(self.extractions, 1,
                         "pages already read must not be read a second time")

    def test_running_it_twice_imports_nothing_the_second_time(self):
        self.drop("Smith_2021_first-book.pdf")
        first = bulk_ingest.import_folder(self.connection, self.folder, subject="management")
        second = bulk_ingest.import_folder(self.connection, self.folder, subject="management")
        self.assertEqual(bulk_ingest.summarise(first), {"ingested": 1})
        self.assertEqual(bulk_ingest.summarise(second), {"duplicate": 1})
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 1)

    def test_metadata_from_a_file_name_is_recorded_as_unverified(self):
        self.drop("Smith_2021_first-book.pdf")
        bulk_ingest.import_folder(self.connection, self.folder, subject="management")
        row = self.connection.execute("SELECT * FROM documents").fetchone()
        self.assertEqual(row["metadata_source"], "filename")
        self.assertEqual(row["metadata_verified"], 0)

    def test_a_dry_run_writes_nothing(self):
        self.drop("Smith_2021_first-book.pdf")
        rows = bulk_ingest.import_folder(self.connection, self.folder, subject="management",
                                         dry_run=True)
        self.assertEqual(rows[0]["status"], "would_ingest")
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 0)

    def test_a_sample_is_scaled_up_and_labelled_as_one(self):
        real = bulk_ingest.probe
        bulk_ingest.probe = lambda path: (10, 0)
        try:
            for name in ("a_2020_one.pdf", "b_2020_two.pdf",
                         "c_2020_three.pdf", "d_2020_four.pdf"):
                self.drop(name)
            result = bulk_ingest.estimate(self.folder, sample=2)
        finally:
            bulk_ingest.probe = real
        self.assertEqual(result["files"], 4)
        self.assertEqual(result["measured"], 2)
        self.assertTrue(result["sampled"], "a scaled answer must say it was scaled")
        self.assertEqual(result["text_pages"], 40, "2 files x 10 pages, scaled to 4 files")

    def test_the_pages_are_pushed_to_search_once_at_the_end(self):
        """Without this the documents exist and nothing can find them."""
        self.drop("Smith_2021_first-book.pdf")
        self.drop("Jones_2020_second-book.pdf")
        calls = []
        real = lib.index_pages
        lib.index_pages = lambda connection, **kw: calls.append(1) or 0
        try:
            bulk_ingest.import_folder(self.connection, self.folder, subject="management")
            self.assertEqual(calls, [], "importing alone must not index")
            bulk_ingest.import_folder(self.connection, self.folder, subject="management",
                                      index=True)
        finally:
            lib.index_pages = real
        self.assertEqual(len(calls), 1,
                         "the index is rebuilt once for the run, not once per file")

    def test_a_journal_article_is_not_recorded_as_a_book(self):
        """A book and an article are shaped differently in a citation.

        The owner's exported names carry the DOI with its '/' mangled to '-',
        because a file name cannot contain '/'. That still proves it is an
        article; it does not license storing the mangled form as the DOI.
        """
        kind, doi, where = bulk_ingest.resolve_kind(
            "Moneta_2026_industry-structure_10.2139-ssrn.7556958.pdf", None, "auto")
        self.assertEqual(kind, "journal-article")
        self.assertIsNone(doi, "a repaired identifier is not the identifier")
        self.assertEqual(where, "filename-hint")

    def test_a_doi_written_properly_in_the_name_is_stored(self):
        """A name string can contain '/', so this is the clean case."""
        kind, doi, where = bulk_ingest.resolve_kind(
            "Paper_2026_some-title_10.1000/abc.1.pdf", None, "auto")
        self.assertEqual((kind, doi, where), ("journal-article", "10.1000/abc.1", "filename"))

    def test_a_doi_printed_on_the_first_page_decides_it_and_is_stored(self):
        kind, doi, where = bulk_ingest.resolve_kind(
            "Some Article.pdf",
            [(1, "Journal of Strategy 12(3) https://doi.org/10.1000/XYZ.1 body text", "x")],
            "auto")
        self.assertEqual(kind, "journal-article")
        self.assertEqual(doi, "10.1000/xyz.1")
        self.assertEqual(where, "page-text")

    def test_a_document_with_no_doi_anywhere_stays_a_book(self):
        kind, doi, _where = bulk_ingest.resolve_kind(
            "Porter_1980_competitive-strategy.pdf", [(1, "no identifier here", "x")], "auto")
        self.assertEqual((kind, doi), ("book", None))

    def test_an_explicit_kind_is_never_overridden(self):
        kind, _doi, _where = bulk_ingest.resolve_kind(
            "Something_10.1000-abc.pdf", None, "book")
        self.assertEqual(kind, "book", "what the caller asked for wins")

    def test_a_doi_carrying_file_is_stored_as_an_article(self):
        self.drop("Paper_2026_some-title_10.1000-abc.1.pdf")
        bulk_ingest.import_folder(self.connection, self.folder, subject="management")
        row = self.connection.execute("SELECT * FROM documents").fetchone()
        self.assertEqual(row["source_kind"], "journal-article")
        self.assertTrue(row["doc_id"].startswith("ja-"),
                        "the id prefix follows the kind, so a book id would give it away")
        self.assertIsNone(row["doi"], "the mangled name form is not stored as the DOI")


class SubjectHintTest(unittest.TestCase):
    """The subject is a hint, but it must not be a misleading one.

    These are real titles from the owner's library that were all filed under
    'research', because that shelf owned the word 'analysis'.
    """

    def test_a_swot_paper_is_management(self):
        self.assertEqual(lib.classify_subject(
            "A SWOT analysis of ChatGPT Implications for educational practice and research"),
            "management")

    def test_a_porter_paper_is_management(self):
        self.assertEqual(lib.classify_subject(
            "Porter s five forces and competitive advantage a study on banana chips msmes in"),
            "management")
        self.assertEqual(lib.classify_subject(
            "Porter s five forces analysis of the organic farming in laguna province"),
            "management")

    def test_a_methodology_paper_is_still_research(self):
        self.assertEqual(lib.classify_subject(
            "A systematic review of research design in management studies"), "research")


if __name__ == "__main__":
    unittest.main(verbosity=2)
