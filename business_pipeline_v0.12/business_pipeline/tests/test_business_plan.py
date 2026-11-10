"""The business plan: read into the guide's schema, solved by the frozen core."""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from bp import methods  # noqa: E402
from bp.product import api, business_plan, declared  # noqa: E402
from bp.product import business_plan_briefs, business_plan_paper, business_plan_sections  # noqa: E402
from bp.product import business_plan_writer, providers  # noqa: E402


def _run(name, inputs):
    return methods.LIBRARY[name].impl(inputs)

CASE = """
Business name: Riverside Supplies
Business type: retail
Stage: startup
Location: a mid-sized city
Currency: USD

Funding Source            Amount
Owner equity              60000
Bank loan                 120000

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
Payroll taxes and benefits 12%
Utilities                 1100

Average daily transactions
Month   Transactions
1       55
2       65
3       75
4       85
5       95
6       100
7       105
8       110
9       110
10      115
11      115
12      120

Average ticket per transaction   9.50
Days open per month              26
Variable cost ratio              35%
Loan annual interest rate        7.5%
Loan term                        60
Tax rate                         25%

Annual Escalations
Rent +4% at start of Year 2 and Year 3
Staff wages +3% annually
Other fixed cash costs +3% annually

Leasehold improvements useful life 7 years
Kitchen and bakery equipment useful life 7 years
Furniture and fixtures useful life 7 years
POS and IT setup useful life 3 years
"""


class BusinessPlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        business_plan.set_runner(_run)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bp-plan-")
        self.previous = declared.REGISTRY
        declared.REGISTRY = os.path.join(self.tmp, "plan_vocab.json")
        declared._ALIASES = None

    def tearDown(self):
        declared.REGISTRY = self.previous
        declared._ALIASES = None

    def test_the_plan_is_read_and_solved(self):
        reading = declared.read(CASE)
        self.assertEqual(len(reading["lines"]["startup"]), 10)
        self.assertEqual(len(reading["lines"]["ramp"]), 12)
        record = business_plan.solve(reading, "test")
        self.assertEqual(record["format"], business_plan.FORMAT)
        self.assertTrue(record["startup"])
        self.assertTrue(record["revenue"])
        self.assertTrue(record["statements"])
        self.assertIn("net_income_1", record["statements"])

    def test_escalations_and_asset_lives_are_applied(self):
        reading = declared.read(CASE)
        self.assertEqual(reading["fields"]["escalation.rent"], "0.04")
        self.assertEqual(reading["fields"]["escalation.wages"], "0.03")
        self.assertEqual(reading["fields"]["asset_life.pos"], "3")
        record = business_plan.solve(reading, "test")
        self.assertIsNotNone(record["sensitivity"])
        pos = [row for row in record["depreciation"]["by_class"] if "POS" in str(row["label"]).upper()]
        self.assertTrue(pos and pos[0]["life"] == "3", record["depreciation"])
        # revenue does not grow in this case, so escalating costs must lower year 2 profit
        self.assertLess(float(record["statements"]["operating_profit_2"]),
                        float(record["statements"]["operating_profit_1"]))

    def test_a_five_year_horizon_is_computed_end_to_end(self):
        record = business_plan.solve(declared.read(CASE + "\nPlanning horizon 5 years\n"), "test")
        self.assertEqual(len(record["revenue_years"]), 5)
        self.assertIn("revenue_5", record["statements"])
        self.assertIn("net_income_5", record["statements"])
        headings = [heading for heading, _lines in business_plan_paper.sections(record)]
        self.assertIn("Pro forma (Years 1-5)", headings)

    def test_the_us_tax_basis_is_applied_only_when_no_rate_is_stated(self):
        from bp.product import chat
        text = CASE.replace("Tax rate                         25%\n", "")
        reading = declared.read(text)
        chat._apply_tax({"tax_jurisdiction": "US"}, reading)
        self.assertEqual(reading["fields"]["financial.tax_rate"], "0.21")
        self.assertIn("US federal corporate", reading["fields"]["financial.tax_rate_basis"])
        declared_rate = declared.read(CASE)
        chat._apply_tax({"tax_jurisdiction": "US"}, declared_rate)
        self.assertEqual(declared_rate["fields"]["financial.tax_rate"], "0.25")
        self.assertIn("overrides", declared_rate["fields"]["financial.tax_rate_basis"])
        self.assertEqual(declared.read(CASE + "\nTax 18%\n")["fields"]["financial.tax_rate"], "0.18")

    def test_owner_withdrawals_leave_cash_and_equity(self):
        base = business_plan.solve(declared.read(CASE), "test")
        drawn = business_plan.solve(declared.read(CASE + "\nOwner withdrawals 12000\n"), "test")
        self.assertEqual(drawn["statements"]["owner_withdrawals_1"], "12000")
        self.assertLess(float(drawn["statements"]["closing_cash_1"]),
                        float(base["statements"]["closing_cash_1"]))
        self.assertLess(float(drawn["statements"]["equity_1"]),
                        float(base["statements"]["equity_1"]))

    def test_a_declared_seasonal_index_reshapes_the_months(self):
        index = ["1.10", "0.95", "1.00", "1.00", "1.00", "1.00",
                 "0.95", "1.00", "1.00", "1.00", "1.00", "1.00"]
        table = "\nSeasonality\nMonth   Index\n" + "\n".join(
            "%d   %s" % (month, value) for month, value in enumerate(index, 1)) + "\n"
        reading = declared.read(CASE + table)
        self.assertEqual(len(reading["lines"]["seasonality"]), 12)
        record = business_plan.solve(reading, "test")
        self.assertIsNotNone(record["seasonality"])
        self.assertEqual(record["revenue"]["revenue_1"], "14943.5000")
        self.assertNotEqual(record["revenue"]["total_revenue"], "284050.00")

    def test_the_gates_report_what_holds_and_what_does_not(self):
        record = business_plan.solve(declared.read(CASE), "test")
        gates = {gate["code"]: gate for gate in record["gates"]}
        self.assertTrue(gates["H2"]["ok"], gates["H2"])
        self.assertTrue(gates["H6"]["ok"], gates["H6"])
        self.assertTrue(gates["H9"]["ok"], gates["H9"])
        self.assertFalse(gates["H1"]["ok"], "the declared sources exceed the declared uses")

    def test_a_missing_table_is_a_named_gap_not_a_figure(self):
        text = "Business name: X\nCurrency: USD\nAverage ticket per transaction 9.50\n"
        record = business_plan.solve(declared.read(text), "test")
        joined = " ".join(record["gaps"])
        self.assertIn("startup costs", joined)
        self.assertIsNone(record["statements"])


class BusinessPlanRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        api.attach_methods(_run, methods.describe)

    def test_the_route_reads_and_solves(self):
        status, payload = api.handle("POST", "/api/cases/business-plan",
                                     {"instruction": CASE, "objective": "test"})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["format"], business_plan.FORMAT)
        self.assertTrue(payload["gates"])

    def test_an_empty_brief_is_refused(self):
        status, payload = api.handle("POST", "/api/cases/business-plan", {"instruction": ""})
        self.assertEqual(status, 422, payload)


class BusinessPlanPaperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        business_plan.set_runner(_run)

    def test_the_paper_carries_the_plan_tables(self):
        from bp.product import business_plan_paper
        record = business_plan.solve(declared.read(CASE), "test")
        headings = [heading for heading, _lines in business_plan_paper.sections(record)]
        for wanted in ("Executive Summary", "Company Description", "Market Analysis",
                       "Products and Services", "Marketing and Sales Plan", "Operations Plan",
                       "Management and Organisation", "Financial Plan", "Risk Analysis and Mitigation",
                       "Implementation Timeline and Milestones", "Appendices",
                       "Financial summary", "Startup budget", "Sources and uses", "Sales forecast",
                       "Pro forma (Years 1-3)", "Year 1 monthly", "Break-even", "Sensitivity",
                       "Checks", "Gaps"):
            self.assertIn(wanted, headings)
        self.assertNotIn("Must include", "\n".join(
            line for _heading, lines in business_plan_paper.sections(record) for line in lines))
        self.assertTrue(business_plan_paper.document(record).startswith(b"PK"))

    def test_the_document_route_returns_word_bytes(self):
        status, payload = api.handle("POST", "/api/cases/business-plan/document",
                                     {"instruction": CASE})
        self.assertEqual(status, 200, payload)
        import base64
        raw = base64.b64decode(payload["document"]["data"])
        self.assertTrue(raw.startswith(b"PK"))

    def test_the_workbook_route_returns_a_real_package(self):
        status, payload = api.handle("POST", "/api/cases/business-plan/workbook",
                                     {"instruction": CASE})
        self.assertEqual(status, 200, payload)
        import base64
        raw = base64.b64decode(payload["workbook"]["data"])
        self.assertTrue(raw.startswith(b"PK"))


