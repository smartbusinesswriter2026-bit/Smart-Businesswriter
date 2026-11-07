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


if __name__ == "__main__":
    unittest.main()
