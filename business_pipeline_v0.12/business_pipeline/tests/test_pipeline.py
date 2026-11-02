import sys, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.quantity import Quantity, Tagged, TypeMismatch, UntaggedNumber
from bp.artifacts import ArtifactStore, Artifact, RefMismatch
from bp.spec import ProblemSpec, SpecFrozen
from bp.orchestrator import Pipeline
from bp.claims import license_check
from bp import methods

REQ = {"objective": "Should we invest?", "method": "npv", "currency": "USD", "period": "annual",
       "inputs": {"rate": "0.10", "cashflows": ["-1000", "400", "400", "400"]},
       "sensitivity": {"rate": ["0.05", "0.25"]}}
yes = lambda s: True

class T(unittest.TestCase):
    def test_float_rejected(self):
        with self.assertRaises(TypeMismatch): Quantity(0.1)
    def test_mismatched_types_raise(self):
        with self.assertRaises(TypeMismatch): Quantity("1", currency="USD") + Quantity("1", currency="EUR")
    def test_untagged_rejected(self):
        with self.assertRaises(UntaggedNumber): Tagged("x", Quantity("1"), "guess")
    def test_negative_display_parentheses(self):
        self.assertEqual(Quantity("-5", currency="USD").display(), "USD (5.00)")
    def test_artifact_immutable_and_label_match(self):
        s = ArtifactStore(); a = Artifact("a", Quantity("1"), ("rev", "Q3", "e", "s"), "h", "c", "i", "d", "p"); s.put(a)
        with self.assertRaises(ValueError): s.put(a)
        with self.assertRaises(RefMismatch): s.resolve("a", "rev", "Q2")
    def test_spec_freeze_and_amend(self):
        sp = ProblemSpec("o", "npv", [], {}, [], {}, {}); sp.freeze()
        with self.assertRaises(SpecFrozen): sp.objective = "changed"
        sp2 = sp.amend("scope change", objective="new"); self.assertEqual(sp2.version, 2); self.assertIsNone(sp2.hash)
    def test_npv_known_value(self):
        self.assertEqual(round(methods.npv(REQ["inputs"]), 4), D("-5.2592"))
    def test_happy_path_delivers_with_numbers_by_reference(self):
        p = Pipeline(); d = p.run(REQ, yes)
        self.assertEqual(d.status, "delivered"); self.assertEqual(d.tier, "T1")
        self.assertIn("USD (5.26)", d.report); self.assertIn("does not clear", d.report)
        self.assertIn("9.7", d.report)  # flip rate ~9.70% from bisection
        self.assertEqual([e["stage"] for e in p.events if e["stage"] in ("intake","formalization","delivery")], ["intake","formalization","formalization","delivery"])
    def test_user_must_confirm(self):
        self.assertEqual(Pipeline().run(REQ, lambda s: False).status, "blocked")
    def test_no_method_is_framework_only(self):
        d = Pipeline().run({**REQ, "method": "mystery"}, yes); self.assertEqual(d.tier, "T4"); self.assertIn("No computed answer", d.report)
    def test_profiling_blocks_bad_input(self):
        r = {"objective": "x", "method": "breakeven", "inputs": {"fixed": "100", "price": "5", "variable": "6"}}
        self.assertEqual(Pipeline().run(r, yes).status, "blocked")
    def test_breakeven(self):
        r = {"objective": "x", "method": "breakeven", "inputs": {"fixed": "1000", "price": "20", "variable": "10"}}
        d = Pipeline().run(r, yes); self.assertEqual(d.status, "delivered"); self.assertIn("100.00", d.report)
    def test_buggy_impl_blocked_without_builder(self):
        orig = methods.LIBRARY["npv"]
        bad = orig.__class__(**{**orig.__dict__, "impl": lambda i: methods.npv(i) + 1})
        methods.LIBRARY["npv"] = bad
        try: d = Pipeline().run(REQ, yes)
        finally: methods.LIBRARY["npv"] = orig
        self.assertEqual(d.status, "blocked"); self.assertIn("second_implementation_agrees", d.blocked_reason)
    def test_builder_repairs_within_budget_and_logs_amendment(self):
        orig = methods.LIBRARY["npv"]
        methods.LIBRARY["npv"] = orig.__class__(**{**orig.__dict__, "impl": lambda i: methods.npv(i) + 1})
        try:
            p = Pipeline(); d = p.run(REQ, yes, builder=lambda impl, failed: methods.npv)
        finally: methods.LIBRARY["npv"] = orig
        self.assertEqual(d.status, "delivered"); self.assertEqual(d.appendix["amendments"], 1)
    def test_builder_exhausting_budget_escalates(self):
        orig = methods.LIBRARY["npv"]
        bad = lambda i: methods.npv(i) + 1
        methods.LIBRARY["npv"] = orig.__class__(**{**orig.__dict__, "impl": bad})
        try: d = Pipeline(3).run(REQ, yes, builder=lambda impl, failed: bad)
        finally: methods.LIBRARY["npv"] = orig
        self.assertEqual(d.status, "blocked"); self.assertIn("3 amendment", d.blocked_reason)
    def test_raw_digits_in_draft_rejected_years_allowed(self):
        self.assertEqual(Pipeline().run(REQ, yes, template="NPV is 5.26 dollars.").status, "blocked")
        d = Pipeline().run(REQ, yes, template="In 2026 the NPV is {{ref:result:npv:annual}}."); self.assertEqual(d.status, "delivered")
    def test_wrong_reference_label_rejected(self):
        d = Pipeline().run(REQ, yes, template="NPV is {{ref:result:npv:quarterly}}."); self.assertEqual(d.status, "blocked")
    def test_claim_licensing(self):
        self.assertTrue(license_check("Loyalty drives spend.", "associational"))
        self.assertTrue(license_check("The effect of the program is large.", "descriptive"))
        self.assertTrue(license_check("This proves the effect.", "causal"))
        d = Pipeline().run(REQ, yes, template="The impact of the project is {{ref:result:npv:annual}}."); self.assertEqual(d.status, "blocked")
if __name__ == "__main__": unittest.main()
