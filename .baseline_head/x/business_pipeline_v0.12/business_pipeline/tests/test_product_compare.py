import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import compare, versions  # noqa: E402


def versioned(npv="50.00", outputs_hash=None, method="npv", unit=None):
    bundle = product_fixtures.make_bundle()
    bundle["method"] = method
    bundle["reperform"]["outputs"] = {"npv": npv}
    if outputs_hash is not None:
        bundle["outputs_hash"] = outputs_hash
    if unit is not None:
        bundle["delivery"]["appendix"]["artifacts"] = [["npv", ["npv", "annual", "entity", "base"], "npv formula"]]
        bundle["delivery"]["appendix"]["method"]["version"] = "1.2.0"
    return bundle


class CompareTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-compare-test-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def store(self, *bundles):
        case_id = None
        for bundle in bundles:
            case_id, _ = versions.append(bundle, case_id)
        return case_id

    def test_compares_stored_values_verbatim(self):
        case_id = self.store(versioned("50.00", "sha256:out-1"), versioned("60.00", "sha256:out-2"))
        result = compare.compare(case_id)
        self.assertEqual(result["format"], "bp-comparison/1")
        self.assertEqual([column["version"] for column in result["columns"]], [1, 2])
        row = result["rows"][0]
        self.assertEqual(row["metric"], "npv")
        self.assertEqual(row["values"], {"1": "50.00", "2": "60.00"})
        self.assertEqual(row["not_computed"], [])
        fields = {item["field"] for item in result["differences"]}
        self.assertIn("outputs_hash", fields)
        self.assertEqual([item["version"] for item in result["disclosure"]], [1, 2])
        self.assertTrue(all(item["bundle_hash"] for item in result["disclosure"]))

    def test_a_missing_metric_is_reported_as_not_computed(self):
        bundle = versioned("50.00")
        bundle["delivery"]["appendix"]["artifacts"] = [
            ["npv", ["npv", "annual", "entity", "base"], "npv formula"],
            ["irr", ["irr", "annual", "entity", "base"], "irr formula"],
        ]
        bundle["reperform"]["outputs"] = {"npv": "50.00", "irr": "0.21"}
        case_id = self.store(bundle, versioned("60.00"))
        result = compare.compare(case_id)
        irr = [row for row in result["rows"] if row["metric"] == "irr"][0]
        self.assertEqual(irr["not_computed"], [2])
        self.assertIsNone(irr["values"]["2"])

    def test_different_methods_are_refused(self):
        case_id = self.store(versioned("50.00"), versioned("60.00", method="irr"))
        with self.assertRaises(compare.CompareError):
            compare.compare(case_id)

    def test_a_comparison_needs_two_versions(self):
        case_id = self.store(versioned("50.00"))
        with self.assertRaises(compare.CompareError):
            compare.compare(case_id)

    def test_the_html_export_copies_the_stored_values(self):
        case_id = self.store(versioned("50.00"), versioned("60.00"))
        result = compare.compare(case_id)
        path = os.path.join(self.root, "comparison.html")
        compare.render_html(result, path)
        document = open(path, encoding="utf-8").read()
        self.assertIn("50.00", document)
        self.assertIn("60.00", document)
        self.assertIn("nothing in this file was recomputed", document)
        self.assertIn("v1", document)
        self.assertNotIn("999", document)


if __name__ == "__main__":
    unittest.main()
