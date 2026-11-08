"""The cause-keyed closure rule: what counts as a fix, and what counts as a recurrence.

An error message is not a cause.  These tests pin the three scopes (transient,
input, pipeline), the narrative trial-balance guard that used to walk past the
imbalance check, and the ledger rule that a replay pass with no durable artifact
is an instance close, never a cause fix.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, "src")

from bp.product import auto_resolve, causes, ops_log  # noqa: E402
from bp.product.problem_norm import narrative_balance, trial_balance_imbalance  # noqa: E402


MAPLE = ("Maple Retail Co. has the following declared figures as of December 31: "
         "Cash $18,500; Accounts Receivable $7,200; Inventory $12,400; "
         "Equipment $26,000; Accumulated Depreciation $4,600; Accounts Payable $9,300; "
         "Salaries Payable $1,100; Common Stock $30,000; Retained Earnings $12,000; "
         "Sales Revenue $48,000; Cost of Goods Sold $22,500; Operating Expenses $13,800. "
         "Prepare a trial balance, calculate net income, and determine whether total "
         "debits equal total credits.")


class CauseClassificationTest(unittest.TestCase):
    def test_each_known_message_maps_to_one_cause(self):
        table = [
            ("could not reach the provider: TimeoutError", "transient.provider"),
            ("the trial balance does not balance: debits 1, credits 2", "input.unbalanced"),
            ("the model response was not in the expected format. Try restating as a trial balance",
             "pipeline.parser_shape"),
            ("could not find an account 'Deferred grant'", "pipeline.vocabulary"),
            ("the paper does not contain 'declared inputs'", "pipeline.case_expectation"),
            ("the journal did not build: closing with abnormal balances needs a human decision",
             "pipeline.journal_human"),
            ("the statements tile is not attached to the frozen core", "pipeline.core_missing"),
            ("case id must be 12 lowercase hex characters", "input.validation"),
            ("this mentions 'consolidated', so it reads as consolidated accounts",
             "input.unsupported_group"),
            ("the instruction does not state: household consumption", "input.incomplete"),
        ]
        for message, expected in table:
            self.assertEqual(causes.classify_cause(message)["cause"], expected, message)

    def test_only_a_pipeline_cause_is_a_defect(self):
        self.assertFalse(causes.is_defect("could not reach the provider: TimeoutError"))
        self.assertFalse(causes.is_defect("the trial balance does not balance"))
        self.assertFalse(causes.is_defect("case id must be 12 lowercase hex characters"))
        self.assertTrue(causes.is_defect("could not find an account 'Deferred grant'"))
        self.assertTrue(causes.is_defect("the paper does not contain 'declared inputs'"))

    def test_a_pipeline_cause_needs_a_durable_artifact(self):
        self.assertEqual(causes.closure("pipeline.vocabulary"), "instance")
        self.assertEqual(causes.closure("pipeline.case_expectation"), "keep_open")
        self.assertEqual(causes.closure("input.unbalanced"), "invalid")
        self.assertEqual(causes.closure("transient.provider"), "dismiss")


class NarrativeBalanceTest(unittest.TestCase):
    def test_the_generated_narrative_trial_balance_is_out_by_the_contra_account(self):
        # Debits: cash + receivables + inventory + equipment + COGS + expenses = 100,400.
        # Credits: accumulated depreciation + payables + stock + retained + sales = 105,000.
        self.assertEqual(narrative_balance(MAPLE), -4600)
        self.assertEqual(trial_balance_imbalance(MAPLE), -4600)

    def test_a_balanced_narrative_trial_balance_reads_zero(self):
        problem = ("Trial balance as at 31 December: Cash $10,000; Equipment $5,000; "
                   "Capital $10,000; Loan $5,000. Prepare a trial balance.")
        self.assertEqual(narrative_balance(problem), 0)

    def test_the_generator_drops_the_narrative_unbalanced_fixture(self):
        from bp.product import chat_heal
        # The intake path, not just the checker: a generated narrative trial balance
        # that does not balance never reaches the solver or the error log.
        self.assertEqual(chat_heal._valid_problems([MAPLE]), [])

    def test_a_problem_with_adjustments_is_not_classified(self):
        problem = ("Trial balance before adjustments: Cash $10,000; Equipment $5,000; "
                   "Capital $15,000. Adjusting entries: depreciation $1,000. Prepare the "
                   "adjusted trial balance.")
        self.assertIsNone(narrative_balance(problem))
        self.assertIsNone(trial_balance_imbalance(problem))


class ErrorLogPolicyTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-causes-")
        self.previous = os.environ.get("BP_OPS_LOG")
        os.environ["BP_OPS_LOG"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_OPS_LOG", None)
        else:
            os.environ["BP_OPS_LOG"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_input_and_transient_failures_are_not_written(self):
        self.assertFalse(ops_log.log_error(
            "statements", "the trial balance does not balance: debits 1, credits 2"))
        self.assertFalse(ops_log.log_error(
            "statements", "could not reach the provider: TimeoutError"))
        self.assertFalse(ops_log.log_error(
            "computation", "case id must be 12 lowercase hex characters"))
        self.assertEqual(ops_log.list_errors(limit=50, status="all"), [])

    def test_a_pipeline_failure_is_written_with_its_cause(self):
        self.assertTrue(ops_log.log_error(
            "statements", "the model response was not in the expected format"))
        rows = ops_log.list_errors(limit=10, status="all")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cause"], "pipeline.parser_shape")
        self.assertEqual(rows[0]["scope"], "pipeline")

    def test_force_records_a_legacy_input_error(self):
        self.assertTrue(ops_log.log_error(
            "statements", "the trial balance does not balance: debits 1, credits 2",
            force=True))
        self.assertEqual(len(ops_log.list_errors(limit=10, status="all")), 1)


class CauseLedgerTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-ledger-")
        self.previous = os.environ.get("BP_OPS_LOG")
        os.environ["BP_OPS_LOG"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_OPS_LOG", None)
        else:
            os.environ["BP_OPS_LOG"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def _log(self, error, problem="Cash 1,000\nCapital 1,000"):
        ops_log.log_error("statements", error, problem_text=problem, force=True)
        return ops_log.list_errors(limit=10, status="all")[0]["error_id"]

    def test_an_instance_close_is_not_a_fixed_cause(self):
        error_id = self._log("the model response was not in the expected format")
        ops_log.mark_error_verified(error_id, "replayed once", cause="pipeline.parser_shape",
                                    artifact="")
        from bp.product import cause_ledger
        view = cause_ledger.summary()
        row = next(r for r in view["causes"] if r["cause"] == "pipeline.parser_shape")
        self.assertEqual(row["status"], "closed_instance")
        self.assertEqual(row["fixed_at"], "")
        self.assertEqual(view["summary"]["fixed"], 0)

    def test_a_durable_fix_counts_and_a_later_occurrence_is_a_recurrence(self):
        error_id = self._log("the model response was not in the expected format")
        ops_log.mark_error_verified(error_id, "normalizer pinned", cause="pipeline.parser_shape",
                                    artifact="golden_case")
        from bp.product import cause_ledger
        view = cause_ledger.summary()
        row = next(r for r in view["causes"] if r["cause"] == "pipeline.parser_shape")
        self.assertEqual(row["status"], "fixed")
        self.assertEqual(row["recurrences"], 0)

        self._log("the model response was not in the expected format, again")
        view = cause_ledger.summary()
        row = next(r for r in view["causes"] if r["cause"] == "pipeline.parser_shape")
        self.assertEqual(row["status"], "recurring")
        self.assertEqual(row["recurrences"], 1)
        self.assertEqual(view["summary"]["recurring"], 1)


class FixerArtifactTest(unittest.TestCase):
    """A verified replay names the durable artifact it wrote, or it is an instance close."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-fixer-cause-")
        self.previous = os.environ.get("BP_OPS_LOG")
        os.environ["BP_OPS_LOG"] = self.root
        from bp.product import tier1_tables
        self._previous_store = tier1_tables._STORE_DIR
        self._previous_path = tier1_tables._TABLES_PATH
        tier1_tables._STORE_DIR = os.path.join(self.root, "library")
        tier1_tables._TABLES_PATH = os.path.join(tier1_tables._STORE_DIR, "tier1_tables.json")
        tier1_tables.reload()

    def tearDown(self):
        from bp.product import tier1_tables
        if self.previous is None:
            os.environ.pop("BP_OPS_LOG", None)
        else:
            os.environ["BP_OPS_LOG"] = self.previous
        tier1_tables._STORE_DIR = self._previous_store
        tier1_tables._TABLES_PATH = self._previous_path
        tier1_tables.reload()
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_vocabulary_error_closes_with_a_tier1_rule(self):
        problem = "Trial balance: Cash 10,000; Deferred grant 2,000; Capital 8,000."
        ops_log.log_error("statements", "could not find an account 'Deferred grant'",
                          problem_text=problem, force=True)
        error_id = ops_log.list_errors(limit=10, status="all")[0]["error_id"]
        with mock.patch.object(auto_resolve, "_replay_on", return_value={"status": "ok"}):
            result = auto_resolve.resolve(error_id)
        self.assertTrue(result["resolved"], result)
        self.assertEqual(result["artifact"], "tier1_rule")
        self.assertEqual(result["cause"], "pipeline.vocabulary")
        from bp.product import tier1_tables
        labels = [str(rule[0]).replace("\\", "") for rule in (tier1_tables.get_rules() or [])]
        self.assertTrue(any("deferred grant" in label.lower() for label in labels), labels[-3:])

    def test_a_replay_pass_with_no_normalisation_is_an_instance_close(self):
        problem = "Cash 1,000\nCapital 1,000"
        ops_log.log_error("statements", "the model response was not in the expected format",
                          problem_text=problem, force=True)
        error_id = ops_log.list_errors(limit=10, status="all")[0]["error_id"]
        with mock.patch.object(auto_resolve, "_replay_on", return_value={"status": "ok"}), \
             mock.patch("bp.product.regression_cases.record_case", return_value=False):
            result = auto_resolve.resolve(error_id)
        self.assertTrue(result["resolved"], result)
        self.assertEqual(result["artifact"], "")
        from bp.product import cause_ledger
        view = cause_ledger.summary()
        row = next(r for r in view["causes"] if r["cause"] == "pipeline.parser_shape")
        self.assertEqual(row["status"], "closed_instance")

    def test_an_unfixed_pipeline_cause_names_the_remedy_and_waits(self):
        ops_log.log_error("statements", "the journal did not build: abnormal balances",
                          problem_text="Cash 1,000\nCapital 900", force=True)
        error_id = ops_log.list_errors(limit=10, status="all")[0]["error_id"]
        with mock.patch.object(auto_resolve, "_replay_on",
                               return_value={"status": "error", "error": "still fails"}):
            result = auto_resolve.resolve(error_id)
        self.assertFalse(result["resolved"])
        self.assertEqual(result["unfixed_cause"], "pipeline.journal_human")
        self.assertEqual(result["needed_remedy"], "human_decision")

    def test_a_legacy_input_record_leaves_as_invalid_not_attended(self):
        ops_log.log_error(
            "statements",
            "this mentions 'consolidated', so it reads as consolidated or group accounts",
            problem_text="A group problem", force=True)
        error_id = ops_log.list_errors(limit=10, status="all")[0]["error_id"]
        with mock.patch.object(auto_resolve, "_replay_on",
                               return_value={"status": "error", "error": "still consolidated"}):
            result = auto_resolve.resolve(error_id)
        self.assertTrue(result["invalid"])
        self.assertEqual(result["cause"], "input.unsupported_group")
        merged = ops_log.merge_resolved(ops_log.list_errors(limit=100, status="all"))
        rec = next(r for r in merged if r["error_id"] == error_id)
        self.assertTrue(rec.get("invalid"))
        self.assertFalse(rec.get("attended"))


if __name__ == "__main__":
    unittest.main()