class BusinessPlanProposalTest(unittest.TestCase):
    def test_a_business_plan_is_not_asked_for_a_framework_or_a_lone_block(self):
        from bp.product import instruction_reading, plan_proposal
        brief = CASE
        reading = instruction_reading.read_frameworks(brief)
        slots = instruction_reading.extract_slots(brief)
        proposal = plan_proposal.build(brief, reading, slots, "plan_proposal", "none", [])
        keys = [row["key"] for row in proposal["computations"]]
        self.assertNotIn("breakeven", keys)
        self.assertEqual(keys, ["business_plan"])
        self.assertFalse(proposal["framework_required"])
        self.assertEqual(proposal["paper"], "business_plan")
        self.assertEqual(proposal["gaps"], [])


    def test_the_paper_structure_is_the_guides_skeleton(self):
        from bp.product import instruction_reading, plan_proposal, plan_schema
        reading = instruction_reading.read_frameworks(CASE)
        slots = instruction_reading.extract_slots(CASE)
        proposal = plan_proposal.build(CASE, reading, slots, "analytical_report", "none", [])
        self.assertEqual(proposal["structure"], list(plan_schema.SECTIONS))


class ChatPlanBlockTest(unittest.TestCase):
    def setUp(self):
        from bp.product import chat
        business_plan.set_runner(_run)
        chat.set_method_compute(_run, methods.describe)

    def test_the_chat_runs_the_business_plan_block(self):
        from bp.product import capabilities, chat
        state = {"stage": "plan", "brief": CASE, "objective": "test",
                 "selection": {"selected": [capabilities.entry("business_plan")]},
                 "computations": {}}
        state = chat.run_capability(state, "business_plan", {})
        block = state["computations"]["business_plan"]
        self.assertTrue(block["ok"], block)
        self.assertEqual(block["result"]["format"], business_plan.FORMAT)
        lines = chat._block_lines(state, {"key": "business_plan"})
        self.assertTrue(any("Startup budget" in line for line in lines), lines[:4])


SERVICE_CASE = """
Business name: Bright Path Tutoring
Business type: service
Stage: startup
Location: a small town
Currency: USD

Funding Source  Amount
Owner equity  40000
Bank loan  60000

Startup Cost Item  Amount
Leasehold improvements  10000
Computers and equipment  15000
Furniture  5000
Initial inventory  1000
Marketing  2000
Working capital reserve  8000
Contingency  3000

Fixed Monthly Cost  Amount
Rent  1500
Tutor wages  7000
Utilities  400
Marketing  300

Average daily transactions
Month  Transactions
1  8
2  9
3  10
4  10
5  11
6  12

Average ticket per transaction  45
Days open per month  20
Variable cost ratio  20%
Loan annual interest rate  6%
Loan term  48
Tax rate  20%
Discount rate  10%
Receivable days  30
Inventory days  15
Payable days  20
Population within 3 miles  42000
Annual spend per customer  500
Serviceable share  40%
Obtainable share  3%
"""


class ServicePlanTest(unittest.TestCase):
    """A different business, different wording, the same structural pipeline."""

    @classmethod
    def setUpClass(cls):
        business_plan.set_runner(_run)

    def test_a_service_business_solves_without_new_code(self):
        reading = declared.read(SERVICE_CASE)
        record = business_plan.solve(reading, "Bright Path")
        self.assertTrue(record["startup"])
        self.assertTrue(record["statements"])
        self.assertTrue(record["monthly"])
        self.assertIsNotNone(record["ratios"])
        self.assertIsNotNone(record["sensitivity"])
        self.assertIsNotNone(record["market"])
        self.assertIsNotNone(record["returns"])
        self.assertIsInstance(record["warnings"], list)
        self.assertTrue(record["assumptions"])
        self.assertGreater(float(record["statements"]["receivables_1"]), 0)
        gates = {gate["code"]: gate for gate in record["gates"]}
        self.assertTrue(gates["H2"]["ok"], gates["H2"])
        self.assertTrue(gates["H5"]["ok"], gates["H5"])
        self.assertTrue(gates["H9"]["ok"], gates["H9"])


