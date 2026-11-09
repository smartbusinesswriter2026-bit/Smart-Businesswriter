"""The verifier: a replay is not a fix unless an independent model agrees.

The repair loop used to let one model replay a problem and call the pass a fix.
MASS's finding is that a homogeneous loop reinforces its own errors; this test
pins the split: the solver proposes, a different model verifies, and only their
agreement writes a durable fix.
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, "src")

from bp.product import auto_resolve, ops_log  # noqa: E402

ERROR = "the model response was not in the expected format. Try restating as a trial balance"
PROBLEM = ("Cash 7,000 debit; Trade receivables 3,000 debit; Equipment 10,000 debit; "
           "Trade payables 5,000 credit; Capital 15,000 credit.")


class VerifierTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-verify-")
        self.previous = os.environ.get("BP_OPS_LOG")
        os.environ["BP_OPS_LOG"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_OPS_LOG", None)
        else:
            os.environ["BP_OPS_LOG"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def _log(self):
        ops_log.log_error("statements", ERROR, problem_text=PROBLEM, force=True)
        return ops_log.list_errors(limit=10, status="all")[0]["error_id"]

    def _open(self, error_id):
        merged = ops_log.merge_resolved(ops_log.list_errors(limit=100, status="all"))
        row = next(r for r in merged if r["error_id"] == error_id)
        return not (row.get("resolved") or row.get("invalid") or row.get("dismissed"))

    def test_a_verifier_disagreement_keeps_the_error_open(self):
        error_id = self._log()
        with mock.patch.object(auto_resolve, "_replay_on", return_value={"status": "ok"}), \
                mock.patch.object(auto_resolve, "normalize_problem",
                                  return_value=(PROBLEM, ["split inline list"])), \
                mock.patch.object(auto_resolve, "_verify_fix",
                                  return_value={"ok": False, "model": "beam-free",
                                                "reason": "the answer uses the wrong figure"}):
            result = auto_resolve.resolve(error_id)
        self.assertFalse(result["resolved"])
        self.assertFalse(result["verified"])
        self.assertTrue(self._open(error_id), "a disagreed fix must not close the error")

    def test_a_verifier_agreement_writes_the_durable_fix(self):
        error_id = self._log()
        with mock.patch.object(auto_resolve, "_replay_on", return_value={"status": "ok"}), \
                mock.patch.object(auto_resolve, "normalize_problem",
                                  return_value=(PROBLEM, ["split inline list"])), \
                mock.patch.object(auto_resolve, "_verify_fix",
                                  return_value={"ok": True, "model": "beam-free",
                                                "reason": "the answer matches"}):
            result = auto_resolve.resolve(error_id)
        self.assertTrue(result["resolved"])
        self.assertTrue(result["verified"])
        self.assertEqual(result.get("artifact"), "golden_case")
        self.assertFalse(self._open(error_id))

    def test_no_verifier_answer_is_an_instance_close_not_a_fix(self):
        error_id = self._log()
        with mock.patch.object(auto_resolve, "_replay_on", return_value={"status": "ok"}), \
                mock.patch.object(auto_resolve, "normalize_problem",
                                  return_value=(PROBLEM, ["split inline list"])), \
                mock.patch.object(auto_resolve, "_verify_fix",
                                  return_value={"ok": None, "model": "",
                                                "reason": "no verifier model answered"}):
            result = auto_resolve.resolve(error_id)
        self.assertTrue(result["resolved"])
        self.assertEqual(result.get("artifact"), "",
                         "a replay no verifier could check is not a durable fix")

    def test_the_verifier_uses_a_different_model_than_the_solver(self):
        models = auto_resolve._verifier_models()
        self.assertTrue(models)
        self.assertNotIn(auto_resolve.FIX_MODEL, models,
                         "the verifier must not be the solver's model")

    def test_the_problem_solver_rejects_an_answer_the_verifier_rejects(self):
        from bp.product import chat_heal
        problem = "Cash 7,000 debit; Capital 7,000 credit."
        with mock.patch("bp.product.statements.solve",
                        return_value={"solved": True, "working": {}}), \
                mock.patch("bp.product.verifier.verify_fix",
                           return_value={"ok": False, "model": "beam-free",
                                         "reason": "the figure is wrong"}):
            results, _error = chat_heal.solve_problems([problem], log_failures=False)
        self.assertEqual(results[0]["status"], "error")
        self.assertIn("verifier rejected", results[0]["error"])


if __name__ == "__main__":
    unittest.main()
