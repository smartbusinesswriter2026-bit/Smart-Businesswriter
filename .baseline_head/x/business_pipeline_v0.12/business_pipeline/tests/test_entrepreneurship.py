"""The Entrepreneurship shelf: the five venture methods, the break-even extension
and the student page (B-103/B-104).

The arithmetic is hand-checked against the PHP worked examples in
`docs/ENTREPRENEURSHIP_STUDENT_GUIDE.md`.  The page tests are structural: every
tile must carry a group, a period, a level and study notes, and every preset the
tiles launch must exist.
"""

import re
import sys
import unittest
from decimal import Decimal as D

sys.path.insert(0, "src")
from bp import server
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline
from bp.product import subjects

YES = lambda spec: True

BREAKEVEN = {"fixed": "45000", "price": "25", "variable": "15",
             "expected_units": "6000", "target_profit": "20000"}
MARKET = {"target_population": "50000", "annual_spend_per_customer": "1200",
          "serviceable_share": "0.30", "obtainable_share": "0.10"}
CAPITAL = {"start_up_costs": "350000", "working_capital": "120000", "contingency_rate": "0.10",
           "owner_equity": "150000", "loan_amount": "200000"}
RUNWAY = {"opening_cash": "300000", "monthly_net_cash_flow": "-40000",
          "monthly_growth": "0", "target_months": "9"}
PRICING = {"unit_cost": "15", "fixed_cost": "45000", "expected_units": "6000",
           "markup_rate": "0.60", "target_margin_rate": "0.375", "target_profit": "20000"}
ROI = {"total_investment": "500000", "net_gain": "125000", "years": "3"}

NEW_METHODS = ("market_sizing", "startup_capital", "cash_runway", "pricing_decision",
               "return_on_investment")
NEW_PRESETS = ("marketsize", "startupcapital", "cashrunway", "pricing", "roi")


def delivered(request):
    d = Pipeline().run(request, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


def blocked(method, inputs):
    return Pipeline().run({"objective": "x", "method": method, "inputs": inputs}, YES).status == "blocked"


def checks_pass(method, inputs):
    m = LIBRARY[method]
    result = m.tests(inputs, m.impl)
    assert tuple(name for name, _ in result) == m.test_names, (method, result)
    return all(ok for _, ok in result)


def template_has_no_raw_digits(method, inputs, period="annual"):
    m = LIBRARY[method]
    text = m.template(m.impl(inputs), period, {})
    return not re.search(r"\d", re.sub(r"\{\{ref:[^}]*\}\}", "", text))


class BreakEvenExtension(unittest.TestCase):
    def m(self):
        return LIBRARY["breakeven"]

    def test_the_original_quantity_and_the_new_figures(self):
        out = self.m().impl(BREAKEVEN)
        self.assertEqual(out["breakeven_units"], D(4500))
        self.assertEqual(out["contribution_margin"], D(10))
        self.assertEqual(out["breakeven_revenue"], D(112500))
        self.assertEqual(out["margin_of_safety_units"], D(1500))
        self.assertEqual(out["margin_of_safety_ratio"], D("0.25"))
        self.assertEqual(out["target_profit_units"], D(6500))

    def test_the_quantity_is_unchanged_when_no_optional_input_is_declared(self):
        out = self.m().impl({"fixed": "1000", "price": "20", "variable": "10"})
        self.assertEqual(out["breakeven_units"], D(100))
        for key in ("margin_of_safety_units", "target_profit_units"):
            self.assertNotIn(key, out)

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("breakeven", BREAKEVEN))
        self.assertTrue(checks_pass("breakeven", {"fixed": "1000", "price": "20", "variable": "10"}))
        for inputs in ({"fixed": "1000", "price": "10", "variable": "10"},
                       {"fixed": "-1", "price": "20", "variable": "10"},
                       {"fixed": "1000", "price": "20", "variable": "10", "expected_units": "-5"}):
            self.assertTrue(blocked("breakeven", inputs), inputs)

    def test_pipeline_delivers_a_php_example(self):
        d = delivered({"objective": "Break-even", "method": "breakeven", "currency": "PHP",
                       "period": "annual", "inputs": BREAKEVEN})
        self.assertIn("breaks even", d.report.lower())
        self.assertIn("margin of safety", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class MarketSizing(unittest.TestCase):
    def m(self):
        return LIBRARY["market_sizing"]

    def test_arithmetic(self):
        out = self.m().impl(MARKET)
        self.assertEqual((out["total_addressable_market"], out["serviceable_available_market"],
                          out["serviceable_obtainable_market"]),
                         (D(60000000), D(18000000), D(1800000)))
        self.assertEqual(out["customers_in_som"], D(1500))
        self.assertEqual(out["share_of_tam_obtained"], D("0.03"))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("market_sizing", MARKET))
        for inputs in ({"target_population": "0", "annual_spend_per_customer": "1200",
                        "serviceable_share": "0.3", "obtainable_share": "0.1"},
                       {"target_population": "100", "annual_spend_per_customer": "1200",
                        "serviceable_share": "1.5", "obtainable_share": "0.1"},
                       {"target_population": "100", "annual_spend_per_customer": "1200",
                        "serviceable_share": "0.3", "obtainable_share": "0"}):
            self.assertTrue(blocked("market_sizing", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Market size", "method": "market_sizing", "currency": "PHP",
                       "period": "annual", "inputs": MARKET})
        self.assertIn("addressable market", d.report.lower())
        self.assertNotIn("{{ref:", d.report)
        self.assertTrue(template_has_no_raw_digits("market_sizing", MARKET))


