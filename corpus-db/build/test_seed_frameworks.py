"""The framework seeder: the lens list and the storage contract.

    python corpus-db/build/test_seed_frameworks.py

No test touches the network or the real corpus: the search is injected and the
database is a throwaway file.
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

import corpus_lib as lib  # noqa: E402
import seed_frameworks  # noqa: E402


class TempCorpusTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="seed-frameworks-test-")
        self.connection = lib.connect(os.path.join(self.directory, "corpus.sqlite"))
        lib.apply_schema(self.connection)

    def tearDown(self):
        self.connection.close()
        shutil.rmtree(self.directory, ignore_errors=True)


class LensListTest(unittest.TestCase):
    def test_the_pipeline_s_own_frameworks_are_present(self):
        names = {lens["name"] for lens in seed_frameworks.load_lenses()}
        for expected in ("PESTEL", "SWOT", "Ansoff Growth Matrix", "Porter's Five Forces",
                         "Porter's Value Chain", "VRIO", "Porter's Diamond"):
            self.assertIn(expected, names)

    def test_the_main_theories_are_present_as_named_lenses(self):
        names = {lens["name"] for lens in seed_frameworks.load_lenses()}
        for expected in ("Resource-Based View", "Dynamic Capabilities Theory",
                         "Transformational leadership", "servant leadership",
                         "Stakeholder Theory", "Prospect Theory"):
            self.assertIn(expected, names)

    def test_a_document_or_a_computation_is_not_a_lens(self):
        names = {seed_frameworks._norm(lens["name"])
                 for lens in seed_frameworks.load_lenses()}
        self.assertNotIn("no framework", names)
        self.assertNotIn("break even", names)
        self.assertNotIn("business plan", names)

    def test_quantitative_methods_are_opt_in(self):
        without = {seed_frameworks._norm(lens["name"])
                   for lens in seed_frameworks.load_lenses()}
        with_methods = {seed_frameworks._norm(lens["name"])
                        for lens in seed_frameworks.load_lenses(include_methods=True)}
        self.assertNotIn("chi square", without)
        self.assertTrue(any(name.startswith("chi square") for name in with_methods))


class QueryTest(unittest.TestCase):
    def test_a_query_names_the_lens_and_its_kind(self):
        lens = {"name": "PESTEL", "kind": "framework",
                "queries": ["government policy regulation trade sanctions"]}
        queries = seed_frameworks.build_queries(lens)
        self.assertEqual(queries[0], "PESTEL framework")
        self.assertEqual(queries[1], "PESTEL government policy regulation trade sanctions")

    def test_the_kind_word_is_not_repeated(self):
        lens = {"name": "AMO Framework", "kind": "framework"}
        self.assertEqual(seed_frameworks.build_queries(lens)[0], "AMO framework")

    def test_a_lens_without_a_block_query_still_gets_a_second_query(self):
        lens = {"name": "Prospect Theory", "kind": "theory"}
        queries = seed_frameworks.build_queries(lens)
        self.assertEqual(queries[0], "Prospect theory")
        self.assertEqual(queries[1], "Prospect review")


class SeedTest(TempCorpusTest):
    def result(self, title="A study of PESTEL", doi="10.1234/pestel"):
        return {"title": title, "doi": doi, "url": "https://doi.org/" + doi,
                "year": 2020, "venue": "Journal of Strategy",
                "database": "OpenAlex", "abstract": "A relevant abstract."}

    def fake_search(self, query, databases=None, limit=5, year_from=None):
        return {"results": [self.result()], "errors": [], "skipped": []}

    def test_a_found_work_is_stored_as_a_candidate_with_its_lens(self):
        report = seed_frameworks.seed(
            self.connection, [{"name": "PESTEL", "kind": "framework", "queries": []}],
            search=self.fake_search, max_queries=1)
        rows = self.connection.execute("SELECT * FROM candidates").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["doi"], "10.1234/pestel")
        self.assertEqual(rows[0]["status"], "new")
        self.assertIn("framework seed: PESTEL", rows[0]["reason"])
        self.assertEqual(rows[0]["framework"], "PESTEL")
        self.assertEqual(report["totals"]["candidates_new"], 1)
        self.assertEqual(report["totals"]["queries"], 1)

    def test_the_seed_search_is_written_to_the_learning_log(self):
        seed_frameworks.seed(
            self.connection, [{"name": "PESTEL", "kind": "framework", "queries": []}],
            search=self.fake_search, max_queries=1)
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM search_log").fetchone()[0], 1)
        seen = self.connection.execute("SELECT * FROM seen_sources").fetchone()
        self.assertEqual(seen["source"], "OpenAlex")
        self.assertEqual(seen["used"], 0)

    def test_a_work_the_corpus_holds_is_not_queued(self):
        with mock.patch.object(lib, "find_document_for", return_value="ja-existing"):
            seed_frameworks.seed(
                self.connection, [{"name": "PESTEL", "kind": "framework", "queries": []}],
                search=self.fake_search, max_queries=1)
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM candidates").fetchone()[0], 0)

    def test_a_work_seen_in_two_queries_is_one_candidate(self):
        seed_frameworks.seed(
            self.connection,
            [{"name": "PESTEL", "kind": "framework",
              "queries": ["government policy", "economic growth"]}],
            search=self.fake_search, max_queries=2)
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM candidates").fetchone()[0], 1)

    def test_a_paywalled_work_stays_a_candidate(self):
        # Storing metadata is not the same as ingesting bytes.  A work with no
        # open full text is still saved for the owner and the next search.
        def no_pdf(query, databases=None, limit=5, year_from=None):
            return {"results": [{"title": "A paywalled study of PESTEL",
                                 "doi": "10.1234/paywalled", "year": 2021,
                                 "database": "Crossref"}],
                    "errors": [], "skipped": []}

        seed_frameworks.seed(
            self.connection, [{"name": "PESTEL", "kind": "framework", "queries": []}],
            search=no_pdf, max_queries=1)
        row = self.connection.execute("SELECT * FROM candidates").fetchone()
        self.assertEqual(row["status"], "new")
        self.assertIsNone(row["doc_id"])

    def test_an_api_failure_is_reported_not_raised(self):
        def broken(query, databases=None, limit=5, year_from=None):
            raise RuntimeError("API down")

        report = seed_frameworks.seed(
            self.connection, [{"name": "PESTEL", "kind": "framework", "queries": []}],
            search=broken, max_queries=1)
        self.assertEqual(report["totals"]["errors"], 1)
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM candidates").fetchone()[0], 0)


class FilterTest(unittest.TestCase):
    def test_a_name_fragment_selects_only_matching_lenses(self):
        lenses = seed_frameworks.load_lenses()
        selected = seed_frameworks._filter_lenses(lenses, "Porter,Ansoff")
        names = {lens["name"] for lens in selected}
        self.assertTrue(any("Porter" in name for name in names))
        self.assertTrue(any("Ansoff" in name for name in names))
        self.assertFalse(any("PESTEL" in name for name in names))


if __name__ == "__main__":
    unittest.main()
