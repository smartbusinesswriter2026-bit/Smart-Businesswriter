"""Read a project brief into the project-plan record: tables first, nothing invented."""

import unittest

from bp.product import project_plan, project_reader

BRIEF = """
Project plan for the Riverside Community Kitchen.
Objective: Open a community kitchen that serves 200 meals a week.
Sponsor: Riverside Trust
Project manager: Alex Rivera
Budget: 48000
Currency: USD
Start date: 2026-01-05
End date: 2026-06-30
In scope: Kitchen fit-out; Permit applications
Out of scope: Delivery service
Deliverables: Kitchen open; Permit issued
Success measures: 200 meals a week by month six
Assumptions: The lease is signed before work starts
Constraints: The kitchen must open before June

WBS
ID | Work package | Owner | Cost | Acceptance
A1 | Design the kitchen | Architect | 6000 | Drawings signed
A2 | Apply for the permit | Project manager | 2000 | Permit issued
A3 | Fit out the kitchen | Builder | 30000 | Handover signed
A4 | Install equipment | Supplier | 10000 | Equipment commissioned

Activities
ID | Activity | Duration | Predecessors | Resource
A1 | Design | 10 | | Architect
A2 | Permit | 15 | A1 | Project manager
A3 | Fit out | 20 | A2 | Builder
A4 | Install | 5 | A3 | Supplier

Resources
Name | Role | Capacity
Architect | Design | 1
Project manager | Management | 1
Builder | Build | 1
Supplier | Equipment | 1

RACI
Activity | Role | Letter
A1 | Design | R
A1 | Management | A
A2 | Management | R
A2 | Management | A
A3 | Build | R
A3 | Management | A
A4 | Equipment | R
A4 | Management | A

Risks
ID | Risk | Likelihood | Impact | Response | Owner
R1 | Permit delay | Medium | High | Apply early | Project manager
"""

PARTIAL = """
Project plan for a small repair workshop.

WBS
ID | Work package | Owner | Cost | Acceptance
1  | Prepare the site |  |  | 
"""


class ReaderTest(unittest.TestCase):

    def test_a_complete_brief_becomes_a_valid_record(self):
        record = project_reader.read(BRIEF)
        self.assertEqual(project_plan.validate(project_plan.normalise(record)), [])

    def test_the_charter_reads_the_labelled_facts(self):
        charter = project_reader.read(BRIEF)["charter"]
        self.assertEqual(charter["title"], "the Riverside Community Kitchen")
        self.assertEqual(charter["sponsor"], "Riverside Trust")
        self.assertEqual(charter["budget_total"], 48000)
        self.assertEqual(charter["scope_in"], ["Kitchen fit-out", "Permit applications"])
        self.assertIn("Kitchen open", charter["deliverables"])

    def test_the_wbs_and_activity_tables_are_read_with_their_costs(self):
        record = project_reader.read(BRIEF)
        self.assertEqual([row["id"] for row in record["wbs"]], ["A1", "A2", "A3", "A4"])
        self.assertEqual(record["wbs"][0]["cost"], 6000)
        self.assertEqual(record["wbs"][0]["owner"], "Architect")
        self.assertEqual(record["activities"][2]["duration"], 20)
        self.assertEqual(record["activities"][2]["predecessors"], ["A2"])

    def test_an_activity_points_at_the_wbs_row_with_its_id(self):
        record = project_reader.read(BRIEF)
        self.assertEqual([row["wbs"] for row in record["activities"]],
                         ["A1", "A2", "A3", "A4"])

    def test_the_raci_matrix_and_the_risk_register_are_read(self):
        record = project_reader.read(BRIEF)
        self.assertEqual(len(record["raci"]), 8)
        self.assertEqual(record["raci"][1], {"activity": "A1", "role": "Management",
                                             "letter": "A"})
        self.assertEqual(record["risks"][0]["owner"], "Project manager")
        self.assertEqual(record["risks"][0]["impact"], "High")

    def test_a_missing_cell_stays_missing_and_is_named(self):
        record = project_reader.read(PARTIAL)
        self.assertIsNone(record["wbs"][0]["cost"])
        self.assertEqual(record["wbs"][0]["owner"], "")
        problems = project_plan.validate(project_plan.normalise(record))
        self.assertTrue(any("1 has no cost" in problem for problem in problems), problems)
        self.assertTrue(any("1 has no owner" in problem for problem in problems), problems)

    def test_a_dotted_parent_is_read_only_when_that_row_exists(self):
        with_parent = """
Project plan for a kitchen.
ID | Work package | Owner | Cost | Acceptance
1   | Design       | Architect | 1000 | Signed
1.1 | Drawings     | Architect | 2000 | Signed
"""
        flat = """
Project plan for a kitchen.
ID | Work package | Owner | Cost | Acceptance
1.1 | Drawings     | Architect | 2000 | Signed
"""
        self.assertEqual(project_reader.read(with_parent)["wbs"][1]["parent"], "1")
        self.assertIsNone(project_reader.read(flat)["wbs"][0]["parent"])

    def test_a_missing_resource_role_is_not_invented(self):
        record = project_reader.read("""
Project plan for a kitchen.
ID | Task | Duration | Resource
A1 | Draw | 5 | Architect
""")
        self.assertEqual(record["resources"], [{"name": "Architect", "role": "",
                                                "capacity": None}])

    def test_the_first_line_is_the_title_when_no_label_states_one(self):
        record = project_reader.read("""
Kitchen project, opening in June.
Objective: Open a community kitchen.
Sponsor: Riverside Trust
""")
        self.assertEqual(record["charter"]["title"], "Kitchen project, opening in June")


