"""Health: the checks, the verdicts and the overall bit (product layer).

Every check is called with a prepared signal, so a test never needs a server,
a model, or a network.
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")

from bp.product import health as health_mod  # noqa: E402


class HealthTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="health-test-")
        self._saved_env = dict(os.environ)
        os.environ["BP_STATE_DIR"] = os.path.join(self._tmp, "state")
        os.environ["BP_OPS_LOG"] = os.path.join(self._tmp, "ops_log")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved_env)
        shutil.rmtree(self._tmp, ignore_errors=True)


class CaseStoreTest(HealthTestCase):
    def test_a_readable_store_is_ok(self):
        row = health_mod.check_case_store({"total": 915, "by_subject": [{"tiles": 246}]})
        self.assertTrue(row["ok"])
        self.assertEqual(row["cases"], 915)

    def test_a_store_with_no_count_is_degraded(self):
        row = health_mod.check_case_store({"total": None})
        self.assertFalse(row["ok"])
        self.assertEqual(row["severity"], "required")

    def test_an_empty_store_is_degraded(self):
        row = health_mod.check_case_store({"total": 0})
        self.assertFalse(row["ok"])
        self.assertIn("no cases", row["reason"])


class PassRateTest(HealthTestCase):
    def test_an_invalid_fixture_is_never_a_pipeline_failure(self):
        """The case's own figures are the case's problem."""
        row = health_mod.check_case_pass_rate([
            {"case_id": "accounting/ratios/002", "error": "the case's own figures do not balance: assets 15.0 != 30.0"},
        ])
        self.assertTrue(row["ok"])
        self.assertEqual(row["failures"], 0)
        self.assertEqual(row["invalid"], 1)

    def test_a_pipeline_failure_is_counted(self):
        row = health_mod.check_case_pass_rate([
            {"case_id": "accounting/abc/001", "error": "the paper does not show any of the computed values"},
        ])
        self.assertEqual(row["failures"], 1)
        self.assertTrue(row["ok"])          # one is inside the budget

    def test_over_the_budget_is_degraded(self):
        errors = [{"case_id": "a/%03d" % n, "error": "the paper does not show any of the computed values"}
                  for n in range(3)]
        row = health_mod.check_case_pass_rate(errors)
        self.assertFalse(row["ok"])
        self.assertEqual(row["severity"], "required")
        self.assertEqual(row["failures"], 3)

    def test_an_error_without_a_case_is_not_a_case_failure(self):
        row = health_mod.check_case_pass_rate([
            {"error": "the paper does not show any of the computed values"},
        ])
        self.assertEqual(row["failures"], 0)


class RegressionTest(HealthTestCase):
    def test_a_regression_is_degraded(self):
        row = health_mod.check_regressions("run1", [{"case_id": "a/001"}])
        self.assertFalse(row["ok"])
        self.assertIn("a/001", row["regressions"])

    def test_no_regression_is_ok(self):
        row = health_mod.check_regressions("run1", [])
        self.assertTrue(row["ok"])


class CorpusTest(HealthTestCase):
    def test_a_down_corpus_degrades_the_pipeline(self):
        """The corpus adapter fails open, so a down index must be named."""
        row = health_mod.check_corpus(lambda: False)
        self.assertFalse(row["ok"])
        self.assertEqual(row["severity"], "required")
        self.assertIn("not reachable", row["reason"])

    def test_an_up_corpus_is_ok(self):
        row = health_mod.check_corpus(lambda: True)
        self.assertTrue(row["ok"])


class RepairLoopTest(HealthTestCase):
    LEDGER = {"summary": {"unfixed": 2, "recurring": 0, "fixed": 1, "causes": 3, "fixed_pct": 33.3},
              "causes": []}

    def test_an_idle_loop_with_an_open_queue_is_degraded(self):
        row = health_mod.check_repair_loop({"running": False}, self.LEDGER,
                                           [{"key": "loop.repair", "enabled": True}])
        self.assertFalse(row["ok"])
        self.assertEqual(row["severity"], "required")

    def test_a_switched_off_loop_is_a_reason_not_a_failure(self):
        row = health_mod.check_repair_loop({"running": False}, self.LEDGER,
                                           [{"key": "loop.repair", "enabled": False}])
        self.assertTrue(row["ok"])
        self.assertEqual(row["severity"], "advisory")

    def test_a_running_loop_is_ok(self):
        row = health_mod.check_repair_loop({"running": True}, self.LEDGER,
                                           [{"key": "loop.repair", "enabled": True}])
        self.assertTrue(row["ok"])

    def test_nothing_to_do_is_ok(self):
        ledger = {"summary": {"unfixed": 0, "recurring": 0, "fixed": 1, "causes": 1}, "causes": []}
        row = health_mod.check_repair_loop({"running": False}, ledger,
                                           [{"key": "loop.repair", "enabled": True}])
        self.assertTrue(row["ok"])


class CauseTest(HealthTestCase):
    def test_a_recurring_cause_is_degraded(self):
        ledger = {"summary": {"recurring": 1, "fixed": 2, "causes": 3, "fixed_pct": 66.7},
                  "causes": [{"cause": "pipeline.parser_shape", "status": "recurring"}]}
        row = health_mod.check_causes(ledger)
        self.assertFalse(row["ok"])
        self.assertIn("pipeline.parser_shape", row["causes"])

    def test_no_recurring_cause_is_ok(self):
        ledger = {"summary": {"recurring": 0, "fixed": 2, "causes": 3, "fixed_pct": 66.7}, "causes": []}
        row = health_mod.check_causes(ledger)
        self.assertTrue(row["ok"])


class BaselineTest(HealthTestCase):
    def _manifest(self, **over):
        manifest = {"run_id": "run1", "direction": "direction1",
                    "counts": {"pass": 906, "fail": 0, "invalid": 9, "error": 0, "total": 915},
                    "regressions": [], "finished_at": "2026-11-10T05:00:00+00:00"}
        manifest.update(over)
        return manifest

    def test_no_run_at_all_is_degraded(self):
        row = health_mod.check_eval_baseline(None, "2026-11-10")
        self.assertFalse(row["ok"])
        self.assertEqual(row["severity"], "required")

    def test_a_green_run_is_ok(self):
        row = health_mod.check_eval_baseline(self._manifest(), "2026-11-10")
        self.assertTrue(row["ok"])

    def test_a_run_over_the_budget_is_degraded(self):
        manifest = self._manifest(counts={"pass": 900, "fail": 5, "invalid": 9, "error": 0, "total": 915})
        row = health_mod.check_eval_baseline(manifest, "2026-11-10")
        self.assertFalse(row["ok"])

    def test_a_run_with_a_regression_is_degraded(self):
        row = health_mod.check_eval_baseline(self._manifest(regressions=[{"case_id": "a/001"}]),
                                             "2026-11-10")
        self.assertFalse(row["ok"])

    def test_a_run_older_than_the_build_is_stale(self):
        row = health_mod.check_eval_baseline(self._manifest(finished_at="2026-11-01T00:00:00+00:00"),
                                             "2026-11-10")
        self.assertFalse(row["ok"])
        self.assertIn("predates", row["reason"])


class SuiteTest(HealthTestCase):
    def test_no_suite_has_run_is_not_measured_not_broken(self):
        row = health_mod.check_test_suite([])
        self.assertFalse(row["ok"])
        self.assertEqual(row["severity"], "advisory")

    def test_a_failed_suite_degrades_the_pipeline(self):
        row = health_mod.check_test_suite([
            {"suite": "computations", "passed": 10, "failed": 1, "total": 11, "ts": "2026-11-10T05:00:00"},
        ])
        self.assertFalse(row["ok"])
        self.assertEqual(row["severity"], "required")
        self.assertIn("computations", row["failing"])

    def test_the_newest_result_of_a_suite_counts(self):
        row = health_mod.check_test_suite([
            {"suite": "computations", "passed": 10, "failed": 1, "total": 11,
             "ts": "2026-11-10T05:00:00+00:00"},
            {"suite": "computations", "passed": 11, "failed": 0, "total": 11,
             "ts": "2026-11-10T06:00:00+00:00"},
        ])
        self.assertTrue(row["ok"])


class RelevanceTest(HealthTestCase):
    def test_a_sweep_that_never_ran_is_not_measured(self):
        row = health_mod.check_relevance(None)
        self.assertFalse(row["ok"])
        self.assertEqual(row["severity"], "advisory")

    def test_a_sweep_whose_controls_failed_is_degraded(self):
        run = {"run_id": "r1", "status": "completed",
               "controls": {"held": 5, "total": 12, "min_held": 0.75}}
        row = health_mod.check_relevance(run)
        self.assertFalse(row["ok"])
        self.assertEqual(row["severity"], "required")

    def test_a_sweep_whose_controls_held_is_ok(self):
        run = {"run_id": "r1", "status": "completed",
               "controls": {"held": 10, "total": 12, "min_held": 0.75}}
        row = health_mod.check_relevance(run)
        self.assertTrue(row["ok"])

    def test_the_newest_run_is_the_one_that_counts(self):
        """The store is append-only; a capped read returns the oldest rows."""
        runs = [
            {"run_id": "old", "status": "completed",
             "controls": {"held": 10, "total": 12, "min_held": 0.75}},
            {"run_id": "new", "status": "completed",
             "controls": {"held": 5, "total": 12, "min_held": 0.75}},
        ]
        row = health_mod.check_relevance(runs=runs)
        self.assertEqual(row["run_id"], "new")
        self.assertFalse(row["ok"])


class OverallTest(HealthTestCase):
    def _sources(self, **over):
        sources = {
            "extra": {"model_assistance": True, "sandbox": "on"},
            "case_store": {"total": 915, "by_subject": []},
            "errors": [],
            "regressions": [],
            "corpus_probe": lambda: True,
            "repair_status": {"running": True},
            "ledger": {"summary": {"unfixed": 0, "recurring": 0, "fixed": 3, "causes": 3,
                                   "fixed_pct": 100.0}, "causes": []},
            "switches": [{"key": "loop.repair", "enabled": True, "running": True}],
            "manifest": {"run_id": "run1", "direction": "direction1",
                         "counts": {"pass": 906, "fail": 0, "invalid": 9, "error": 0, "total": 915},
                         "regressions": [], "finished_at": "2026-11-10T05:00:00+00:00"},
            "tree_date": "2026-11-10",
            "test_results": [{"suite": "computations", "passed": 11, "failed": 0, "total": 11}],
            "relevance_run": {"run_id": "r1", "status": "completed",
                              "controls": {"held": 10, "total": 12, "min_held": 0.75}},
        }
        sources.update(over)
        return sources

    def test_a_healthy_pipeline_is_ok(self):
        report = health_mod.health(sources=self._sources())
        self.assertTrue(report["overall"])
        self.assertEqual(report["failing"], [])

    def test_every_check_is_present(self):
        report = health_mod.health(sources=self._sources())
        names = [row["name"] for row in report["checks"]]
        self.assertEqual(sorted(names), sorted(health_mod.CHECKS))

    def test_a_down_corpus_degrades_the_overall_bit(self):
        report = health_mod.health(sources=self._sources(corpus_probe=lambda: False))
        self.assertFalse(report["overall"])
        self.assertIn("corpus", report["failing"])

    def test_a_recurring_cause_degrades_the_overall_bit(self):
        ledger = {"summary": {"unfixed": 0, "recurring": 1, "fixed": 2, "causes": 3},
                  "causes": [{"cause": "pipeline.parser_shape", "status": "recurring"}]}
        report = health_mod.health(sources=self._sources(ledger=ledger))
        self.assertFalse(report["overall"])
        self.assertIn("causes", report["failing"])

    def test_an_advisory_signal_does_not_degrade_the_overall_bit(self):
        """The model being off is a fact, not a fault."""
        report = health_mod.health(sources=self._sources(
            extra={"model_assistance": False}, test_results=[]))
        self.assertTrue(report["overall"])
        self.assertIn("test_suite", report["advisory"])


    def test_a_stale_suite_degrades_the_overall_bit(self):
        """The suites ran before the code changed, so they say nothing about it."""
        sources = self._sources()
        sources["test_results"] = [{"suite": "computations", "passed": 11, "failed": 0,
                                    "total": 11, "ts": "2026-11-01T05:00:00+00:00"}]
        report = health_mod.health(sources=sources)
        self.assertFalse(report["overall"])
        self.assertIn("test_suite", report["failing"])

    def test_a_suite_that_never_ran_does_not_degrade_the_overall_bit(self):
        sources = self._sources()
        sources["test_results"] = []
        report = health_mod.health(sources=sources)
        self.assertTrue(report["overall"])
        self.assertIn("test_suite", report["advisory"])

class FreshnessTest(HealthTestCase):
    def test_a_suite_that_ran_before_the_code_changed_is_stale(self):
        """A measurement from before the change says nothing about the change."""
        row = health_mod.check_test_suite(
            [{"suite": "computations", "passed": 11, "failed": 0, "total": 11,
              "ts": "2026-11-01T05:00:00+00:00"}], "2026-11-10")
        self.assertFalse(row["ok"])
        self.assertIn("predates", row["reason"])

    def test_a_suite_that_ran_after_the_change_is_fresh(self):
        row = health_mod.check_test_suite(
            [{"suite": "computations", "passed": 11, "failed": 0, "total": 11,
              "ts": "2026-11-10T05:00:00+00:00"}], "2026-11-10")
        self.assertTrue(row["ok"])

    def test_a_signal_carries_when_it_was_taken_and_how_old_it_is(self):
        row = health_mod.check_test_suite(
            [{"suite": "computations", "passed": 11, "failed": 0, "total": 11,
              "ts": "2026-11-10T05:00:00+00:00"}], "2026-11-10")
        self.assertEqual(row["signal_checked_at"], "2026-11-10T05:00:00+00:00")
        self.assertTrue(row["age"])

    def test_the_age_is_in_words(self):
        self.assertIn("ago", health_mod._age_of("2026-11-10T05:00:00+00:00"))
        self.assertEqual(health_mod._age_of(""), "")
        self.assertEqual(health_mod._age_of("not a date"), "")

    def test_a_missing_signal_is_never_checked_not_ok(self):
        row = health_mod.check_test_suite([])
        self.assertFalse(row["ok"])
        self.assertEqual(row["severity"], "advisory")
        self.assertIn("no suite has been run", row["reason"])


class BareProcessTest(HealthTestCase):
    """H4: the check runs without a server, a model, or a network."""

    def test_health_runs_with_no_server_and_no_prepared_signals(self):
        report = health_mod.health()
        self.assertIn("overall", report)
        self.assertTrue(report["checks"])
        for row in report["checks"]:
            self.assertIn("name", row)
            self.assertIn("ok", row)
            self.assertIn("reason", row)
            self.assertIn("checked_at", row)

    def test_the_bare_report_names_the_checks_it_could_not_run(self):
        report = health_mod.health()
        for row in report["checks"]:
            if not row["ok"]:
                self.assertTrue(row["reason"], "%s failed without a reason" % row["name"])

    def test_the_report_is_json_serialisable(self):
        import json
        json.dumps(health_mod.health())


class IssueTest(HealthTestCase):
    """A failing check is logged once, and a recovery is a record, not a deletion."""

    def _report(self, failing=("corpus",), ok=("case_store",)):
        checks = []
        for name in health_mod.CHECKS:
            if name in failing:
                checks.append({"name": name, "ok": False, "severity": "required",
                               "reason": "the corpus index is not reachable",
                               "checked_at": "2026-11-10T05:00:00+00:00"})
            elif name in ok:
                checks.append({"name": name, "ok": True, "severity": "required",
                               "reason": "ok", "checked_at": "2026-11-10T05:00:00+00:00"})
            else:
                checks.append({"name": name, "ok": True, "severity": "advisory",
                               "reason": "ok", "checked_at": "2026-11-10T05:00:00+00:00"})
        return {"format": "bp-pipeline-health/1", "overall": not failing,
                "checked_at": "2026-11-10T05:00:00+00:00", "checks": checks,
                "failing": list(failing), "advisory": []}

    def test_a_failing_check_is_logged_once(self):
        from bp.product import ops_log
        first = health_mod.log_issues(self._report())
        self.assertIn("corpus", first["logged"])
        second = health_mod.log_issues(self._report())
        self.assertEqual(second["logged"], [])
        self.assertIn("corpus", second["kept"])
        rows = ops_log.list_errors(limit=100, lane=health_mod.LANE, status="all")
        self.assertEqual(len([r for r in rows if r.get("gap_label") == "corpus"]), 1)

    def test_a_recovery_is_a_record_not_a_deletion(self):
        from bp.product import ops_log
        health_mod.log_issues(self._report())
        recovered = self._report(failing=(), ok=("corpus", "case_store"))
        result = health_mod.log_issues(recovered)
        self.assertIn("corpus", result["resolved"])
        rows = ops_log.list_errors(limit=100, lane=health_mod.LANE, status="all")
        self.assertTrue(rows)                      # the failure is still in the log
        self.assertTrue(any(r.get("resolved") for r in rows))

    def test_an_advisory_signal_is_not_an_issue(self):
        report = self._report(failing=(), ok=("case_store",))
        for row in report["checks"]:
            if row["name"] == "switches":
                row["ok"] = False
                row["severity"] = "advisory"
        result = health_mod.log_issues(report)
        self.assertNotIn("switches", result["logged"])

    def test_a_finding_is_attended_so_the_loop_leaves_it_alone(self):
        from bp.product import ops_log
        health_mod.log_issues(self._report())
        rows = ops_log.list_errors(limit=100, lane=health_mod.LANE, status="all")
        self.assertTrue(any(r.get("attended") for r in rows))



class RecordTest(HealthTestCase):
    def test_the_report_is_written_and_read_back(self):
        report = health_mod.health(sources={
            "extra": {}, "case_store": {"total": 915}, "errors": [],
            "regressions": [], "corpus_probe": lambda: True,
            "repair_status": {"running": False},
            "ledger": {"summary": {"unfixed": 0, "recurring": 0, "fixed": 1, "causes": 1}},
            "switches": [], "manifest": None, "tree_date": "2026-11-10",
            "test_results": [], "relevance_run": None,
        })
        path = health_mod.health_record(report)
        self.assertTrue(path)
        self.assertTrue(os.path.isfile(path))
        rows = health_mod.history()
        self.assertTrue(rows)
        self.assertEqual(rows[0]["format"], "bp-pipeline-health/1")

    def test_the_record_never_replaces_the_earlier_one(self):
        for _ in range(2):
            health_mod.health_record({"format": "bp-pipeline-health/1", "overall": True})
        self.assertEqual(len(health_mod.history()), 2)


if __name__ == "__main__":
    unittest.main()
