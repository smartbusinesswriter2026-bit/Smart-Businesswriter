import sys, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY, validate_inputs
from bp.orchestrator import Pipeline

YES = lambda s: True
HOLM_EXAMPLE = {"p_values": ["0.01", "0.04", "0.03", "0.005"], "method": "holm"}


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class MultipleComparison(unittest.TestCase):
    def test_holm_matches_the_published_step_down_example(self):
        out = LIBRARY["multiple_comparison"].impl(HOLM_EXAMPLE)
        self.assertEqual([str(out[f"p_adj_{i}"]) for i in range(1, 5)], ["0.03", "0.06", "0.06", "0.02"])
        self.assertEqual((out["n_tests"], out["n_rejected"]), (D(4), D(2)))

    def test_bonferroni_is_k_times_p_capped_at_one(self):
        out = LIBRARY["multiple_comparison"].impl({"p_values": ["0.01", "0.04", "0.9"], "method": "bonferroni"})
        self.assertEqual([str(out[f"p_adj_{i}"]) for i in range(1, 4)], ["0.03", "0.12", "1.0"])

    def test_order_does_not_change_the_adjusted_values(self):
        m = LIBRARY["multiple_comparison"]
        a = m.impl(HOLM_EXAMPLE); b = m.impl({**HOLM_EXAMPLE, "p_values": list(reversed(HOLM_EXAMPLE["p_values"]))})
        self.assertEqual([a[f"p_adj_{i}"] for i in range(1, 5)], list(reversed([b[f"p_adj_{i}"] for i in range(1, 5)])))

    def test_declared_checks_all_pass(self):
        m = LIBRARY["multiple_comparison"]
        for inp in (HOLM_EXAMPLE, {"p_values": ["0.01", "0.04", "0.9"], "method": "bonferroni"}, {"p_values": ["0.5", "0.5"], "method": "holm"}):
            self.assertEqual(tuple(n for n, _ in m.tests(inp, m.impl)), m.test_names)
            self.assertTrue(all(ok for _, ok in m.tests(inp, m.impl)), inp)

    def test_alpha_changes_only_the_rejection_count(self):
        m = LIBRARY["multiple_comparison"]
        self.assertEqual(m.impl(HOLM_EXAMPLE)["n_rejected"], D(2))                      # adjusted 0.02 and 0.03 are at or below 0.05
        self.assertEqual(m.impl({**HOLM_EXAMPLE, "alpha": "0.07"})["n_rejected"], D(4))  # all four adjusted values are at or below 0.07

    def test_invalid_inputs_are_refused_at_intake(self):
        bad = ({"p_values": ["1.2", "0.1"], "method": "holm"},
               {"p_values": ["0.1", "0.2"], "method": "bogus"},
               {"p_values": ["0.1", "0.2"], "method": "holm", "alpha": "1.5"},
               {"p_values": ["0.1"], "method": "holm"})
        for inputs in bad:
            d = Pipeline().run({"objective": "x", "method": "multiple_comparison", "inputs": inputs}, YES)
            self.assertEqual(d.status, "blocked", inputs)

    def test_full_pipeline_delivers_a_licensed_report(self):
        d = delivered({"objective": "Correct the family of tests", "method": "multiple_comparison",
                       "inputs": {**HOLM_EXAMPLE, "alpha": "0.05"}})
        self.assertIn("declared family", d.report); self.assertIn("declared correction", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 7)      # 4 adjusted p-values + n_tests + n_rejected + alpha
        self.assertTrue(all(ok for ok in d.appendix["tests"]))
        self.assertIn("does not decide", d.appendix["honesty"]["multiple_comparisons"])

    def test_contract_and_preset(self):
        from bp import server
        m = LIBRARY["multiple_comparison"]
        self.assertEqual((m.tier, m.claim_ceiling, m.metric, m.unit, m.decision), ("T1", "descriptive", "n_rejected", "count", None))
        self.assertEqual(validate_inputs(m, HOLM_EXAMPLE), [])
        self.assertIn("multicomp", server.PRESETS); self.assertEqual(server.PRESETS["multicomp"]["method"], "multiple_comparison")

    def test_deterministic(self):
        m = LIBRARY["multiple_comparison"]
        self.assertEqual({k: str(v) for k, v in m.impl(HOLM_EXAMPLE).items() if k != "_appendix"},
                         {k: str(v) for k, v in m.impl(HOLM_EXAMPLE).items() if k != "_appendix"})


if __name__ == "__main__":
    unittest.main()
