"""Stored tile cases, their runner, and the token-free replay in the loop."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, "src")

from bp import methods  # noqa: E402
from bp.product import auto_resolve, autoresearch, case_runner, case_store, ops_log, paper_batch  # noqa: E402

PRESETS = {
    "breakeven": {
        "objective": "How many units must we sell to break even?",
        "method": "breakeven",
        "inputs": {"fixed": "1000", "price": "20", "variable": "10"},
    },
    "ratios": {
        "objective": "Compute the key ratios from our financial statements",
        "method": "ratio_analysis",
        "inputs": {"current_assets": "5000", "current_liabilities": "2000"},
    },
}


class CaseLoopTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paper_batch.configure(lambda method, inputs: methods.LIBRARY[method].impl(inputs),
                              methods.describe, PRESETS)
        paper_batch.sections(refresh=True)

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-case-loop-")
        self.previous_case_root = case_store._root
        self.previous_run_root = case_runner._state_root
        self.previous_ops_log = os.environ.get("BP_OPS_LOG")
        case_store._root = lambda: os.path.join(self.root, "cases")
        case_runner._state_root = lambda: os.path.join(self.root, "case_runs")
        os.environ["BP_OPS_LOG"] = os.path.join(self.root, "ops_log")
        os.makedirs(case_store._root(), exist_ok=True)
        self.search_patch = mock.patch.object(
            paper_batch.source_finder, "search_academic",
            return_value={"results": [], "errors": []})
        self.search_patch.start()

    def tearDown(self):
        self.search_patch.stop()
        case_store._root = self.previous_case_root
        case_runner._state_root = self.previous_run_root
        if self.previous_ops_log is None:
            os.environ.pop("BP_OPS_LOG", None)
        else:
            os.environ["BP_OPS_LOG"] = self.previous_ops_log
        shutil.rmtree(self.root, ignore_errors=True)

    def _seed(self):
        written = case_store.seed(overwrite=True)
        self.assertGreaterEqual(written["written"], 2)
        return case_store.load_cases()

    def test_seed_writes_a_case_for_each_tile_with_defaults(self):
        cases = self._seed()
        tiles = {case["tile"] for case in cases}
        self.assertIn("breakeven", tiles)
        self.assertIn("ratios", tiles)
        for case in cases:
            self.assertEqual(case["format"], case_store.FORMAT)
            self.assertTrue(case["instruction"])
            self.assertTrue(case["expected"]["result"])

    def test_a_case_replays_on_a_tile_with_no_published_default(self):
        """A case carries its own figures; the preset is only a preview fallback.

        `generate_one` used to refuse any tile without `has_defaults` before it looked
        at the case's inputs, so every accounting case failed the runner even when its
        figures were complete and its expected result was the core's own output.
        """
        inputs = {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"}
        computed = methods.LIBRARY["depreciation_schedule"].impl(inputs)
        payload = {
            "format": case_store.FORMAT, "id": "accounting/depreciation/001",
            "subject": "accounting", "subject_label": "Accounting",
            "tile": "depreciation", "tile_label": "Depreciation schedule",
            "group": "Adjustments and depreciation", "method": "depreciation_schedule",
            "objective": "Depreciation schedule at a declared rate",
            "instruction": "A machine costs 500,000 with a residual value of 50,000 and a "
                           "five-year life. Prepare the straight-line depreciation schedule.",
            "inputs": inputs,
            "expected": {"status": "ok",
                         "result": {k: str(v) for k, v in computed.items() if not k.startswith("_")},
                         "contains": ["What you declared", "How the figures were checked"],
                         "xlsx_sheets": ["Summary", "Inputs", "Results", "Record"]},
            "created_at": "2026-11-08T00:00:00+00:00", "origin": "authored"}
        path = case_store._case_path("accounting", "depreciation", 1)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        run = case_runner.run_case("accounting/depreciation/001", log=False)
        self.assertEqual(run["status"], "pass", run.get("error"))

    def test_a_tile_with_no_inputs_still_asks_for_them(self):
        result = paper_batch.generate_one("accounting", "depreciation")
        self.assertEqual(result["status"], "needs_input")
        self.assertIn("no published default inputs", result["error"])

    def _failing_case(self):
        cases = self._seed()
        case = next(c for c in cases if c["tile"] == "breakeven")
        good = case_runner.run_case(case["id"])
        self.assertEqual(good["status"], "pass", good["error"])

        payload = json.loads(open(case["_path"], encoding="utf-8").read())
        key = next(iter(payload["expected"]["result"]))
        payload["expected"]["result"][key] = "-999999"
        with open(case["_path"], "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        bad = case_runner.run_case(case["id"])
        self.assertEqual(bad["status"], "fail")
        self.assertIn("expected -999999", bad["error"])
        rows = ops_log.merge_resolved(ops_log.list_errors(limit=50))
        logged = [row for row in rows if row.get("case_id") == case["id"]]
        self.assertEqual(len(logged), 1)
        self.assertTrue(logged[0].get("problem"))
        return case["id"], logged[0]["error_id"]

    def test_a_passing_case_passes_and_a_wrong_expectation_fails(self):
        self._failing_case()

    def _case_payload(self):
        cases = self._seed()
        case = next(c for c in cases if c["tile"] == "breakeven")
        payload = json.loads(open(case["_path"], encoding="utf-8").read())
        return case, payload

    def _write(self, case, payload):
        with open(case["_path"], "w", encoding="utf-8") as handle:
            json.dump(payload, handle)

    def test_a_missing_expected_key_fails_on_the_extra_computed_key(self):
        case, payload = self._case_payload()
        del payload["expected"]["result"]["contribution_margin"]
        self._write(case, payload)
        outcome = case_runner.run_case(case["id"], log=False)
        self.assertEqual(outcome["status"], "fail")
        self.assertIn("does not expect", outcome["error"])

    def test_an_empty_expectation_cannot_pass(self):
        case, payload = self._case_payload()
        payload["expected"]["result"] = {}
        self._write(case, payload)
        outcome = case_runner.run_case(case["id"], log=False)
        self.assertEqual(outcome["status"], "fail")
        self.assertIn("declares no expected result", outcome["error"])

    def test_a_wrong_paper_value_fails(self):
        case, payload = self._case_payload()
        payload["expected"]["paper_values"] = ["no-such-value-xyz"]
        self._write(case, payload)
        outcome = case_runner.run_case(case["id"], log=False)
        self.assertEqual(outcome["status"], "fail")
        self.assertIn("does not show any of the computed values", outcome["error"])

    def test_an_extra_expected_key_fails(self):
        case, payload = self._case_payload()
        payload["expected"]["result"]["bogus_metric"] = "1"
        self._write(case, payload)
        outcome = case_runner.run_case(case["id"], log=False)
        self.assertEqual(outcome["status"], "fail")
        self.assertIn("did not return bogus_metric", outcome["error"])

    def test_the_loop_replays_a_case_by_code_and_needs_no_model(self):
        case_id, error_id = self._failing_case()
        with mock.patch("bp.product.chat_heal.generate_problems_from_error") as generate, \
             mock.patch("bp.product.chat_heal.solve_problems") as solve:
            still_bad = auto_resolve.resolve(error_id)
            self.assertEqual(still_bad["category"], "tile_case")
            self.assertFalse(still_bad["verified"])
            # Repair the stored expectation, as a computation-owner change would.
            case = case_store.get_case(case_id)
            payload = json.loads(open(case["_path"], encoding="utf-8").read())
            computed = paper_batch.generate_one("accounting", "breakeven")["computation"]
            payload["expected"]["result"] = computed
            with open(case["_path"], "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            fixed = auto_resolve.resolve(error_id)
            self.assertTrue(fixed["verified"], fixed["reason"])
            self.assertEqual(fixed["model"], "none (code)")
            generate.assert_not_called()
            solve.assert_not_called()

    def test_an_error_without_a_problem_is_skipped_without_a_model_call(self):
        error = {"error_id": "nope", "error": "something happened", "severity": "light"}
        captured = []
        with mock.patch.object(autoresearch, "_log_experiment", side_effect=captured.append), \
             mock.patch("bp.product.chat_heal.generate_problems_from_error") as generate:
            exp = autoresearch._run_experiment(error)
            self.assertEqual(exp["outcome"], "no_replayable_problem")
            generate.assert_not_called()
        self.assertTrue(captured)

    def test_the_loop_keeps_a_verified_case_fix(self):
        case_id, error_id = self._failing_case()
        case = case_store.get_case(case_id)
        payload = json.loads(open(case["_path"], encoding="utf-8").read())
        payload["expected"]["result"] = paper_batch.generate_one("accounting", "breakeven")["computation"]
        with open(case["_path"], "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        captured = []
        error = {"error_id": error_id, "error": "case failed", "severity": "light",
                 "case_id": case_id}
        with mock.patch.object(autoresearch, "_log_experiment", side_effect=captured.append):
            exp = autoresearch._run_experiment(error)
        self.assertEqual(exp["outcome"], "kept")
        self.assertTrue(exp["verified"])
        self.assertEqual(exp["model"], "none (code)")

    def test_a_passing_case_closes_its_open_error(self):
        case_id, error_id = self._failing_case()
        case = case_store.get_case(case_id)
        payload = json.loads(open(case["_path"], encoding="utf-8").read())
        payload["expected"]["result"] = paper_batch.generate_one("accounting", "breakeven")["computation"]
        with open(case["_path"], "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        outcome = case_runner.run_case(case_id, log=False)
        self.assertEqual(outcome["status"], "pass", outcome["error"])
        self.assertGreaterEqual(outcome.get("closed_errors", 0), 1)
        rows = ops_log.merge_resolved(ops_log.list_errors(limit=100, status="all"))
        target = next(row for row in rows if row.get("error_id") == error_id)
        self.assertTrue(target.get("resolved"))

    def test_a_rounded_display_value_is_accepted(self):
        self.assertTrue(case_runner._paper_has_value("the quantity is 26.67 units", "26.666666666666666"))
        self.assertFalse(case_runner._paper_has_value("the quantity is 26.67 units", "30"))

    def test_a_case_run_writes_an_explainer(self):
        cases = self._seed()
        case = next(c for c in cases if c["tile"] == "breakeven")
        outcome = case_runner.run_case(case["id"], log=False)
        sections = dict(outcome["explainer"])
        self.assertIn("Check", sections)
        self.assertTrue(any("Status: pass" in line for line in sections["Check"]))
        manifest = case_runner.run_cases([case["id"]])
        self.assertTrue(manifest["results"][0]["explainer_file"].endswith(".docx"))
        self.assertEqual(manifest.get("explainer"), "explainer.docx")


class FixerClassificationTest(unittest.TestCase):
    """The fixer classifies and closes the two failure classes it cannot replay."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-fixer-")
        self.previous_ops_log = os.environ.get("BP_OPS_LOG")
        os.environ["BP_OPS_LOG"] = os.path.join(self.root, "ops_log")
        # The tier-1 store path is captured at import; patch the module's own path so the
        # test never writes into the real statement library.
        from bp.product import tier1_tables
        self._previous_store = tier1_tables._STORE_DIR
        self._previous_path = tier1_tables._TABLES_PATH
        tier1_tables._STORE_DIR = os.path.join(self.root, "library")
        tier1_tables._TABLES_PATH = os.path.join(tier1_tables._STORE_DIR, "tier1_tables.json")
        tier1_tables.reload()

    def tearDown(self):
        from bp.product import tier1_tables
        if self.previous_ops_log is None:
            os.environ.pop("BP_OPS_LOG", None)
        else:
            os.environ["BP_OPS_LOG"] = self.previous_ops_log
        tier1_tables._STORE_DIR = self._previous_store
        tier1_tables._TABLES_PATH = self._previous_path
        tier1_tables.reload()
        shutil.rmtree(self.root, ignore_errors=True)

    def test_diagnose_recognises_unbalanced_and_timeout(self):
        self.assertEqual(
            auto_resolve.diagnose("the trial balance does not balance: debits 1, credits 2"),
            "unbalanced_input")
        self.assertEqual(auto_resolve.diagnose("no answer within 120s"), "timeout")
        self.assertEqual(auto_resolve.diagnose("Failed to fetch"), "timeout")

    def test_guess_rule_types_accounts_by_keyword(self):
        self.assertEqual(auto_resolve._guess_rule("Deferred grant")[1], "liability")
        self.assertEqual(auto_resolve._guess_rule("Trade receivable")[1], "asset")
        self.assertEqual(auto_resolve._guess_rule("Bank loan")[1], "liability")
        self.assertEqual(auto_resolve._guess_rule("Share capital")[1], "equity")
        self.assertEqual(auto_resolve._guess_rule("Sales revenue")[1], "income")
        self.assertIsNone(auto_resolve._guess_rule("Zzz qqq"))

    def test_a_skipped_account_is_recognised_and_balances_the_trial_balance(self):
        """An unknown account dropped by the parser is added back by its keywords."""
        from bp.product import statements
        problem = ("The following trial balance was extracted at 31 December 2026.\n"
                   "Cash 10,000\n"
                   "Capital 8,000 Cr\n"
                   "Deferred grant 2,000 Cr")
        # Before the rule, the reader drops the unknown account and the sides disagree.
        reading = statements.read_deterministic(problem)
        self.assertNotEqual(auto_resolve._journal_imbalance(reading), 0)
        fixed = auto_resolve._try_fix_unbalanced(problem)
        self.assertEqual(fixed, "Deferred grant")
        after = statements.read_deterministic(problem)
        self.assertEqual(auto_resolve._journal_imbalance(after), 0)

    def test_an_unbalanced_problem_with_no_skipped_account_is_closed_as_invalid(self):
        ops_log.log_error(
            "statements",
            "the accounts do not build: entries[0]: entry 'the trial balance as given' "
            "on 2026-12-31 does not balance: debits 10000, credits 8000",
            problem_text="Cash 10,000\nCapital 8,000 Cr")
        err = ops_log.list_errors(limit=5)[0]
        result = auto_resolve.resolve(err["error_id"])
        self.assertTrue(result["invalid"])
        self.assertEqual(result["category"], "unbalanced_input")
        # It leaves the open list, and it is never labelled solved.
        self.assertEqual([e["error_id"] for e in ops_log.list_errors(limit=10)], [])
        merged = ops_log.merge_resolved(ops_log.list_errors(limit=100, status="all"))
        rec = next(m for m in merged if m.get("error_id") == err["error_id"])
        self.assertTrue(rec.get("invalid"))
        self.assertFalse(rec.get("resolved"))

    def test_a_timeout_is_dismissed_as_transient(self):
        ops_log.log_error("statements", "no answer within 120s",
                          problem_text="A narrative that times out")
        err = ops_log.list_errors(limit=5)[0]
        result = auto_resolve.resolve(err["error_id"])
        self.assertEqual(result["category"], "timeout")
        self.assertFalse(result["attempted"])
        self.assertEqual([e["error_id"] for e in ops_log.list_errors(limit=10)], [])
        merged = ops_log.merge_resolved(ops_log.list_errors(limit=100, status="all"))
        rec = next(m for m in merged if m.get("error_id") == err["error_id"])
        self.assertTrue(rec.get("dismissed"))


if __name__ == "__main__":
    unittest.main()
