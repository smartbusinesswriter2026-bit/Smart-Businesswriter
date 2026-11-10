"""The business-plan reader: structural, schema-driven, and it learns an alias."""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from bp.product import declared  # noqa: E402

CASE = """
Business name: Riverside Supplies
Business type: retail
Stage: startup
Location: a mid-sized city
Currency: USD

Funding Source            Amount
Owner equity              60000
Bank loan                 120000
Total funding available   180000

Startup Cost Item                    Amount
Security deposit and first month rent 8400
Leasehold improvements               55000
Kitchen and bakery equipment         50000
Furniture and fixtures               12000
POS and IT setup                     3500
Initial inventory                    7500
Permits and licenses                 2800
Pre-opening marketing                4000
Working capital reserve              20300
Contingency                          8000

Fixed Monthly Cost        Amount
Rent                      4200
Staff wages               9800
Utilities                 1100

Average ticket per transaction   9.50
Days open per month              26
Variable cost ratio              35%
Loan annual interest rate        7.5%
Tax rate                         25%
"""


class ReaderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bp-plan-vocab-")
        self.previous = declared.REGISTRY
        declared.REGISTRY = os.path.join(self.tmp, "plan_vocab.json")
        declared._ALIASES = None

    def tearDown(self):
        declared.REGISTRY = self.previous
        declared._ALIASES = None

    def test_fields_are_placed_by_their_labels(self):
        out = declared.read(CASE)
        self.assertEqual(out["fields"]["financial.currency"], "USD")
        self.assertEqual(out["fields"]["revenue.average_ticket"], "9.50")
        self.assertEqual(out["fields"]["revenue.days_open_per_month"], "26")
        self.assertEqual(out["fields"]["financial.tax_rate"], "0.25")
        self.assertEqual(out["fields"]["financial.loan_rate"], "0.075")

    def test_the_startup_table_is_read_with_categories(self):
        out = declared.read(CASE)
        rows = out["lines"]["startup"]
        self.assertEqual(len(rows), 10)
        by_label = {row["label"]: row for row in rows}
        self.assertEqual(by_label["Leasehold improvements"]["amount"], "55000")
        self.assertEqual(by_label["Leasehold improvements"]["category"], "premises")
        self.assertEqual(by_label["Working capital reserve"]["category"], "working_capital")

    def test_the_fixed_and_funding_tables_are_separate(self):
        out = declared.read(CASE)
        self.assertEqual(len(out["lines"]["fixed"]), 3)
        self.assertEqual(len(out["lines"]["funding"]), 3)

    def test_an_unknown_label_is_returned_not_dropped(self):
        text = CASE + "\nPet grooming licence  300\n"
        out = declared.read(text)
        labels = [row["label"] for row in out["unplaced"]]
        self.assertIn("Pet grooming licence", labels)

    def test_a_business_name_is_read_from_the_title_or_the_prose(self):
        self.assertEqual(
            declared.read("Case Study: Creating a Business Plan - Harbor & Hearth Bakery-Cafe")["fields"]["business.name"],
            "Harbor & Hearth Bakery-Cafe")
        self.assertEqual(
            declared.read("Maria is preparing a business plan for Riverside Traders in a small town.")["fields"]["business.name"],
            "Riverside Traders")

    def test_a_plan_is_recognised_by_its_tables_not_a_cue(self):
        self.assertTrue(declared.is_business_plan(CASE))
        self.assertFalse(declared.is_business_plan(
            "Startup costs are rising across the industry. Analyse the competitive forces."))

    def test_a_growth_multiplier_is_read_as_a_rate(self):
        out = declared.read("Year 2 revenue assumption: Year 1 revenue x 1.08\n")
        self.assertEqual(out["fields"]["revenue.year_1_growth"], "0.08")

    def test_a_learned_alias_is_used_by_the_next_case(self):
        text = CASE + "\nTurnover per head  12.50\n"
        before = declared.read(text)
        self.assertIn("Turnover per head", [row["label"] for row in before["unplaced"]])
        declared.learn("Turnover per head", "revenue.average_ticket")
        declared._ALIASES = None
        after = declared.read(text)
        self.assertEqual(after["fields"]["revenue.average_ticket"], "12.50")
        self.assertNotIn("Turnover per head", [row["label"] for row in after["unplaced"]])


if __name__ == "__main__":
    unittest.main()
