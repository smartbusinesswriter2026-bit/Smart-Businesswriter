"""Uploaded tile cases: automatic mapping, the replay gate, and storage."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, "src")

from bp import methods  # noqa: E402
from bp.product import case_store, case_upload, paper_batch, spreadsheets  # noqa: E402

PRESETS = {
    "breakeven": {
        "objective": "How many units must we sell to break even?",
        "method": "breakeven",
        "inputs": {"fixed": "1000", "price": "20", "variable": "10"},
    },
}


class CaseUploadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paper_batch.configure(lambda method, inputs: methods.LIBRARY[method].impl(inputs),
                              methods.describe, PRESETS)
        paper_batch.sections(refresh=True)

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-case-upload-")
        self.previous = case_store._root
        case_store._root = lambda: os.path.join(self.root, "cases")
        os.makedirs(case_store._root(), exist_ok=True)
        self.search = mock.patch.object(paper_batch.source_finder, "search_academic",
                                        return_value={"results": [], "errors": []})
        self.search.start()

    def tearDown(self):
        self.search.stop()
        case_store._root = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_csv_is_mapped_automatically_and_accepted(self):
        raw = b"fixed,price,variable\n1200,25,10\n"
        case = case_upload.upload("accounting", "breakeven", "case.csv", raw)
        self.assertEqual(case["origin"], "uploaded")
        self.assertEqual(case["inputs"]["fixed"], "1200")
        self.assertEqual(case["inputs"]["price"], "25")
        self.assertEqual(case["expected"]["result"]["breakeven_units"], "80")
        self.assertEqual(len(case_store.load_cases(subject="accounting")), 1)

    def test_an_xlsx_is_mapped_automatically_and_accepted(self):
        workbook = spreadsheets.write_xlsx(
            [("Sheet1", [["fixed", "price", "variable"], ["1000", "20", "10"]], {})])
        case = case_upload.upload("accounting", "breakeven", "case.xlsx", workbook)
        self.assertEqual(case["inputs"]["fixed"], "1000")
        self.assertEqual(case["expected"]["result"]["breakeven_units"], "100")

    def test_a_json_case_is_gated_and_stored(self):
        raw = json.dumps({
            "tile": "breakeven",
            "instruction": "A store sells at 20 with variable 10 and fixed 1000. How many units to break even?",
            "inputs": {"fixed": "1000", "price": "20", "variable": "10"},
        }).encode()
        case = case_upload.upload("accounting", "breakeven", "case.json", raw)
        self.assertEqual(case["instruction"].startswith("A store sells"), True)
        self.assertEqual(case["expected"]["result"]["breakeven_units"], "100")

    def test_a_case_that_cannot_replay_is_rejected_and_not_written(self):
        with self.assertRaises(ValueError):
            case_upload.upload("accounting", "breakeven", "bad.csv", b"price,variable\n20,10\n")
        self.assertEqual(case_store.load_cases(subject="accounting"), [])

    def test_the_uploaded_case_runs_through_the_runner(self):
        from bp.product import case_runner
        raw = b"fixed,price,variable\n1200,25,10\n"
        case = case_upload.upload("accounting", "breakeven", "case.csv", raw)
        outcome = case_runner.run_case(case["id"])
        self.assertEqual(outcome["status"], "pass", outcome["error"])


class BundleUploadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paper_batch.configure(lambda method, inputs: methods.LIBRARY[method].impl(inputs),
                              methods.describe, PRESETS)
        paper_batch.sections(refresh=True)

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-bundle-upload-")
        self.previous = case_store._root
        case_store._root = lambda: os.path.join(self.root, "cases")
        os.makedirs(case_store._root(), exist_ok=True)
        self.search = mock.patch.object(paper_batch.source_finder, "search_academic",
                                        return_value={"results": [], "errors": []})
        self.search.start()

    def tearDown(self):
        self.search.stop()
        case_store._root = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_problem_bundle_is_accepted_and_replays(self):
        bundle = {
            "topic": "break-even",
            "problems": [
                {"id": "be-001", "title": "t", "difficulty": "easy", "tests": "x",
                 "problem": "A product sells for USD 50 with variable cost USD 30 and fixed costs USD 100,000. Actual sales 6,000 units.",
                 "data": {"selling_price": 50, "variable_cost_per_unit": 30,
                          "fixed_costs": 100000, "actual_units": 6000},
                 "required": ["contribution_per_unit", "break_even_units"],
                 "answer": {"contribution_per_unit": 20, "break_even_units": 5000,
                            "break_even_revenue": 250000, "margin_of_safety_units": 1000},
                 "workings": "1. 50-30=20. 2. 100000/20=5000. 3. 5000*50=250000.",
                 "assumptions": ["costs are linear"], "reject": False},
                {"id": "be-009", "title": "missing fixed costs", "difficulty": "easy",
                 "tests": "refusal", "problem": "A product sells for USD 60 with variable cost USD 36.",
                 "data": {"selling_price": 60, "variable_cost_per_unit": 36},
                 "required": [], "answer": {}, "workings": "", "assumptions": [], "reject": True},
            ],
        }
        import json as _json
        raw = _json.dumps(bundle).encode()
        result = case_upload.upload("accounting", "breakeven", "break-even.json", raw)
        self.assertEqual(len(result["stored"]), 2, result)
        self.assertEqual(result["skipped"], [])
        self.assertEqual(result["errors"], [])
        from bp.product import case_runner
        for cid in result["stored"]:
            run = case_runner.run_case(cid, log=False)
            self.assertEqual(run["status"], "pass", (cid, run.get("error")))

    def test_a_multi_period_problem_is_skipped_with_a_reason(self):
        bundle = {"topic": "break-even", "problems": [
            {"id": "be-007", "problem": "two years",
             "data": {"year_1_price": 50, "year_1_variable_cost": 30, "year_1_fixed_costs": 100000},
             "answer": {}, "reject": False},
        ]}
        raw = json.dumps(bundle).encode()
        result = case_upload.upload("accounting", "breakeven", "break-even.json", raw)
        self.assertEqual(result["stored"], [])
        self.assertEqual(len(result["skipped"]), 1)
        self.assertIn("multi-period", result["skipped"][0][1])

    def test_the_bundle_topic_chooses_the_tile_not_the_selection(self):
        bundle = {"topic": "financial statement ratios", "problems": [{
            "id": "r-001",
            "problem": "Current assets 5000, current liabilities 2000, cash 800, inventory 1200, "
                       "receivables 900, payables 700, total assets 12000, total liabilities 5000, "
                       "equity 7000, revenue 20000, cost of sales 12000, operating profit 3000, net income 1800.",
            "data": {"current_assets": 5000, "current_liabilities": 2000, "cash": 800,
                     "inventory": 1200, "receivables": 900, "payables": 700, "total_assets": 12000,
                     "total_liabilities": 5000, "equity": 7000, "revenue": 20000,
                     "cost_of_sales": 12000, "operating_profit": 3000, "net_income": 1800},
            "answer": {}, "reject": False}]}
        import json as _json
        result = case_upload.upload("accounting", "breakeven", "ratios.json", _json.dumps(bundle).encode())
        self.assertEqual(result["tile"], "ratios")
        self.assertTrue(result["stored"][0].startswith("accounting/ratios/"), result)

    def test_a_single_case_json_still_works(self):
        raw = json.dumps({
            "tile": "breakeven",
            "instruction": "A store sells at 20 with variable 10 and fixed 1000.",
            "inputs": {"fixed": "1000", "price": "20", "variable": "10"},
        }).encode()
        case = case_upload.upload("accounting", "breakeven", "case.json", raw)
        self.assertEqual(case["origin"], "uploaded")


if __name__ == "__main__":
    unittest.main()
