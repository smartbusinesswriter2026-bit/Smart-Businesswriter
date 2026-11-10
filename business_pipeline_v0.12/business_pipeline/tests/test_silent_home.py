"""Home, silent: one brief in, one paper out, one download per paper."""

import io
import json
import os
import sys
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from bp import methods  # noqa: E402
from bp.product import business_plan, chat, providers  # noqa: E402

CASE = """
Business name: Riverside Supplies
Business type: retail
Stage: startup
Location: a mid-sized city
Currency: USD

Funding Source        Amount
Owner equity          60000
Bank loan             120000

Startup Cost Item                     Amount
Leasehold improvements                55000
Kitchen and bakery equipment          50000
Furniture and fixtures                12000
Initial inventory                     7500
Working capital reserve               20300
Contingency                           8000

Fixed Monthly Cost        Amount
Rent                      4200
Staff wages               9800

Average daily transactions
Month   Transactions
1       55
2       65
3       75

Average ticket per transaction   9.50
Days open per month              26
Variable cost ratio              35%
Loan annual interest rate        7.5%
Loan term                        60
Tax rate                         25%
"""


def _run(name, inputs):
    return methods.LIBRARY[name].impl(inputs)


class SilentHomeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        business_plan.set_runner(_run)
        chat.set_method_compute(_run, methods.describe)

    def test_three_plan_profiles_are_detected_from_the_brief(self):
        cases = (
            ("Marketing plan for a coffee shop in a small city.", "marketing_plan"),
            ("Feasibility study for a 50-seat cafe.", "feasibility_study"),
            ("Project proposal for a community garden.", "project_proposal"),
        )
        for brief, profile in cases:
            state = chat.start(brief, subject="any")
            self.assertEqual(state["profile"], profile, brief)
            self.assertEqual(state["stage"], "plan", brief)
            self.assertEqual(state["questions"], [], brief)

    def test_a_profile_paper_is_silent_and_carries_no_gap_section(self):
        def no_research(state):
            state["stage"] = "evidence"
            state["evidence"], state["background"], state["sources"], state["gaps"] = [], [], [], []
            return state
        original = chat.research
        chat.research = no_research
        try:
            state = chat.silent(chat.start("Marketing plan for a coffee shop.", subject="any"))
        finally:
            chat.research = original
        paper = state["paper"]
        headings = [heading for heading, _lines in paper["sections"]]
        self.assertTrue(headings)
        self.assertNotIn("Gaps", headings)
        self.assertNotIn("not stated", json.dumps(paper).lower())
        self.assertFalse(paper["has_workbook"])

    def test_each_profile_fills_its_guide_sections(self):
        def expand(messages):
            words = ("This section follows the brief and the recorded notes in a clear and practical way "
                     "for the reader. " * 8).split()
            return json.dumps({"lines": [" ".join(words[:70])]})

        def no_research(state):
            state["stage"] = "evidence"
            state["evidence"], state["background"], state["sources"], state["gaps"] = [], [], [], []
            return state

        providers.register(expand)
        original = chat.research
        chat.research = no_research
        try:
            cases = (
                ("Marketing plan for a coffee shop.", "marketing_plan", "Situation Analysis"),
                ("Feasibility study for a cafe.", "feasibility_study",
                 "Introduction and Project Background"),
                ("Project proposal for a community garden.", "project_proposal",
                 "Background and Needs Statement"),
            )
            for brief, profile, second in cases:
                state = chat.silent(chat.start(brief, subject="any"))
                self.assertEqual(state["profile"], profile, brief)
                headings = [heading for heading, _lines in state["paper"]["sections"]]
                self.assertEqual(len(headings), 13, brief)
                self.assertEqual(headings[1], second, brief)
        finally:
            chat.research = original
            providers.register(None)

    def test_the_profile_reader_reads_the_labelled_facts(self):
        from bp.product import profile_reader
        facts = profile_reader.read("Business name: Harbor Cafe\nLocation: Midtown\n"
                                    "Product: coffee and bread\nCustomers: commuters\n"
                                    "Budget: 20000\nTax rate: 18%")
        self.assertEqual(facts["name"], "Harbor Cafe")
        self.assertEqual(facts["location"], "Midtown")
        self.assertEqual(facts["customers"], "commuters")
        self.assertEqual(facts["tax"], "18%")

    def test_marketing_declarations_run_through_the_core(self):
        def expand(messages):
            words = ("This section follows the brief and the recorded notes in a clear and practical way "
                     "for the reader. " * 8).split()
            return json.dumps({"lines": [" ".join(words[:70])]})

        def no_research(state):
            state["stage"] = "evidence"
            state["evidence"], state["background"], state["sources"], state["gaps"] = [], [], [], []
            return state

        providers.register(expand)
        original = chat.research
        chat.research = no_research
        try:
            brief = ("Marketing plan for a coffee shop. Price 50, unit cost 20, "
                     "fixed monthly cost 5000, acquisition cost 100, churn rate 10%. "
                     "Leads 1000, inquiries 400, customers 50. Marketing budget 2000.\n\n"
                     "Marketing Channels\nChannel            Spend  Customers  Margin  Churn\n"
                     "Search ads         2000   40         30      10%\n"
                     "Local flyers       1000   10         30      10%\n")
            state = chat.silent(chat.start(brief, subject="any"))
        finally:
            chat.research = original
            providers.register(None)
        self.assertIn("unit_economics", state["computations"])
        self.assertIn("breakeven", state["computations"])
        self.assertIn("sales_funnel", state["computations"])
        self.assertIn("channel_economics", state["computations"])
        budget = next(lines for heading, lines in state["paper"]["sections"]
                      if heading == "Budget and Projections")
        self.assertTrue(any("Unit margin" in line for line in budget))
        self.assertTrue(any("Marketing budget" in line for line in budget))
        funnel = next(lines for heading, lines in state["paper"]["sections"]
                      if heading == "Funnel, Conversion and Retention")
        self.assertTrue(any("overall conversion" in line for line in funnel))
        channels = next(lines for heading, lines in state["paper"]["sections"]
                        if heading == "Channel Plan and Tactics")
        self.assertTrue(any("Blended cost" in line for line in channels))
        measurement = next(lines for heading, lines in state["paper"]["sections"]
                           if heading == "Measurement and Optimization")
        self.assertTrue(any("Blended cost" in line for line in measurement))
        data, filename, mime = chat.paper_bytes(state, "xlsx")
        self.assertTrue(data.startswith(b"PK"))
        self.assertTrue(filename.endswith(".xlsx"))

    def test_a_revision_can_be_undone(self):
        state = chat.silent(chat.start(CASE, subject="any"))
        before = state["paper"]["sections"][0][1][0]

        def change(messages):
            body = json.loads(messages[-1]["content"])
            sections = [[heading, [lines[0] + " changed."] + list(lines[1:])]
                        for heading, lines in body["paper"]["sections"]]
            return json.dumps({"sections": sections})

        providers.register(change)
        try:
            state, result = chat.revise(state, "change the opening")
            self.assertIn("changed.", result["paper"]["sections"][0][1][0])
            state, result = chat.undo(state)
            self.assertEqual(result["paper"]["sections"][0][1][0], before)
        finally:
            providers.register(None)

    def test_a_business_plan_bundle_holds_only_its_own_files(self):
        state = chat.start(CASE, subject="any")
        state = chat.silent(state)
        data, filename, mime = chat.paper_bytes(state, "bundle")
        self.assertTrue(filename.endswith(".zip"))
        self.assertEqual(mime, "application/zip")
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            names = bundle.namelist()
        self.assertTrue(any(name.endswith(".docx") for name in names))
        self.assertTrue(any(name.endswith("-workbook.xlsx") for name in names))
        self.assertTrue(any(name.endswith(".pdf") for name in names) or len(names) == 2)

    def test_a_paper_without_financial_tables_downloads_as_one_word_file(self):
        def no_research(state):
            state["stage"] = "evidence"
            state["evidence"], state["background"], state["sources"], state["gaps"] = [], [], [], []
            return state
        original = chat.research
        chat.research = no_research
        try:
            state = chat.silent(chat.start("Feasibility study for a cafe.", subject="any"))
        finally:
            chat.research = original
        data, filename, mime = chat.paper_bytes(state, "docx")
        self.assertTrue(data.startswith(b"PK"))
        self.assertTrue(filename.endswith(".docx"))
        self.assertIn("wordprocessingml", mime)


