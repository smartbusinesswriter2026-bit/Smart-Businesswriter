import sys, json, os, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import methods
from bp.methods import LIBRARY, validate_inputs, describe, list_methods, describe_impl
from bp.orchestrator import Pipeline
from bp.session import SessionManager

yes = lambda s: True
GOLD = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "descriptive_golden.json")))
def req(values, codes=None, **kw):
    r = {"objective": "Describe the scores", "method": "descriptive_stats", "unit": "points", "inputs": {"values": values, "missing_codes": codes or []}}
    r.update(kw); return r

class Golden(unittest.TestCase):
    def test_golden_set(self):
        for c in GOLD:
            out = describe_impl({"values": c["values"], "missing_codes": c["missing_codes"]})
            self.assertEqual(set(out), set(c["expected"]), c["name"])
            for k, v in c["expected"].items():
                self.assertLessEqual(abs(out[k] - D(v)), D("1e-12") * max(1, abs(D(v))), f"{c['name']}.{k}")

class Contract(unittest.TestCase):
    def test_discovery_does_not_execute(self):
        orig = LIBRARY["descriptive_stats"]
        def boom(i): raise AssertionError("executed during discovery")
        LIBRARY["descriptive_stats"] = orig.__class__(**{**orig.__dict__, "impl": boom, "tests": boom})
        try: self.assertEqual(describe("descriptive_stats")["method_id"], "descriptive_stats"); list_methods()
        finally: LIBRARY["descriptive_stats"] = orig
    def test_every_method_has_complete_contract(self):
        for d in list_methods():
            for k in ("version", "category", "tier", "status", "review_status", "intended_use", "unsupported_use", "input_schema", "defaults", "assumptions", "limitations", "planned_checks"):
                self.assertTrue(d[k], f"{d['method_id']}.{k}")
    def test_t1_label_discloses_pending_review(self):
        s = SessionManager().create(req(["1", "2", "3"])); self.assertIn("review pending", s.plan["tier_label"])
    def test_invalid_inputs_actionable(self):
        m = LIBRARY["descriptive_stats"]
        self.assertTrue(any("missing required input 'values'" in e for e in validate_inputs(m, {})))
        self.assertTrue(any("unknown input 'valuez'" in e for e in validate_inputs(m, {"values": ["1"], "valuez": 1})))
        self.assertTrue(any("[1] = 'abc'" in e for e in validate_inputs(m, {"values": ["1", "abc"]})))
        self.assertTrue(any("binary float" in e for e in validate_inputs(m, {"values": [1.5]})))
        self.assertTrue(any("not a finite" in e or "not a valid" in e for e in validate_inputs(m, {"values": ["nan"]})))
    def test_bad_input_blocks_without_defaults(self):
        d = Pipeline().run(req(["1", "x"]), yes); self.assertEqual(d.status, "blocked"); self.assertIn("'x'", d.blocked_reason)
    def test_all_missing_blocks(self):
        d = Pipeline().run(req(["99", "99"], ["99"]), yes); self.assertEqual(d.status, "blocked"); self.assertIn("no valid observations", d.blocked_reason)

