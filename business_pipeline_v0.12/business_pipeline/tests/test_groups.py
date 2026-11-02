import sys, json, os, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import methods
from bp.methods import LIBRARY, welch_impl, mwu_impl, validate_inputs
from bp.orchestrator import Pipeline
from bp.session import SessionManager

yes = lambda s: True
GOLD = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "groups_golden.json")))
LEC = {"lecture": ["62", "70", "68", "75", "66", "71", "64", "73"], "workshop": ["72", "78", "74", "85", "80", "77", "69", "83", "79"]}
SKEWED = {"a": ["1", "1", "1", "2", "1", "1", "2", "3", "30"], "b": ["2", "3", "4", "5", "3", "4", "6", "5", "4"]}
def req(G=LEC, method="welch_t", codes=None, **kw):
    r = {"objective": "Do the groups differ?", "method": method, "unit": "points", "inputs": {"groups": G, "missing_codes": codes or []}}; r.update(kw); return r

class Golden(unittest.TestCase):
    def test_against_offline_scipy_references(self):
        for c in GOLD:
            out = (welch_impl if c["method"] == "welch_t" else mwu_impl)({"groups": c["groups"], "missing_codes": c["missing_codes"]})
            for k, v in c["expected"].items(): self.assertLessEqual(abs(float(out[k]) - float(v)), 1e-9 * max(1, abs(float(v))), f"{c['name']}.{k}")
    def test_hand_checked_welch(self):   # means 3 and 6, variances 2.5 and 10 -> se^2 = 2.5, df = 6.25 / 1.0625
        o = welch_impl({"groups": {"a": ["1", "2", "3", "4", "5"], "b": ["2", "4", "6", "8", "10"]}})
        self.assertLess(abs(float(o["t_stat"]) + 3 / 2.5 ** 0.5), 1e-12); self.assertLess(abs(float(o["df"]) - 6.25 / 1.0625), 1e-12); self.assertEqual(o["diff"], D(-3))
    def test_hand_checked_mwu_u(self):
        o = mwu_impl({"groups": {"a": ["5", "6", "7", "8", "9"], "b": ["1", "2", "3", "4", "10"]}}); self.assertEqual(o["u_stat"], D(20)); self.assertEqual(o["rank_biserial"], D("0.6"))

class Inputs(unittest.TestCase):
    def blocked(self, r, text):
        d = Pipeline().run(r, yes); self.assertEqual(d.status, "blocked"); self.assertIn(text, d.blocked_reason); return d
    def test_schema(self):
        m = LIBRARY["welch_t"]
        self.assertTrue(any("at least 2 columns" in e for e in validate_inputs(m, {"groups": {"a": ["1", "2", "3"]}})))
        self.assertTrue(any("at most 2" in e for e in validate_inputs(m, {"groups": {"a": ["1"] * 3, "b": ["1"] * 3, "c": ["1"] * 3}})))
        self.assertTrue(any("group1" in e or "digits" in e for e in validate_inputs(m, {"groups": {"group1": ["1"] * 3, "b": ["1"] * 3}})))
    def test_too_few_valid(self): self.blocked(req({"a": ["1", "2", "99"], "b": ["1", "2", "3", "4"]}, codes=["99"]), "fewer than three valid")
    def test_zero_variance_both(self): self.blocked(req({"a": ["5", "5", "5"], "b": ["5", "5", "5"]}), "zero variance")
    def test_interval_needs_enough_data_for_mann_whitney(self): self.blocked(req({"a": ["1", "2", "3"], "b": ["4", "5", "6"]}, method="mann_whitney"), "too few observations")
    def test_unequal_sizes_allowed(self): self.assertEqual(Pipeline().run(req(), yes).status, "delivered")

