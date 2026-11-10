"""The fault harness: the owner's cases are never touched, and every fault is
classified the way the cause rules say it must be (product layer).
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")

from bp.product import case_store  # noqa: E402
from bp.product import eval_faults  # noqa: E402


class FaultTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="eval-faults-test-")
        self._saved_env = dict(os.environ)
        os.environ["BP_STATE_DIR"] = os.path.join(self._tmp, "state")
        os.environ["BP_OPS_LOG"] = os.path.join(self._tmp, "ops_log")
        os.environ.pop("BP_CASE_ROOT", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved_env)
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _case(self, method=None):
        for case in case_store.load_cases():
            if method is None or str(case.get("method")) == method:
                return case
        return None


class CaseRootTest(FaultTestCase):
    def test_the_root_is_the_projects_own_store_when_unset(self):
        root = case_store._root()
        self.assertTrue(root.endswith(os.path.join("qa", "cases")))

    def test_the_root_follows_the_environment(self):
        os.environ["BP_CASE_ROOT"] = self._tmp
        self.assertEqual(case_store._root(), os.path.normpath(self._tmp))

    def test_the_store_reads_the_redirected_root(self):
        """A copy of the cases is read when the root is redirected."""
        sandbox = eval_faults.sandbox()
        try:
            os.environ["BP_CASE_ROOT"] = sandbox
            cases = case_store.load_cases()
            self.assertTrue(cases)
            self.assertTrue(all(str(case.get("id")).startswith(("accounting", "finance",
                        "marketing", "operations", "economics", "people", "research",
                        "supply-chain", "entrepreneurship", "project-management"))
                               for case in cases[:50]))
        finally:
            os.environ.pop("BP_CASE_ROOT", None)
            shutil.rmtree(sandbox, ignore_errors=True)


class InjectionTest(FaultTestCase):
    def test_an_unknown_fault_is_refused_with_a_reason(self):
        with self.assertRaises(ValueError) as caught:
            eval_faults.inject("no_such_fault", self._case())
        self.assertIn("no_such_fault", str(caught.exception))

    def test_a_tampered_expectation_changes_the_recorded_value(self):
        case = self._case()
        seeded, expectation = eval_faults.inject("tampered_expectation", case)
        self.assertEqual(expectation["scope"], "fail")
        self.assertNotEqual(seeded["expected"]["result"][expectation["tampered"]],
                            case["expected"]["result"][expectation["tampered"]])

    def test_the_original_case_is_never_modified(self):
        case = self._case()
        before = dict(case.get("expected").get("result") or {})
        eval_faults.inject("tampered_expectation", case)
        self.assertEqual(case["expected"]["result"], before)


class FaultRunTest(FaultTestCase):
    def test_a_tampered_expectation_is_a_pipeline_failure(self):
        case = self._case()
        outcome = eval_faults.run_fault("tampered_expectation", case_id=case.get("id"))
        self.assertEqual(outcome["scope"], "fail")
        self.assertTrue(outcome["ok"])

    def test_a_missing_phrase_is_a_pipeline_failure(self):
        case = self._case()
        outcome = eval_faults.run_fault("missing_phrase", case_id=case.get("id"))
        self.assertEqual(outcome["scope"], "fail")
        self.assertTrue(outcome["ok"])

    def test_broken_figures_are_invalid_not_a_defect(self):
        """The case's own figures are refused; they never reach the ledger."""
        case = self._case(method="ratio_analysis")
        if case is None:
            self.skipTest("no ratio_analysis case is stored")
        outcome = eval_faults.run_fault("broken_inputs", case_id=case.get("id"))
        self.assertEqual(outcome["scope"], "invalid")
        self.assertTrue(outcome["ok"])

    def test_a_corpus_that_answers_nothing_is_not_a_green(self):
        from bp.product import eval_rubric
        saved = os.environ.get("CORPUS_MEILI_URL")
        os.environ["CORPUS_MEILI_URL"] = "http://127.0.0.1:1"
        try:
            result = eval_rubric.score_rag("accounting", "abc")
        finally:
            if saved is None:
                os.environ.pop("CORPUS_MEILI_URL", None)
            else:
                os.environ["CORPUS_MEILI_URL"] = saved
        self.assertFalse(result["measured"])
        self.assertFalse(result["corpus_available"])

    def test_the_owners_cases_are_untouched_by_a_fault_run(self):
        case = self._case()
        path = case.get("_path")
        with open(path, "r", encoding="utf-8") as handle:
            before = handle.read()
        eval_faults.run_fault("tampered_expectation", case_id=case.get("id"))
        with open(path, "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), before)

    def test_the_live_error_log_is_untouched_by_a_fault_run(self):
        case = self._case()
        before = eval_faults.live_log_fingerprint()
        eval_faults.run_fault("tampered_expectation", case_id=case.get("id"))
        self.assertEqual(eval_faults.live_log_fingerprint(), before)

    def test_every_fault_is_seeded_and_reported(self):
        case = self._case()
        report = eval_faults.run_faults(case_id=case.get("id"))
        self.assertEqual(len(report["faults"]), len(eval_faults.FAULTS))
        self.assertTrue(report["live_log_untouched"])
        for row in report["faults"]:
            self.assertIn("fault", row)


if __name__ == "__main__":
    unittest.main()
