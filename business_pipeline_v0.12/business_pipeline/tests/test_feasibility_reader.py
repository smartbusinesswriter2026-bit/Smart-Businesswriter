"""The simplified feasibility record: three declared tables, nothing filled."""

import unittest

from bp.product import feasibility_plan, feasibility_reader

BRIEF = """
Feasibility study for the Riverside Community Kitchen.
Project: Riverside Community Kitchen
Description: Open a community kitchen that serves 200 meals a week.
Location: Riverside
Proponents: Alex Rivera
Currency: USD
Target market: local households
Risks: Permit delay; Equipment lead time

Market and demand
Item | Value
Target market | local households
Demand a year | 12000
Price per unit | 8

Costs
Item | Amount
Kitchen fit-out | 30000
Equipment | 18000
Working capital | 6000
Fixed cost a year | 24000
Variable cost per unit | 3
"""

PARTIAL = """
Feasibility study for a repair workshop.
Project: Repair workshop
Description: Repair household appliances.

Market
Item | Value
Target market | local households

Costs
Item | Amount
Tools | 5000
"""


class ReaderTest(unittest.TestCase):

    def test_the_three_tables_become_a_valid_record(self):
        record = feasibility_reader.read(BRIEF)
        self.assertTrue(feasibility_reader.has_tables(record))
        self.assertEqual(feasibility_plan.validate(feasibility_plan.normalise(record)), [])

    def test_the_project_labels_reach_the_record(self):
        project = feasibility_reader.read(BRIEF)["project"]
        self.assertEqual(project["name"], "Riverside Community Kitchen")
        self.assertEqual(project["proponents"], "Alex Rivera")
        self.assertEqual(project["currency"], "USD")

    def test_the_market_and_cost_rows_are_read_by_their_labels(self):
        record = feasibility_reader.read(BRIEF)
        self.assertEqual(record["market"]["demand"], 12000)
        self.assertEqual(record["market"]["price"], 8)
        self.assertEqual(record["operating"], {"fixed": 24000, "variable": 3})
        self.assertEqual([row["item"] for row in record["costs"]],
                         ["Kitchen fit-out", "Equipment", "Working capital"])

    def test_a_missing_figure_stays_missing_and_is_named(self):
        record = feasibility_reader.read(PARTIAL)
        self.assertIsNone(record["market"]["demand"])
        self.assertIsNone(record["market"]["price"])
        self.assertIsNone(record["operating"]["fixed"])
        problems = feasibility_plan.validate(feasibility_plan.normalise(record))
        self.assertTrue(any("demand above zero" in problem for problem in problems), problems)
        self.assertTrue(any("fixed cost" in problem for problem in problems), problems)

    def test_a_narrative_brief_is_not_the_three_table_route(self):
        self.assertFalse(feasibility_reader.has_tables(
            feasibility_reader.read("Feasibility study for a 50-seat cafe.")))


if __name__ == "__main__":
    unittest.main()
