"""The three economics service tiles: order, grouping, solving and the gate."""

import base64
import unittest

from bp import methods
from bp.product import api, economics, subjects


def _run(method_id, inputs):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


api.attach_methods(_run, methods.describe)


class TileOrderTest(unittest.TestCase):
    def test_the_shelf_starts_with_the_three_service_tiles(self):
        page = subjects.detail("economics")
        self.assertEqual([tile["key"] for tile in page["tiles"]][:3],
                         ["macroeconomics", "microeconomics", "managerial_economics"])
        for tile in page["tiles"][:3]:
            self.assertTrue(tile["service"], tile["key"])

    def test_the_old_market_and_firm_tiles_are_gone_and_their_tools_moved(self):
        page = subjects.detail("economics")
        keys = {tile["key"] for tile in page["tiles"]}
        self.assertNotIn("market_basics", keys)
        self.assertNotIn("firm_behaviour", keys)
        micro = next(tile for tile in page["tiles"] if tile["key"] == "microeconomics")
        self.assertEqual([tool["key"] for tool in micro["tools"]],
                         ["equilibrium", "elasticity", "taxincidence", "pricecontrol",
                          "concentration", "costcurves", "profitmax", "marketpower",
                          "pricediscrimination", "cournot", "nash"])

    def test_pricing_and_cost_benefit_moved_to_managerial_economics(self):
        page = subjects.detail("economics")
        managerial = next(tile for tile in page["tiles"] if tile["key"] == "managerial_economics")
        methods_offered = {tool["method"] for tool in managerial["tools"]}
        for method in ("pricing_decision", "demand_curve", "cost_benefit",
                       "cost_effectiveness", "sroi", "breakeven", "multi_product_breakeven",
                       "unit_economics"):
            self.assertIn(method, methods_offered)

    def test_the_remaining_tiles_keep_their_tools(self):
        page = subjects.detail("economics")
        by_key = {tile["key"]: tile for tile in page["tiles"]}
        self.assertEqual([tool["method"] for tool in by_key["econometrics"]["tools"]],
                         ["panel_regression", "instrumental_variables", "regression_discontinuity",
                          "probit", "difference_in_differences"])
        self.assertIn("npv", {tool["key"] for tool in by_key["quantitative_core"]["tools"]})


class ServiceTest(unittest.TestCase):
    def test_each_service_offers_its_problem_types(self):
        self.assertIn("nationalincome", [row["key"] for row in economics.problem_types("macroeconomics")])
        self.assertIn("cournot", [row["key"] for row in economics.problem_types("microeconomics")])
        self.assertIn("breakeven", [row["key"] for row in economics.problem_types("managerial_economics")])

    def test_a_macro_problem_solves_and_returns_a_word_file(self):
        out = economics.solve("macroeconomics", "nationalincome",
                              {"consumption": "500", "investment": "200", "government_spending": "100",
                               "exports": "50", "imports": "30"}, "Compute GDP")
        self.assertEqual(out["lines"][0], "Gdp: 820")
        data = base64.b64decode(out["docx"]["data"])
        self.assertTrue(data.startswith(b"PK"))
        self.assertGreater(len(data), 5000)

    def test_a_micro_problem_solves(self):
        out = economics.solve("microeconomics", "equilibrium",
                              {"demand_intercept": "100", "demand_slope": "2",
                               "supply_intercept": "20", "supply_slope": "2"},
                              "Find the equilibrium price and quantity")
        self.assertIn("Equilibrium price: 20", out["lines"])

    def test_a_managerial_problem_solves(self):
        out = economics.solve("managerial_economics", "breakeven",
                              {"fixed": "300000", "price": "120", "variable": "55"},
                              "Find the break-even quantity")
        self.assertTrue(any("4,615" in line for line in out["lines"]), out["lines"])

    def test_the_gate_refuses_an_instruction_for_another_problem_type(self):
        with self.assertRaises(economics.EconomicsError) as raised:
            economics.solve("macroeconomics", "nationalincome", {"consumption": "1"},
                            "Find the Cournot equilibrium")
        self.assertIn("does not look like", str(raised.exception))

    def test_figures_are_read_from_the_instruction(self):
        text = ("Household consumption 500; gross investment 200; government consumption and "
                "investment 100; exports 50; imports 30.")
        out = economics.solve("macroeconomics", "nationalincome", {}, text)
        self.assertEqual(out["read"]["consumption"], "500")
        self.assertEqual(out["read"]["government_spending"], "100")
        self.assertEqual(out["lines"][0], "Gdp: 820")

    def test_manual_figures_override_the_reader(self):
        out = economics.solve("macroeconomics", "nationalincome",
                              {"consumption": "600"},
                              "Household consumption 500; gross investment 200; "
                              "government consumption and investment 100; exports 50; imports 30.")
        self.assertEqual(out["inputs"]["consumption"], "600")

    def test_a_missing_required_figure_is_named(self):
        with self.assertRaises(economics.EconomicsError) as raised:
            economics.solve("managerial_economics", "breakeven", {"fixed": "300000"})
        self.assertIn("does not state", str(raised.exception))

    def test_the_route_serves_types_and_solves(self):
        status, page = api.handle("GET", "/api/cases/economics/macroeconomics")
        self.assertEqual(status, 200)
        self.assertIn("nationalincome", [row["key"] for row in page["types"]])
        status, out = api.handle("POST", "/api/cases/economics/macroeconomics",
                                 {"problem": "nationalincome",
                                  "figures": {"consumption": "500", "investment": "200",
                                              "government_spending": "100", "exports": "50",
                                              "imports": "30"},
                                  "instruction": "Compute GDP"})
        self.assertEqual(status, 200)
        self.assertEqual(out["lines"][0], "Gdp: 820")


if __name__ == "__main__":
    unittest.main()
