"""The quality table reader: it reads the worksheet, and names a missing column."""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import quality_reader  # noqa: E402

FMEA = """ID | Failure mode | S | O | D | Recommended action
1 | Seal leaks | 7 | 4 | 3 | Change the seal material
2 | Wrong part | 4 | 6 | 2 | Add a poka-yoke
"""

FIVE_S = """S | Criterion | Score | Maximum
Sort | Unneeded items | 3 | 4
Sort | Clear rules | 2 | 4
Shine | Clean floors | 4 | 4
"""

PDCA = """Measure | Baseline | Target | Result
Cosmetic rejects | 4.2% | 1.0% | 1.1%
"""


class QualityReaderTest(unittest.TestCase):
    def test_the_fmea_table_is_read(self):
        result = quality_reader.read_fmea(FMEA)
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["rows"]), 2)
        first = result["rows"][0]
        self.assertEqual(first["failure"], "Seal leaks")
        self.assertEqual(first["severity"], 7.0)
        self.assertEqual(first["occurrence"], 4.0)
        self.assertEqual(first["detection"], 3.0)

    def test_the_five_s_scorecard_is_read(self):
        result = quality_reader.read_five_s(FIVE_S)
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["rows"]), 3)
        self.assertEqual(result["rows"][0]["category"], "Sort")
        self.assertEqual(result["rows"][0]["score"], 3.0)

    def test_the_pdca_measure_table_is_read(self):
        result = quality_reader.read_pdca(PDCA)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["rows"][0]["measure"], "Cosmetic rejects")

    def test_a_missing_column_is_named(self):
        result = quality_reader.read_fmea("Failure mode | Severity\nSeal leaks | 7\n")
        self.assertFalse(result["ok"])
        self.assertIn("occurrence", result["problems"][0].lower())


if __name__ == "__main__":
    unittest.main()
