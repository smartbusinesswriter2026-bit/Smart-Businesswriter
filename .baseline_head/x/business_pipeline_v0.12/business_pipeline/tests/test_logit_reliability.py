import sys, json, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline

YES = lambda s: True
GOLD = json.load(open("tests/fixtures/logistic_golden.json", encoding="utf-8"))
LOGIT = {"y": GOLD["data"]["y"], "predictors": {"size": GOLD["data"]["size"], "group": GOLD["data"]["group"]}}
ITEMS = {"items": {"one": ["4", "5", "3", "4", "5", "2", "4", "3"], "two": ["4", "4", "3", "5", "4", "3", "4", "2"],
                   "three": ["3", "4", "2", "4", "5", "3", "4", "3"], "four": ["4", "5", "3", "4", "4", "2", "3", "3"]}}


def close(a, b, tol="1e-6"):
    a, b = D(str(a)), D(str(b))
    return abs(a - b) <= D(tol) * max(D(1), abs(b))


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class Logistic(unittest.TestCase):
    def m(self): return LIBRARY["logistic_regression"]

    def test_goldens_match_statsmodels(self):
        out = self.m().impl(LOGIT)
        for k, exp in GOLD["expected"].items():
            self.assertTrue(close(out[k], exp), f"{k}: {out[k]} vs {exp}")

    def test_frozen_checks_pass_and_are_declared(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(LOGIT, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(LOGIT, self.m().impl)))

    def test_invalid_outcomes_and_separation_are_refused(self):
        one_class = {"y": ["1"] * 10, "predictors": {"x": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]}}
        bad_code = {"y": ["0", "1", "2", "0", "1", "0", "1", "0", "1", "0"], "predictors": {"x": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]}}
        separated = {"y": ["0", "0", "0", "0", "1", "1", "1", "1", "1", "1"], "predictors": {"x": ["-3", "-2", "-1", "0", "1", "2", "3", "4", "5", "6"]}}
        for inputs in (one_class, bad_code, separated):
            self.assertEqual(Pipeline().run({"objective": "x", "method": "logistic_regression", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "What predicts the outcome?", "method": "logistic_regression", "period": "cross_section", "inputs": LOGIT})
        self.assertIn("logistic model", d.report); self.assertIn("odds ratio", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 18); self.assertTrue(all(ok for ok in d.appendix["tests"]))


class Alpha(unittest.TestCase):
    def m(self): return LIBRARY["reliability_alpha"]

    def test_alpha_against_the_classic_formula(self):
        out = self.m().impl(ITEMS)
        cols = list(ITEMS["items"].values()); k = len(cols); rows = list(zip(*[[float(v) for v in c] for c in cols]))
        def var(xs):
            m = sum(xs) / len(xs); return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
        item_var = [var([r[j] for r in rows]) for j in range(k)]; tv = var([sum(r) for r in rows])
        self.assertTrue(close(out["alpha"], (k / (k - 1)) * (1 - sum(item_var) / tv), "1e-9"))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(ITEMS, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(ITEMS, self.m().impl)))
        for inputs in ({"items": {"one": ["1", "2", "3"]}},
                       {"items": {"one": ["1", "2"], "two": ["1", "2", "3"]}},
                       {"items": {"one": ["2", "2", "2"], "two": ["2", "2", "2"]}}):
            self.assertEqual(Pipeline().run({"objective": "x", "method": "reliability_alpha", "inputs": inputs}, YES).status, "blocked", inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Item consistency", "method": "reliability_alpha", "unit": "points", "period": "cross_section", "inputs": ITEMS})
        self.assertIn("internal consistency", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 6); self.assertTrue(all(ok for ok in d.appendix["tests"]))


class Registration(unittest.TestCase):
    def test_contracts_and_presets(self):
        from bp import server
        self.assertEqual((LIBRARY["logistic_regression"].tier, LIBRARY["logistic_regression"].claim_ceiling), ("T1", "associational"))
        self.assertEqual((LIBRARY["reliability_alpha"].tier, LIBRARY["reliability_alpha"].claim_ceiling), ("T1", "descriptive"))
        self.assertIn("logit", server.PRESETS); self.assertIn("alpha", server.PRESETS)

    def test_deterministic(self):
        for mid, inp in (("logistic_regression", LOGIT), ("reliability_alpha", ITEMS)):
            m = LIBRARY[mid]
            self.assertEqual({k: str(v) for k, v in m.impl(inp).items() if k != "_appendix"},
                             {k: str(v) for k, v in m.impl(inp).items() if k != "_appendix"})


if __name__ == "__main__":
    unittest.main()
