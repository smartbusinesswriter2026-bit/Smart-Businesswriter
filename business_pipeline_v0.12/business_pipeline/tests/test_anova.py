import sys, json, os, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import methods
from bp.methods import LIBRARY, anova_impl, kw_impl, validate_inputs
from bp.orchestrator import Pipeline
from bp.session import SessionManager

yes = lambda s: True
GOLD = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "anova_golden.json")))
G3 = {"lecture": ["62", "70", "68", "75", "66", "71", "64", "73"], "workshop": ["72", "78", "74", "85", "80", "77", "69", "83", "79"], "online": ["60", "63", "58", "66", "61", "65", "60"]}
SKEW3 = {"a": ["1", "1", "1", "2", "1", "1", "2", "3", "30"], "b": ["2", "3", "4", "5", "3", "4", "6", "5", "4"], "c": ["3", "2", "4", "3", "2", "3", "2", "3", "2"]}
UNEQ = {"a": ["1", "2", "3", "4", "5", "6", "7", "8"], "b": ["10", "11", "12", "13", "14", "15", "16", "17"], "c": ["100", "-100", "300", "-300", "500", "-500", "700", "-700"]}
def req(G=G3, method="anova", codes=None, **kw):
    r = {"objective": "Do the groups differ?", "method": method, "unit": "points", "inputs": {"groups": G, "missing_codes": codes or []}}; r.update(kw); return r

class Golden(unittest.TestCase):
    def test_against_offline_scipy_references(self):
        for c in GOLD:
            out = (anova_impl if c["method"] == "anova" else kw_impl)({"groups": c["groups"], "missing_codes": c["missing_codes"]})
            for k, v in c["expected"].items(): self.assertLessEqual(abs(float(out[k]) - float(v)), 1e-9 * max(1, abs(float(v))), f"{c['name']}.{k}")

class Inputs(unittest.TestCase):
    def blocked(self, r, text):
        d = Pipeline().run(r, yes); self.assertEqual(d.status, "blocked"); self.assertIn(text, d.blocked_reason); return d
    def test_schema_needs_three_groups_and_clean_names(self):
        m = LIBRARY["anova"]
        self.assertTrue(any("at least 3 columns" in e for e in validate_inputs(m, {"groups": {"a": ["1", "2"], "b": ["1", "2"]}})))
        self.assertTrue(any("group1" in e or "digits" in e for e in validate_inputs(m, {"groups": {"group1": ["1"] * 3, "b": ["1"] * 3, "c": ["1"] * 3}})))
    def test_group_with_one_valid_observation_blocks(self):
        self.blocked(req({"a": ["1", "2", "3"], "b": ["2", "3", "4"], "c": ["99", "2", "99"]}, codes=["99"]), "fewer than two valid")
    def test_zero_within_group_variance_blocks(self):
        self.blocked(req({"a": ["5"] * 4, "b": ["5"] * 4, "c": ["5"] * 4}), "within-group variance is zero")
    def test_unequal_group_sizes_allowed(self):
        self.assertEqual(Pipeline().run(req(), yes).status, "delivered")

