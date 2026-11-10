"""The proposal record: validation, budget roll-up and the table rows."""

import unittest

from bp.product import proposal_plan


def record():
    return {
        "project": {"title": "Riverside Kitchen",
                    "problem": "No affordable shared kitchen.",
                    "objectives": ["Open a kitchen"],
                    "location": "Riverside", "proponents": "Alex Rivera",
                    "timeline": "6 months", "funding_source": "Grant",
                    "currency": "USD"},
        "work_plan": [{"activity": "Fit out", "duration": "3 months",
                       "deliverable": "Kitchen ready", "owner": "Builder"}],
        "budget": [{"item": "Fit-out", "amount": 30000}, {"item": "Equipment", "amount": 18000}],
        "risks": [{"description": "Permit delay", "response": "Apply early", "owner": "PM"}],
    }


class RecordTest(unittest.TestCase):

    def test_a_complete_record_has_no_problems(self):
        self.assertEqual(proposal_plan.validate(proposal_plan.normalise(record())), [])

    def test_a_missing_objective_is_named(self):
        data = record()
        data["project"]["objectives"] = []
        problems = proposal_plan.validate(proposal_plan.normalise(data))
        self.assertTrue(any("at least one objective" in problem for problem in problems), problems)

    def test_a_budget_line_needs_an_amount_above_zero(self):
        data = record()
        data["budget"][1]["amount"] = 0
        problems = proposal_plan.validate(proposal_plan.normalise(data))
        self.assertTrue(any("budget line 2 needs an amount" in problem for problem in problems), problems)


class TableTest(unittest.TestCase):

    def test_the_budget_is_the_declared_lines_summed(self):
        data = proposal_plan.normalise(record())
        rolled = proposal_plan.rollup(data)
        self.assertEqual(rolled["total"], 48000)
        rows = proposal_plan.budget_rows(data, rolled)
        self.assertEqual(rows[-1], ["Total", "USD 48,000.00"])

    def test_the_work_plan_and_risk_rows_are_the_record(self):
        data = proposal_plan.normalise(record())
        self.assertEqual(proposal_plan.work_plan_rows(data),
                         [["Fit out", "3 months", "Kitchen ready", "Builder"]])
        self.assertEqual(proposal_plan.risk_rows(data),
                         [["Permit delay", "Apply early", "PM"]])


if __name__ == "__main__":
    unittest.main()
