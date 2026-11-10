"""The eval runner: the manifest, the scope split, the trend and the
regression line (product layer, standard library only).

The runner writes to `state/eval_runs/`.  These tests point that at a
temporary directory so a test run never touches the real state.
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")

from bp.product import eval_runner  # noqa: E402


class EvalRunnerTestCase(unittest.TestCase):
    """A test case with an isolated state directory."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="eval-runner-")
        self._saved_env = dict(os.environ)
        os.environ["BP_STATE_DIR"] = os.path.join(self._tmp, "state")
        os.environ["BP_OPS_LOG"] = os.path.join(self._tmp, "ops_log")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved_env)
        shutil.rmtree(self._tmp, ignore_errors=True)


class ManifestTest(EvalRunnerTestCase):
    def test_a_manifest_round_trips(self):
        manifest = eval_runner.new_manifest("direction1")
        eval_runner.save_manifest(manifest["run_id"], manifest)
        loaded = eval_runner.load_manifest(manifest["run_id"])
        self.assertEqual(loaded["run_id"], manifest["run_id"])
        self.assertEqual(loaded["direction"], "direction1")
        self.assertEqual(loaded["format"], "bp-eval-run/1")

    def test_the_state_directory_is_created_on_demand(self):
        manifest = eval_runner.new_manifest("direction1")
        path = eval_runner.save_manifest(manifest["run_id"], manifest)
        self.assertTrue(os.path.isfile(path))

    def test_an_unknown_direction_is_refused_with_a_reason(self):
        with self.assertRaises(ValueError) as caught:
            eval_runner.new_manifest("direction9")
        self.assertIn("direction9", str(caught.exception))
        self.assertIn("direction1", str(caught.exception))

    def test_an_interrupted_run_survives_on_disk(self):
        """A run that was killed mid-flight still says what it had reached."""
        manifest = eval_runner.new_manifest("direction1")
        manifest["cases"] = [{"case_id": "a/b/001", "status": "pass", "scope": "pass"}]
        manifest["counts"] = eval_runner.count(manifest["cases"])
        eval_runner.save_manifest(manifest["run_id"], manifest)
        loaded = eval_runner.load_manifest(manifest["run_id"])
        self.assertEqual(loaded["status"], "running")
        self.assertEqual(loaded["finished_at"], "")
        self.assertEqual(len(loaded["cases"]), 1)


class RunIdTest(EvalRunnerTestCase):
    """A run id names a folder under the state directory, and nothing else."""

    def test_a_run_id_that_walks_out_of_the_state_is_refused(self):
        for bad in ("../escape", "..\\escape", "a/b", "a\\b", "state/../../x"):
            with self.assertRaises(ValueError):
                eval_runner.save_manifest(bad, eval_runner.new_manifest("direction1"))

    def test_a_run_id_with_a_separator_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            eval_runner.save_manifest("run/../../etc", eval_runner.new_manifest("direction1"))
        self.assertIn("letters", str(caught.exception))

    def test_an_ordinary_run_id_is_accepted(self):
        manifest = eval_runner.new_manifest("direction1")
        path = eval_runner.save_manifest(manifest["run_id"], manifest)
        self.assertTrue(os.path.isfile(path))


class ScopeTest(EvalRunnerTestCase):
    def test_the_scopes_are_read_from_the_runner_verdict(self):
        self.assertEqual(eval_runner.scope_of("pass"), "pass")
        self.assertEqual(eval_runner.scope_of("fail"), "fail")
        self.assertEqual(eval_runner.scope_of("invalid"), "invalid")
        self.assertEqual(eval_runner.scope_of("error"), "error")

    def test_a_missing_case_is_an_error_not_a_failure(self):
        self.assertEqual(eval_runner.scope_of("missing"), "error")
        self.assertEqual(eval_runner.scope_of(""), "error")

    def test_an_invalid_case_never_counts_as_a_pipeline_failure(self):
        """The case's own figures are not the pipeline's defect."""
        counts = eval_runner.count([
            {"status": "pass"}, {"status": "pass"}, {"status": "fail"},
            {"status": "invalid"}, {"status": "invalid"}, {"status": "error"},
        ])
        self.assertEqual(counts["pass"], 2)
        self.assertEqual(counts["fail"], 1)
        self.assertEqual(counts["invalid"], 2)
        self.assertEqual(counts["error"], 1)
        self.assertEqual(counts["total"], 6)

    def test_the_runner_counter_is_not_copied_into_the_failure_count(self):
        """`case_runner` counts an invalid case in its own `failed` number.

        The eval must not inherit that: an invalid fixture would otherwise
        read as a pipeline defect and blow the budget.
        """
        rows = [{"status": "pass"}, {"status": "invalid"}]
        runner_failed = len([r for r in rows if r["status"] != "pass"])
        counts = eval_runner.count(rows)
        self.assertEqual(runner_failed, 1)
        self.assertEqual(counts["fail"], 0)
        self.assertEqual(counts["invalid"], 1)


