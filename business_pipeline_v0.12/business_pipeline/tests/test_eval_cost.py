"""What the repair loop spent, and whether the fix held (product layer).

The dollar figure is the owner's to supply.  Until it is supplied, the cost
is **unknown** - never zero, which would read as "free" and be wrong.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")

from bp.product import auto_resolve  # noqa: E402
from bp.product import eval_runner  # noqa: E402
from bp.product import ops_log  # noqa: E402
from bp.product import usage  # noqa: E402


class UsageTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="eval-cost-")
        self._saved_env = dict(os.environ)
        os.environ["BP_STATE_DIR"] = os.path.join(self._tmp, "state")
        os.environ["BP_OPS_LOG"] = os.path.join(self._tmp, "ops_log")
        os.environ.pop("BP_MODEL_PRICES", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved_env)
        shutil.rmtree(self._tmp, ignore_errors=True)


class UsageTest(UsageTestCase):
    def test_only_the_records_after_the_index_are_counted(self):
        log = [{"model": "m", "input_tokens": 10, "output_tokens": 5, "seconds": 1.0},
               {"model": "m", "input_tokens": 20, "output_tokens": 7, "seconds": 2.0}]
        spent = usage.usage_since(log, 1)
        self.assertEqual(spent["calls"], 1)
        self.assertEqual(spent["input_tokens"], 20)
        self.assertEqual(spent["output_tokens"], 7)

    def test_no_calls_cost_nothing(self):
        self.assertEqual(usage.cost_of({"calls": 0, "models": {}}), 0.0)

    def test_an_unpriced_model_costs_an_unknown_amount(self):
        spent = usage.usage_since([{"model": "some-model", "input_tokens": 100,
                                    "output_tokens": 50}], 0)
        self.assertIsNone(usage.cost_of(spent))

    def test_a_priced_model_costs_what_the_owner_declared(self):
        spent = usage.usage_since([{"model": "some-model", "input_tokens": 1000000,
                                    "output_tokens": 1000000}], 0)
        prices = {"some-model": (1.0, 3.0)}
        self.assertAlmostEqual(usage.cost_of(spent, prices=prices), 4.0)

    def test_the_owner_can_supply_the_prices_in_a_file(self):
        path = os.path.join(self._tmp, "prices.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"some-model": {"input": 2.0, "output": 2.0}}, handle)
        os.environ["BP_MODEL_PRICES"] = path
        spent = usage.usage_since([{"model": "some-model", "input_tokens": 1000000,
                                    "output_tokens": 0}], 0)
        self.assertAlmostEqual(usage.cost_of(spent), 2.0)

    def test_two_records_add_together(self):
        left = usage.usage_since([{"model": "m", "input_tokens": 10, "output_tokens": 1}], 0)
        right = usage.usage_since([{"model": "m", "input_tokens": 5, "output_tokens": 2}], 0)
        total = usage.add(left, right)
        self.assertEqual(total["input_tokens"], 15)
        self.assertEqual(total["output_tokens"], 3)
        self.assertEqual(total["calls"], 2)


class StepCostTest(UsageTestCase):
    def test_the_steps_report_what_they_spent(self):
        spent = usage.usage_since([{"model": "m", "input_tokens": 100, "output_tokens": 20,
                                    "seconds": 1.5}], 0)
        cost = auto_resolve.cost_of_steps([{"strategy": "replay", "usage": spent}])
        self.assertEqual(cost["model_calls"], 1)
        self.assertEqual(cost["input_tokens"], 100)
        self.assertIsNone(cost["usd"])

    def test_a_code_only_step_spent_nothing_and_says_so(self):
        cost = auto_resolve.cost_of_steps([{"strategy": "replay stored tile case",
                                            "model": "none (code)"}])
        self.assertEqual(cost["model_calls"], 0)
        self.assertEqual(cost["usd"], 0.0)


class DurabilityTest(UsageTestCase):
    """A fix counts only after three consecutive green replays."""

    MESSAGE = "could not read this as a journal: put two figures on one line"

    def _log_pipeline_error(self, index):
        ops_log.log_error("tile-case", "%s (#%d)" % (self.MESSAGE, index),
                          gap_label="test", force=True)
        rows = ops_log.list_errors(limit=50, status="open")
        for row in rows:
            if str(row.get("error") or "").endswith("(#%d)" % index):
                return row.get("error_id")
        return None

    def test_one_green_replay_is_not_a_fix(self):
        error_id = self._log_pipeline_error(1)
        self.assertTrue(error_id)
        ops_log.mark_error_verified(error_id, "replayed and passed",
                                    cause="pipeline.parser_shape", artifact="golden_case")
        rows = eval_runner.durability(green_runs=3)
        entry = [row for row in rows if row["cause"] == "pipeline.parser_shape"]
        self.assertTrue(entry)
        self.assertEqual(entry[0]["run"], 1)
        self.assertFalse(entry[0]["durable"])

    def test_three_green_replays_make_the_fix_durable(self):
        ops_log.log_cause_fix("pipeline.parser_shape", "golden_case", "the normalizer changed")
        for index in (1, 2, 3):
            error_id = self._log_pipeline_error(index)
            ops_log.mark_error_verified(error_id, "replayed and passed",
                                        cause="pipeline.parser_shape", artifact="golden_case")
        rows = eval_runner.durability(green_runs=3)
        entry = [row for row in rows if row["cause"] == "pipeline.parser_shape"][0]
        self.assertEqual(entry["run"], 3)
        self.assertTrue(entry["durable"])

    def test_a_failure_between_greens_breaks_the_run(self):
        ops_log.log_cause_fix("pipeline.parser_shape", "golden_case", "the normalizer changed")
        for index in (1, 2):
            error_id = self._log_pipeline_error(index)
            ops_log.mark_error_verified(error_id, "replayed and passed",
                                        cause="pipeline.parser_shape", artifact="golden_case")
        broken = self._log_pipeline_error(3)      # this one stays open
        self.assertTrue(broken)
        error_id = self._log_pipeline_error(4)
        ops_log.mark_error_verified(error_id, "replayed and passed",
                                    cause="pipeline.parser_shape", artifact="golden_case")
        rows = eval_runner.durability(green_runs=3)
        entry = [row for row in rows if row["cause"] == "pipeline.parser_shape"][0]
        self.assertLess(entry["run"], 3)
        self.assertFalse(entry["durable"])


class DirectionThreeTest(UsageTestCase):
    def test_the_run_reports_the_causes_and_the_cost(self):
        manifest = eval_runner.run_direction3()
        self.assertEqual(manifest["status"], "done")
        self.assertIn("causes", manifest["counts"])
        self.assertIn("model_calls", manifest["cost"])
        self.assertIn("usd", manifest["cost"])
        self.assertIn("durability", manifest)
        stored = eval_runner.load_manifest(manifest["run_id"])
        self.assertEqual(stored["direction"], "direction3")


if __name__ == "__main__":
    unittest.main()
