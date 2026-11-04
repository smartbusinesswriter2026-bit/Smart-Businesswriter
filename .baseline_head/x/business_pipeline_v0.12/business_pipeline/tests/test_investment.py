import sys, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY, DataError
from bp.orchestrator import Pipeline

YES = lambda s: True
IRR_IN = {"cashflows": ["-1000", "400", "400", "400", "400"]}
DPB_IN = {"cashflows": ["-1000", "400", "400", "400", "400"], "rate": "0.10"}


def close(a, b, tol="1e-9"):
    a, b = D(str(a)), D(str(b))
    return abs(a - b) <= D(tol) * max(D(1), abs(b))


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class Irr(unittest.TestCase):
    def m(self): return LIBRARY["irr"]

    def test_finds_the_rate_where_npv_is_zero(self):
        out = self.m().impl(IRR_IN)
        self.assertTrue(close(out["irr"], "0.21862269609834228"))
        cfs = [D(c) for c in IRR_IN["cashflows"]]
        npv = sum((cf / (1 + out["irr"]) ** t for t, cf in enumerate(cfs)), D(0))
        self.assertTrue(abs(npv) <= D("1e-9"))
        self.assertEqual((out["n_roots"], out["n_periods"]), (D(1), D(5)))

    def test_frozen_checks_pass_and_are_declared(self):
        checks = self.m().tests(IRR_IN, self.m().impl)
        self.assertEqual(tuple(n for n, _ in checks), self.m().test_names)
        self.assertTrue(all(ok for _, ok in checks))

    def test_unconventional_or_signless_cash_flows_are_refused(self):
        for inputs in ({"cashflows": ["100", "200", "300"]}, {"cashflows": ["-100", "400", "-300"]},
                       {"cashflows": ["-1000"]}, {"cashflows": ["-1000", "x"]}):
            with self.assertRaises((DataError, ValueError), msg=inputs):
                self.m().impl(inputs)

    def test_pipeline_delivers_a_percentage(self):
        d = delivered({"objective": "What is the project IRR?", "method": "irr", "period": "annual", "inputs": IRR_IN})
        self.assertIn("%", d.report)
        self.assertTrue(all(ok for ok in d.appendix["tests"]))
        self.assertEqual(len(d.appendix["artifacts"]), 4)


class DiscountedPayback(unittest.TestCase):
    def m(self): return LIBRARY["discounted_payback"]

    def test_payback_interpolates_inside_the_recovering_period(self):
        out = self.m().impl(DPB_IN)
        self.assertTrue(close(out["discounted_payback"], "3.01925"))
        self.assertEqual(out["recovered_in_period"], D(4))
        self.assertTrue(close(out["net_present_value"], "267.946178539717"))

    def test_zero_rate_equals_the_ordinary_payback(self):
        out = self.m().impl({**DPB_IN, "rate": "0"})
        self.assertEqual(out["discounted_payback"], D("2.5"))

    def test_frozen_checks_pass_and_are_declared(self):
        checks = self.m().tests(DPB_IN, self.m().impl)
        self.assertEqual(tuple(n for n, _ in checks), self.m().test_names)
        self.assertTrue(all(ok for _, ok in checks))

    def test_outlays_never_recovered_and_positive_starts_are_refused(self):
        for inputs in ({"cashflows": ["-1000", "100", "100"]}, {"cashflows": ["1000", "100"]},
                       {"cashflows": ["-1000", "100", "100"], "rate": "1.5"}):
            with self.assertRaises((DataError, ValueError), msg=inputs):
                self.m().impl(inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "How long to recover?", "method": "discounted_payback", "currency": "USD",
                       "period": "annual", "inputs": DPB_IN})
        self.assertTrue(all(ok for ok in d.appendix["tests"]))
        self.assertIn("USD", d.report)
        self.assertIn("3.02", d.report)


class Registration(unittest.TestCase):
    def test_contracts_and_presets(self):
        from bp import server
        self.assertEqual((LIBRARY["irr"].tier, LIBRARY["irr"].unit), ("T1", "rate"))
        self.assertEqual((LIBRARY["discounted_payback"].tier, LIBRARY["discounted_payback"].unit), ("T1", "periods"))
        self.assertEqual(LIBRARY["irr"].claim_ceiling, "descriptive")
        self.assertEqual(server.PRESETS["irr"]["method"], "irr"); self.assertEqual(server.PRESETS["dpayback"]["method"], "discounted_payback")

    def test_deterministic(self):
        for mid, inp in (("irr", IRR_IN), ("discounted_payback", DPB_IN)):
            m = LIBRARY[mid]
            self.assertEqual({k: str(v) for k, v in m.impl(inp).items()}, {k: str(v) for k, v in m.impl(inp).items()})


if __name__ == "__main__":
    unittest.main()