class BusinessPlanWriterTest(unittest.TestCase):
    """The written half: briefs are data, the model is any gateway, the checks decide."""

    @classmethod
    def setUpClass(cls):
        business_plan.set_runner(_run)

    def setUp(self):
        providers.register(None)
        self.record = business_plan.solve(declared.read(CASE), "test")

    def tearDown(self):
        providers.register(None)

    def _passing_reply(self, messages):
        payload = json.loads(messages[1]["content"])
        low = payload["length_words"][0]
        sentence = ("This section states the recorded facts and names what the case does not state. "
                    * 100).split()
        return json.dumps({"lines": [" ".join(sentence[:max(int(low * 0.6), 60)])]})

    def test_without_a_model_the_deterministic_sections_stand(self):
        result = business_plan_writer.write(self.record)
        self.assertEqual(result["written"], [])
        self.assertEqual(len(result["sections"]), len(business_plan_briefs.BRIEFS))
        self.assertTrue(result["reason"])

    def test_the_briefs_cover_every_narrative_section(self):
        self.assertEqual([heading for heading, _lines in business_plan_sections.sections(self.record)],
                         business_plan_briefs.headings())

    def test_a_registered_model_writes_only_checked_prose(self):
        providers.register(self._passing_reply)
        result = business_plan_writer.write(self.record, headings=["Executive Summary"])
        self.assertIn("Executive Summary", result["written"])
        self.assertEqual(result["model"], "callable")
        written = dict(result["sections"])["Executive Summary"]
        self.assertIn("states the recorded facts", " ".join(written))

    def test_a_model_that_invents_a_number_is_overruled(self):
        providers.register(lambda messages: json.dumps({"lines": ["Revenue is 999999999."]}))
        result = business_plan_writer.write(self.record, headings=["Executive Summary"])
        self.assertNotIn("Executive Summary", result["written"])
        self.assertIn("Executive Summary", result["fallback"])
        self.assertIn("not in the record", result["problems"]["Executive Summary"])
        deterministic = dict(business_plan_sections.sections(self.record))
        self.assertEqual(dict(result["sections"])["Executive Summary"],
                         deterministic["Executive Summary"])

    def test_a_model_that_flips_a_sign_is_overruled(self):
        magnitude = str(self.record["statements"]["net_income_3"]).lstrip("-")
        providers.register(lambda messages: json.dumps(
            {"lines": ["Net income is %s." % magnitude]}))
        result = business_plan_writer.write(self.record, headings=["Executive Summary"])
        self.assertNotIn("Executive Summary", result["written"])
        self.assertIn("not in the record", result["problems"]["Executive Summary"])

    def test_a_model_that_adds_a_source_is_overruled(self):
        providers.register(lambda messages: json.dumps(
            {"lines": ["Demand grows quickly (Smith, 2020)."]}))
        result = business_plan_writer.write(self.record, headings=["Executive Summary"])
        self.assertNotIn("Executive Summary", result["written"])

    def test_a_failing_reply_leaves_the_other_sections_alone(self):
        providers.register(self._passing_reply)
        result = business_plan_writer.write(self.record, headings=["Executive Summary"])
        unknown = [heading for heading in result["written"] if heading != "Executive Summary"]
        self.assertEqual(unknown, [])

    def test_the_paper_uses_a_written_section_where_it_passed(self):
        providers.register(self._passing_reply)
        result = business_plan_writer.write(self.record, headings=["Executive Summary"])
        pairs = dict(business_plan_paper.sections(self.record, result))
        self.assertIn("states the recorded facts", " ".join(pairs["Executive Summary"]))

    def test_the_route_can_opt_in_to_the_writer(self):
        providers.register(self._passing_reply)
        status, payload = api.handle("POST", "/api/cases/business-plan",
                                     {"instruction": CASE, "prose": True})
        self.assertEqual(status, 200, payload)
        narrative = payload.get("narrative") or {}
        self.assertEqual(len(narrative.get("written") or []), len(business_plan_briefs.BRIEFS),
                         narrative.get("problems"))

    def test_the_route_stays_deterministic_without_the_flag(self):
        providers.register(self._passing_reply)
        status, payload = api.handle("POST", "/api/cases/business-plan", {"instruction": CASE})
        self.assertEqual(status, 200, payload)
        self.assertNotIn("narrative", payload)