class EndToEnd(unittest.TestCase):
    def run_ok(self, r, **kw):
        p = Pipeline(); d = p.run(r, yes, **kw); self.assertEqual(d.status, "delivered", d.blocked_reason); return p, d
    def test_report_numbers_by_reference_with_metadata(self):
        p, d = self.run_ok(req(["72", "85", "90", "68", "99", "77", "81"], ["99"]))
        self.assertIn("5 valid observations".replace("5", "6"), d.report)  # 99 excluded -> 6 valid
        self.assertIn("1 excluded as missing", d.report); self.assertIn("78.83", d.report)  # mean of 72,85,90,68,77,81
        a = {x.id: x for x in p.store.all()}
        self.assertEqual(a["mean"].value.unit, "points"); self.assertEqual(a["n"].value.unit, "count"); self.assertEqual(a["n"].value.precision, 0)
        self.assertTrue(a["mean"].env_hash and a["mean"].run_id and a["mean"].method_version == "1.0.0")
        self.assertEqual(d.appendix["method"]["review_status"], "pending_named_reviewer")
        self.assertEqual(sum(1 for e in p.events if e["stage"] == "verification" and e["status"] == "pass"), 1)
    def test_trap_user_missing_code_not_read_as_value(self):
        _, with_code = self.run_ok(req(["10", "20", "99"], ["99"])); _, plain = self.run_ok(req(["10", "20"]))
        self.assertIn("15.00", with_code.report); self.assertIn("15.00", plain.report)
        _, wrong = self.run_ok(req(["10", "20", "99"]))   # no code declared: 99 IS a value
        self.assertIn("43.00", wrong.report)
    def test_trap_small_sample_cannot_use_strong_wording(self):
        _, d = self.run_ok(req(["1", "2", "3"])); self.assertIn("sample is small", d.report); self.assertIn("not generalized", d.report)
        _, big = self.run_ok(req([str(i) for i in range(40)])); self.assertNotIn("sample is small", big.report)
        _, tuned = self.run_ok(req(["1", "2", "3"], thresholds={"small_sample_n": 2})); self.assertNotIn("sample is small", tuned.report)
    def test_singleton_omits_spread(self):
        _, d = self.run_ok(req(["42"])); self.assertNotIn("standard deviation", d.report); self.assertIn("not defined for a single", d.report)
    def test_synthetic_data_is_labelled(self):
        _, d = self.run_ok(req(["1", "2", "3"], provenance={"values": "synthetic"})); self.assertIn("synthetic data", d.report)
        _, o = self.run_ok(req(["1", "2", "3"])); self.assertNotIn("synthetic", o.report)
    def test_spec_has_appendix_a_fields_and_frozen_checks(self):
        s = SessionManager().create(req(["1", "2", "3"])); s.confirm(True); sp = s.to_dict()["spec"]
        for k in ("decision_context", "checks", "data_manifest", "user_values", "framework"): self.assertIn(k, sp)
        self.assertEqual(sp["checks"], list(LIBRARY["descriptive_stats"].test_names))
        self.assertEqual(sum(1 for a in sp["ambiguity_register"] if "Missing-value" in a["question"]), 1)
    def test_wrong_implementations_are_blocked(self):
        orig = LIBRARY["descriptive_stats"]
        bugs = {"population_sd": lambda i: {**describe_impl(i), "sd": describe_impl(i)["variance"].__mul__(D(len(i["values"]) - 1) / D(len(i["values"]))).sqrt()} if "sd" in describe_impl(i) else describe_impl(i),
                "reads_codes_as_values": lambda i: describe_impl({**i, "missing_codes": []}),
                "mean_off_by_one": lambda i: {**describe_impl(i), "mean": describe_impl(i)["mean"] + 1}}
        for name, bad in bugs.items():
            LIBRARY["descriptive_stats"] = orig.__class__(**{**orig.__dict__, "impl": bad})
            try: d = Pipeline().run(req(["5", "99", "7", "9", "12"], ["99"]), yes)
            finally: LIBRARY["descriptive_stats"] = orig
            self.assertEqual(d.status, "blocked", name)
    def test_builder_repair_keeps_tests_frozen(self):
        orig = LIBRARY["descriptive_stats"]
        LIBRARY["descriptive_stats"] = orig.__class__(**{**orig.__dict__, "impl": lambda i: {**describe_impl(i), "mean": D(0)}})
        try: p = Pipeline(); d = p.run(req(["1", "2", "3"]), yes, builder=lambda impl, failed: describe_impl)
        finally: LIBRARY["descriptive_stats"] = orig
        self.assertEqual(d.status, "delivered"); self.assertEqual(d.appendix["amendments"], 1)
        self.assertEqual([e for e in p.events if e["stage"] == "test_planning"][0]["tests"], tuple(orig.test_names))

class Metamorphic(unittest.TestCase):
    def test_shift_scale_permutation(self):
        v = ["3", "9", "4", "10", "1"]; b = describe_impl({"values": v})
        sh = describe_impl({"values": [str(D(x) + 7) for x in v]}); sc = describe_impl({"values": [str(D(x) * 2) for x in v]})
        self.assertEqual(sh["mean"], b["mean"] + 7); self.assertLess(abs(sh["sd"] - b["sd"]), D("1e-30")); self.assertLess(abs(sc["sd"] - b["sd"] * 2), D("1e-30"))
        self.assertEqual(describe_impl({"values": v[::-1]}), b)
if __name__ == "__main__": unittest.main()
