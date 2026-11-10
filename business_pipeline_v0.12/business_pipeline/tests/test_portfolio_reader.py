"""The portfolio table reader: it reads a table, and names what is missing."""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import portfolio_reader  # noqa: E402

BRIEF = """Portfolio | Market | Market growth | Own share | Top competitor share | Revenue
Kestrel Fresh | grocery retail | 4% | 25% | 20% | 1200
Kestrel Home | household goods | 1% | 10% | 30% | 300
"""


class PortfolioReaderTest(unittest.TestCase):
    def test_a_markdown_table_is_read(self):
        result = portfolio_reader.read(BRIEF)
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["units"]), 2)
        first = result["units"][0]
        self.assertEqual(first["unit"], "Kestrel Fresh")
        self.assertEqual(first["market"], "grocery retail")
        self.assertAlmostEqual(first["growth"], 0.04)
        self.assertAlmostEqual(first["own_share"], 0.25)
        self.assertAlmostEqual(first["competitor_share"], 0.20)
        self.assertAlmostEqual(first["revenue"], 1200.0)

    def test_a_missing_share_is_named_not_guessed(self):
        brief = ("Unit | Market | Growth | Own share\n"
                 "A | grocery | 4% | 25%\n")
        result = portfolio_reader.read(brief)
        self.assertTrue(result["ok"])
        self.assertIsNone(result["units"][0]["competitor_share"])
        self.assertTrue(any("competitor share" in problem.lower()
                            for problem in result["problems"]), result["problems"])

    def test_no_table_is_a_named_problem(self):
        result = portfolio_reader.read("A firm is reviewing its portfolio.")
        self.assertFalse(result["ok"])
        self.assertIn("portfolio table", result["problems"][0].lower())

    def test_a_tab_table_works(self):
        brief = ("Unit\tMarket\tGrowth\tOwn share\tTop competitor share\n"
                 "A\tgrocery\t4%\t25%\t20%\n")
        result = portfolio_reader.read(brief)
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["units"]), 1)


if __name__ == "__main__":
    unittest.main()
