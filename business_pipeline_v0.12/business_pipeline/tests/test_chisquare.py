import sys, json, os, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import methods
from bp.methods import LIBRARY, chi_square_impl, validate_inputs
from bp.orchestrator import Pipeline
from bp.session import SessionManager

yes = lambda s: True
GOLD = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "chisquare_golden.json")))
T = [[45, 30, 25], [20, 40, 40], [10, 20, 70]]
def req(table=T, **kw):
    r = {"objective": "Are the categories associated?", "method": "chi_square", "inputs": {"table": table}}; r.update(kw); return r

class Golden(unittest.TestCase):
    def test_against_offline_scipy_references(self):
        for c in GOLD:
            out = chi_square_impl({"table": c["table"]})
            for k, v in c["expected"].items(): self.assertLessEqual(abs(float(out[k]) - float(v)), 1e-9 * max(1, abs(float(v))), f"{c['name']}.{k}")

class Inputs(unittest.TestCase):
    def blocked(self, r, text):
        d = Pipeline().run(r, yes); self.assertEqual(d.status, "blocked"); self.assertIn(text, d.blocked_reason); return d
    def test_schema(self):
        m = LIBRARY["chi_square"]
        for bad in ({"table": [[1, 2]]}, {"table": [[1, 2], [3]]}, {"table": [[1, -2], [3, 4]]}, {"table": [[1, 1.5], [3, 4]]}, {"table": [[1, "x"], [3, 4]]}):
            self.assertTrue(validate_inputs(m, bad), bad)
        self.assertEqual(validate_inputs(m, {"table": [["1", "2"], ["3", "4"]]}), [])
    def test_empty_table_and_zero_column_block(self):
        self.blocked(req([[0, 0], [0, 0]]), "no observations")
        self.blocked(req([[0, 5], [0, 5]]), "a column sums to zero")
    def test_small_expected_counts_block_fail_closed(self):
        d = self.blocked(req([[5, 5], [5, 25]]), "minimum_expected_count")
        self.assertIn("2.5", d.blocked_reason); self.assertIn("no pre-declared fallback", d.blocked_reason)
    def test_large_expected_counts_delivered(self):
        self.assertEqual(Pipeline().run(req(), yes).status, "delivered")

class EndToEnd(unittest.TestCase):
    def ok(self, r):
        p = Pipeline(); d = p.run(r, yes); self.assertEqual(d.status, "delivered", d.blocked_reason); return p, d
    def test_chi2_report(self):
        p, d = self.ok(req())
        for frag in ("chi-square test of independence gives chi-squared = 56", "4 degree(s) of freedom", "below the reporting floor", "statistically significantly associated",
                     "Cramer's V is 0.306", "medium association", "smallest expected count is 25", "does not show that one causes the other"): self.assertIn(frag, d.report)
        self.assertNotIn("{{", d.report)
        a = {x.id: x for x in p.store.all()}; self.assertEqual(a["p_value"].value.unit, "probability"); self.assertEqual(a["cramers_v"].value.unit, "ratio"); self.assertEqual(a["df"].value.precision, 0); self.assertEqual(a["n_total"].value.unit, "count")
    def test_independent_table_wording(self):
        _, d = self.ok(req([[10, 20, 30], [20, 40, 60]])); self.assertIn("not statistically significantly associated", d.report); self.assertIn("Cramer's V is 0.000", d.report)
    def test_effect_word_from_declared_thresholds(self):
        _, d = self.ok(req(thresholds={"v_medium": "1", "v_large": "5"})); self.assertIn("small association", d.report)
    def test_synthetic_label(self):
        _, d = self.ok(req(provenance={"table": "synthetic"})); self.assertIn("synthetic data", d.report)
    def test_plan_and_states(self):
        s = SessionManager().create(req()); self.assertEqual(s.plan["fallbacks"], {}); self.assertEqual(s.plan["assumption_checks"], ["minimum_expected_count"])
        s.confirm(True); d = s.to_dict(); self.assertEqual(d["stage_states"]["verification"], "passed")

class WrongImplementations(unittest.TestCase):
    def run_bad(self, bad):
        orig = LIBRARY["chi_square"]; LIBRARY["chi_square"] = orig.__class__(**{**orig.__dict__, "impl": bad})
        try: return Pipeline().run(req(), yes)
        finally: LIBRARY["chi_square"] = orig
    def test_chi2_bugs_blocked(self):
        g = chi_square_impl
        bugs = {"one_sided_p": lambda i: {**g(i), "p_value": g(i)["p_value"] / 2},
                "wrong_df": lambda i: {**g(i), "df": g(i)["df"] + 1},
                "v_without_sqrt": lambda i: {**g(i), "cramers_v": g(i)["cramers_v"] ** 2},
                "chi2_sign": lambda i: {**g(i), "chi_squared": -g(i)["chi_squared"]}}
        for name, bad in bugs.items(): self.assertEqual(self.run_bad(bad).status, "blocked", name)
    def test_discovery(self):
        d = methods.describe("chi_square"); self.assertEqual(d["assumption_checks"], ["minimum_expected_count"]); self.assertEqual(d["fallbacks"], {}); self.assertIn("v_large", d["default_thresholds"])
if __name__ == "__main__": unittest.main()
