import sys, json, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY, validate_inputs
from bp.orchestrator import Pipeline

YES = lambda s: True
GOLDEN = json.load(open("tests/fixtures/power_golden.json", encoding="utf-8"))
TWO = {"design": "two_sample", "effect": "5", "n1": "30", "n2": "40", "sd1": "10", "sd2": "12", "alpha": "0.05", "tails": "two_sided", "target_power": "0.8"}


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class PowerGolden(unittest.TestCase):
    def test_power_and_mde_match_scipy_to_1e9(self):
        for c in GOLDEN["cases"]:
            out = LIBRARY["power_analysis"].impl(c["inputs"])
            for k, exp in c["expected"].items():
                self.assertLessEqual(abs(float(out[k]) - exp), 1e-9 * max(1.0, abs(exp)), f"{c['name']}.{k}")
            self.assertTrue(all(ok for _, ok, _ in out["_checks"]), c["name"])


class PowerProperties(unittest.TestCase):
    def int(self): return LIBRARY["power_analysis"]

    def test_zero_effect_gives_power_equal_to_alpha(self):
        out = self.int().impl({**TWO, "effect": "0"})
        self.assertAlmostEqual(float(out["power"]), 0.05, places=12)

    def test_one_sided_is_more_powerful_than_two_sided(self):
        two = self.int().impl({**TWO, "tails": "two_sided"})
        one = self.int().impl({**TWO, "tails": "one_sided"})
        self.assertGreater(float(one["power"]), float(two["power"]))

    def test_power_and_mde_move_with_sample_size(self):
        base = self.int().impl(TWO)
        bigger = self.int().impl({**TWO, "n1": "60", "n2": "80"})
        self.assertGreater(float(bigger["power"]), float(base["power"]))
        self.assertLess(float(bigger["mde"]), float(base["mde"]))

    def test_invalid_designs_are_refused_at_intake(self):
        bad = ({**TWO, "design": "three_sample"},
               {**TWO, "sd1": "-1"}, {**TWO, "alpha": "1.2"},
               {"design": "one_sample", "effect": "1", "n1": "30", "sd1": "10", "n2": "20"},
               {"design": "two_sample", "effect": "1", "n1": "30", "sd1": "10", "sd2": "12"})   # missing n2
        for inputs in bad:
            d = Pipeline().run({"objective": "x", "method": "power_analysis", "inputs": inputs}, YES)
            self.assertEqual(d.status, "blocked", inputs)

    def test_full_pipeline_delivers_a_licensed_report(self):
        d = delivered({"objective": "Size the study", "method": "power_analysis", "unit": "points", "inputs": TWO})
        self.assertIn("power", d.report); self.assertIn("normal approximation", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 9)   # power, mde, se, ncp, z_alpha, alpha, target_power, n1, n2
        self.assertTrue(all(ok for ok in d.appendix["tests"]))

    def test_contract_and_preset(self):
        from bp import server
        m = LIBRARY["power_analysis"]
        self.assertEqual((m.tier, m.claim_ceiling, m.metric, m.unit, m.decision), ("T1", "descriptive", "power", "probability", None))
        self.assertEqual(validate_inputs(m, TWO), [])
        self.assertIn("power", server.PRESETS); self.assertEqual(server.PRESETS["power"]["method"], "power_analysis")

    def test_deterministic(self):
        m = self.int()
        a = {k: str(v) for k, v in m.impl(TWO).items() if k != "_appendix"}
        b = {k: str(v) for k, v in m.impl(TWO).items() if k != "_appendix"}
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
