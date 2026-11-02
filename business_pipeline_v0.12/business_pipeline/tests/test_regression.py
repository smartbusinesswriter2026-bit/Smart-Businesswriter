import sys, json, os, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import methods
from bp.methods import LIBRARY, ols_impl, ols_robust_impl, validate_inputs
from bp.orchestrator import Pipeline
from bp.session import SessionManager

yes = lambda s: True
GOLD = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "regression_golden.json")))
Y10 = ["52", "55", "61", "58", "70", "72", "69", "80", "66", "74"]
P2 = {"study_hours": ["1", "2", "3", "4", "5", "6", "7", "8", "4", "6"], "sleep_hours": ["6", "7", "5", "8", "6", "7", "8", "6", "7", "7"]}
HET = ({"x": [str(i) for i in range(1, 21)]}, [str(round(2 * i + (i ** 1.6) * ((-1) ** i) * 0.9, 2)) for i in range(1, 21)])
COLLIN = ({"a": [str(i) for i in range(1, 13)], "b": [str(i + (0.01 if i % 2 else -0.01)) for i in range(1, 13)]}, ["3", "5", "4", "7", "8", "6", "9", "11", "10", "12", "14", "13"])
INFL = ({"x": [str(i) for i in range(1, 10)] + ["40"]}, ["3", "1", "4", "2", "5", "3", "4", "2", "3", "30"])
SKEW = ({"x": [str(i % 5) for i in range(20)]}, ["1"] * 19 + ["40"])
def req(y=Y10, P=P2, method="ols", codes=None, **kw):
    r = {"objective": "How are the predictors associated with the outcome?", "method": method, "inputs": {"y": y, "predictors": P, "missing_codes": codes or []}}; r.update(kw); return r

class Golden(unittest.TestCase):
    def test_against_offline_numpy_scipy_references(self):
        for c in GOLD:
            out = (ols_robust_impl if c["method"] == "ols_robust" else ols_impl)({"y": c["y"], "predictors": c["predictors"], "missing_codes": c["missing_codes"]})
            self.assertEqual(set(out) - {"f_squared", "k", "df_residual", "confidence_level", "alpha"} - {k for k in out if k.startswith("std_beta_")}, set(c["expected"]), c["name"])
            for k, v in c["expected"].items(): self.assertLessEqual(abs(float(out[k]) - float(v)), 1e-9 * max(1, abs(float(v))), f"{c['name']}.{k}")
    def test_hand_checked(self):   # slope sxy/sxx = 6/10, intercept 4 - 0.6*3, R2 = 6^2/(10*6)
        o = ols_impl({"y": ["2", "4", "5", "4", "5"], "predictors": {"x": ["1", "2", "3", "4", "5"]}})
        for k, v in (("coef_x", "0.6"), ("coef_intercept", "2.2"), ("r_squared", "0.6")): self.assertLess(abs(o[k] - D(v)), D("1e-20"), k)

class Inputs(unittest.TestCase):
    def blocked(self, r, text):
        d = Pipeline().run(r, yes); self.assertEqual(d.status, "blocked"); self.assertIn(text, d.blocked_reason); return d
    def test_schema_names(self):
        m = LIBRARY["ols"]
        for bad in ("x1", "<script>", "intercept", "has space"): self.assertTrue(validate_inputs(m, {"y": Y10, "predictors": {bad: Y10}}), bad)
        self.assertTrue(any("at most 5" in e for e in validate_inputs(m, {"y": Y10, "predictors": {c: Y10 for c in "abcdef"}})))
    def test_unpaired(self): self.blocked(req(P={"x": ["1"] * 9}), "must be paired")
    def test_too_few_rows(self): self.blocked(req(y=Y10[:5] + [None, None], P={k: v[:7] for k, v in P2.items()}), "too few complete rows")
    def test_constant_predictor(self): self.blocked(req(P={"x": ["3"] * 10}), "constant")
    def test_perfect_collinearity(self): self.blocked(req(P={"a": P2["study_hours"], "b": [str(int(v) * 2) for v in P2["study_hours"]]}), "perfectly collinear")
    def test_perfect_fit(self): self.blocked(req(y=[str(2 * int(v) + 1) for v in P2["study_hours"]], P={"x": P2["study_hours"]}), "perfect fit")

