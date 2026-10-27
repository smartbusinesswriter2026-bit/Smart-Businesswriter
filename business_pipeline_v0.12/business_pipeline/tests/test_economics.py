import sys, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import ingest
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline

YES = lambda s: True
PRODUCTS = [{"name": "coffee", "price": "5", "variable_cost": "2", "mix_units": "3"},
            {"name": "cake", "price": "6", "variable_cost": "3", "mix_units": "1"}]
UNIT = {"price": "49", "variable_cost": "12", "acquisition_cost": "80", "churn_rate": "0.04"}
MULTI = {"fixed_costs": "6000", "products": PRODUCTS}
EQ = {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2"}
ELASTIC = {"quantity_1": "100", "price_1": "10", "quantity_2": "140", "price_2": "8"}
TAX = {**EQ, "tax_per_unit": "6"}
CEILING = {**EQ, "control_type": "ceiling", "control_price": "15"}
CONCENTRATION = {"firm_revenues": ["40", "25", "15", "10", "10"]}


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class Mapping(unittest.TestCase):
    def test_maps_a_value_column_into_a_method(self):
        t = ingest.read_table("scores.csv", b"name,score\nAda,10\nBo,12.5\nCy,9\n")
        req = ingest.to_method_inputs(t, "descriptive_stats", {"values": "score"})
        self.assertEqual(req["method"], "descriptive_stats"); self.assertEqual(req["inputs"], {"values": ["10", "12.5", "9"]})
        self.assertEqual(req["provenance"]["kind"], "sourced"); self.assertIn("does not verify", req["provenance"]["note"])
        self.assertEqual(req["not_mapped"], ["missing_codes"])

    def test_maps_columns_into_a_column_map_input(self):
        t = ingest.read_table("wide.csv", b"a,b\n10,14\n12,15\n11,16\n")
        req = ingest.to_method_inputs(t, "welch_t", {"groups": {"a": "a", "b": "b"}})
        self.assertEqual(req["inputs"]["groups"], {"a": ["10", "12", "11"], "b": ["14", "15", "16"]})

    def test_refuses_bad_mappings(self):
        t = ingest.read_table("scores.csv", b"name,score\nAda,10\nBo,12\n")
        bad = (({"values": "name"}, "descriptive_stats"), ({"values": "nope"}, "descriptive_stats"),
               ({}, "descriptive_stats"), ({"values": "score"}, "no_such_method"),
               ({"values": "score"}, "wacc"))
        for mapping, mid in bad:
            with self.assertRaises(ingest.IngestError): ingest.to_method_inputs(t, mid, mapping)


class UnitEconomics(unittest.TestCase):
    def m(self): return LIBRARY["unit_economics"]

    def test_arithmetic(self):
        out = self.m().impl(UNIT)
        self.assertEqual((out["unit_margin"], out["ltv"], out["ltv_cac"]), (D(37), D(925), D("11.5625")))
        self.assertLess(abs(float(out["payback_periods"]) - 80 / 37), 1e-12)

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(UNIT, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(UNIT, self.m().impl)))
        for inputs in ({"price": "0", "variable_cost": "1", "acquisition_cost": "5"},
                       {"price": "5", "variable_cost": "5", "acquisition_cost": "5"},
                       {"price": "5", "variable_cost": "1", "acquisition_cost": "5", "churn_rate": "1.2"},
                       {"price": "5"}):
            self.assertEqual(Pipeline().run({"objective": "x", "method": "unit_economics", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Unit economics", "method": "unit_economics", "currency": "USD", "period": "annual", "inputs": UNIT})
        self.assertIn("contribution margin", d.report); self.assertIn("lifetime value", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 9)
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class MultiBreakeven(unittest.TestCase):
    def m(self): return LIBRARY["multi_product_breakeven"]

    def test_arithmetic(self):
        out = self.m().impl(MULTI)
        self.assertEqual((out["weighted_contribution"], out["breakeven_total_units"]), (D(3), D(2000)))
        self.assertEqual((out["units_coffee"], out["units_cake"]), (D(1500), D(500)))
        self.assertEqual(out["breakeven_revenue"], D("10500"))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(MULTI, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(MULTI, self.m().impl)))
        bad = ({"fixed_costs": "10", "products": PRODUCTS[:1]},
               {"fixed_costs": "10", "products": [{"name": "a", "price": "1", "variable_cost": "2", "mix_units": "1"},
                                                    {"name": "b", "price": "1", "variable_cost": "2", "mix_units": "1"}]},
               {"fixed_costs": "10", "products": [{"name": "a", "price": "1", "variable_cost": "0", "mix_units": "0"}, PRODUCTS[1]]})
        for inputs in bad:
            self.assertEqual(Pipeline().run({"objective": "x", "method": "multi_product_breakeven", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Break-even for the mix", "method": "multi_product_breakeven", "currency": "USD", "period": "annual", "inputs": MULTI})
        self.assertIn("break-even", d.report); self.assertIn("mix-weighted", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 7)
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class Registration(unittest.TestCase):
    def test_contracts_and_presets(self):
        from bp import server
        self.assertEqual((LIBRARY["unit_economics"].tier, LIBRARY["unit_economics"].metric), ("T1", "unit_margin"))
        self.assertEqual((LIBRARY["multi_product_breakeven"].tier, LIBRARY["multi_product_breakeven"].metric), ("T1", "breakeven_total_units"))
        self.assertIn("unitecon", server.PRESETS); self.assertIn("multibreakeven", server.PRESETS)

    def test_deterministic(self):
        for mid, inp in (("unit_economics", UNIT), ("multi_product_breakeven", MULTI)):
            m = LIBRARY[mid]
            self.assertEqual({k: str(v) for k, v in m.impl(inp).items() if k != "_appendix"},
                             {k: str(v) for k, v in m.impl(inp).items() if k != "_appendix"})


class Equilibrium(unittest.TestCase):
    def m(self): return LIBRARY["demand_supply_equilibrium"]

    def test_arithmetic(self):
        out = self.m().impl(EQ)
        self.assertEqual((out["equilibrium_price"], out["equilibrium_quantity"]), (D(20), D(60)))
        self.assertEqual((out["consumer_surplus"], out["producer_surplus"], out["total_surplus"]),
                         (D(900), D(900), D(1800)))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(EQ, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(EQ, self.m().impl)))
        bad = ({"demand_intercept": "100", "demand_slope": "0", "supply_intercept": "20", "supply_slope": "2"},
               {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "120", "supply_slope": "2"},
               {"demand_intercept": "100", "demand_slope": "-2", "supply_intercept": "20", "supply_slope": "2"},
               {"demand_intercept": "100"})
        for inputs in bad:
            self.assertEqual(Pipeline().run({"objective": "x", "method": "demand_supply_equilibrium", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Market equilibrium", "method": "demand_supply_equilibrium", "currency": "PHP", "period": "annual", "inputs": EQ})
        self.assertIn("consumer surplus", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class Elasticity(unittest.TestCase):
    def m(self): return LIBRARY["elasticity"]

    def test_arithmetic(self):
        out = self.m().impl(ELASTIC)
        self.assertEqual(out["price_elasticity"], D("-1.5"))
        self.assertEqual(out["revenue_change"], D(120))
        self.assertEqual(out["elastic"], D(1))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(ELASTIC, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(ELASTIC, self.m().impl)))
        bad = ({"quantity_1": "100", "price_1": "10", "quantity_2": "140", "price_2": "10"},
               {"quantity_1": "0", "price_1": "10", "quantity_2": "0", "price_2": "8"},
               {"quantity_1": "100", "price_1": "-1", "quantity_2": "140", "price_2": "8"},
               {"quantity_1": "100", "price_1": "10"})
        for inputs in bad:
            self.assertEqual(Pipeline().run({"objective": "x", "method": "elasticity", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Elasticity", "method": "elasticity", "currency": "PHP", "period": "annual", "inputs": ELASTIC})
        self.assertIn("elasticity", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class TaxIncidence(unittest.TestCase):
    def m(self): return LIBRARY["tax_incidence"]

    def test_arithmetic(self):
        out = self.m().impl(TAX)
        self.assertEqual((out["consumer_price"], out["producer_price"], out["quantity_traded"]), (D(23), D(17), D(54)))
        self.assertEqual((out["consumer_incidence"], out["producer_incidence"]), (D(3), D(3)))
        self.assertEqual((out["tax_revenue"], out["deadweight_loss"]), (D(324), D(18)))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(TAX, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(TAX, self.m().impl)))
        bad = ({**EQ, "tax_per_unit": "-1"},
               {**EQ, "tax_per_unit": "100"},
               {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2"})
        for inputs in bad:
            self.assertEqual(Pipeline().run({"objective": "x", "method": "tax_incidence", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Tax incidence", "method": "tax_incidence", "currency": "PHP", "period": "annual", "inputs": TAX})
        self.assertIn("tax", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class PriceControl(unittest.TestCase):
    def m(self): return LIBRARY["price_control"]

    def test_arithmetic(self):
        out = self.m().impl(CEILING)
        self.assertEqual((out["quantity_traded"], out["shortage"], out["deadweight_loss"]), (D(50), D(20), D(50)))
        floor = self.m().impl({**EQ, "control_type": "floor", "control_price": "25"})
        self.assertEqual((floor["quantity_traded"], floor["surplus"], floor["deadweight_loss"]), (D(50), D(20), D(50)))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(CEILING, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(CEILING, self.m().impl)))
        bad = ({**EQ, "control_type": "ceiling", "control_price": "0"},
               {**EQ, "control_type": "floor", "control_price": "60"},
               {**EQ, "control_type": "sideways", "control_price": "15"})
        for inputs in bad:
            self.assertEqual(Pipeline().run({"objective": "x", "method": "price_control", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Price ceiling", "method": "price_control", "currency": "PHP", "period": "annual", "inputs": CEILING})
        self.assertIn("control", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class MarketConcentration(unittest.TestCase):
    def m(self): return LIBRARY["market_concentration"]

    def test_arithmetic(self):
        out = self.m().impl(CONCENTRATION)
        self.assertEqual((out["n_firms"], out["hhi"]), (D(5), D("2650.0000")))
        self.assertEqual(out["cr4"], D("90.00"))
        self.assertLess(abs(float(out["effective_n"]) - 10000 / 2650), 1e-12)

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(CONCENTRATION, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(CONCENTRATION, self.m().impl)))
        bad = ({"firm_revenues": ["100"]},
               {"firm_revenues": ["-1", "2"]},
               {"firm_revenues": ["0", "0"]})
        for inputs in bad:
            self.assertEqual(Pipeline().run({"objective": "x", "method": "market_concentration", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Concentration", "method": "market_concentration", "currency": "PHP", "period": "annual", "inputs": CONCENTRATION})
        self.assertIn("hhi", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


if __name__ == "__main__":
    unittest.main()
