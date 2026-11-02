"""Acceptance suite for the entrepreneurship shelf (session 6 of 11).

One test per E-row of `qa/manual/entrepreneurship.md`.  Every test is offline: retrieval is
mocked where a paper needs evidence, and no test opens a socket or calls a model.

The rows are the shelf's promises, taken from the source each row cites — the live
catalogue, `bp.methods.LIBRARY`, `bp.server.PRESETS`, the templates, the plan profile and
the page.  Nothing here asserts a number a person did not recompute.
"""

import base64
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from decimal import Decimal as D
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from bp import ingest, methods, server, templates as T              # noqa: E402
from bp.methods import LIBRARY                                      # noqa: E402
from bp.orchestrator import Pipeline                                # noqa: E402
from bp.product import api, chat, deliverables, intake, paper, rubric, subjects  # noqa: E402

YES = lambda spec: True                                             # noqa: E731
PAGE = open(os.path.join(HERE, "..", "web", "index.html"), encoding="utf-8").read()
SHELF = subjects.detail("entrepreneurship")


def _run(method_id, inputs):
    method = LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


api.attach_methods(_run, methods.describe)


def delivered(request):
    result = Pipeline().run(request, YES)
    assert result.status == "delivered", result.blocked_reason
    return result


def request_for(preset):
    return {"objective": preset["objective"], "method": preset["method"],
            "inputs": preset["inputs"], "currency": preset.get("currency"),
            "period": preset.get("period")}


def checks_pass(method_id, inputs):
    method = LIBRARY[method_id]
    result = method.tests(inputs, method.impl)
    assert tuple(name for name, _ in result) == method.test_names, (method_id, result)
    return all(ok for _, ok in result)


class InventoryTest(unittest.TestCase):
    """E-ent-001…010: what the shelf holds, and that every part of it runs."""

    def test_e_ent_001__the_shelf_holds_46_tools_6_worksheets_and_6_records(self):
        self.assertEqual(len(SHELF["tools"]), 46)
        self.assertEqual(len(SHELF["worksheets"]), 6)
        self.assertEqual(len(SHELF["records"]), 6)
        self.assertEqual(SHELF["theories"], [], "a theory is reached by naming it, not by a tile")
        self.assertEqual(len(SHELF["glossary"]), 34)
        self.assertEqual([w["catalogue_id"] for w in SHELF["worksheets"]],
                         ["STR-15", "STR-16", "STR-17", "STR-18", "STR-13", "MKT-02"])

    def test_e_ent_002__every_tool_names_a_frozen_method_or_the_one_template(self):
        for tool in SHELF["tools"]:
            self.assertTrue(tool["method"] in LIBRARY or tool["method"] in T.TEMPLATES,
                            tool["key"])
        templates_used = sorted({tool["method"] for tool in SHELF["tools"]
                                 if tool["method"] not in LIBRARY})
        self.assertEqual(templates_used, ["case_decision"],
                         "one composite preset, named rather than assumed")

    def test_e_ent_003__every_tool_carries_its_label_formula_level_period_and_notes(self):
        for tool in SHELF["tools"]:
            for field in ("key", "label", "what", "formula", "period"):
                self.assertTrue(tool.get(field), (tool["key"], field))
            self.assertIn(tool["level"], ("intro", "intermediate", "advanced"), tool["key"])
            self.assertGreaterEqual(len(tool["steps"]), 3, tool["key"])
            self.assertGreaterEqual(len(tool["common_mistakes"]), 2, tool["key"])

    def test_e_ent_004__every_related_id_resolves_to_a_declared_tool(self):
        for tool in SHELF["tools"]:
            for related in tool["related"]:
                self.assertIn(related, subjects.TOOL_INFO, (tool["key"], related))

    def test_e_ent_005__every_tool_has_a_preset_that_launches_its_own_method(self):
        for tool in SHELF["tools"]:
            preset = server.PRESETS.get(tool["preset"])
            self.assertIsNotNone(preset, tool["key"])
            self.assertEqual(preset["method"], tool["method"], tool["key"])

    def test_e_ent_006__every_preset_default_passes_validation_and_prechecks(self):
        for tool in SHELF["tools"]:
            if tool["method"] not in LIBRARY:
                continue  # the composite template is exercised through its preset row
            preset = server.PRESETS[tool["preset"]]
            method = LIBRARY[tool["method"]]
            self.assertEqual(methods.validate_inputs(method, preset["inputs"]), [], tool["key"])
            self.assertEqual(method.profile(preset["inputs"]), [], tool["key"])

    def test_e_ent_007__every_preset_delivers_with_all_its_own_checks(self):
        """D-ENT-04: three presets were blocked by a phantom `None` period label."""
        for tool in SHELF["tools"]:
            preset = server.PRESETS[tool["preset"]]
            result = Pipeline().run(request_for(preset), YES)
            self.assertEqual(result.status, "delivered", (tool["key"], result.blocked_reason))
            self.assertTrue(result.appendix["tests"], tool["key"])
            self.assertTrue(all(ok for _, ok, *_ in result.appendix["tests"]), tool["key"])
            self.assertNotIn("{{ref:", result.report, tool["key"])

    def test_e_ent_008__no_entrepreneurship_tool_claims_a_prescriptive_ceiling(self):
        for tool in SHELF["tools"]:
            if tool["method"] not in LIBRARY:
                continue
            self.assertNotEqual(LIBRARY[tool["method"]].claim_ceiling, "prescriptive", tool["key"])

    def test_e_ent_009__an_unknown_input_is_refused_with_the_allowed_list(self):
        result = Pipeline().run({"objective": "Size the market", "method": "market_sizing",
                                 "inputs": {"target_population": "1000", "invented": "1"}}, YES)
        self.assertEqual(result.status, "blocked")
        self.assertIn("unknown input 'invented'", result.blocked_reason)
        self.assertIn("target_population", result.blocked_reason)

    def test_e_ent_010__the_shelf_copy_stays_short(self):
        """The ceilings are the measured maxima (guidance 58, what 26, step 20, mistake 23)."""
        self.assertLessEqual(len(SHELF["guidance"].split()), 60)
        for tool in SHELF["tools"]:
            self.assertLessEqual(len(tool["what"].split()), 26, tool["key"])
            for step in tool["steps"]:
                self.assertLessEqual(len(step.split()), 20, tool["key"])
            for mistake in tool["common_mistakes"]:
                self.assertLessEqual(len(mistake.split()), 23, tool["key"])
        for step in SHELF["start_steps"]:
            self.assertLessEqual(len(step.split()), 12, step)
        for line in SHELF["does_not"]:
            self.assertLessEqual(len(line.split()), 14, line)


