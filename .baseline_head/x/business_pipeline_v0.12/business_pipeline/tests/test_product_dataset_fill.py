"""Acceptance suite for proposing a method's inputs from an attached table (E-map-001…005).

C is a surface, not new maths: the frozen core already maps columns to a method's
declared inputs and refuses what a column cannot feed.  What is tested here is that the
product reaches that mapper from a **stored** file, that every refusal keeps the core's
own words, and that **nothing is executed** — the student gets values to confirm.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")

from bp import ingest  # noqa: E402
from bp.product import intake  # noqa: E402

CSV = b"region,sales\nnorth,10\nsouth,20\neast,30\n"
TEXT = b"region,sales\nnorth,10\n"


def _store(name, raw, table=True):
    record = intake.save(name, raw)
    if table:
        intake.attach_table(record["id"], ingest.read_table(name, raw))
    return record["id"]


class DatasetFillTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-fill-test-")
        self.previous = os.environ.get("BP_INTAKE_DIR")
        os.environ["BP_INTAKE_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_INTAKE_DIR", None)
        else:
            os.environ["BP_INTAKE_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_e_map_001__a_column_feeds_a_list_input_through_the_cores_own_mapper(self):
        file_id = _store("sales.csv", CSV)
        mapped = intake.mapped_request(file_id, "descriptive_stats", {"values": "sales"})
        self.assertEqual(mapped["method"], "descriptive_stats")
        self.assertEqual(mapped["inputs"]["values"], ["10", "20", "30"],
                         "the mapper carries the values as the file holds them; number "
                         "coercion is the frozen method's job, and it does it")
        self.assertIn("missing_codes", mapped["not_mapped"],
                      "an input the student did not map is named, never invented")

    def test_e_map_002__an_unknown_column_is_refused_in_the_cores_words(self):
        file_id = _store("sales.csv", CSV)
        with self.assertRaises(intake.IntakeError) as refused:
            intake.mapped_request(file_id, "descriptive_stats", {"values": "revenue"})
        self.assertIn("unknown column", str(refused.exception))
        self.assertIn("sales", str(refused.exception), "the message lists the columns that do exist")

    def test_e_map_003__an_unknown_method_is_refused_by_name(self):
        file_id = _store("sales.csv", CSV)
        with self.assertRaises(intake.IntakeError) as refused:
            intake.mapped_request(file_id, "no_such_method", {"values": "sales"})
        self.assertIn("unknown method", str(refused.exception))

    def test_e_map_004__a_scalar_input_cannot_be_pulled_from_a_column(self):
        file_id = _store("sales.csv", CSV)
        with self.assertRaises(intake.IntakeError) as refused:
            intake.mapped_request(file_id, "ratio_analysis", {"current_assets": "sales"})
        self.assertIn("cannot be mapped from a column", str(refused.exception),
                      "the core's own refusal is passed on unchanged")

    def test_e_map_005__a_mapping_proposes_values_and_executes_nothing(self):
        file_id = _store("sales.csv", CSV)
        mapped = intake.mapped_request(file_id, "descriptive_stats", {"values": "sales"})
        for key in ("report", "delivery", "session", "result", "checks"):
            self.assertNotIn(key, mapped,
                             "a mapping is a proposal; nothing may be computed by it")
        self.assertEqual(sorted(mapped), sorted(["method", "inputs", "provenance",
                                                 "input_provenance", "data_manifest", "not_mapped"]))

    def test_e_map_006__a_file_that_is_not_a_table_is_refused_by_name(self):
        record = intake.save("memo.pdf", b"%PDF-1.4 not really a pdf")
        with self.assertRaises(intake.IntakeError) as refused:
            intake.mapped_request(record["id"], "descriptive_stats", {"values": "sales"})
        self.assertIn("not a table", str(refused.exception))


if __name__ == "__main__":
    unittest.main()
