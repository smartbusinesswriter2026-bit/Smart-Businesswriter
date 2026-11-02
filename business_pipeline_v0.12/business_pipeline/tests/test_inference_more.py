import sys, json, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline

YES = lambda s: True
GOLD = json.load(open("tests/fixtures/inference_golden.json", encoding="utf-8"))
PAIRED = {"pairs": {"before": ["10", "12", "11", "9", "13"], "after": ["12", "13", "12", "10", "14"]}}
ONE = {"values": ["72", "85", "90", "68", "99", "77", "81"], "missing_codes": ["99"], "mu0": "75"}


def close(a, b, tol=1e-9):
    a, b = D(str(a)), D(str(b))
    return abs(a - b) <= D(str(tol)) * max(D(1), abs(b))


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class PairedT(unittest.TestCase):
    def m(self): return LIBRARY["paired_t"]

    def test_golden_values_match_scipy(self):
        for c in GOLD["paired"]:
            out = self.m().impl(c["inputs"])
            for k, exp in c["expected"].items():
                self.assertTrue(close(out[k], exp), f"{c['name']}.{k}: {out[k]} vs {exp}")

    def test_frozen_checks_pass_and_are_declared(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(PAIRED, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(PAIRED, self.m().impl)))

    def test_constant_differences_are_refused(self):
        d = Pipeline().run({"objective": "x", "method": "paired_t", "inputs": {"pairs": {"a": ["1", "2", "3"], "b": ["2", "3", "4"]}}}, YES)
        self.assertEqual(d.status, "blocked")
        self.assertIn("identical", d.blocked_reason)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Did the scores change?", "method": "paired_t", "unit": "points", "inputs": PAIRED})
        self.assertIn("paired comparison", d.report); self.assertIn("mean within-pair difference", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 15)
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class OneSampleT(unittest.TestCase):
    def m(self): return LIBRARY["one_sample_t"]

    def test_golden_values_match_scipy(self):
        for c in GOLD["one_sample"]:
            out = self.m().impl(c["inputs"])
            for k, exp in c["expected"].items():
                self.assertTrue(close(out[k], exp), f"{c['name']}.{k}: {out[k]} vs {exp}")

    def test_frozen_checks_pass_and_are_declared(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(ONE, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(ONE, self.m().impl)))

    def test_zero_variance_and_missing_reference_are_refused(self):
        self.assertEqual(Pipeline().run({"objective": "x", "method": "one_sample_t", "inputs": {"values": ["1", "1", "1"], "mu0": "2"}}, YES).status, "blocked")
        self.assertEqual(Pipeline().run({"objective": "x", "method": "one_sample_t", "inputs": {"values": ["1", "2", "3"]}}, YES).status, "blocked")

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Is the mean different from the target?", "method": "one_sample_t", "unit": "points", "inputs": ONE})
        self.assertIn("reference value", d.report); self.assertIn("confidence interval", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 14)
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class Registration(unittest.TestCase):
    def test_contracts_and_presets(self):
        from bp import server
        for mid, metric, preset in (("paired_t", "mean_diff", "paired"), ("one_sample_t", "mean", "onesample")):
            m = LIBRARY[mid]
            self.assertEqual((m.tier, m.claim_ceiling, m.metric, m.decision), ("T1", "associational", metric, None))
            self.assertIn(preset, server.PRESETS); self.assertEqual(server.PRESETS[preset]["method"], mid)

    def test_deterministic(self):
        for mid, inp in (("paired_t", PAIRED), ("one_sample_t", ONE)):
            m = LIBRARY[mid]
            a = {k: str(v) for k, v in m.impl(inp).items()}
            b = {k: str(v) for k, v in m.impl(inp).items()}
            self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