class EndToEnd(unittest.TestCase):
    def ok(self, r):
        p = Pipeline(); d = p.run(r, yes); self.assertEqual(d.status, "delivered", d.blocked_reason); return p, d
    def test_anova_report(self):
        p, d = self.ok(req()); self.assertIsNone(d.appendix["fallback_used"]); self.assertEqual(d.appendix["method"]["id"], "anova")
        for frag in ("compares 3 groups", "Group lecture has 8 valid observations with a mean of 68.625", "Group online has 7", "One-way ANOVA gives F(2, 21) = 25.611",
                     "below the reporting floor", "group means are statistically significantly different", "Eta-squared is 0.709", "large effect", "practical importance are separate", "no causal claim", "sample is small"): self.assertIn(frag, d.report)
        self.assertNotIn("{{", d.report); self.assertNotRegex(d.report.lower(), r"\bcauses?\b|\bleads? to\b|\bdrives?\b|\beffect of\b|\bimpact of\b")
        a = {x.id: x for x in p.store.all()}; self.assertEqual(a["mean_lecture"].value.unit, "points"); self.assertEqual(a["p_value"].value.unit, "probability"); self.assertEqual(a["df_between"].value.precision, 0); self.assertEqual(a["eta_squared"].value.unit, "ratio")
    def test_skewed_groups_switch_to_kruskal_wallis_as_logged_amendment(self):
        p, d = self.ok(req(SKEW3)); self.assertEqual(d.appendix["fallback_used"]["to"], "kruskal_wallis"); self.assertEqual(d.appendix["fallback_used"]["check"], "group_normality_screen")
        for frag in ("switched from anova to the pre-declared fallback, kruskal_wallis", "Kruskal-Wallis gives H", "Epsilon-squared", "rank distributions"): self.assertIn(frag, d.report)
        self.assertEqual(p.spec.fallbacks, {"group_normality_screen": "kruskal_wallis", "homogeneity_of_variance_screen": "kruskal_wallis"}); self.assertTrue(set(LIBRARY["kruskal_wallis"].test_names) <= set(p.spec.checks))
        self.assertEqual(len([e for e in p.events if e["stage"] == "amendment" and e.get("kind") == "fallback"]), 1)
    def test_levene_failure_switches_to_kruskal_wallis(self):
        _, d = self.ok(req(UNEQ)); self.assertEqual(d.appendix["fallback_used"]["check"], "homogeneity_of_variance_screen")
    def test_declared_screen_limits_decide(self):
        _, d = self.ok(req(UNEQ, thresholds={"levene_alpha": "1e-300"})); self.assertEqual(d.appendix["method"]["id"], "anova")
    def test_missing_counted(self):
        _, d = self.ok(req(GOLD[1]["groups"], codes=GOLD[1]["missing_codes"])); self.assertIn("3 entries were excluded as missing", d.report)
    def test_effect_word_from_declared_thresholds(self):
        _, d = self.ok(req(thresholds={"eta_large": "5"})); self.assertIn("medium effect", d.report)
    def test_not_significant_wording(self):
        _, d = self.ok(req({"a": ["1", "2", "3", "4", "5", "6"], "b": ["2", "3", "4", "5", "6", "7"], "c": ["1", "2", "3", "4", "5", "6"]})); self.assertIn("not statistically significantly different", d.report)
    def test_synthetic_label(self):
        _, d = self.ok(req(provenance={"groups": "synthetic"})); self.assertIn("synthetic data", d.report)
    def test_plan_and_states(self):
        s = SessionManager().create(req()); self.assertEqual(s.plan["task_family"], "Group comparison"); self.assertEqual(s.plan["fallbacks"], {"group_normality_screen": "kruskal_wallis", "homogeneity_of_variance_screen": "kruskal_wallis"})
        s = SessionManager().create(req(SKEW3)); s.confirm(True); d = s.to_dict(); self.assertEqual(d["stage_states"]["verification"], "passed")

class WrongImplementations(unittest.TestCase):
    def run_bad(self, method, bad, G=G3):
        orig = LIBRARY[method]; LIBRARY[method] = orig.__class__(**{**orig.__dict__, "impl": bad})
        try: return Pipeline().run(req(G, method=method), yes)
        finally: LIBRARY[method] = orig
    def test_anova_bugs_blocked(self):
        g = anova_impl
        bugs = {"one_sided_p": lambda i: {**g(i), "p_value": g(i)["p_value"] / 2},
                "wrong_df_between": lambda i: {**g(i), "df_between": g(i)["df_between"] - 1},
                "eta2_from_within": lambda i: {**g(i), "eta_squared": 1 - g(i)["eta_squared"]},
                "f_as_product": lambda i: {**g(i), "f_stat": g(i)["f_stat"] ** 2}}
        for name, bad in bugs.items(): self.assertEqual(self.run_bad("anova", bad).status, "blocked", name)
    def test_kruskal_bugs_blocked(self):
        g = kw_impl
        bugs = {"p_scaled": lambda i: {**g(i), "p_value": g(i)["p_value"] * D("0.8")},
                "h_doubled": lambda i: {**g(i), "h_stat": g(i)["h_stat"] * 2},
                "epsilon_negative": lambda i: {**g(i), "epsilon_squared": -g(i)["epsilon_squared"]}}
        for name, bad in bugs.items(): self.assertEqual(self.run_bad("kruskal_wallis", bad).status, "blocked", name)
    def test_discovery(self):
        d = methods.describe("anova"); self.assertEqual(d["fallbacks"], {"group_normality_screen": "kruskal_wallis", "homogeneity_of_variance_screen": "kruskal_wallis"}); self.assertIn("eta_large", d["default_thresholds"]); self.assertEqual(methods.describe("kruskal_wallis")["assumption_checks"], [])
if __name__ == "__main__": unittest.main()