PROJECT = """
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


class SilentProjectPlanTest(unittest.TestCase):
    """A WBS brief becomes one paper with its tables, a workbook and a Word file."""

    @classmethod
    def setUpClass(cls):
        business_plan.set_runner(_run)
        chat.set_method_compute(_run, methods.describe)

    def test_a_wbs_brief_is_detected_and_asks_nothing(self):
        state = chat.start(PROJECT, subject="any")
        self.assertEqual(state["profile"], "project_plan")
        self.assertEqual(state["stage"], "plan")
        self.assertEqual(state["questions"], [])

    def test_the_silent_paper_carries_the_tables_and_no_gap_section(self):
        state = chat.silent(chat.start(PROJECT, subject="any"))
        headings = [heading for heading, _lines in state["paper"]["sections"]]
        for heading in ("Work Breakdown Structure", "Schedule", "Cost Plan",
                        "RACI Matrix", "Risk Register"):
            self.assertIn(heading, headings)
        self.assertNotIn("Gaps", headings)
        wbs = next(lines for heading, lines in state["paper"]["sections"]
                   if heading == "Work Breakdown Structure")
        self.assertTrue(any(line.startswith("| A1 |") for line in wbs), wbs)
        self.assertTrue(any("Install equipment" in line for line in wbs), wbs)

    def test_the_silent_paper_computes_the_schedule_and_the_cost(self):
        state = chat.silent(chat.start(PROJECT, subject="any"))
        result = (state.get("project_schedule") or {}).get("result") or {}
        self.assertEqual(float(result.get("project_duration")), 50.0)
        self.assertEqual(state["project_cost"]["total"], 48000)
        self.assertEqual(state["project_problems"], [])

    def test_a_labelled_charter_fact_reaches_the_table(self):
        state = chat.silent(chat.start(PROJECT, subject="any"))
        charter = next(lines for heading, lines in state["paper"]["sections"]
                       if heading == "Project Charter")
        self.assertTrue(any("Alex Rivera" in line for line in charter), charter)

    def test_a_missing_optional_section_is_omitted_not_filled(self):
        state = chat.silent(chat.start(PROJECT, subject="any"))
        headings = [heading for heading, _lines in state["paper"]["sections"]]
        self.assertNotIn("Governance and Change Control", headings)
        text = " ".join(line for _heading, lines in state["paper"]["sections"] for line in lines)
        self.assertNotIn("No governance arrangement was supplied", text)

    def test_the_download_holds_the_word_paper_and_the_project_workbook(self):
        state = chat.silent(chat.start(PROJECT, subject="any"))
        data, filename, mime = chat.paper_bytes(state, "bundle")
        self.assertTrue(filename.endswith(".zip"))
        self.assertEqual(mime, "application/zip")
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            names = bundle.namelist()
        self.assertTrue(any(name.endswith(".docx") for name in names), names)
        self.assertTrue(any(name.endswith("-workbook.xlsx") for name in names), names)
        self.assertFalse(any("marketing" in name for name in names))

    def test_the_word_paper_carries_a_real_table_and_the_schedule_chart(self):
        state = chat.silent(chat.start(PROJECT, subject="any"))
        data = chat.paper_docx(state)
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            document = bundle.read("word/document.xml").decode("utf-8")
            media = [name for name in bundle.namelist() if name.startswith("word/media/")]
        self.assertIn("<w:tbl>", document)
        self.assertIn("Install equipment", document)
        self.assertTrue(media or "Project schedule" in document, document[:400])

    def test_a_revision_keeps_the_wbs_tables(self):
        state = chat.silent(chat.start(PROJECT, subject="any"))

        def change(messages):
            body = json.loads(messages[-1]["content"])
            sections = []
            for heading, lines in body["paper"]["sections"]:
                kept = [line for line in lines if not line.startswith("|")]
                sections.append([heading, [kept[0] + " Clarified."] + kept[1:]])
            return json.dumps({"sections": sections})

        providers.register(change)
        try:
            state, _result = chat.revise(state, "clarify the opening")
        finally:
            providers.register(None)
        wbs = next(lines for heading, lines in state["paper"]["sections"]
                   if heading == "Work Breakdown Structure")
        self.assertTrue(any(line.startswith("| A1 |") for line in wbs), wbs)

    def test_the_powerpoint_deck_holds_the_chart_and_every_table(self):
        state = chat.silent(chat.start(PROJECT, subject="any"))
        data = chat.pptx_bytes(state)
        self.assertTrue(data.startswith(b"PK"))
        with zipfile.ZipFile(io.BytesIO(data)) as deck:
            names = deck.namelist()
            media = [name for name in names if name.startswith("ppt/media/")]
            slides = [name for name in names
                      if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
            texts = " ".join(deck.read(name).decode("utf-8") for name in slides)
        self.assertTrue(media, names)
        self.assertEqual(len(slides), 8, slides)
        for label in ("Work package", "Activity", "USD 48,000.00", "Management", "Risk"):
            self.assertIn(label, texts)

    def test_the_downloaded_bundle_holds_the_deck(self):
        state = chat.silent(chat.start(PROJECT, subject="any"))
        data, _filename, _mime = chat.paper_bytes(state, "bundle")
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            names = bundle.namelist()
        self.assertTrue(any(name.endswith("-deck.pptx") for name in names), names)


FEASIBILITY = """
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


