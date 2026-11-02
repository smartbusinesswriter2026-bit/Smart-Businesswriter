import sys, json, os, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import methods
from bp.methods import LIBRARY, pearson_impl, spearman_impl, validate_inputs
from bp.orchestrator import Pipeline
from bp.session import SessionManager

yes = lambda s: True
GOLD = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "correlation_golden.json")))
NORMALISH = (["1", "2", "3", "4", "5", "6", "7", "8"], ["52", "55", "61", "58", "70", "72", "69", "80"])
SKEWED = (["1"] * 11 + ["60"], ["2", "4", "3", "5", "6", "4", "7", "5", "6", "8", "7", "20"])
def req(x, y, method="pearson", codes=None, **kw):
    r = {"objective": "Is x associated with y?", "method": method, "inputs": {"x": x, "y": y, "missing_codes": codes or []}}; r.update(kw); return r

class Golden(unittest.TestCase):
    def test_against_offline_scipy_references(self):
        for c in GOLD:
            out = (pearson_impl if c["method"] == "pearson" else spearman_impl)({"x": c["x"], "y": c["y"], "missing_codes": c["missing_codes"]})
            for k, v in c["expected"].items():
                tol = c["p_tol"] if k == "p_value" else 1e-9
                self.assertLessEqual(abs(float(out[k]) - float(v)), tol, f"{c['name']}.{k}")
    def test_hand_checked_classic_case(self):   # r = 6 / sqrt(10*6)
        out = pearson_impl({"x": ["1", "2", "3", "4", "5"], "y": ["2", "4", "5", "4", "5"]})
        self.assertLess(abs(float(out["r"]) - 6 / 60 ** 0.5), 1e-12); self.assertLess(abs(float(out["r_squared"]) - 0.6), 1e-12)
        self.assertEqual(spearman_impl({"x": ["1", "2", "3", "4", "5"], "y": ["1", "4", "9", "16", "10"]})["rho"], D("0.9"))  # 1 - 6*2/(5*24)

class Inputs(unittest.TestCase):
    def blocked(self, r, text):
        d = Pipeline().run(r, yes); self.assertEqual(d.status, "blocked"); self.assertIn(text, d.blocked_reason); return d
    def test_unequal_lengths(self): self.blocked(req(["1", "2", "3", "4", "5"], ["1", "2", "3", "4"]), "must be paired")
    def test_too_few_pairs_after_exclusion(self): self.blocked(req(["1", "2", "3", "4", "5"], ["1", "3", "99", "99", "4"], codes=["99"]), "fewer than four complete pairs")
    def test_constant_variable(self): self.blocked(req(["1", "2", "3", "4"], ["5", "5", "5", "5"]), "constant")
    def test_perfect_correlation_blocked_with_reason(self): self.blocked(req(["1", "2", "3", "4"], ["2", "4", "6", "8"]), "perfect correlation")
    def test_schema_errors(self):
        m = LIBRARY["pearson"]
        self.assertTrue(any("missing required input 'y'" in e for e in validate_inputs(m, {"x": ["1"] * 4})))
        self.assertTrue(any("[2] = 'q'" in e for e in validate_inputs(m, {"x": ["1", "2", "q", "4"], "y": ["1", "2", "3", "4"]})))
    def test_bad_confidence_level(self): self.blocked(req(*NORMALISH, **{}) | {"inputs": {"x": NORMALISH[0], "y": NORMALISH[1], "confidence_level": "1.5"}}, "confidence_level")