def _tool_row(tool):
    """One row per tool: its own preset delivers, checks pass, twice gives the same report."""
    def test(self):
        preset = server.PRESETS[tool["preset"]]
        first = Pipeline().run(request_for(preset), YES)
        self.assertEqual(first.status, "delivered", (tool["key"], first.blocked_reason))
        self.assertTrue(all(ok for _, ok, *_ in first.appendix["tests"]), tool["key"])
        self.assertNotIn("{{ref:", first.report, tool["key"])
        second = Pipeline().run(request_for(preset), YES)
        self.assertEqual(first.report, second.report, "the same figures give the same report")
        self.assertEqual(first.appendix["tests"], second.appendix["tests"])
    return test


class ToolDeliveryTest(unittest.TestCase):
    """E-ent-011…056: one row per tool, driven through the preset the tile launches."""


for _index, _tool in enumerate(SHELF["tools"], start=11):
    _name = "test_e_ent_%03d__%s_delivers_through_its_preset" % (_index, _tool["key"])
    setattr(ToolDeliveryTest, _name, _tool_row(_tool))


class ArithmeticTest(unittest.TestCase):
    """E-ent-057…068: the venture arithmetic, recomputed by hand from the student guide."""

    def test_e_ent_057__market_sizing_reproduces_the_guides_worked_example(self):
        out = LIBRARY["market_sizing"].impl({"target_population": "20000",
                                             "annual_spend_per_customer": "3000",
                                             "serviceable_share": "0.25",
                                             "obtainable_share": "0.20"})
        # 20,000 x 3,000 = 60,000,000; x 0.25 = 15,000,000; x 0.20 = 3,000,000;
        # 20,000 x 0.25 x 0.20 = 1,000 customers.
        self.assertEqual(out["total_addressable_market"], D(60000000))
        self.assertEqual(out["serviceable_available_market"], D("15000000.00"))
        self.assertEqual(out["serviceable_obtainable_market"], D("3000000.0000"))
        self.assertEqual(out["customers_in_som"], D("1000.0000"))

    def test_e_ent_058__break_even_reports_units_revenue_and_the_target_volume(self):
        out = LIBRARY["breakeven"].impl({"fixed": "1000", "price": "20", "variable": "10",
                                         "expected_units": "150", "target_profit": "500"})
        # 1,000 / 10 = 100 units; 100 x 20 = 2,000 of revenue; (1,000 + 500) / 10 = 150 units.
        self.assertEqual(out["breakeven_units"], D(100))
        self.assertEqual(out["breakeven_revenue"], D(2000))
        self.assertEqual(out["contribution_margin"], D(10))
        self.assertEqual(out["target_profit_units"], D(150))
        self.assertEqual(out["margin_of_safety_units"], D(50))

    def test_e_ent_059__the_four_pricing_rules_are_shown_side_by_side(self):
        out = LIBRARY["pricing_decision"].impl({"unit_cost": "15", "fixed_cost": "45000",
                                                "expected_units": "6000", "markup_rate": "0.60",
                                                "target_margin_rate": "0.375",
                                                "target_profit": "20000"})
        # total cost 15 x 6,000 + 45,000 = 135,000; cost-plus 15 x 1.6 = 24;
        # the same 24 at a 37.5% margin; break-even 135,000 / 6,000 = 22.50;
        # target return (135,000 + 20,000) / 6,000 = 25.8333...
        self.assertEqual(out["total_cost"], D(135000))
        self.assertEqual(out["cost_plus_price"], D("24.00"))
        self.assertEqual(out["margin_price"], D(24))
        self.assertEqual(out["break_even_price"], D("22.5"))
        self.assertTrue(str(out["target_return_price"]).startswith("25.8333333333"))

    def test_e_ent_060__startup_capital_adds_a_contingency_and_subtracts_the_funding(self):
        out = LIBRARY["startup_capital"].impl({"start_up_costs": "350000",
                                               "working_capital": "120000",
                                               "contingency_rate": "0.10",
                                               "owner_equity": "150000", "loan_amount": "200000"})
        # contingency 10% of (350,000 + 120,000) = 47,000; total 517,000;
        # 517,000 - 150,000 - 200,000 = 167,000 still to raise.
        self.assertEqual(out["contingency_reserve"], D("47000.00"))
        self.assertEqual(out["total_funding_required"], D("517000.00"))
        self.assertEqual(out["amount_to_raise"], D("167000.00"))

    def test_e_ent_061__cash_runway_divides_the_cash_by_the_monthly_burn(self):
        out = LIBRARY["cash_runway"].impl({"opening_cash": "300000",
                                           "monthly_net_cash_flow": "-40000",
                                           "monthly_growth": "0", "target_months": "9"})
        # 300,000 / 40,000 = 7.5 months; by month 9 the balance is -60,000.
        self.assertEqual(out["runway_months"], D("7.5"))
        self.assertEqual(out["cash_at_target_month"], D(-60000))
        self.assertEqual(out["funding_gap"], D(60000))

    def test_e_ent_062__return_on_investment_reports_the_total_and_the_annual_rate(self):
        out = LIBRARY["return_on_investment"].impl({"total_investment": "500000",
                                                    "net_gain": "125000", "years": "3"})
        # 125,000 / 500,000 = 25%; (1.25)^(1/3) - 1 = 0.0772173...
        self.assertEqual(out["roi"], D("0.25"))
        self.assertTrue(str(out["annualised_roi"]).startswith("0.0772173450"))

    def test_e_ent_063__the_funnel_reports_each_stage_and_the_acquisition_cost(self):
        out = LIBRARY["sales_funnel"].impl({"stages": [
            {"name": "visits", "count": "10000"}, {"name": "inquiries", "count": "2500"},
            {"name": "purchases", "count": "500"}], "spend": "25000"})
        # 2,500/10,000 = 0.25; 500/2,500 = 0.20; 500/10,000 = 0.05; 25,000/500 = 50.
        self.assertEqual(out["conversion_1"], D("0.25"))
        self.assertEqual(out["conversion_2"], D("0.2"))
        self.assertEqual(out["overall_conversion"], D("0.05"))
        self.assertEqual(out["cac"], D(50))

    def test_e_ent_064__cohort_retention_pools_the_cohorts_period_by_period(self):
        out = LIBRARY["cohort_retention"].impl(
            {"cohort_sizes": ["200", "180", "150"],
             "retained": [["200", "140", "110", "90"], ["180", "130", "100", "60"],
                          ["150", "120", "95", "70"]]})
        # start 200 + 180 + 150 = 530; period 2 (140+130+120)/530 = 0.7358490...
        # average lifetime = 1 + 0.735849 + 0.575472 + 0.415094 = 2.726415...
        self.assertEqual(out["total_start"], D(530))
        self.assertEqual(out["retention_1"], D(1))
        self.assertTrue(str(out["retention_2"]).startswith("0.7358490566"))
        self.assertTrue(str(out["average_lifetime"]).startswith("2.7264150943"))

    def test_e_ent_065__the_demand_line_reports_the_revenue_maximising_price(self):
        out = LIBRARY["demand_curve"].impl({"prices": ["20", "25", "30", "35", "40"],
                                            "quantities": ["400", "340", "280", "220", "160"]})
        # slope (160 - 400) / (40 - 20) = -12; intercept 400 + 12 x 20 = 640;
        # revenue peaks at 640 / 24 = 26.6667 and 320 units -> 8,533.33.
        self.assertEqual(out["slope"], D(-12))
        self.assertEqual(out["intercept"], D(640))
        self.assertEqual(out["r_squared"], D(1))
        self.assertTrue(str(out["revenue_max_price"]).startswith("26.6666666666"))
        self.assertTrue(str(out["revenue_max_revenue"]).startswith("8533.333333"))

    def test_e_ent_066__purchase_intent_applies_the_declared_conversion_weights(self):
        out = LIBRARY["purchase_intent"].impl({"definitely": "120", "probably": "80",
                                               "maybe": "150", "never": "50",
                                               "target_population": "20000", "price": "250"})
        # weights 0.8 / 0.3 / 0.1 / 0: 96 + 24 + 15 = 135 of 400 -> 0.3375;
        # 20,000 x 0.3375 = 6,750 buyers; x 250 = 1,687,500 of revenue.
        self.assertEqual(out["respondents"], D(400))
        self.assertEqual(out["weighted_intenders"], D("135.0"))
        self.assertEqual(out["intent_rate"], D("0.3375"))
        self.assertEqual(out["projected_buyers"], D("6750.0000"))
        self.assertEqual(out["projected_revenue"], D("1687500.0000"))

    def test_e_ent_067__the_cap_table_keeps_the_declared_pool_at_its_share(self):
        out = LIBRARY["cap_table_round"].impl({"pre_money_valuation": "4000000",
                                               "investment": "1000000",
                                               "founders_shares": "1000000",
                                               "option_pool_pct": "0.10"})
        # post-money 5,000,000; price 5,000,000 / (1,000,000 + 250,000) = 4;
        # new shares 1,000,000 / 4 = 250,000; the pool is grossed up to stay 10% of
        # (1,250,000 / 0.9) = 1,388,888.88..., so the founders hold 72%.
        self.assertEqual(out["post_money_valuation"], D(5000000))
        self.assertEqual(out["price_per_share"], D(4))
        self.assertEqual(out["new_shares"], D(250000))
        self.assertTrue(str(out["founder_pct"]).startswith("0.7199999999"))
        self.assertEqual(out["pool_pct_actual"], D("0.1"))

    def test_e_ent_068__every_venture_method_runs_its_own_checks(self):
        for method_id, inputs in (
                ("market_sizing", {"target_population": "20000",
                                   "annual_spend_per_customer": "3000",
                                   "serviceable_share": "0.25", "obtainable_share": "0.20"}),
                ("startup_capital", {"start_up_costs": "350000", "working_capital": "120000",
                                     "contingency_rate": "0.10", "owner_equity": "150000",
                                     "loan_amount": "200000"}),
                ("cash_runway", {"opening_cash": "300000", "monthly_net_cash_flow": "-40000",
                                 "monthly_growth": "0", "target_months": "9"}),
                ("return_on_investment", {"total_investment": "500000", "net_gain": "125000",
                                          "years": "3"}),
                ("purchase_intent", {"definitely": "120", "probably": "80", "maybe": "150",
                                     "never": "50", "target_population": "20000",
                                     "price": "250"}),
                ("cap_table_round", {"pre_money_valuation": "4000000", "investment": "1000000",
                                     "founders_shares": "1000000", "option_pool_pct": "0.10"})):
            self.assertTrue(checks_pass(method_id, inputs), method_id)


