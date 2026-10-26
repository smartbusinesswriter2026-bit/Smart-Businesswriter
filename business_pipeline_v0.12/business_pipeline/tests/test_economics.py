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


if __name__ == "__main__":
    unittest.main()