class SilentFeasibilityTest(unittest.TestCase):
    """A three-table feasibility brief becomes one paper with its tables and workbook."""

    @classmethod
    def setUpClass(cls):
        business_plan.set_runner(_run)
        chat.set_method_compute(_run, methods.describe)

    def test_a_table_brief_is_a_feasibility_study_and_asks_nothing(self):
        state = chat.start(FEASIBILITY, subject="any")
        self.assertEqual(state["profile"], "feasibility_study")
        self.assertEqual(state["questions"], [])

    def test_the_silent_paper_carries_the_three_tables_and_no_gap_section(self):
        state = chat.silent(chat.start(FEASIBILITY, subject="any"))
        headings = [heading for heading, _lines in state["paper"]["sections"]]
        self.assertIn("Market Feasibility", headings)
        self.assertIn("Financial Feasibility", headings)
        self.assertIn("Returns at the Declared Figures", headings)
        self.assertNotIn("Gaps", headings)
        market = next(lines for heading, lines in state["paper"]["sections"]
                      if heading == "Market Feasibility")
        self.assertTrue(any("Declared demand" in line for line in market), market)

    def test_the_paper_uses_the_frozen_break_even_values(self):
        state = chat.silent(chat.start(FEASIBILITY, subject="any"))
        result = (state.get("feasibility_run") or {}).get("result") or {}
        self.assertEqual(float(result.get("breakeven_units")), 4800.0)
        self.assertEqual(float(result.get("expected_revenue")), 96000.0)
        self.assertEqual(state["feasibility_problems"], [])

    def test_the_download_holds_the_paper_and_the_feasibility_workbook(self):
        state = chat.silent(chat.start(FEASIBILITY, subject="any"))
        data, filename, mime = chat.paper_bytes(state, "bundle")
        self.assertTrue(filename.endswith(".zip"))
        self.assertEqual(mime, "application/zip")
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            names = bundle.namelist()
        self.assertTrue(any(name.endswith(".docx") for name in names), names)
        self.assertTrue(any(name.endswith("-workbook.xlsx") for name in names), names)
        self.assertTrue(any(name.endswith("-deck.pptx") for name in names), names)

    def test_the_feasibility_deck_holds_its_three_tables(self):
        state = chat.silent(chat.start(FEASIBILITY, subject="any"))
        data = chat.pptx_bytes(state)
        self.assertTrue(data.startswith(b"PK"))
        with zipfile.ZipFile(io.BytesIO(data)) as deck:
            slides = [name for name in deck.namelist()
                      if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
            texts = " ".join(deck.read(name).decode("utf-8") for name in slides)
        self.assertEqual(len(slides), 5, slides)
        for label in ("Declared demand", "Total investment", "Break-even volume"):
            self.assertIn(label, texts)

    def test_a_revision_keeps_the_three_tables(self):
        state = chat.silent(chat.start(FEASIBILITY, subject="any"))

        def change(messages):
            body = json.loads(messages[-1]["content"])
            sections = []
            for heading, lines in body["paper"]["sections"]:
                kept = [line for line in lines if not line.startswith("|")]
                sections.append([heading, [kept[0] + " Clarified."] + kept[1:]])
            return json.dumps({"sections": sections})

        providers.register(change)
        try:
            state, _result = chat.revise(state, "clarify the opening")
        finally:
            providers.register(None)
        market = next(lines for heading, lines in state["paper"]["sections"]
                      if heading == "Market Feasibility")
        self.assertTrue(any("Declared demand" in line for line in market), market)


PROPOSAL = """
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


class SilentProposalTest(unittest.TestCase):
    """A work-plan brief becomes one proposal with its tables and workbook."""

    @classmethod
    def setUpClass(cls):
        business_plan.set_runner(_run)
        chat.set_method_compute(_run, methods.describe)

    def test_a_table_brief_is_a_proposal_and_asks_nothing(self):
        state = chat.start(PROPOSAL, subject="any")
        self.assertEqual(state["profile"], "project_proposal")
        self.assertEqual(state["questions"], [])

    def test_the_silent_paper_carries_the_work_plan_and_budget(self):
        state = chat.silent(chat.start(PROPOSAL, subject="any"))
        headings = [heading for heading, _lines in state["paper"]["sections"]]
        for heading in ("Problem and Need", "Objectives", "Work Plan and Timeline", "Budget",
                        "Monitoring and Evaluation", "Risk Analysis"):
            self.assertIn(heading, headings)
        self.assertNotIn("Gaps", headings)
        work = next(lines for heading, lines in state["paper"]["sections"]
                    if heading == "Work Plan and Timeline")
        self.assertTrue(any(line.startswith("| Secure the lease |") for line in work), work)

    def test_the_budget_is_the_declared_lines_summed(self):
        state = chat.silent(chat.start(PROPOSAL, subject="any"))
        self.assertEqual(state["proposal_budget"]["total"], 54000)
        self.assertEqual(state["proposal_problems"], [])

    def test_the_download_holds_the_paper_and_the_proposal_workbook(self):
        state = chat.silent(chat.start(PROPOSAL, subject="any"))
        data, filename, mime = chat.paper_bytes(state, "bundle")
        self.assertTrue(filename.endswith(".zip"))
        self.assertEqual(mime, "application/zip")
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            names = bundle.namelist()
        self.assertTrue(any(name.endswith(".docx") for name in names), names)
        self.assertTrue(any(name.endswith("-workbook.xlsx") for name in names), names)

    def test_a_revision_keeps_the_work_plan_table(self):
        state = chat.silent(chat.start(PROPOSAL, subject="any"))

        def change(messages):
            body = json.loads(messages[-1]["content"])
            sections = []
            for heading, lines in body["paper"]["sections"]:
                kept = [line for line in lines if not line.startswith("|")]
                sections.append([heading, [kept[0] + " Clarified."] + kept[1:]])
            return json.dumps({"sections": sections})

        providers.register(change)
        try:
            state, _result = chat.revise(state, "clarify the opening")
        finally:
            providers.register(None)
        work = next(lines for heading, lines in state["paper"]["sections"]
                    if heading == "Work Plan and Timeline")
        self.assertTrue(any(line.startswith("| Secure the lease |") for line in work), work)

    def test_the_guide_writer_never_replaces_the_work_plan_tables(self):
        """A live model made the guide writer rewrite the paper and drop its tables."""
        state = chat.start(PROPOSAL, subject="any")
        original = chat.profile_writer.write
        chat.profile_writer.write = lambda *args, **kwargs: {
            "title": "Guide", "sections": [["Background and Needs Statement", ["guide text"]]]}
        try:
            state = chat.silent(state)
        finally:
            chat.profile_writer.write = original
        headings = [heading for heading, _lines in state["paper"]["sections"]]
        self.assertIn("Work Plan and Timeline", headings)
        self.assertIn("Budget", headings)
        self.assertNotIn("Background and Needs Statement", headings)


if __name__ == "__main__":
    unittest.main()
