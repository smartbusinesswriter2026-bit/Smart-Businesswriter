import sys, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY, validate_inputs
from bp.orchestrator import Pipeline

YES = lambda s: True
BASE = {"values": ["1", "2", "3", "4"], "weights": ["1", "1", "1", "3"], "weight_kind": "reliability"}


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class WeightedSummary(unittest.TestCase):
    def m(self): return LIBRARY["weighted_summary"]

    def test_weighted_mean_and_reliability_sd_are_exact(self):
        out = self.m().impl(BASE)
        self.assertEqual(out["weighted_mean"], D(3))                 # (1+2+3+12)/6
        self.assertLess(abs(float(out["weighted_sd"]) - 2 ** 0.5), 1e-12)   # var = 8/(6 - 12/6) = 2
        self.assertEqual(out["sum_weights"], D("6.0"))
        self.assertLess(abs(float(out["n_eff"]) - 3.0), 1e-12)       # 36/12
        self.assertLess(abs(float(out["design_effect"]) - 4 / 3), 1e-12)

    def test_frequency_weights_use_the_count_convention(self):
        out = self.m().impl({**BASE, "weight_kind": "frequency"})
        self.assertEqual(out["weighted_mean"], D(3))
        self.assertLess(abs(float(out["weighted_sd"]) - 1.6 ** 0.5), 1e-12)   # var = 8/(6-1)

    def test_equal_weights_reproduce_the_ordinary_sample_summary(self):
        out = self.m().impl({"values": ["1", "2", "3", "4"], "weights": ["1", "1", "1", "1"]})
        self.assertEqual(out["weighted_mean"], D("2.5"))
        self.assertLess(abs(float(out["weighted_sd"]) - (5 / 3) ** 0.5), 1e-12)
        self.assertLess(abs(float(out["design_effect"]) - 1.0), 1e-12)

    def test_missing_values_drop_their_weights(self):
        out = self.m().impl({"values": ["1", "", "3", "4"], "weights": ["1", "99", "1", "3"], "missing_codes": []})
        self.assertEqual((out["n"], out["n_missing"]), (D(3), D(1)))
        self.assertEqual(out["weighted_mean"], D("3.2"))             # (1*1 + 3*1 + 4*3) / (1+1+3)

    def test_all_frozen_checks_pass_and_are_declared(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(BASE, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(BASE, self.m().impl)))

    def test_invalid_inputs_are_refused_at_intake(self):
        bad = ({"values": ["1", "2"], "weights": ["1"]},
               {"values": ["1", "2"], "weights": ["1", "0"]},
               {"values": ["1", "2"], "weights": ["1", "-2"]},
               {"values": ["1", "2"], "weights": ["1", "1"], "weight_kind": "analytic"},
               {"values": ["", ""], "weights": ["1", "1"]})
        for inputs in bad:
            d = Pipeline().run({"objective": "x", "method": "weighted_summary", "inputs": inputs}, YES)
            self.assertEqual(d.status, "blocked", inputs)

    def test_full_pipeline_delivers_with_the_design_disclaimer(self):
        d = delivered({"objective": "Summarize the survey", "method": "weighted_summary", "unit": "points", "inputs": BASE})
        self.assertIn("weighted mean", d.report); self.assertIn("effective sample size", d.report)
        self.assertIn("no standard error", d.appendix["honesty"]["weights_and_clusters"])
        self.assertEqual(len(d.appendix["artifacts"]), 7)
        self.assertTrue(all(ok for ok in d.appendix["tests"]))

    def test_contract_and_preset(self):
        from bp import server
        m = self.m()
        self.assertEqual((m.tier, m.claim_ceiling, m.metric, m.unit, m.decision), ("T1", "descriptive", "weighted_mean", "from_request", None))
        self.assertEqual(validate_inputs(m, BASE), [])
        self.assertIn("weighted", server.PRESETS); self.assertEqual(server.PRESETS["weighted"]["method"], "weighted_summary")

    def test_deterministic(self):
        a = {k: str(v) for k, v in self.m().impl(BASE).items() if k != "_appendix"}
        b = {k: str(v) for k, v in self.m().impl(BASE).items() if k != "_appendix"}
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
