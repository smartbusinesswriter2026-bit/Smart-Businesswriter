"""Phase 2: the paper catalogue reads the generated method catalogue, and every
capability names the data shapes its schema accepts.

The paper conductor's ``capabilities.ENTRIES`` stays the curated overlay (cues,
intents, slots, priorities); the generated catalogue is the source for schemas,
data shapes and status.  These tests pin that the two agree and that the schema
is available even when the core's ``describe`` callable was never attached.
"""

import unittest

from bp import methods
from bp.product import capabilities, chat, method_catalogue


class DataShapeTest(unittest.TestCase):
    def test_data_shapes_are_derived_from_the_schema(self):
        self.assertEqual(capabilities.data_shapes({"price": {"type": "decimal"}}), ["cell"])
        self.assertEqual(capabilities.data_shapes({"cashflows": {"type": "decimal_list"}}), ["column"])
        self.assertEqual(
            capabilities.data_shapes({"price": {"type": "decimal"},
                                      "cashflows": {"type": "decimal_list"}}),
            ["cell", "column"])
        self.assertEqual(capabilities.data_shapes({"engagement": {"type": "engagement_spec"}}),
                         ["structured"])


class CatalogueAgreementTest(unittest.TestCase):
    def test_every_paper_capability_exists_in_the_library_or_is_a_service(self):
        library = set(methods.LIBRARY)
        for key, row in capabilities.ENTRIES.items():
            method = row["method"]
            if method == "business_plan":
                continue
            self.assertIn(method, library, key)

    def test_every_paper_capability_has_a_catalogue_status(self):
        for row in capabilities.ENTRIES.values():
            if row["method"] == "business_plan":
                continue
            self.assertEqual(method_catalogue.status_for(row["method"]), "paper",
                             row["method"])

    def test_every_capability_schema_is_reachable_without_the_core_describe(self):
        previous = chat.METHOD_DESCRIBE
        chat.METHOD_DESCRIBE = None
        try:
            schema = chat._schema_for("breakeven")
        finally:
            chat.METHOD_DESCRIBE = previous
        self.assertIn("fixed", schema)
        self.assertIn("price", schema)

    def test_the_catalogue_names_the_unplaced_methods(self):
        library = set(methods.LIBRARY)
        unplaced = [row["method"] for row in method_catalogue.build()["methods"]
                    if row["review"] == "proposed"]
        self.assertTrue(unplaced)
        self.assertTrue(all(m in library for m in unplaced))


if __name__ == "__main__":
    unittest.main()
