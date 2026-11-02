import sys, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline

YES = lambda s: True
CBA = {"costs": ["50000", "10000", "10000"], "benefits": ["20000", "30000", "40000"], "discount_rate": "0.05"}
CEA = {"options": [{"name": "basic", "cost": "10000", "effect": "40"}, {"name": "intensive", "cost": "18000", "effect": "60"}]}
SROI = {"investment": "60000", "benefits": ["20000", "25000", "30000"], "discount_rate": "0.04"}


def close(a, b, tol="1e-9"):
    a, b = D(str(a)), D(str(b))
    return abs(a - b) <= D(tol) * max(D(1), abs(b))


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class CostBenefit(unittest.TestCase):
    def m(self): return LIBRARY["cost_benefit"]

    def test_present_values_against_an_independent_loop(self):
        out = self.m().impl(CBA)
        pv = lambda xs: sum(D(str(x)) / D("1.05") ** (i + 1) for i, x in enumerate(xs))
        self.assertTrue(close(out["pv_costs"], pv(CBA["costs"])))
        self.assertTrue(close(out["pv_benefits"], pv(CBA["benefits"])))
        self.assertTrue(close(out["net_present_value"], pv(CBA["benefits"]) - pv(CBA["costs"])))
        self.assertTrue(close(out["benefit_cost_ratio"], pv(CBA["benefits"]) / pv(CBA["costs"])))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(CBA, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(CBA, self.m().impl)))
        for inp in ({"costs": ["1"], "benefits": ["1", "2"]}, {"costs": [], "benefits": []},
                    {"costs": ["1"], "benefits": ["1"], "discount_rate": "-1"}):
            self.assertEqual(Pipeline().run({"objective": "x", "method": "cost_benefit", "inputs": inp}, YES).status, "blocked", inp)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Appraise", "method": "cost_benefit", "currency": "USD", "period": "annual", "inputs": CBA})
        self.assertIn("present value of benefits", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 6); self.assertTrue(all(ok for ok in d.appendix["tests"]))


class CostEffectiveness(unittest.TestCase):
    def m(self): return LIBRARY["cost_effectiveness"]

    def test_icer_and_dominance(self):
        out = self.m().impl(CEA)
        self.assertEqual(out["icer_intensive"], D(400)); self.assertEqual(out["delta_effect_intensive"], D(20))
        cheap = self.m().impl({"options": [{"name": "base", "cost": "100", "effect": "10"}, {"name": "better", "cost": "80", "effect": "12"}]})
        self.assertEqual(cheap["dominant_better"], D(1))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(CEA, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(CEA, self.m().impl)))
        for inp in ({"options": CEA["options"][:1]},
                    {"options": [{"name": "a", "cost": "1", "effect": "5"}, {"name": "b", "cost": "2", "effect": "5"}]},
                    {"options": [{"name": "a", "cost": "-1", "effect": "5"}, {"name": "b", "cost": "2", "effect": "6"}]}):
            self.assertEqual(Pipeline().run({"objective": "x", "method": "cost_effectiveness", "inputs": inp}, YES).status, "blocked", inp)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Compare", "method": "cost_effectiveness", "currency": "USD", "period": "annual", "inputs": CEA})
        self.assertIn("incremental cost per unit of effect", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 7); self.assertTrue(all(ok for ok in d.appendix["tests"]))


class SocialReturn(unittest.TestCase):
    def m(self): return LIBRARY["sroi"]

    def test_ratio_arithmetic(self):
        out = self.m().impl(SROI)
        pv = sum(D(str(x)) / D("1.04") ** (i + 1) for i, x in enumerate(SROI["benefits"]))
        self.assertTrue(close(out["pv_benefits"], pv)); self.assertTrue(close(out["sroi_ratio"], pv / D("60000")))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(SROI, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(SROI, self.m().impl)))
        for inp in ({"investment": "0", "benefits": ["1"]}, {"investment": "5", "benefits": []},
                    {"investment": "5", "benefits": ["1"], "discount_rate": "-2"}):
            self.assertEqual(Pipeline().run({"objective": "x", "method": "sroi", "inputs": inp}, YES).status, "blocked", inp)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Social return", "method": "sroi", "currency": "USD", "period": "annual", "inputs": SROI})
        self.assertIn("social return", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 6); self.assertTrue(all(ok for ok in d.appendix["tests"]))


class Registration(unittest.TestCase):
    def test_contracts_and_presets(self):
        from bp import server
        for mid, metric, preset in (("cost_benefit", "net_present_value", "cba"), ("cost_effectiveness", "n_options", "cea"), ("sroi", "sroi_ratio", "sroi")):
            self.assertEqual(LIBRARY[mid].tier, "T2"); self.assertEqual(LIBRARY[mid].metric, metric)
            self.assertIn(preset, server.PRESETS); self.assertEqual(server.PRESETS[preset]["method"], mid)

    def test_deterministic(self):
        for mid, inp in (("cost_benefit", CBA), ("cost_effectiveness", CEA), ("sroi", SROI)):
            m = LIBRARY[mid]
            self.assertEqual({k: str(v) for k, v in m.impl(inp).items() if k != "_appendix"},
                             {k: str(v) for k, v in m.impl(inp).items() if k != "_appendix"})


if __name__ == "__main__":
    unittest.main()
