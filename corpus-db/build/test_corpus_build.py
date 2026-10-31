"""The corpus build tools: the contracts that must not break.

    python corpus-db/build/test_corpus_build.py

Stdlib only, and no test may touch the real corpus database or the network:
every test builds its own throwaway SQLite file in a temporary directory.

Four defects are pinned here. Each was found by running the code, not by
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
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