class TrendTest(EvalRunnerTestCase):
    def _store(self, run_id, direction, rows, created):
        manifest = eval_runner.new_manifest(direction, run_id=run_id)
        manifest["created_at"] = created
        manifest["cases"] = rows
        manifest["counts"] = eval_runner.count(rows)
        eval_runner.save_manifest(run_id, manifest)
        return manifest

    def test_the_first_run_has_no_trend_and_says_so(self):
        manifest = self._store("run1", "direction1", [{"case_id": "a", "status": "fail"}],
                               "2026-01-01T00:00:00+00:00")
        self.assertEqual(eval_runner.regressions(manifest["run_id"]), [])

    def test_a_case_that_passed_and_now_fails_is_a_regression(self):
        self._store("run1", "direction1", [{"case_id": "a/001", "status": "pass"}],
                    "2026-01-01T00:00:00+00:00")
        second = self._store("run2", "direction1",
                             [{"case_id": "a/001", "status": "fail", "error": "broken"}],
                             "2026-01-02T00:00:00+00:00")
        found = eval_runner.regressions(second["run_id"])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["case_id"], "a/001")
        self.assertTrue(found[0]["blocker"])

    def test_an_invalid_case_that_became_a_pass_is_not_a_regression(self):
        self._store("run1", "direction1", [{"case_id": "a/001", "status": "invalid"}],
                    "2026-01-01T00:00:00+00:00")
        second = self._store("run2", "direction1", [{"case_id": "a/001", "status": "pass"}],
                             "2026-01-02T00:00:00+00:00")
        self.assertEqual(eval_runner.regressions(second["run_id"]), [])

    def test_the_trend_lists_the_counts_of_recent_runs(self):
        self._store("run1", "direction1", [{"case_id": "a", "status": "pass"}],
                    "2026-01-01T00:00:00+00:00")
        self._store("run2", "direction1", [{"case_id": "a", "status": "fail"}],
                    "2026-01-02T00:00:00+00:00")
        rows = eval_runner.trend(direction="direction1")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["run_id"], "run2")
        self.assertEqual(rows[0]["counts"]["fail"], 1)

    def test_a_run_of_another_direction_is_not_the_previous_run(self):
        self._store("run1", "direction2", [{"case_id": "a/001", "status": "pass"}],
                    "2026-01-01T00:00:00+00:00")
        second = self._store("run2", "direction1",
                             [{"case_id": "a/001", "status": "fail"}],
                             "2026-01-02T00:00:00+00:00")
        self.assertEqual(eval_runner.regressions(second["run_id"]), [])


class DirectionOneTest(EvalRunnerTestCase):
    """Direction 1 replays the real stored cases through the real paper path."""

    def test_one_real_case_is_replayed_and_counted(self):
        from bp.product import case_store
        cases = case_store.load_cases(subject="accounting", tile="abc")
        self.assertTrue(cases, "the accounting/abc cases are missing")
        manifest = eval_runner.run_direction1(case_ids=[cases[0].get("id")], log=False)
        self.assertEqual(manifest["status"], "done")
        self.assertEqual(manifest["counts"]["total"], 1)
        self.assertIn(manifest["counts"]["pass"], (0, 1))
        self.assertEqual(manifest["cost"]["model_calls"], 0)
        self.assertTrue(manifest["finished_at"])
        stored = eval_runner.load_manifest(manifest["run_id"])
        self.assertEqual(len(stored["cases"]), 1)

    def test_a_case_that_does_not_exist_is_an_error_not_a_failure(self):
        manifest = eval_runner.run_direction1(case_ids=["nope/nope/999"], log=False)
        self.assertEqual(manifest["counts"]["error"], 1)
        self.assertEqual(manifest["counts"]["fail"], 0)


