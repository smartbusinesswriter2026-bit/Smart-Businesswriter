"""Statement reader for the Portfolio Lab (Slice 2).

Reads a financial statement (CSV/TSV/text) and extracts the line items a
student's classroom ratios need.  Missing lines are named gaps, never zeros.
"""

import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))

from bp.product import statement_reader  # noqa: E402


class ReadTest(unittest.TestCase):
    def test_reads_a_csv_statement(self):
        text = ("Line,Amount\n"
                "Revenue,1000\n"
                "Cost of goods sold,400\n"
                "Gross profit,600\n"
                "Net income,120\n"
                "Total assets,800\n"
                "Current assets,300\n"
                "Current liabilities,150\n"
                "Inventory,50\n"
                "Total liabilities,320\n"
                "Shareholders equity,480\n"
                "Earnings per share,2.4\n"
                "Book value per share,9.6\n")
        result = statement_reader.read(text)
        self.assertEqual(result["lines"]["revenue"], 1000.0)
        self.assertEqual(result["lines"]["net_income"], 120.0)
        self.assertEqual(result["lines"]["total_assets"], 800.0)
        self.assertAlmostEqual(result["ratios"]["gross_margin"], 0.6)
        self.assertAlmostEqual(result["ratios"]["net_margin"], 0.12)
        self.assertAlmostEqual(result["ratios"]["current_ratio"], 2.0)
        self.assertAlmostEqual(result["ratios"]["quick_ratio"], (300 - 50) / 150)
        self.assertAlmostEqual(result["ratios"]["debt_to_equity"], 320 / 480)
        self.assertAlmostEqual(result["ratios"]["roa"], 120 / 800)
        self.assertAlmostEqual(result["ratios"]["roe"], 120 / 480)
        # altman_z and piotroski_f need statement lines this CSV does not carry
        self.assertEqual(result["gaps"], ["altman_z", "piotroski_f"])

    def test_missing_lines_are_named_gaps(self):
        text = "Revenue,1000\nNet income,120\n"
        result = statement_reader.read(text)
        self.assertEqual(result["lines"]["revenue"], 1000.0)
        self.assertIn("roa", result["gaps"])
        self.assertIn("current_ratio", result["gaps"])
        # computed ratios that depend on missing lines are absent
        self.assertNotIn("roa", result["ratios"])
        self.assertNotIn("current_ratio", result["ratios"])

    def test_no_invented_values(self):
        result = statement_reader.read("Revenue,1000\n")
        self.assertEqual(result["lines"], {"revenue": 1000.0})
        self.assertEqual(result["ratios"], {})
        self.assertTrue(result["gaps"])

    def test_altman_z_when_all_lines_present(self):
        text = ("Revenue,1000\nNet income,120\nTotal assets,800\n"
                "Current assets,300\nCurrent liabilities,150\n"
                "Retained earnings,200\nEBIT,180\nTotal liabilities,320\n"
                "Market value of equity,960\n")
        result = statement_reader.read(text)
        self.assertIn("altman_z", result["ratios"])
        self.assertAlmostEqual(result["ratios"]["altman_z"],
                               1.2 * (300 - 150) / 800
                               + 1.4 * 200 / 800
                               + 3.3 * 180 / 800
                               + 0.6 * 960 / 320
                               + 1.0 * 1000 / 800, places=4)

    def test_dupont_and_graham_when_lines_present(self):
        text = ("Net income,120\nRevenue,1000\nTotal assets,800\n"
                "Shareholders equity,480\nEarnings per share,2.4\n"
                "Book value per share,9.6\n")
        result = statement_reader.read(text)
        self.assertIn("dupont_roe", result["ratios"])
        self.assertIn("graham_number", result["ratios"])
        self.assertAlmostEqual(result["ratios"]["graham_number"],
                               (22.5 * 2.4 * 9.6) ** 0.5, places=4)

    def test_reads_colon_and_tab_separators(self):
        text = "Revenue:\t1000\nNet income: 120\n"
        result = statement_reader.read(text)
        self.assertEqual(result["lines"]["revenue"], 1000.0)
        self.assertEqual(result["lines"]["net_income"], 120.0)

    def test_unknown_lines_are_ignored_not_invented(self):
        result = statement_reader.read("Revenue,1000\nFoo bar,999\n")
        self.assertEqual(result["lines"], {"revenue": 1000.0})
        self.assertNotIn("foo", result["lines"])


if __name__ == "__main__":
    unittest.main()