class EndToEnd(unittest.TestCase):
    def ok(self, r):
        p = Pipeline(); d = p.run(r, yes); self.assertEqual(d.status, "delivered", d.blocked_reason); return p, d
    def test_clean_model_report(self):
        p, d = self.ok(req()); self.assertIsNone(d.appendix["fallback_used"]); self.assertEqual(d.appendix["method"]["id"], "ols")
        for frag in ("10 complete observations", "2 predictor variable(s)", "study_hours is associated with a difference of", "sleep_hours is associated with", "holding the other predictors constant",
                     "The overall F test has", "standardized coefficient", "practical importance are separate", "makes no causal claim"): self.assertIn(frag, d.report)
        self.assertNotIn("{{", d.report); self.assertNotRegex(d.report.lower(), r"\bcauses?\b|\bleads? to\b|\bdrives?\b|\beffect of\b|\bimpact of\b")
        self.assertIn("sample is small", d.report)
        a = {x.id: x for x in p.store.all()}; self.assertEqual(a["coef_study_hours"].value.unit, "coefficient"); self.assertEqual(a["p_study_hours"].value.unit, "probability"); self.assertEqual(a["n"].value.precision, 0)
        self.assertEqual(len([e for e in p.events if e["stage"] == "verification" and e.get("status") == "assumptions"]), 1)
    def test_heteroskedastic_switches_to_robust_as_logged_amendment(self):
        P, y = HET; p, d = self.ok(req(y, P))
        self.assertEqual(d.appendix["fallback_used"]["to"], "ols_robust"); self.assertEqual(d.appendix["method"]["id"], "ols_robust")
        self.assertIn("switched from ols to the pre-declared fallback, ols_robust", d.report); self.assertNotIn("The overall F test has", d.report); self.assertIn("HC3 robust", d.report)
        self.assertEqual(p.spec.fallbacks, {"heteroskedasticity_screen": "ols_robust"}); self.assertTrue(set(LIBRARY["ols_robust"].test_names) <= set(p.spec.checks))
        a = [e for e in p.events if e["stage"] == "amendment" and e.get("kind") == "fallback"]; self.assertEqual(len(a), 1); self.assertEqual(a[0]["check"], "heteroskedasticity_screen")
    def test_blocking_screens_name_the_check_and_the_numbers(self):
        for (P, y), text in ((COLLIN, "multicollinearity_screen (largest variance inflation factor"), (INFL, "influence_screen (largest Cook's distance"), (SKEW, "residual_normality_screen (residual skewness")):
            d = Pipeline().run(req(y, P), yes); self.assertEqual(d.status, "blocked", text); self.assertIn("no pre-declared fallback", d.blocked_reason); self.assertIn(text, d.blocked_reason)
    def test_declared_thresholds_change_screen_outcomes(self):
        P, y = COLLIN; _, d = self.ok(req(y, P, thresholds={"vif_limit": "1000000"})); self.assertEqual(d.status, "delivered")
        P, y = HET; _, d = self.ok(req(y, P, thresholds={"bp_alpha": "0"})); self.assertIsNone(d.appendix["fallback_used"])
    def test_missing_rows_counted(self):
        P = {"study_hours": P2["study_hours"] + ["3", "99"], "sleep_hours": P2["sleep_hours"] + ["7", "6"]}
        _, d = self.ok(req(Y10 + ["99", "60"], P, codes=["99"])); _, clean = self.ok(req())
        self.assertIn("2 excluded as missing", d.report); self.assertIn("10 complete observations", d.report)
        self.assertEqual(d.report.split("Each one-unit")[1][:60], clean.report.split("Each one-unit")[1][:60])   # same estimates as the clean data
    def test_effect_word_from_declared_thresholds(self):
        _, a = self.ok(req()); _, b = self.ok(req(thresholds={"f2_large": "100", "f2_medium": "50"})); self.assertIn("large effect", a.report); self.assertIn("small effect", b.report)
    def test_synthetic_label(self): _, d = self.ok(req(provenance={"y": "synthetic"})); self.assertIn("synthetic data", d.report)
    def test_robust_selectable_directly(self): _, d = self.ok(req(method="ols_robust")); self.assertNotIn("The overall F test has", d.report)
    def test_plan_before_running(self):
        pl = SessionManager().create(req()).plan
        self.assertEqual(pl["assumption_checks"], ["residual_normality_screen", "heteroskedasticity_screen", "multicollinearity_screen", "influence_screen"])
        self.assertEqual(pl["fallbacks"], {"heteroskedasticity_screen": "ols_robust"}); self.assertEqual(pl["thresholds"]["vif_limit"], "10"); self.assertEqual(pl["task_family"], "Regression analysis")
    def test_stage_states_clean_after_fallback(self):
        P, y = HET; s = SessionManager().create(req(y, P)); s.confirm(True); d = s.to_dict()
        self.assertEqual(d["stage_states"]["verification"], "passed"); self.assertTrue(all(v in ("passed", "not_run") for v in d["stage_states"].values()))
    def test_simple_regression_consistent_with_correlation_report_numbers(self):
        x = [str(i) for i in range(1, 9)]; y = ["2", "4", "5", "4", "5", "7", "6", "8"]
        o = ols_impl({"y": y, "predictors": {"x": x}}); c = methods.pearson_impl({"x": x, "y": y})
        self.assertLess(abs(float(o["std_beta_x"]) - float(c["r"])), 1e-12); self.assertLess(abs(float(o["p_x"]) - float(c["p_value"])), 1e-9)