class EndToEnd(unittest.TestCase):
    def ok(self, r):
        p = Pipeline(); d = p.run(r, yes); self.assertEqual(d.status, "delivered", d.blocked_reason); return p, d
    def test_welch_report(self):
        p, d = self.ok(req()); self.assertIsNone(d.appendix["fallback_used"]); self.assertEqual(d.appendix["method"]["id"], "welch_t")
        for frag in ("Group lecture has 8 valid observations with a mean of 68.625", "group workshop has 9", "(lecture minus workshop) is -8.819", "Welch's test gives a p-value of 0.0018",
                     "Hedges' g", "-1.733", "large difference", "is statistically significant", "practical importance are separate", "no causal claim", "groups are small"): self.assertIn(frag, d.report)
        self.assertNotIn("{{", d.report); self.assertNotRegex(d.report.lower(), r"\bcauses?\b|\bleads? to\b|\bdrives?\b|\beffect of\b|\bimpact of\b")
        a = {x.id: x for x in p.store.all()}; self.assertEqual(a["mean_lecture"].value.unit, "points"); self.assertEqual(a["p_value"].value.unit, "probability"); self.assertEqual(a["n_lecture"].value.precision, 0)
    def test_skewed_group_switches_to_mann_whitney_as_logged_amendment(self):
        p, d = self.ok(req(SKEWED)); self.assertEqual(d.appendix["fallback_used"]["to"], "mann_whitney")
        for frag in ("switched from welch_t to the pre-declared fallback, mann_whitney", "Hodges-Lehmann", "Mann-Whitney test gives", "rank-biserial", "normal approximations"): self.assertIn(frag, d.report)
        self.assertEqual(p.spec.fallbacks, {"group_normality_screen": "mann_whitney"}); self.assertTrue(set(LIBRARY["mann_whitney"].test_names) <= set(p.spec.checks))
        self.assertEqual(len([e for e in p.events if e["stage"] == "amendment" and e.get("kind") == "fallback"]), 1)
    def test_declared_screen_limits_decide(self):
        _, d = self.ok(req(SKEWED, thresholds={"skew_limit": "50", "kurtosis_limit": "500"})); self.assertEqual(d.appendix["method"]["id"], "welch_t")
    def test_missing_counted(self):
        c = GOLD[2]; _, d = self.ok(req(c["groups"], codes=c["missing_codes"])); self.assertIn("2 entries were excluded as missing", d.report)
    def test_effect_word_from_declared_thresholds(self): _, d = self.ok(req(thresholds={"g_medium": "1", "g_large": "5"})); self.assertIn("medium difference", d.report)
    def test_not_significant_wording(self):
        _, d = self.ok(req({"a": ["1", "2", "3", "4", "5", "6"], "b": ["2", "3", "4", "5", "6", "7"]})); self.assertIn("is not statistically significant", d.report)
    def test_synthetic_label(self): _, d = self.ok(req(provenance={"groups": "synthetic"})); self.assertIn("synthetic data", d.report)
    def test_plan_and_states(self):
        s = SessionManager().create(req()); self.assertEqual(s.plan["task_family"], "Group comparison"); self.assertEqual(s.plan["fallbacks"], {"group_normality_screen": "mann_whitney"})
        s = SessionManager().create(req(SKEWED)); s.confirm(True); d = s.to_dict(); self.assertEqual(d["stage_states"]["verification"], "passed")
        self.assertTrue(all(v in ("passed", "not_run") for v in d["stage_states"].values()))

class WrongImplementations(unittest.TestCase):
    def run_bad(self, method, bad, G=LEC, codes=None):
        orig = LIBRARY[method]; LIBRARY[method] = orig.__class__(**{**orig.__dict__, "impl": bad})
        try: return Pipeline().run(req(G, method=method, codes=codes), yes)
        finally: LIBRARY[method] = orig
    def test_welch_bugs_blocked(self):
        g = welch_impl
        def student(i):   # pooled-variance Student t instead of Welch
            o = g(i); (na, a), (nb, b) = list(methods._grp(i)[0].items()); n1, n2 = len(a), len(b)
            sp2 = ((n1 - 1) * methods._var(a) + (n2 - 1) * methods._var(b)) / (n1 + n2 - 2); se = (sp2 * (D(1) / n1 + D(1) / n2)).sqrt(); t = o["diff"] / se
            return {**o, "se_diff": se, "t_stat": t, "df": D(n1 + n2 - 2), "p_value": methods._fd(methods._p_t(float(t), n1 + n2 - 2))}
        bugs = {"student_instead_of_welch": student, "se_too_small": lambda i: {**g(i), "se_diff": g(i)["se_diff"] * D("0.9")},
                "one_sided_p": lambda i: {**g(i), "p_value": g(i)["p_value"] / 2}, "g_without_small_sample_correction": lambda i: {**g(i), "hedges_g": g(i)["hedges_g"] * D("1.05")},
                "sign_flip": lambda i: {**g(i), "diff": -g(i)["diff"]}, "reads_codes_as_values": lambda i: g({**i, "missing_codes": [], "groups": {k: [v if v not in i["missing_codes"] else "99" for v in col] for k, col in i["groups"].items()}}),
                "magnitude_dependent": lambda i: {**g(i), "p_value": g(i)["p_value"] * (D("1.5") if max(D(str(v)) for c in i["groups"].values() for v in c if v is not None) > 200 else 1)}}
        G = {"lecture": LEC["lecture"] + ["99"], "workshop": LEC["workshop"]}
        for name, bad in bugs.items(): self.assertEqual(self.run_bad("welch_t", bad, G, ["99"]).status, "blocked", name)
    def test_mann_whitney_bugs_blocked(self):
        g = mwu_impl
        bugs = {"rank_biserial_sign": lambda i: {**g(i), "rank_biserial": -g(i)["rank_biserial"]}, "p_without_continuity": lambda i: {**g(i), "p_value": g(i)["p_value"] * D("0.8")},
                "narrow_interval": lambda i: {**g(i), "ci_lower": g(i)["hl_shift"] - D("0.1"), "ci_upper": g(i)["hl_shift"] + D("0.1")},
                "wrong_group_u": lambda i: {**g(i), "u_stat": D(len(i["groups"]["lecture"]) * len(i["groups"]["workshop"])) - g(i)["u_stat"]}}
        for name, bad in bugs.items(): self.assertEqual(self.run_bad("mann_whitney", bad).status, "blocked", name)
    def test_discovery(self):
        d = methods.describe("welch_t"); self.assertEqual(d["fallbacks"], {"group_normality_screen": "mann_whitney"}); self.assertIn("g_large", d["default_thresholds"])
if __name__ == "__main__": unittest.main()
