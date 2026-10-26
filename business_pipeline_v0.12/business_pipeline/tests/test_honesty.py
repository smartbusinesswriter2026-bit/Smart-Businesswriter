import sys, unittest
sys.path.insert(0, "src")
from bp.orchestrator import Pipeline, _honesty
from bp.methods import LIBRARY

YES = lambda s: True

OLS = {"objective": "Explain exam scores", "method": "ols",
       "inputs": {"y": ["52", "55", "61", "58", "70", "72", "69", "80", "66", "74"],
                  "predictors": {"study_hours": ["1", "2", "3", "4", "5", "6", "7", "8", "4", "6"],
                                 "sleep_hours": ["6", "7", "5", "8", "6", "7", "8", "6", "7", "7"]}}}
ANOVA = {"objective": "Compare formats", "method": "anova",
         "inputs": {"groups": {"lecture": ["62", "70", "68", "75", "66", "71", "64", "73"],
                               "workshop": ["72", "78", "74", "85", "80", "77", "69", "83", "79"],
                               "online": ["60", "63", "58", "66", "61", "65", "60"]}}}
DESC = {"objective": "Describe the scores", "method": "descriptive_stats",
        "inputs": {"values": ["72", "85", "90", "68", "99", "77", "81"], "missing_codes": ["99"]}}
NPV = {"objective": "Invest?", "method": "npv", "inputs": {"rate": "0.10", "cashflows": ["-1000", "400", "400", "400"]}}
RATIOS = {"objective": "Ratios", "method": "ratio_analysis",
          "inputs": {"current_assets": "5000", "current_liabilities": "2000", "revenue": "20000", "net_income": "1800"}}
MULTICOMP = {"objective": "Correct the family", "method": "multiple_comparison",
             "inputs": {"p_values": ["0.01", "0.04", "0.03", "0.005"], "method": "holm"}}


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class HonestyBlock(unittest.TestCase):
    def test_every_delivered_library_result_carries_the_honesty_block(self):
        for req in (OLS, ANOVA, DESC, NPV, RATIOS, MULTICOMP):
            d = delivered(req)
            self.assertEqual(set(d.appendix["honesty"]), {"missing_data", "multiple_comparisons", "power", "weights_and_clusters"}, req["method"])

    def test_the_correction_method_discloses_its_scope_and_invents_no_missing_data_handling(self):
        h = delivered(MULTICOMP).appendix["honesty"]
        self.assertIn("family you supplied", h["multiple_comparisons"]); self.assertIn("does not model dependence", h["multiple_comparisons"])
        self.assertIsNone(h["missing_data"])          # p-values are not a missing-data problem; no invented listwise note

    def test_single_hypothesis_inferential_methods_disclose_no_correction_and_no_power(self):
        d = delivered(DESC)
        h = d.appendix["honesty"]
        self.assertIn("excluded listwise", h["missing_data"]); self.assertIn("mechanism", h["missing_data"])
        self.assertIsNone(h["multiple_comparisons"]); self.assertIsNone(h["power"])       # descriptive: nothing to correct or power
        self.assertIn("excluded listwise", d.report)

    def test_ols_discloses_the_untested_family_and_absent_power(self):
        d = delivered(OLS); h = d.appendix["honesty"]
        self.assertIn("2 coefficient hypotheses", h["multiple_comparisons"])
        self.assertIn("family-wise", h["multiple_comparisons"])
        self.assertIn("minimum-detectable-effect", h["power"])
        self.assertIn("treated as independent", h["weights_and_clusters"])
        self.assertIn("family-wise", d.report)

    def test_omnibus_test_discloses_no_post_hoc_and_no_correction(self):
        h = delivered(ANOVA).appendix["honesty"]
        self.assertIn("omnibus", h["multiple_comparisons"])
        self.assertIn("minimum-detectable-effect", h["power"])

    def test_non_data_methods_report_not_applicable_rather_than_blank(self):
        h = delivered(NPV).appendix["honesty"]
        self.assertTrue(all(v is None for v in h.values()))
        self.assertNotIn("multiple-comparison", delivered(NPV).report)

    def test_ratio_analysis_is_descriptive_and_carries_no_inferential_notices(self):
        h = delivered(RATIOS).appendix["honesty"]
        self.assertTrue(all(v is None for v in h.values()))

    def test_honesty_is_deterministic_and_json_safe(self):
        import json
        a, b = delivered(OLS).appendix["honesty"], delivered(OLS).appendix["honesty"]
        self.assertEqual(a, b); json.dumps(a)


class UnsupportedStructures(unittest.TestCase):
    def test_weights_and_clusters_are_refused_with_a_specific_reason(self):
        for key, words in (("weights", "survey weights"), ("clusters", "clustered observations"), ("strata", "stratified sampling")):
            d = Pipeline().run({**DESC, "inputs": {**DESC["inputs"], key: ["1", "2"]}}, YES)
            self.assertEqual(d.status, "blocked", key)
            self.assertIn(words, d.blocked_reason, key)
            self.assertIn("independent", d.blocked_reason, key)

    def test_a_genuinely_unknown_key_keeps_the_generic_message(self):
        d = Pipeline().run({**DESC, "inputs": {**DESC["inputs"], "nonsense": "1"}}, YES)
        self.assertEqual(d.status, "blocked")
        self.assertIn("unknown input", d.blocked_reason)

    def test_the_helper_names_the_fields_that_are_not_applicable(self):
        m = LIBRARY["descriptive_stats"]
        out, notes = _honesty(m, {"values": ["1"], "missing_codes": []})
        self.assertIsNotNone(out["missing_data"]); self.assertEqual(len(notes), 1)
        m = LIBRARY["npv"]; out, notes = _honesty(m, {"rate": "0.1", "cashflows": ["1", "2"]})
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