class EndToEnd(unittest.TestCase):
    def ok(self, r):
        p = Pipeline(); d = p.run(r, yes); self.assertEqual(d.status, "delivered", d.blocked_reason); return p, d
    def test_normalish_stays_pearson_and_reports_everything(self):
        p, d = self.ok(req(*NORMALISH))
        self.assertIsNone(d.appendix["fallback_used"]); self.assertEqual(d.appendix["method"]["id"], "pearson")
        for frag in ("Pearson correlation is 0.943", "large positive association", "from 0.709 to 0.990", "level 95.00%", "p-value is 0.0005", "statistically significant", "practical importance are separate"):
            self.assertIn(frag, d.report)
        self.assertIn("makes no causal claim", d.report); self.assertNotRegex(d.report.lower(), r"\bcauses?\b|\bleads? to\b|\bdrives?\b")
        a = {x.id: x for x in p.store.all()}; self.assertEqual(a["r"].value.unit, "correlation"); self.assertEqual(a["p_value"].value.unit, "probability"); self.assertEqual(a["n_pairs"].value.unit, "count")
    def test_failed_screen_switches_to_declared_fallback_as_logged_amendment(self):
        p, d = self.ok(req(*SKEWED))
        self.assertEqual(d.appendix["fallback_used"]["to"], "spearman"); self.assertEqual(d.appendix["method"]["id"], "spearman")
        self.assertIn("switched from pearson to the pre-declared fallback, spearman", d.report); self.assertIn("rank correlation", d.report)
        amend = [e for e in p.events if e["stage"] == "amendment" and e.get("kind") == "fallback"]
        self.assertEqual(len(amend), 1); self.assertEqual(amend[0]["check"], "normality_screen")
        self.assertEqual(p.spec.fallbacks, {"normality_screen": "spearman"})   # was in the frozen spec before running
        self.assertTrue(set(LIBRARY["spearman"].test_names) <= set(p.spec.checks))
    def test_screen_limits_are_declared_thresholds_not_hidden_defaults(self):
        s = SessionManager().create(req(*SKEWED, thresholds={"skew_limit": "50", "kurtosis_limit": "500"})); s.confirm(True)
        self.assertIsNone(s.to_dict()["delivery"]["appendix"]["fallback_used"]); self.assertEqual(s.to_dict()["spec"]["thresholds"]["skew_limit"], "50")
    def test_missing_pairs_counted(self):
        _, d = self.ok(req(["1", "2", "99", "4", "5", "6", None, "8"], ["52", "55", "61", "99", "70", "72", "69", "80"], codes=["99"]))
        self.assertIn("with 3 excluded as missing", d.report); self.assertIn("complete pairs", d.report)
    def test_small_sample_wording(self):
        _, d = self.ok(req(*NORMALISH)); self.assertIn("sample is small", d.report)
        _, e = self.ok(req(*NORMALISH, thresholds={"small_sample_n": "5"})); self.assertNotIn("sample is small", e.report)
    def test_effect_words_come_from_declared_thresholds(self):
        _, d = self.ok(req(*NORMALISH, thresholds={"effect_large": "0.99"})); self.assertIn("medium positive", d.report)
    def test_synthetic_label(self):
        _, d = self.ok(req(*NORMALISH, provenance={"x": "synthetic", "y": "synthetic"})); self.assertIn("synthetic data", d.report)
    def test_spearman_selectable_directly_and_no_screen(self):
        p, d = self.ok(req(*NORMALISH, method="spearman")); self.assertIn("Spearman rank correlation is", d.report); self.assertIn("approximations", d.report)
    def test_stage_states_show_fallback_run_cleanly(self):
        s = SessionManager().create(req(*SKEWED)); s.confirm(True); d = s.to_dict()
        self.assertTrue(all(v in ("passed", "not_run") for v in d["stage_states"].values()), d["stage_states"]); self.assertEqual(d["stage_states"]["verification"], "passed")
    def test_plan_shows_checks_fallback_and_thresholds_before_running(self):
        pl = SessionManager().create(req(*NORMALISH)).plan
        self.assertEqual(pl["assumption_checks"], ["normality_screen"]); self.assertEqual(pl["fallbacks"], {"normality_screen": "spearman"}); self.assertEqual(pl["thresholds"]["skew_limit"], "2")
        self.assertEqual(pl["task_family"], "Correlation analysis")

class WrongImplementations(unittest.TestCase):
    def run_bad(self, method, bad, x=NORMALISH[0], y=NORMALISH[1], codes=None):
        orig = LIBRARY[method]; LIBRARY[method] = orig.__class__(**{**orig.__dict__, "impl": bad})
        try: return Pipeline().run(req(x, y, method=method, codes=codes), yes)
        finally: LIBRARY[method] = orig
    def test_bugs_are_blocked(self):
        good = pearson_impl
        bugs = {"wrong_sign": lambda i: {**good(i), "r": -good(i)["r"]},
                "wrong_p": lambda i: {**good(i), "p_value": good(i)["p_value"] * 2},
                "narrow_interval": lambda i: {**good(i), "ci_lower": good(i)["r"] - D("0.001"), "ci_upper": good(i)["r"] + D("0.001")},
                "reads_codes_as_values": lambda i: good({**i, "missing_codes": [], "x": [v if v not in i["missing_codes"] else "99" for v in i["x"]]}),
                "scale_sensitive": lambda i: {**good(i), "r": good(i)["r"] * D("0.9") if max(D(str(v)) for v in i["x"] if v is not None) > 10 else good(i)["r"]}}
        for name, bad in bugs.items():
            d = self.run_bad("pearson", bad, x=["1", "2", "3", "99", "5", "6", "7", "8"], y=["52", "55", "61", "58", "70", "72", "69", "80"], codes=["99"]); self.assertEqual(d.status, "blocked", name)
    def test_spearman_ranking_bug_blocked(self):
        d = self.run_bad("spearman", lambda i: spearman_impl({**i, "x": [str(-D(v)) if v else v for v in i["x"]]}), x=["1", "2", "2", "3", "5"], y=["1", "3", "2", "4", "4"])
        self.assertEqual(d.status, "blocked")
    def test_discovery_lists_checks_and_fallbacks_without_running(self):
        d = methods.describe("pearson"); self.assertEqual(d["fallbacks"], {"normality_screen": "spearman"}); self.assertIn("skew_limit", d["default_thresholds"])
if __name__ == "__main__": unittest.main()
