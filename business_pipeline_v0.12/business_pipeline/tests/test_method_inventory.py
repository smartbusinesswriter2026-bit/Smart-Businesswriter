"""The method inventory: one generated record per frozen method, no drift.

These tests pin the completeness the product depends on.  A method that exists in
the core but has no catalogue record, no status, no schema, or no data shape is
a failure here -- the product must never silently lose a computation.
"""

import json
import os
import unittest
from pathlib import Path

from bp import methods
from bp.product import capabilities, method_catalogue, subjects

HERE = Path(__file__).resolve()
CATALOGUE_PATH = (HERE.parent.parent / "src" / "bp" / "product" / "data"
                  / "method_catalogue_v1.json")

EXPECTED_LIBRARY = 218


class LibraryCompletenessTest(unittest.TestCase):
    def test_the_library_exposes_every_method_from_one_import(self):
        # finance_methods registers the additional computations at import; a bare
        # ``import bp.methods`` must already see all of them (no import-order drift).
        self.assertEqual(len(methods.LIBRARY), EXPECTED_LIBRARY)

    def test_every_method_has_a_status_schema_and_data_shapes(self):
        for method_id, method in methods.LIBRARY.items():
            described = methods.describe(method_id)
            self.assertIn(described["tier"], ("T1", "T2", "T3", "T4"), method_id)
            self.assertTrue(method.input_schema, method_id)
            for name, spec in method.input_schema.items():
                self.assertIn("type", spec, (method_id, name))
                self.assertTrue(spec.get("desc"), (method_id, name))

    def test_every_method_is_in_the_catalogue(self):
        catalogue = method_catalogue.build()
        keys = {row["key"] for row in catalogue["methods"]}
        self.assertEqual(keys, set(methods.LIBRARY))
        self.assertEqual(len(catalogue["methods"]), EXPECTED_LIBRARY)

    def test_every_catalogue_record_is_complete(self):
        for row in method_catalogue.build()["methods"]:
            self.assertIn(row["status"], method_catalogue.STATUSES, row["key"])
            self.assertIn("type", next(iter(row["schema"].values()), {}) or {}, row["key"])
            self.assertTrue(row["data_shapes"], row["key"])
            self.assertIn(row["tier"], ("T1", "T2", "T3", "T4"), row["key"])

    def test_every_paper_capability_exists_in_the_library(self):
        library = set(methods.LIBRARY)
        for key, row in capabilities.ENTRIES.items():
            method = row["method"]
            if method in ("business_plan",):
                continue  # a service, not a frozen method
            self.assertIn(method, library, key)

    def test_every_tool_method_exists_in_the_library(self):
        library = set(methods.LIBRARY)
        for key, row in subjects.TOOL_INFO.items():
            method = row.get("method")
            if method in ("case_decision",):
                continue  # a template, not a frozen method
            self.assertIn(method, library, key)

    def test_the_committed_catalogue_matches_the_library(self):
        if not CATALOGUE_PATH.exists():
            self.fail("run scripts/build_method_catalogue.py to regenerate the catalogue")
        committed = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(committed["format"], method_catalogue.FORMAT)
        self.assertEqual(committed["methods"], method_catalogue.build()["methods"])
        self.assertEqual(committed["source"], method_catalogue.build()["source"])


class CountSanityTest(unittest.TestCase):
    def test_no_method_is_uncatalogued(self):
        # 216 methods, 126 paper + 87 tile + 2 service = 216; zero internal/deprecated
        # until the Phase 0.5 status review classifies the 73 proposed additions.
        by_status = {}
        for row in method_catalogue.build()["methods"]:
            by_status[row["status"]] = by_status.get(row["status"], 0) + 1
        self.assertEqual(sum(by_status.values()), EXPECTED_LIBRARY)
        self.assertEqual(by_status.get("paper"), 126)
        self.assertEqual(by_status.get("service"), 2)

    def test_the_reported_counts_are_self_consistent(self):
        source = method_catalogue.build()["source"]
        self.assertEqual(source["library"], EXPECTED_LIBRARY)
        self.assertEqual(source["calc_inputs_methods"], EXPECTED_LIBRARY)
        self.assertEqual(source["statement_specs"], 128)
        self.assertGreater(source["frameworks"], 200)


if __name__ == "__main__":
    unittest.main()