class StartupCapital(unittest.TestCase):
    def m(self):
        return LIBRARY["startup_capital"]

    def test_arithmetic(self):
        out = self.m().impl(CAPITAL)
        self.assertEqual((out["contingency_reserve"], out["total_funding_required"],
                          out["declared_sources"], out["amount_to_raise"]),
                         (D(47000), D(517000), D(350000), D(167000)))
        self.assertEqual(out["funding_surplus"], D(0))
        self.assertAlmostEqual(float(out["funded_share"]), 350000 / 517000, places=9)

    def test_a_surplus_is_reported_rather_than_a_negative_raise(self):
        out = self.m().impl({**CAPITAL, "loan_amount": "400000"})
        self.assertEqual(out["amount_to_raise"], D(0))
        self.assertEqual(out["funding_surplus"], D(33000))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("startup_capital", CAPITAL))
        for inputs in ({"start_up_costs": "0", "working_capital": "0"},
                       {"start_up_costs": "100000", "working_capital": "0", "contingency_rate": "1"},
                       {"start_up_costs": "100000", "working_capital": "0", "owner_equity": "-1"}):
            self.assertTrue(blocked("startup_capital", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Capital", "method": "startup_capital", "currency": "PHP",
                       "period": "annual", "inputs": CAPITAL})
        self.assertIn("amount to raise", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class CashRunway(unittest.TestCase):
    def m(self):
        return LIBRARY["cash_runway"]

    def test_arithmetic_flat_and_growing(self):
        out = self.m().impl(RUNWAY)
        self.assertEqual(out["runway_months"], D("7.5"))
        self.assertEqual(out["lowest_cash_balance"], D(-60000))
        self.assertEqual(out["funding_gap"], D(60000))
        self.assertEqual(out["cash_at_target_month"], D(-60000))
        growing = self.m().impl({**RUNWAY, "monthly_growth": "0.05", "target_months": "12"})
        self.assertLess(growing["runway_months"], out["runway_months"])

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("cash_runway", RUNWAY))
        self.assertTrue(checks_pass("cash_runway", {**RUNWAY, "monthly_growth": "0.05"}))
        for inputs in ({"opening_cash": "300000", "monthly_net_cash_flow": "1000"},
                       {"opening_cash": "300000", "monthly_net_cash_flow": "-1000", "target_months": "0"},
                       {"opening_cash": "-1", "monthly_net_cash_flow": "-1000"},
                       {"opening_cash": "300000", "monthly_net_cash_flow": "-1000", "monthly_growth": "-1"}):
            self.assertTrue(blocked("cash_runway", inputs), inputs)

    def test_a_flow_that_never_burns_cash_blocks_instead_of_reporting_infinity(self):
        self.assertTrue(blocked("cash_runway", {"opening_cash": "1000", "monthly_net_cash_flow": "0"}))

    def test_pipeline_delivers_monthly(self):
        d = delivered({"objective": "Runway", "method": "cash_runway", "currency": "PHP",
                       "period": "monthly", "inputs": RUNWAY})
        self.assertIn("runway", d.report.lower())
        self.assertIn("months", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class PricingDecision(unittest.TestCase):
    def m(self):
        return LIBRARY["pricing_decision"]

    def test_arithmetic(self):
        out = self.m().impl(PRICING)
        self.assertEqual((out["cost_plus_price"], out["break_even_price"]),
                         (D(24), D("22.5")))
        self.assertEqual(out["margin_price"], D(24))
        self.assertAlmostEqual(float(out["target_return_price"]), float(D(155000) / D(6000)), places=9)

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("pricing_decision", PRICING))
        for inputs in ({"unit_cost": "0", "expected_units": "100", "markup_rate": "0.5"},
                       {"unit_cost": "10", "expected_units": "0", "markup_rate": "0.5"},
                       {"unit_cost": "10", "expected_units": "100", "markup_rate": "-0.1"},
                       {"unit_cost": "10", "expected_units": "100", "markup_rate": "0.5",
                        "target_margin_rate": "1"}):
            self.assertTrue(blocked("pricing_decision", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Pricing", "method": "pricing_decision", "currency": "PHP",
                       "period": "annual", "inputs": PRICING})
        self.assertIn("cost-plus", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class ReturnOnInvestment(unittest.TestCase):
    def m(self):
        return LIBRARY["return_on_investment"]

    def test_arithmetic(self):
        out = self.m().impl(ROI)
        self.assertEqual(out["roi"], D("0.25"))
        self.assertAlmostEqual(float(out["annualised_roi"]), 1.25 ** (1 / 3) - 1, places=9)

    def test_a_loss_is_reported_and_a_total_loss_is_refused_with_years(self):
        self.assertEqual(self.m().impl({"total_investment": "1000", "net_gain": "-250"})["roi"], D("-0.25"))
        self.assertTrue(blocked("return_on_investment", {"total_investment": "1000", "net_gain": "-1000", "years": "2"}))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("return_on_investment", ROI))
        for inputs in ({"total_investment": "0", "net_gain": "100"},
                       {"total_investment": "1000", "net_gain": "100", "years": "0"}):
            self.assertTrue(blocked("return_on_investment", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "ROI", "method": "return_on_investment", "currency": "PHP",
                       "period": "annual", "inputs": ROI})
        self.assertIn("return on investment", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class PresetDelivery(unittest.TestCase):
    def test_every_new_preset_delivers(self):
        for preset in NEW_PRESETS:
            p = server.PRESETS[preset]
            d = delivered({"objective": p["objective"], "method": p["method"], "inputs": p["inputs"],
                           "currency": p.get("currency"), "period": p.get("period")})
            self.assertTrue(d.report, preset)
            self.assertNotIn("{{ref:", d.report, preset)
            self.assertTrue(all(ok for _, ok, *_ in d.appendix["tests"]), preset)


class EntrepreneurshipPage(unittest.TestCase):
    def setUp(self):
        self.page = subjects.detail("entrepreneurship")

    def test_the_shelf_is_a_business_plan_not_a_grid(self):
        self.assertGreaterEqual(len(self.page["tools"]), 28)
        order = []
        for tool in self.page["tools"]:
            if tool["group"] not in order:
                order.append(tool["group"])
        self.assertEqual(order, ["Market and customers", "Costs, pricing and break-even",
                                 "Operations plan", "Financial plan and return", "Funding and valuation",
                                 "Impact and options"])
        self.assertTrue(self.page["guidance"])
        self.assertIn("business plan", self.page["guidance"])

    def test_every_tile_carries_a_period_level_and_study_notes(self):
        for tool in self.page["tools"]:
            self.assertTrue(tool["period"], tool["key"])
            self.assertIn(tool["level"], ("intro", "intermediate", "advanced"), tool["key"])
            self.assertTrue(tool["formula"], tool["key"])
            self.assertTrue(tool["steps"], tool["key"])
            self.assertTrue(tool["common_mistakes"], tool["key"])
            for related in tool["related"]:
                self.assertIn(related, subjects.TOOL_INFO, (tool["key"], related))

    def test_every_tile_launches_a_real_method_and_preset(self):
        composites = {"case_decision"}  # a composite preset, not a single LIBRARY method
        for tool in self.page["tools"]:
            if tool["method"] not in composites:
                self.assertIn(tool["method"], LIBRARY, tool["key"])
            self.assertIn(tool["preset"], server.PRESETS, tool["key"])
            self.assertEqual(server.PRESETS[tool["preset"]]["method"], tool["method"], tool["key"])

    def test_the_page_has_a_glossary_and_the_new_terms(self):
        terms = {row["term"] for row in self.page["glossary"]}
        for term in ("TAM", "SAM", "SOM", "Break-even point", "Margin of safety",
                     "CAC", "LTV", "Runway", "ROI"):
            self.assertIn(term, terms)

    def test_the_catalogue_rows_state_what_is_partial_and_what_is_not_built(self):
        rows = {row["id"]: row for row in self.page["catalogue"]}
        for rid in ("QNT-MKT-01", "QNT-FIN-07"):
            self.assertTrue(rows[rid]["implementation_status"].startswith("partial:"), rid)
        for rid in ("STR-15", "STR-16", "STR-17"):
            self.assertTrue(rows[rid]["implementation_status"].startswith(("worksheet available", "template available")), rid)
        # Reading lenses are not shelf rows any more: a theory is reached by
        # naming it in the brief, not by clicking a tile.
        self.assertNotIn("THE-06", rows)

    def test_the_finance_grouping_did_not_leak(self):
        finance = subjects.detail("finance")
        self.assertTrue(all(tool["group"] for tool in finance["tools"]))
        # Economics has its own grouping now (ECONOMICS_GROUPS).  The Finance
        # group names must not leak into it: every Economics tool is either
        # ungrouped or grouped by an Economics group name.
        economics = subjects.detail("economics")
        finance_groups = set(subjects.FINANCE_GROUPS.values())
        economics_groups = set(subjects.ECONOMICS_GROUPS.values())
        for tool in economics["tools"]:
            self.assertIn(tool["group"], economics_groups | {None}, tool["key"])
            self.assertNotIn(tool["group"], finance_groups - economics_groups, tool["key"])


if __name__ == "__main__":
    unittest.main()
