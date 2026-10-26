import sys, json, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline

YES = lambda s: True
TWO = json.load(open("tests/fixtures/two_way_golden.json", encoding="utf-8"))
PH = json.load(open("tests/fixtures/posthoc_golden.json", encoding="utf-8"))
HAND = [{"response": r, "factor_a": a, "factor_b": b} for a, b, vs in
        [("low", "x", ["1", "3"]), ("low", "y", ["5", "7"]), ("high", "x", ["3", "5"]), ("high", "y", ["7", "9"])] for r in vs]


def close(a, b, tol="1e-9"):
    a, b = D(str(a)), D(str(b))
    return abs(a - b) <= D(tol) * max(D(1), abs(b))


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class TwoWay(unittest.TestCase):
    def m(self): return LIBRARY["two_way_anova"]

    def test_goldens_match_numpy_and_scipy(self):
        for c in TWO["cases"]:
            out = self.m().impl({"data": c["data"]})
            for k, exp in c["expected"].items():
                self.assertTrue(close(out[k], exp), f"{c['name']}.{k}: {out[k]} vs {exp}")

    def test_hand_computable_design_is_exact(self):
        out = self.m().impl({"data": HAND})
        self.assertEqual((out["ss_a"], out["ss_b"], out["ss_ab"], out["ss_error"], out["ss_total"]), (D(8), D(32), D(0), D(8), D(48)))
        self.assertEqual((out["f_a"], out["f_b"], out["f_ab"]), (D(4), D(16), D(0)))

    def test_frozen_checks_pass_and_are_declared(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests({"data": HAND}, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests({"data": HAND}, self.m().impl)))

    def test_unbalanced_and_broken_designs_are_refused(self):
        unbalanced = HAND + [{"response": "99", "factor_a": "low", "factor_b": "x"}]
        one_level = [r for r in HAND if r["factor_a"] == "low"]
        for data in (unbalanced, one_level, []):
            self.assertEqual(Pipeline().run({"objective": "x", "method": "two_way_anova", "inputs": {"data": data}}, YES).status, "blocked")

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Do the factors matter?", "method": "two_way_anova", "unit": "points", "period": "cross_section", "inputs": {"data": HAND}})
        self.assertIn("balanced two-way ANOVA", d.report); self.assertIn("interaction F", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 26)
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class Posthoc(unittest.TestCase):
    def m(self): return LIBRARY["posthoc_pairwise"]

    def inp(self): return {"groups": PH["groups"], "adjust": PH["adjust"], "alpha": str(PH["alpha"])}

    def test_goldens_match_scipy_welch_and_holm(self):
        out = self.m().impl(self.inp())
        for exp in PH["expected"]["pairs"]:
            a, b = exp["pair"]
            self.assertTrue(close(out[f"diff_{a}_{b}"], exp["diff"]), f"diff {a}-{b}")
            self.assertTrue(close(out[f"p_raw_{a}_{b}"], exp["p_raw"]), f"raw {a}-{b}")
            self.assertTrue(close(out[f"p_adj_{a}_{b}"], exp["p_adj"]), f"adj {a}-{b}")
        self.assertEqual(int(out["n_rejected"]), PH["expected"]["n_rejected"])

    def test_frozen_checks_pass_and_are_declared(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(self.inp(), self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(self.inp(), self.m().impl)))

    def test_adjustment_methods_behave(self):
        m = self.m()
        raw = {k: v for k, v in m.impl({**self.inp(), "adjust": "none"}).items() if k.startswith("p_")}
        bon = m.impl({**self.inp(), "adjust": "bonferroni"})
        holm = m.impl(self.inp())
        for k in [x for x in raw if x.startswith("p_raw")]:
            adj_key = k.replace("p_raw", "p_adj")
            self.assertEqual(raw[k], raw[adj_key] if adj_key in raw else raw[k])   # 'none' keeps raw = adjusted
            self.assertGreaterEqual(D(str(holm[adj_key])), D(str(raw[k])))
            self.assertGreaterEqual(D(str(bon[adj_key])), D(str(raw[k])))

    def test_invalid_groups_are_refused(self):
        for inp in ({"groups": {"a": ["1", "2"]}}, {"groups": {"a": ["1", "2"], "b": ["3", "3"]}},
                    {"groups": {"a": ["1", "2"], "b": ["1", "2"]}, "adjust": "tukey"},
                    {"groups": {"a": ["1", "2"], "b": ["3", "4"]}, "alpha": "1.5"}):
            self.assertEqual(Pipeline().run({"objective": "x", "method": "posthoc_pairwise", "inputs": inp}, YES).status, "blocked", inp)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Which groups differ?", "method": "posthoc_pairwise", "unit": "points", "period": "cross_section", "inputs": self.inp()})
        self.assertIn("pairwise comparisons", d.report); self.assertIn("adjusted p-values", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 19)
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class Registration(unittest.TestCase):
    def test_contracts_and_presets(self):
        from bp import server
        self.assertEqual((LIBRARY["two_way_anova"].tier, LIBRARY["two_way_anova"].claim_ceiling), ("T1", "associational"))
        self.assertEqual((LIBRARY["posthoc_pairwise"].tier, LIBRARY["posthoc_pairwise"].claim_ceiling), ("T1", "associational"))
        self.assertIn("factorial", server.PRESETS); self.assertIn("posthoc", server.PRESETS)

    def test_deterministic(self):
        for mid, inp in (("two_way_anova", {"data": HAND}), ("posthoc_pairwise", {"groups": PH["groups"], "adjust": "holm"})):
            m = LIBRARY[mid]
            self.assertEqual({k: str(v) for k, v in m.impl(inp).items() if k != "_appendix"},
                             {k: str(v) for k, v in m.impl(inp).items() if k != "_appendix"})


if __name__ == "__main__":
    unittest.main()