class WrongImplementations(unittest.TestCase):
    def run_bad(self, method, bad, y=Y10, P=P2, codes=None):
        orig = LIBRARY[method]; LIBRARY[method] = orig.__class__(**{**orig.__dict__, "impl": bad})
        try: return Pipeline().run(req(y, P, method=method, codes=codes), yes)
        finally: LIBRARY[method] = orig
    def test_bugs_are_blocked(self):
        g = ols_impl
        bugs = {"se_too_small": lambda i: {**g(i), "se_study_hours": g(i)["se_study_hours"] * D("0.9")},
                "sign_flip_second_predictor": lambda i: {**g(i), "coef_sleep_hours": -g(i)["coef_sleep_hours"]},
                "p_uses_normal": lambda i: {**g(i), "p_study_hours": g(i)["p_study_hours"] / 2},
                "intercept_off": lambda i: {**g(i), "coef_intercept": g(i)["coef_intercept"] + 1},
                "r2_inflated": lambda i: {**g(i), "r_squared": min(D("0.999"), g(i)["r_squared"] + D("0.01"))},
                "reads_codes_as_values": lambda i: g({**i, "missing_codes": [], "y": [v if v not in i["missing_codes"] else "99" for v in i["y"]]}),
                "magnitude_dependent": lambda i: {**g(i), "coef_study_hours": g(i)["coef_study_hours"] * (D("0.95") if max(D(str(v)) for v in i["y"] if v) > 300 else 1)},
                "order_dependent": lambda i: g({**i, "y": i["y"][:-1] + i["y"][-1:], "predictors": {k: v for k, v in i["predictors"].items()}}) if i["y"][0] <= i["y"][-1] else {**g(i), "r_squared": g(i)["r_squared"] * D("0.99")}}
        y = [v if v != "66" else "99" for v in Y10]
        for name, bad in bugs.items():
            d = self.run_bad("ols", bad, y=y, codes=["99"] if name == "reads_codes_as_values" else None); self.assertEqual(d.status, "blocked", name)
    def test_robust_returning_classical_se_is_blocked(self):
        self.assertEqual(self.run_bad("ols_robust", ols_impl).status, "blocked")
    def test_discovery(self):
        d = methods.describe("ols"); self.assertEqual(d["fallbacks"], {"heteroskedasticity_screen": "ols_robust"}); self.assertIn("vif_limit", d["default_thresholds"])
if __name__ == "__main__": unittest.main()
