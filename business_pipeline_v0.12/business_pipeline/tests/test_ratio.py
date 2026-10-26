import sys, json, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY, ratio_impl, _ratio_tests, ratio_profile, _close, _RATIOS, _RATIO_FIGURES

GOLDEN = json.load(open("tests/fixtures/ratio_golden.json", encoding="utf-8"))


def rel_close(a, b, tol=D("1e-9")):
    a, b = D(str(a)), D(str(b))
    return abs(a - b) <= tol * max(D(1), abs(b))


class RatioGolden(unittest.TestCase):
    def test_golden_ratios_match_the_independent_reference(self):
        for c in GOLDEN["cases"]:
            out = ratio_impl(c["inputs"])
            for name, exp in c["expected"].items():
                self.assertTrue(rel_close(out[name], exp), f"{c['name']}.{name}: {out[name]} vs {exp}")
            self.assertEqual(sorted((r["ratio"], r["reason"]) for r in out["_appendix"]["not_computed"]),
                             sorted((r["ratio"], r["reason"]) for r in c["not_computed"]), c["name"])
            self.assertEqual(int(out["n_computed"]), len(c["expected"]), c["name"])

    def test_each_case_passes_every_frozen_check(self):
        for c in GOLDEN["cases"]:
            checks = ratio_impl(c["inputs"])["_checks"]
            self.assertEqual(tuple(n for n, _, _ in checks), LIBRARY["ratio_analysis"].test_names)
            self.assertTrue(all(ok for _, ok, _ in checks), (c["name"], [d for n, ok, d in checks if not ok]))


class RatioProperties(unittest.TestCase):
    FULL = GOLDEN["cases"][0]["inputs"]

    def scaled(self, k):
        return {name: str(D(v) * k) for name, v in self.FULL.items()}

    def test_scale_invariance_unit_of_measure_cancels(self):
        base, big = ratio_impl(self.FULL), ratio_impl(self.scaled(D(1000)))
        for name in (r[0] for r in _RATIOS if r[0] in base):
            self.assertTrue(rel_close(big[name], base[name]), name)

    def test_negating_net_income_flips_the_income_ratios_only(self):
        base = ratio_impl(self.FULL)
        flipped = ratio_impl({**self.FULL, "net_income": str(-D(self.FULL["net_income"]))})
        for name in ("net_margin", "return_on_assets", "return_on_equity"):
            self.assertTrue(rel_close(flipped[name], -base[name]), name)
        for name in ("current_ratio", "gross_margin", "debt_to_equity", "receivables_days"):
            self.assertTrue(rel_close(flipped[name], base[name]), name)

    def test_missing_figure_removes_the_ratio_and_explains_it(self):
        out = ratio_impl({k: v for k, v in self.FULL.items() if k != "inventory"})
        self.assertNotIn("quick_ratio", out)
        self.assertNotIn("inventory_days", out)
        reasons = {r["ratio"]: r["reason"] for r in out["_appendix"]["not_computed"]}
        self.assertIn("inventory", reasons["quick_ratio"])
        self.assertEqual(int(out["n_computed"]), len([r for r in _RATIOS if r[0] in out]))

    def test_zero_denominator_is_not_computed_never_infinite(self):
        out = ratio_impl({**self.FULL, "revenue": "0"})
        for name in ("gross_margin", "operating_margin", "net_margin", "receivables_days"):
            self.assertNotIn(name, out)
        reasons = {r["ratio"]: r["reason"] for r in out["_appendix"]["not_computed"]}
        self.assertIn("zero denominator: revenue", reasons["net_margin"])

    def test_negative_equity_is_computed_and_flagged(self):
        out = ratio_impl({**self.FULL, "equity": "-1000", "total_assets": "6000", "total_liabilities": "7000"})
        row = next(r for r in out["_appendix"]["ratios"] if r["ratio"] == "return_on_equity")
        self.assertEqual(row["status"], "computed_with_negative_base")
        self.assertIn("equity", row["negative_base"])
        ok = dict((n, ok) for n, ok, _ in out["_checks"])
        self.assertTrue(ok["negative_denominators_are_flagged_not_dropped"])
        self.assertTrue(ok["balance_sheet_identity_holds_when_checkable"])   # 7000 + (-1000) == 6000, so the identity still holds

    def test_balance_sheet_identity_checked_when_supplied(self):
        ok = dict((n, ok) for n, ok, _ in ratio_impl(self.FULL)["_checks"])
        self.assertTrue(ok["balance_sheet_identity_holds_when_checkable"])
        bad = dict((n, ok) for n, ok, _ in ratio_impl({**self.FULL, "equity": "4999"})["_checks"])
        self.assertFalse(bad["balance_sheet_identity_holds_when_checkable"])
        partial = dict((n, ok) for n, ok, _ in ratio_impl({"current_assets": "5", "current_liabilities": "2"})["_checks"])
        self.assertTrue(partial["balance_sheet_identity_holds_when_checkable"])   # not applicable

    def test_outputs_are_decimal_not_float_and_echo_the_inputs(self):
        out = ratio_impl(self.FULL)
        self.assertIsInstance(out["current_ratio"], D)
        self.assertEqual(out["_appendix"]["figures_supplied"], self.FULL)

    def test_deterministic(self):
        self.assertEqual(json.dumps(ratio_impl(self.FULL), default=str), json.dumps(ratio_impl(self.FULL), default=str))

    def test_profile_blocks_only_when_nothing_is_computable(self):
        self.assertTrue(ratio_profile({}))
        self.assertEqual(ratio_profile({"current_assets": "5", "current_liabilities": "2"}), [])
        self.assertTrue(ratio_profile({"revenue": "0", "net_income": "1"}))

    def test_registered_with_the_right_contract(self):
        m = LIBRARY["ratio_analysis"]
        self.assertEqual((m.tier, m.claim_ceiling, m.unit, m.decision), ("T1", "descriptive", "count", None))
        self.assertEqual(m.metric, "n_computed")
        self.assertEqual(set(m.input_schema), set(_RATIO_FIGURES))
        self.assertTrue(all(not s.get("required", True) for s in m.input_schema.values()))


class RatioDelivery(unittest.TestCase):
    def test_full_pipeline_delivers_a_licensed_report(self):
        from bp.orchestrator import Pipeline
        yes = lambda s: True
        req = {"objective": "Compute the key ratios from our financial statements", "method": "ratio_analysis", "period": "annual",
               "inputs": dict(GOLDEN["cases"][0]["inputs"])}
        d = Pipeline().run(req, yes)
        self.assertEqual(d.status, "delivered", d.blocked_reason)
        self.assertIn("current ratio", d.report); self.assertIn("no benchmark", d.report)
        self.assertEqual(len(d.appendix["artifacts"]), 16)          # 15 ratios + n_computed
        self.assertTrue(all(ok for ok in [x for x in d.appendix["tests"]]))

    def test_input_errors_block_at_intake(self):
        from bp.orchestrator import Pipeline
        for bad in ({"current_assets": "abc"}, {"current_assets": "5", "nonsense": "1"}):
            d = Pipeline().run({"objective": "x", "method": "ratio_analysis", "inputs": bad}, lambda s: True)
            self.assertEqual(d.status, "blocked")

    def test_preset_is_reachable_from_the_server(self):
        from bp import server
        self.assertIn("ratios", server.PRESETS)
        self.assertEqual(server.PRESETS["ratios"]["method"], "ratio_analysis")


if __name__ == "__main__":
    unittest.main()
