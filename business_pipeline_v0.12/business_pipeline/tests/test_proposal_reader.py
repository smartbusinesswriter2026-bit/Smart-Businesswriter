"""The proposal record: work plan, budget and risks read from the brief's tables."""

import unittest

from bp.product import proposal_plan, proposal_reader

BRIEF = """
Project proposal for the Riverside Community Kitchen.
Project: Riverside Community Kitchen
Problem: The neighbourhood has no affordable shared kitchen.
Objectives: Open a shared kitchen; Serve 200 meals a week
Location: Riverside
Proponents: Alex Rivera
Timeline: 6 months
Funding source: Community grant
Currency: USD
Indicators: Meals served a week
Targets: 200 meals a week by month six
Risks: Permit delay; Equipment lead time

Work plan
Activity | Duration | Deliverable | Owner
Secure the lease | 1 month | Signed lease | Project manager
Fit out the kitchen | 3 months | Kitchen ready | Builder
Open the service | 1 month | 200 meals a week | Team

Budget
Item | Amount
Fit-out | 30000
Equipment | 18000
Working capital | 6000
"""

PARTIAL = """
Project proposal for a repair workshop.
Project: Repair workshop
Problem: Appliances break and nobody repairs them.

Work plan
Activity | Duration | Deliverable | Owner
Repair appliances | 1 month | Working appliances | Technician
"""


class ReaderTest(unittest.TestCase):

    def test_the_tables_become_a_valid_record(self):
        record = proposal_reader.read(BRIEF)
        self.assertTrue(proposal_reader.has_tables(record))
        self.assertEqual(proposal_plan.validate(proposal_plan.normalise(record)), [])

    def test_the_project_labels_reach_the_record(self):
        project = proposal_reader.read(BRIEF)["project"]
        self.assertEqual(project["title"], "Riverside Community Kitchen")
        self.assertEqual(project["objectives"], ["Open a shared kitchen", "Serve 200 meals a week"])
        self.assertEqual(project["timeline"], "6 months")
        self.assertEqual(project["targets"], ["200 meals a week by month six"])

    def test_the_work_plan_and_budget_are_read_by_their_columns(self):
        record = proposal_reader.read(BRIEF)
        self.assertEqual([row["activity"] for row in record["work_plan"]],
                         ["Secure the lease", "Fit out the kitchen", "Open the service"])
        self.assertEqual(record["work_plan"][1]["owner"], "Builder")
        self.assertEqual(record["budget"][0], {"item": "Fit-out", "amount": 30000})

    def test_a_missing_budget_is_named_not_filled(self):
        record = proposal_reader.read(PARTIAL)
        self.assertEqual(record["budget"], [])
        problems = proposal_plan.validate(proposal_plan.normalise(record))
        self.assertTrue(any("budget needs at least one line" in problem for problem in problems), problems)

    def test_a_narrative_brief_is_not_the_work_plan_route(self):
        self.assertFalse(proposal_reader.has_tables(
            proposal_reader.read("Project proposal for a community garden.")))


if __name__ == "__main__":
    unittest.main()