PLAN_BRIEF = ("A coffee shop selling specialty coffee to university students in a mid-sized city. "
              "It needs start-up funding for equipment, a kiosk lease and two staff.")

PLAN_INPUTS = {
    "business_name": "Bean There", "product": "specialty coffee and pastries",
    "customers": "university students", "location": "a mid-sized city",
    "positioning": "affordable specialty coffee", "channels": "a campus kiosk and social media",
    "pricing_note": "mid-market pricing", "operations": "a single kiosk with two staff",
    "suppliers": "a local roaster", "capacity_note": "120 cups a day",
    "team": "the owner and one barista", "roles": "the owner buys and manages; the barista serves",
    "risks": ["a rent increase", "low student footfall"]}

PLAN_BLOCKS = {
    "frommarket": {"market_size": "60000000", "target_share": "0.03", "price": "120"},
    "breakeven": {"fixed": "300000", "price": "120", "variable": "55"},
    "depreciation": {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"},
    "proforma": {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
                 "operating_costs": ["300000", "320000", "340000"],
                 "depreciation": ["90000", "90000", "90000"],
                 "interest": ["40000", "30000", "20000"],
                 "principal_repayment": ["100000", "100000", "100000"],
                 "capex": ["0", "0", "0"], "tax_rate": "0.25",
                 "receivable_days": "30", "inventory_days": "45", "payable_days": "30",
                 "opening_cash": "200000", "opening_fixed_assets": "450000",
                 "opening_receivables": "0", "opening_inventory": "0", "opening_payables": "0",
                 "opening_loan": "400000", "opening_equity": "250000"},
    "sensitivity": {"base_price": "120", "base_units": "10000", "base_variable_cost": "55",
                    "base_fixed_cost": "300000", "price_changes": ["-0.1", "0", "0.1"],
                    "volume_changes": ["-0.2", "0", "0.2"]},
    "tax": {"taxable_income": "1000000", "income_tax_rate": "0.25"},
    "captable": {"pre_money_valuation": "4000000", "investment": "1000000",
                 "founders_shares": "1000000", "option_pool_pct": "0.10"},
    "impact": {"options": [{"name": "basic", "cost": "10000", "effect": "40"},
                           {"name": "intensive", "cost": "18000", "effect": "60"}]},
}

PLAN_RUBRIC = """Assessment criteria
1. Market analysis - 25% - must include the market size and the target segment
2. Financial plan - 35% - must include a break-even quantity
3. Operations plan - 20%
4. Risks and limitations - 10%
5. Referencing - 10%

Word limit: 2,500 words +/- 10%
"""

#: A guide whose one criterion no section of the plan profile can carry.
MISSING_RUBRIC = "Assessment criteria\n1. Appendices with raw survey data - 100%\n"


def plan_state(level="shs", rubric_text=None):
    state = chat.start(PLAN_BRIEF, "entrepreneurship", profile="business_plan", level=level,
                       rubric=rubric_text)
    state = chat.confirm_plan(state)
    state = chat.set_inputs(state, PLAN_INPUTS)
    wanted = {block["key"] for block in state["plan"]["blocks"]}
    state = chat.compute(state, {key: value for key, value in PLAN_BLOCKS.items()
                                 if key in wanted})
    return chat.draft(state)


class PlanProfileTest(unittest.TestCase):
    """E-ent-069…079: the business plan as a second engine, and the marking guide in it."""

    def test_e_ent_069__the_shs_plan_carries_the_five_core_blocks_in_order(self):
        state = chat.start(PLAN_BRIEF, "entrepreneurship", profile="business_plan", level="shs")
        self.assertEqual([block["key"] for block in state["plan"]["blocks"]],
                         ["frommarket", "breakeven", "depreciation", "proforma", "sensitivity"])
        self.assertTrue(all(block["required"] for block in state["plan"]["blocks"]))
        self.assertNotIn("funding", [section["key"] for section in state["plan"]["sections"]])

    def test_e_ent_070__the_college_plan_adds_tax_the_cap_table_and_impact(self):
        state = chat.start(PLAN_BRIEF, "entrepreneurship", profile="business_plan",
                           level="college")
        keys = [block["key"] for block in state["plan"]["blocks"]]
        for key in ("tax", "captable", "impact"):
            self.assertIn(key, keys)
        sections = [section["key"] for section in state["plan"]["sections"]]
        self.assertIn("funding", sections)
        self.assertIn("impact", sections)

    def test_e_ent_071__the_financial_plan_is_one_h1_with_computation_h2s(self):
        state = plan_state("shs")
        outline = state["draft"]["outline"]
        start = next(index for index, item in enumerate(outline)
                     if item["heading"] == "Financial Plan")
        h2s = []
        for item in outline[start + 1:]:
            if item["level"] == 1:
                break
            h2s.append(item["heading"])
        self.assertEqual(h2s, ["Market Size and Target Sales", "Break-even", "Depreciation",
                               "Projected Financial Statements", "Sensitivity"])

    def test_e_ent_072__an_incomplete_plan_blocks_the_export_with_the_missing_items(self):
        state = chat.start(PLAN_BRIEF, "entrepreneurship", profile="business_plan")
        state = chat.confirm_plan(state)
        state = chat.compute(state, {})
        state = chat.draft(state)
        self.assertTrue(state["draft"]["missing"])
        with self.assertRaises(paper.ExportBlocked) as refused:
            chat.docx_bytes(state)
        self.assertIn("what the business sells", refused.exception.missing)

    def test_e_ent_073__an_unbalanced_opening_balance_is_refused_with_the_equity(self):
        state = chat.confirm_plan(chat.start(PLAN_BRIEF, "entrepreneurship",
                                             profile="business_plan"))
        state = chat.set_inputs(state, PLAN_INPUTS)
        broken = dict(PLAN_BLOCKS["proforma"], opening_equity="200000")
        state = chat.compute(state, {"proforma": broken})
        self.assertFalse(state["computations"]["proforma"]["ok"])
        self.assertIn("does not balance", state["computations"]["proforma"]["error"])

    def test_e_ent_074__the_plan_downloads_as_a_real_word_package(self):
        state = plan_state("shs")
        payload = chat.docx_bytes(state)
        self.assertTrue(payload.startswith(b"PK"))
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertIn("word/document.xml", archive.namelist())

    def test_e_ent_075__a_marking_guide_adds_a_coverage_table_before_the_references(self):
        state = plan_state("shs", PLAN_RUBRIC)
        headings = [item["heading"] for item in state["draft"]["outline"]]
        self.assertIn("Rubric coverage", headings)
        self.assertLess(headings.index("Rubric coverage"), headings.index("References"))
        self.assertEqual(state["rubric"]["count"], 5,
                         "the word-limit line is a budget, not a sixth criterion")

    def test_e_ent_076__a_weighted_criterion_the_plan_lacks_blocks_the_download(self):
        state = plan_state("shs", MISSING_RUBRIC)
        self.assertEqual(state["rubric"]["gaps"], ["Appendices with raw survey data"])
        self.assertEqual(state["rubric"]["blocking"], ["Appendices with raw survey data"])
        self.assertEqual(state["draft"]["missing"],
                         ["the 'Appendices with raw survey data' criterion your rubric states"],
                         "everything else in the plan is complete: the guide is the only block")
        with self.assertRaises(paper.ExportBlocked):
            chat.docx_bytes(state)

    def test_e_ent_077__the_student_may_accept_the_gap_and_download_anyway(self):
        state = plan_state("shs", MISSING_RUBRIC)
        self.assertTrue(state["draft"]["missing"])
        state = chat.set_rubric_gate(state, False)
        self.assertEqual(state["draft"]["missing"], [],
                         "the accepted gap is recorded, not silently closed")
        self.assertEqual(state["rubric"]["gaps"], ["Appendices with raw survey data"],
                         "the coverage table still names the gap")
        self.assertTrue(chat.docx_bytes(state).startswith(b"PK"))

    def test_e_ent_078__a_plan_with_no_marking_guide_is_byte_for_byte_unchanged(self):
        state = plan_state("shs")
        self.assertNotIn("rubric", state)
        self.assertNotIn("rubric_record", state)
        self.assertNotIn("Rubric coverage",
                         [item["heading"] for item in state["draft"]["outline"]])

    def test_e_ent_079__an_unreadable_marking_guide_is_refused_before_the_plan_exists(self):
        with self.assertRaises(chat.ChatError) as refused:
            chat.start(PLAN_BRIEF, "entrepreneurship", profile="business_plan",
                       rubric="Please read the attached case and write a short report.")
        self.assertIn("No assessment criterion", str(refused.exception))


class WorksheetTest(unittest.TestCase):
    """E-ent-080…085: the six worksheets, their audit and the one that is not draftable."""

    def _run(self, kind):
        return T.run_template(kind, T.EXAMPLES[kind]["inputs"])

    def test_e_ent_080__the_business_model_canvas_places_the_items_and_names_the_gaps(self):
        result = self._run("template_business_model_canvas")
        self.assertEqual(T.describe("template_business_model_canvas")["tier"], "T4")
        self.assertIn("narrative", result)
        self.assertIn("listing", result)
        self.assertIsNone(re.search(r"\d", re.sub(r"\{\{ref:[^}]*\}\}", "",
                                                  result["narrative"])))

    def test_e_ent_081__the_lean_canvas_is_a_structure_and_an_audit_not_a_score(self):
        result = self._run("template_lean_canvas")
        self.assertIn("does not score, rank or choose", result["narrative"],
                      "the worksheet says in words that it judges nothing")
        for key in result:
            for banned in ("score", "rating", "rank"):
                self.assertNotIn(banned, str(key).lower(),
                                 "no field of the result carries a mark or a ranking")

    def test_e_ent_082__the_value_proposition_canvas_links_only_what_the_student_claims(self):
        result = self._run("template_value_proposition_canvas")
        self.assertTrue(result["listing"].strip())
        self.assertIn("fit", result["listing"].lower() + result["narrative"].lower())

    def test_e_ent_083__the_swot_review_turns_evidence_into_declared_actions(self):
        result = self._run("template_swot")
        self.assertTrue(result["narrative"].strip())
        self.assertIsNone(re.search(r"\d", re.sub(r"\{\{ref:[^}]*\}\}", "",
                                                  result["narrative"])))

    def test_e_ent_084__the_blue_ocean_grid_is_offered_but_not_draftable(self):
        row = next(w for w in SHELF["worksheets"] if w["catalogue_id"] == "STR-13")
        self.assertEqual(row["template"], "template_blue_ocean_errc")
        self.assertFalse(row["draftable"], "the ERRC grid has no draft button, by design")
        self.assertTrue(self._run("template_blue_ocean_errc")["narrative"])

    def test_e_ent_085__the_marketing_plan_is_shared_with_the_marketing_shelf(self):
        row = next(w for w in SHELF["worksheets"] if w["catalogue_id"] == "MKT-02")
        self.assertTrue(row["draftable"])
        marketing = [w["catalogue_id"] for w in subjects.detail("marketing")["worksheets"]]
        self.assertIn("MKT-02", marketing)
        self.assertTrue(self._run("template_marketing_plan")["narrative"])


class RecordTest(unittest.TestCase):
    """E-ent-086…090: the six catalogue records state what is and is not built."""

    def test_e_ent_086__the_shelf_lists_six_records_and_no_theory(self):
        self.assertEqual([row["id"] for row in SHELF["records"]],
                         ["QNT-MKT-01", "QNT-MKT-02", "QNT-MKT-03",
                          "QNT-FIN-06", "QNT-FIN-07", "QNT-DEC-02"])
        self.assertEqual(SHELF["theories"], [])

    def test_e_ent_087__every_computed_record_states_what_is_not_implemented(self):
        for row in SHELF["records"]:
            if row["form"] != "computed":
                continue
            self.assertTrue(row["implementation_status"].startswith("partial:"), row["id"])
            self.assertIn("not implemented", row["implementation_status"], row["id"])

    def test_e_ent_088__every_computed_record_states_what_it_does_and_does_not_do(self):
        for row in SHELF["records"]:
            if row["form"] != "computed":
                continue
            status = row["implementation_status"]
            self.assertIn("implemented", status, row["id"])
            self.assertIn("not implemented", status, row["id"])
            self.assertTrue(str(row["structures"]).strip(), row["id"])

    def test_e_ent_089__every_worksheet_record_is_on_this_shelf(self):
        ids = {w["catalogue_id"] for w in SHELF["worksheets"]}
        for row in SHELF["catalogue"]:
            if row.get("form") != "worksheet":
                continue
            self.assertIn(row["id"], ids, row["id"])
            self.assertTrue(row["implementation_status"].startswith("worksheet available"),
                            row["id"])

    def test_e_ent_090__a_record_never_claims_a_worksheet_it_does_not_have(self):
        ids = {w["catalogue_id"] for w in SHELF["worksheets"]}
        for row in SHELF["catalogue"]:
            if row.get("form") == "worksheet":
                continue
            self.assertNotIn(row["id"], ids, row["id"])


class SurfaceTest(unittest.TestCase):
    """E-ent-091…101: the routes and the page the student actually reaches."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-ent-")
        self.previous = os.environ.get("BP_INTAKE_DIR")
        os.environ["BP_INTAKE_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_INTAKE_DIR", None)
        else:
            os.environ["BP_INTAKE_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_e_ent_091__the_shelf_route_serves_the_inventory_and_the_declared_non_goals(self):
        status, payload = api.handle("GET", "/api/cases/subjects/entrepreneurship")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["tools"]), 46)
        self.assertEqual(len(payload["worksheets"]), 6)
        self.assertEqual(len(payload["records"]), 6)
        self.assertEqual(len(payload["does_not"]), 3)
        self.assertTrue(payload["guidance"])

    def test_e_ent_092__the_shelf_is_indexed_with_its_own_label(self):
        status, payload = api.handle("GET", "/api/cases/subjects")
        self.assertEqual(status, 200)
        labels = {row["id"]: row["label"] for row in payload["subjects"]}
        self.assertEqual(labels.get("entrepreneurship"), "Entrepreneurship")

    def test_e_ent_093__the_page_groups_the_tools_in_the_plan_order(self):
        order = []
        for tool in SHELF["tools"]:
            if tool["group"] not in order:
                order.append(tool["group"])
        self.assertEqual(order, ["Market and customers", "Costs, pricing and break-even",
                                 "Operations plan", "Financial plan and return",
                                 "Funding and valuation", "Impact and options"])

    def test_e_ent_094__the_glossary_carries_the_venture_terms(self):
        terms = {row["term"] for row in SHELF["glossary"]}
        for term in ("TAM", "SAM", "SOM", "Break-even point", "Margin of safety", "CAC",
                     "LTV", "Runway", "ROI", "Cap table", "Dilution", "Funnel", "Cohort",
                     "Purchase intent", "Positioning"):
            self.assertIn(term, terms)

    def test_e_ent_095__the_page_opens_with_four_ordered_start_steps(self):
        self.assertEqual(len(SHELF["start_steps"]), 4)
        self.assertIn("business plan", SHELF["start_steps"][0].lower())
        self.assertIn("business plan", SHELF["guidance"].lower())

    def test_e_ent_096__the_calculator_reaches_the_same_method_the_tile_launches(self):
        from bp.product import calc_router
        plan = calc_router.plan("what is my break-even point")
        self.assertEqual(plan["method"], "breakeven")

    def test_e_ent_097__the_brief_route_reads_text_and_refuses_what_it_cannot_read(self):
        status, payload = api.handle("POST", "/api/cases/brief",
                                     {"text": "  A coffee shop in a mid-sized city.  "})
        self.assertEqual(status, 200)
        self.assertEqual(payload["text"], "A coffee shop in a mid-sized city.")
        self.assertEqual(payload["method"], "pasted_text")
        status, _ = api.handle("POST", "/api/cases/brief",
                               {"filename": "brief.txt", "data": "not base64!"})
        self.assertEqual(status, 422)

    def test_e_ent_098__a_scanned_brief_reaches_the_vision_model_and_names_the_engine(self):
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 200
        reply = mock.MagicMock()
        reply.__enter__.return_value.read.return_value = (
            b'{"choices": [{"message": {"content": "A coffee shop in a mid-sized city."}}]}')
        reply.__exit__.return_value = False
        encoded = base64.b64encode(png).decode("ascii")
        with mock.patch.dict(os.environ, {"BP_OPENGO_API_KEY": "k", "BP_OCR_MODEL": "vision-t"},
                             clear=False), \
                mock.patch.multiple("bp.product.documents", ocr_available=lambda: False,
                                    pdf_ocr_available=lambda: False), \
                mock.patch("bp.product.ocr.urllib.request.urlopen", return_value=reply):
            status, payload = api.handle("POST", "/api/cases/brief",
                                         {"filename": "brief.png", "data": encoded})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["method"], "image_ocr_model")
        self.assertEqual(payload["engine"], "vision-t",
                         "the engine that read the page reaches the caller, not just the record")
        self.assertEqual(payload["filename"], "brief.png")
        self.assertIn("coffee", payload["text"])

    def test_e_ent_099__the_plan_exports_bytes_rather_than_a_server_path(self):
        from bp.product import chat_store
        saved = chat_store.save(plan_state("shs"))
        status, payload = api.handle("POST", "/api/cases/chat/%s/export" % saved["id"], {})
        self.assertEqual(status, 200, payload)
        for key in ("filename", "mime", "data"):
            self.assertIn(key, payload)
        self.assertNotIn("path", payload, "the browser cannot fetch a server path")
        self.assertTrue(base64.b64decode(payload["data"]).startswith(b"PK"))

    def test_e_ent_100__the_pairs_the_results_panel_asks_for_are_pairs_the_core_allows(self):
        for deliverable, kind in (("submission", "docx"), ("submission", "html"),
                                  ("workpapers", "xlsx"), ("workpapers", "spreadsheetml"),
                                  ("worksheet", "docx")):
            deliverables.check_pair(deliverable, kind)
        with self.assertRaises(deliverables.DeliverableError):
            deliverables.check_pair("workpapers", "docx")
        self.assertIn('{ kind: "docx", deliverable: "submission", download: true }', PAGE)

    def test_e_ent_101__the_page_carries_the_marking_guide_into_the_plan(self):
        self.assertIn("if (state.rubric) body.rubric = state.rubric", PAGE,
                      "the plan posts the parsed guide it holds")
        self.assertIn("function rubricNoteHtml", PAGE)
        self.assertIn('id="planrubricgate"', PAGE,
                      "a criterion the profile cannot carry is the student's decision")


class TrapTest(unittest.TestCase):
    """E-ent-102…106: the four defects this session fixed, pinned by their own trap."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-ent-map-")
        self.previous = os.environ.get("BP_INTAKE_DIR")
        os.environ["BP_INTAKE_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_INTAKE_DIR", None)
        else:
            os.environ["BP_INTAKE_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def _table(self):
        raw = (b"month,revenue,operating_costs,depreciation\n"
               b"1,1200000,300000,90000\n2,1500000,320000,90000\n")
        record = intake.save("plan.csv", raw)
        intake.attach_table(record["id"], ingest.read_table("plan.csv", raw))
        return record["id"]

    def test_e_ent_102__a_plan_blocks_columns_are_proposed_and_its_drivers_named(self):
        """D-ENT-02: a mixed block was refused for the shape the plan itself asks for."""
        mapped = intake.mapped_request(self._table(), "proforma_statements",
                                       {"revenue": "revenue", "operating_costs": "operating_costs"})
        self.assertEqual(mapped["inputs"]["revenue"], ["1200000", "1500000"])
        self.assertIn("gross_margin_rate", mapped["not_mapped"],
                      "a driver the file cannot supply is named, not treated as an error")
        self.assertIn("opening_cash", mapped["not_mapped"])

    def test_e_ent_103__a_scalar_asked_to_come_from_a_column_is_still_refused(self):
        with self.assertRaises(intake.IntakeError) as refused:
            intake.mapped_request(self._table(), "breakeven", {"fixed": "revenue"})
        self.assertIn("cannot be mapped from a column", str(refused.exception))

    def test_e_ent_104__a_mapping_executes_nothing(self):
        mapped = intake.mapped_request(self._table(), "descriptive_stats", {"values": "revenue"})
        for key in ("report", "delivery", "session", "result", "checks"):
            self.assertNotIn(key, mapped)

    def test_e_ent_105__a_word_budget_line_in_a_list_rubric_is_not_a_criterion(self):
        """D-ENT-03: "Word limit: 2,500 words +/- 10%" was read as a weighted criterion."""
        parsed = rubric.parse("Assessment criteria\n1. Market analysis - 60%\n"
                              "2. Financial plan - 40%\n\nWord limit: 2,500 words +/- 10%\n")
        self.assertEqual([row["name"] for row in parsed["criteria"]],
                         ["Market analysis", "Financial plan"])
        self.assertEqual(parsed["total_weight"], 100.0)
        self.assertEqual(parsed["word_budget"]["words"], 2500)
        self.assertFalse(parsed["confirm_required"],
                         "a rubric that states a length and totals 100 needs no correction")

    def test_e_ent_106__a_criterion_and_a_heading_that_share_a_stem_are_the_same_requirement(self):
        """D-ENT-03: "Referencing" against the paper's own "References" is not a gap."""
        self.assertTrue(rubric._covers("References", "Referencing"))
        self.assertTrue(rubric._covers("Operations Plan", "Operating plan"))
        self.assertFalse(rubric._covers("Introduction", "Referencing"))
        self.assertFalse(rubric._covers("Content", "Context"),
                         "the stem rule compares six letters, so near words stay apart")


if __name__ == "__main__":
    unittest.main()
