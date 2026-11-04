import sys, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY, validate_inputs
from bp.orchestrator import Pipeline

YES = lambda s: True
CASE = {"values": ["10", "12", "", "14", "99", "16"], "missing_codes": ["99"], "mechanism": "unknown"}


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


class MissingDataBounds(unittest.TestCase):
    def m(self): return LIBRARY["missing_data_bounds"]

    def test_extreme_case_bounds_are_exact(self):
        out = self.m().impl(CASE)
        # 4 valid values 10,12,14,16; 2 missing; total 6
        self.assertEqual((out["n_valid"], out["n_missing"]), (D(4), D(2)))
        self.assertEqual(out["mean_observed"], D(13))
        self.assertEqual((out["bound_low"], out["bound_high"], out["bound_width"]), (D(12), D(14), D(2)))

    def test_declared_missing_codes_and_blanks_both_count_as_missing(self):
        out = self.m().impl({"values": ["1", "", "99", "5"], "missing_codes": ["99"]})
        self.assertEqual((out["n_valid"], out["n_missing"]), (D(2), D(2)))

    def test_no_missing_values_collapses_the_bounds(self):
        out = self.m().impl({"values": ["1", "2", "3"]})
        self.assertEqual((out["n_missing"], out["bound_width"]), (D(0), D(0)))
        self.assertEqual(out["bound_low"], out["bound_high"])

    def test_declared_mechanism_is_recorded_but_changes_no_bound(self):
        for mech in ("unknown", "mcar", "mar", "mnar"):
            out = self.m().impl({**CASE, "mechanism": mech})
            self.assertEqual(out["bound_low"], D(12)); self.assertEqual(out["bound_high"], D(14))
            self.assertEqual(out["_appendix"]["mechanism_declared"], mech)
        self.assertIn("cannot verify", self.m().impl(CASE)["_appendix"]["mechanism_note"])

    def test_all_frozen_checks_pass(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(CASE, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(CASE, self.m().impl)))

    def test_invalid_inputs_are_refused_at_intake(self):
        for inputs in ({"values": ["", ""]}, {"values": ["1", "2"], "mechanism": "linear"}, {"values": []}):
            d = Pipeline().run({"objective": "x", "method": "missing_data_bounds", "inputs": inputs}, YES)
            self.assertEqual(d.status, "blocked", inputs)

    def test_full_pipeline_delivers_without_the_contradictory_listwise_notice(self):
        d = delivered({"objective": "Bound the missing-data sensitivity", "method": "missing_data_bounds", "unit": "points", "inputs": CASE})
        self.assertIn("extreme-case convention", d.report)
        self.assertIsNone(d.appendix["honesty"]["missing_data"])
        self.assertEqual(len(d.appendix["artifacts"]), 7)      # n_valid, n_missing, pct_missing, mean, low, high, width
        self.assertTrue(all(ok for ok in d.appendix["tests"]))

    def test_contract_and_preset(self):
        from bp import server
        m = self.m()
        self.assertEqual((m.tier, m.claim_ceiling, m.metric, m.unit, m.decision), ("T1", "descriptive", "pct_missing", "probability", None))
        self.assertEqual(validate_inputs(m, CASE), [])
        self.assertIn("missing", server.PRESETS); self.assertEqual(server.PRESETS["missing"]["method"], "missing_data_bounds")

    def test_deterministic(self):
        a = {k: str(v) for k, v in self.m().impl(CASE).items() if k != "_appendix"}
        b = {k: str(v) for k, v in self.m().impl(CASE).items() if k != "_appendix"}
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