class DirectionTwoTest(EvalRunnerTestCase):
    """Direction 2 builds the tile's own paper and scores it by code."""

    def test_the_default_sample_is_one_tile_per_subject(self):
        rows = eval_runner.select_tiles()
        subjects = [row["subject"] for row in rows]
        self.assertTrue(rows)
        self.assertEqual(len(subjects), len(set(subjects)))

    def test_the_budget_knob_covers_every_tile_when_asked(self):
        rows = eval_runner.select_tiles("all")
        self.assertGreater(len(rows), 100)
        self.assertEqual(len(rows), len(eval_runner._tile_rows()))

    def test_a_numeric_budget_takes_that_many_tiles(self):
        rows = eval_runner.select_tiles(3)
        self.assertEqual(len(rows), 3)

    def test_a_zero_budget_is_refused_rather_than_running_nothing(self):
        with self.assertRaises(ValueError) as caught:
            eval_runner.select_tiles(0)
        self.assertIn("greater than zero", str(caught.exception))

    def test_a_nonsense_budget_is_refused_with_a_reason(self):
        with self.assertRaises(ValueError):
            eval_runner.select_tiles("many")

    def test_one_real_tile_is_built_and_scored(self):
        manifest = eval_runner.run_direction2(tiles=["abc"], use_rag=False)
        self.assertEqual(manifest["status"], "done")
        self.assertEqual(manifest["counts"]["total"], 1)
        self.assertEqual(manifest["cost"]["model_calls"], 0)
        row = manifest["cases"][0]
        self.assertIn("scope", row)
        self.assertEqual(row["scope"], "pass")


class ExplainerTest(EvalRunnerTestCase):
    def test_the_run_writes_an_explainer_document(self):
        manifest = eval_runner.new_manifest("direction1")
        manifest["counts"] = eval_runner.count([{"status": "pass"}, {"status": "fail"}])
        manifest["cases"] = [{"case_id": "a/001", "status": "fail", "scope": "fail",
                              "error": "the paper does not show any of the computed values"}]
        path = eval_runner.write_explainer(manifest)
        self.assertTrue(path.endswith("explainer.docx"))
        self.assertTrue(os.path.isfile(path))
        with open(path, "rb") as handle:
            self.assertTrue(handle.read(2) == b"PK")

    def test_the_explainer_names_the_budget_and_the_failures(self):
        manifest = eval_runner.new_manifest("direction1")
        manifest["counts"] = eval_runner.count([{"status": "fail"}])
        manifest["cases"] = [{"case_id": "a/001", "status": "fail", "scope": "fail",
                              "error": "broken"}]
        sections = eval_runner.explainer_sections(manifest)
        flat = " ".join(line for _heading, lines in sections for line in lines)
        self.assertIn("budget is 2", flat)
        self.assertIn("a/001", flat)


class SummaryTest(EvalRunnerTestCase):
    def test_the_summary_reports_the_budget_and_the_regressions(self):
        manifest = eval_runner.new_manifest("direction1")
        manifest["counts"] = eval_runner.count([
            {"status": "pass"}, {"status": "fail"}, {"status": "invalid"}])
        manifest["regressions"] = [{"case_id": "a/001", "blocker": True}]
        summary = eval_runner.summarise(manifest)
        self.assertEqual(summary["pass"], 1)
        self.assertEqual(summary["fail"], 1)
        self.assertEqual(summary["invalid"], 1)
        self.assertTrue(summary["within_budget"])
        self.assertEqual(summary["regressions"], 1)

    def test_more_failures_than_the_budget_is_over_budget(self):
        manifest = eval_runner.new_manifest("direction1")
        manifest["counts"] = eval_runner.count([{"status": "fail"}] * 3)
        self.assertFalse(eval_runner.summarise(manifest)["within_budget"])


class CorpusStateTest(EvalRunnerTestCase):
    def test_a_down_corpus_is_reported_as_down(self):
        """The corpus adapter fails open, so the eval asks the index itself."""
        from bp.product import sources
        original = sources.CORPUS_MEILI_URL
        sources.CORPUS_MEILI_URL = "http://127.0.0.1:1"   # nothing listens here
        try:
            self.assertFalse(eval_runner.corpus_available(timeout=0.5, refresh=True))
        finally:
            sources.CORPUS_MEILI_URL = original
            eval_runner.corpus_available(refresh=True)

    def test_the_environment_records_the_corpus_state(self):
        env = eval_runner.environment()
        self.assertIn("corpus_available", env)
        self.assertIn("build", env)


if __name__ == "__main__":
    unittest.main()