class BusinessPlanChatFlowTest(unittest.TestCase):
    """Home must not ask a plan for a framework or make the student retype its figures."""

    def setUp(self):
        from bp.product import chat
        business_plan.set_runner(_run)
        chat.set_method_compute(_run, methods.describe)

    def test_a_business_plan_brief_asks_no_framework_question(self):
        from bp.product import chat
        state = chat.start(CASE, subject="any")
        self.assertFalse(state["proposal"]["framework_required"])
        state = chat.accept_plan(state, framework="none")
        self.assertEqual(state["questions"], [])
        self.assertEqual(state["framework"], "none")
        self.assertEqual([row["key"] for row in state["selection"]["selected"]],
                         ["business_plan"])
        self.assertEqual(state["proposal"]["paper"], "business_plan")

    def test_run_plan_produces_the_plan_paper_in_one_action(self):
        from bp.product import chat
        state = chat.start(CASE, subject="any")
        state = chat.run_plan(state, framework="none")
        self.assertEqual(state["stage"], "draft")
        self.assertEqual(state["draft"]["missing"], [])
        headings = [heading for heading, _lines in state["draft"]["sections"]]
        self.assertIn("Executive Summary", headings)
        self.assertIn("Financial summary", headings)
        self.assertNotIn("Evidence", headings)

    def test_the_business_plan_runs_without_a_validate_and_attach_step(self):
        from bp.product import chat
        state = chat.start(CASE, subject="any")
        state = chat.accept_plan(state)
        state = chat.confirm_plan(state)
        block = (state.get("computations") or {}).get("business_plan") or {}
        self.assertTrue(block.get("ok"), block)
        self.assertTrue((block.get("result") or {}).get("statements"))
        keys = [row["key"] for row in state["selection"]["selected"]]
        self.assertEqual(keys, ["business_plan"])


class SilentHomeTest(unittest.TestCase):
    """Home: one call in, the paper out, then changes in the same box."""

    @classmethod
    def setUpClass(cls):
        business_plan.set_runner(_run)
        api.attach_methods(_run, methods.describe)

    def setUp(self):
        from bp.product import chat
        chat.set_method_compute(_run, methods.describe)
        providers.register(None)
        self.tmp = tempfile.mkdtemp(prefix="bp-silent-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.tmp

    def tearDown(self):
        providers.register(None)
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_silent_run_returns_only_the_paper(self):
        status, payload = api.handle("POST", "/api/cases/chat",
                                     {"brief": CASE, "subject": "any", "silent": True})
        self.assertEqual(status, 201, payload)
        self.assertEqual(set(payload), {"id", "paper"})
        paper = payload["paper"]
        headings = [heading for heading, _lines in paper["sections"]]
        self.assertIn("Executive Summary", headings)
        self.assertNotIn("Gaps", headings)
        self.assertTrue(paper["has_workbook"])
        self.assertNotIn("not stated", json.dumps(paper).lower())

    def test_a_revision_updates_the_paper_and_refuses_a_new_number(self):
        _status, created = api.handle("POST", "/api/cases/chat",
                                      {"brief": CASE, "subject": "any", "silent": True})
        chat_id, paper = created["id"], created["paper"]

        def good(messages):
            body = json.loads(messages[-1]["content"])
            sections = [[heading, [lines[0] + " The plan is stated in the case."]
                         + list(lines[1:])]
                        for heading, lines in body["paper"]["sections"]]
            return json.dumps({"sections": sections})

        providers.register(good)
        status, result = api.handle("POST", "/api/cases/chat/" + chat_id + "/revise",
                                    {"text": "tighten the opening"})
        self.assertEqual(status, 200, result)
        self.assertIn("The plan is stated in the case.",
                      result["paper"]["sections"][0][1][0])

        def bad(messages):
            body = json.loads(messages[-1]["content"])
            sections = [[heading, list(lines)] for heading, lines in body["paper"]["sections"]]
            sections[0][1][0] += " Revenue is 999999999."
            return json.dumps({"sections": sections})

        providers.register(bad)
        status, result = api.handle("POST", "/api/cases/chat/" + chat_id + "/revise",
                                    {"text": "add a bigger revenue"})
        self.assertEqual(status, 200, result)
        self.assertIn("inventing", result["message"])
        self.assertNotIn("999999999", json.dumps(result["paper"]))


class BusinessPlanPdfTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        business_plan.set_runner(_run)
        api.attach_methods(_run, methods.describe)

    def test_the_pdf_route_returns_a_pdf(self):
        from bp.product import renderers
        if not renderers.chrome():
            self.skipTest("no Chrome on this machine")
        status, payload = api.handle("POST", "/api/cases/business-plan/pdf", {"instruction": CASE})
        self.assertEqual(status, 200, payload)
        import base64
        raw = base64.b64decode(payload["pdf"]["data"])
        self.assertTrue(raw.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