class DetectionTest(unittest.TestCase):

    def test_a_wbs_brief_is_a_project_plan(self):
        self.assertTrue(project_reader.is_project_plan(BRIEF))
        self.assertTrue(project_reader.is_project_plan("Write the WBS for the move."))

    def test_a_proposal_is_not_a_project_plan(self):
        self.assertFalse(project_reader.is_project_plan(
            "Project proposal for a community garden."))


class DemandTest(unittest.TestCase):

    def test_a_demand_column_reaches_the_activity(self):
        brief = BRIEF.replace("| Predecessors | Resource",
                              "| Predecessors | Resource | Demand")
        brief = brief.replace("A2 | Permit | 15 | A1 | Project manager",
                              "A2 | Permit | 15 | A1 | Project manager | 1")
        record = project_reader.read(brief)
        self.assertEqual(record["activities"][1]["demand"], 1)

    def test_a_blank_demand_is_missing_not_zero(self):
        record = project_plan.normalise(project_reader.read(BRIEF))
        self.assertIsNone(record["activities"][0]["demand"])


class DeclaredSourcesTest(unittest.TestCase):
    """The sources the brief declares reach the record, as the student wrote them."""

    def test_a_sources_line_reaches_the_record(self):
        brief = BRIEF + "\nSources: City Health Department (2025). Community Kitchen Guidelines\n"
        record = project_plan.normalise(project_reader.read(brief))
        self.assertEqual(record["sources"],
                         ["City Health Department (2025). Community Kitchen Guidelines"])

    def test_several_sources_on_one_line_are_separate_entries(self):
        brief = BRIEF + ("\nSources: City Health Department (2025). Guidelines; "
                         "Ministry of Health (2024). Food Safety Code\n")
        record = project_plan.normalise(project_reader.read(brief))
        self.assertEqual(len(record["sources"]), 2)

    def test_a_funding_source_is_not_a_source_list(self):
        brief = BRIEF.replace("Budget: 48000", "Budget: 48000\nFunding source: Community grant")
        record = project_plan.normalise(project_reader.read(brief))
        self.assertEqual(record["sources"], [])

    def test_a_sources_table_becomes_one_entry_per_row(self):
        brief = BRIEF + "\nSources\nSource | Author | Year\n"
        brief += "Community Kitchen Guidelines | City Health Department | 2025\n"
        record = project_plan.normalise(project_reader.read(brief))
        self.assertEqual(len(record["sources"]), 1)
        self.assertIn("Community Kitchen Guidelines", record["sources"][0])

    def test_a_brief_with_no_sources_declares_none(self):
        record = project_plan.normalise(project_reader.read(BRIEF))
        self.assertEqual(record["sources"], [])


if __name__ == "__main__":
    unittest.main()
