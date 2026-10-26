import sys, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline

YES = lambda s: True
WACC_IN = {"equity_value": "800000", "debt_value": "200000", "cost_of_equity": "0.12", "cost_of_debt_after_tax": "0.05"}
DCF_IN = {"cashflows": ["100000", "120000", "140000", "155000"], "discount_rate": "0.10", "terminal_growth": "0.02"}


def close(a, b, tol="1e-9"):
    a, b = D(str(a)), D(str(b))
    return abs(a - b) <= D(tol) * max(D(1), abs(b))


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class Wacc(unittest.TestCase):
    def m(self): return LIBRARY["wacc"]

    def test_arithmetic(self):
        out = self.m().impl(WACC_IN)
        self.assertEqual(out["wacc"], D("0.106"))
        self.assertEqual((out["weight_equity"], out["weight_debt"]), (D("0.8"), D("0.2")))

    def test_frozen_checks_pass_and_are_declared(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(WACC_IN, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(WACC_IN, self.m().impl)))

    def test_invalid_capital_structures_are_refused(self):
        bad = ({**WACC_IN, "equity_value": "0", "debt_value": "0"}, {**WACC_IN, "debt_value": "-1"},
               {**WACC_IN, "cost_of_equity": "-0.01"}, {"equity_value": "1"})
        for inputs in bad:
            self.assertEqual(Pipeline().run({"objective": "x", "method": "wacc", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers_and_renders_a_percentage(self):
        d = delivered({"objective": "What is our cost of capital?", "method": "wacc", "period": "annual", "inputs": WACC_IN})
        self.assertIn("%", d.report); self.assertEqual(len(d.appendix["artifacts"]), 5)
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class Dcf(unittest.TestCase):
    def m(self): return LIBRARY["dcf_valuation"]

    def expected(self, inp):
        cfs = [D(str(x)) for x in inp["cashflows"]]; r = D(str(inp["discount_rate"]))
        pv = D(0)
        for t in range(1, len(cfs) + 1): pv += cfs[t - 1] / (1 + r) ** t
        g = D(str(inp["terminal_growth"])) if inp.get("terminal_growth") else None
        tv = cfs[-1] * (1 + g) / (r - g) if g is not None else D(0)
        pvt = tv / (1 + r) ** len(cfs)
        return {"pv_explicit": pv, "pv_terminal": pvt, "terminal_value": tv, "enterprise_value": pv + pvt}

    def test_values_match_an_independent_loop(self):
        out = self.m().impl(DCF_IN); exp = self.expected(DCF_IN)
        for k, v in exp.items(): self.assertTrue(close(out[k], v), k)
        self.assertTrue(close(out["enterprise_value"], "1750939.14", "1e-5"))   # rounded reference value
        self.assertGreater(out["terminal_share"], D("0.5"))

    def test_frozen_checks_pass_and_are_declared(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(DCF_IN, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(DCF_IN, self.m().impl)))

    def test_without_terminal_growth_only_the_forecast_is_valued(self):
        out = self.m().impl({k: v for k, v in DCF_IN.items() if k != "terminal_growth"})
        self.assertEqual(out["pv_terminal"], D(0)); self.assertEqual(out["enterprise_value"], out["pv_explicit"])

    def test_invalid_assumptions_are_refused(self):
        bad = ({**DCF_IN, "terminal_growth": "0.10"}, {"cashflows": [], "discount_rate": "0.1"}, {"cashflows": ["1"], "discount_rate": "-1"})
        for inputs in bad:
            self.assertEqual(Pipeline().run({"objective": "x", "method": "dcf_valuation", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Value the project", "method": "dcf_valuation", "currency": "USD", "period": "annual", "inputs": DCF_IN})
        self.assertIn("enterprise value", d.report); self.assertIn("not a market price", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 8)
        self.assertTrue(all(ok for ok in d.appendix["tests"]))
        self.assertIn("terminal value", d.report.lower())


class Registration(unittest.TestCase):
    def test_contracts_and_presets(self):
        from bp import server
        self.assertEqual((LIBRARY["wacc"].tier, LIBRARY["wacc"].claim_ceiling), ("T1", "descriptive"))
        self.assertEqual((LIBRARY["dcf_valuation"].tier, LIBRARY["dcf_valuation"].claim_ceiling), ("T2", "descriptive"))
        self.assertIn("wacc", server.PRESETS); self.assertIn("dcf", server.PRESETS)
        self.assertEqual(server.PRESETS["wacc"]["method"], "wacc"); self.assertEqual(server.PRESETS["dcf"]["method"], "dcf_valuation")

    def test_deterministic(self):
        for mid, inp in (("wacc", WACC_IN), ("dcf_valuation", DCF_IN)):
            m = LIBRARY[mid]
            self.assertEqual({k: str(v) for k, v in m.impl(inp).items()}, {k: str(v) for k, v in m.impl(inp).items()})


if __name__ == "__main__":
    unittest.main()
