import sys, json, copy, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import templates as T, case_decision as C
from bp.orchestrator import Pipeline
from bp.reperform import reperform
from bp.sandbox import SubprocessSandbox
from bp.session import SessionManager, stage_states

yes = lambda s: True
EX = T.EXAMPLES["case_decision"]
def req(**kw):
    r = copy.deepcopy(EX); r["inputs"].update(kw); return r
def two(cfa, cfb, rate="0.05", rng=("0.01", "0.30"), rule="highest_npv", **kw):
    r = {"currency": "USD", "facts": [{"text": "fact one", "provenance": "user"}, {"text": "fact two", "provenance": "user"}],
         "alternatives": [{"name": "Alpha", "supports": ["F1"], "cashflows": cfa, "cashflow_provenance": "user"}, {"name": "Beta", "supports": ["F2"], "cashflows": cfb, "cashflow_provenance": "user"}],
         "rate": rate, "rate_range": list(rng), "decision_rule": rule}; r.update(kw); return r
def run(r, sandbox=None): p = Pipeline(sandbox=sandbox); return p, p.run(r, yes)
CROSS = two(["-100", "110", "0"], ["-100", "0", "121"])           # NPV_A = NPV_B exactly when 1 + r = 1.1

class Validation(unittest.TestCase):
    def errs(self, **kw): return " | ".join(C.validate({**EX["inputs"], **kw}))
    def test_intake_errors_are_actionable(self):
        alt = lambda **k: {"name": "N", "supports": ["F1"], "cashflows": ["-1", "2"], "cashflow_provenance": "user", **k}
        cases = [({"facts": []}, "non-empty list"), ({"alternatives": [alt()]}, "2 to 5"), ({"alternatives": [alt(id=f"X{i}", cashflows=["-1", str(i + 2)]) for i in range(6)]}, "2 to 5"),
                 ({"alternatives": [alt(supports=[]), alt(cashflows=["-1", "3"])]}, "at least one case fact"), ({"alternatives": [alt(supports=["F9"]), alt(cashflows=["-1", "3"])]}, "unknown fact ids"),
                 ({"alternatives": [alt(cashflows=["-1"]), alt(cashflows=["-1", "3"])]}, "2 to 30 numbers"), ({"alternatives": [alt(cashflows=[-1.5, 2]), alt(cashflows=["-1", "3"])]}, "2 to 30 numbers"),
                 ({"alternatives": [alt(cashflow_provenance=None), alt(cashflows=["-1", "3"])]}, "cashflow_provenance"), ({"alternatives": [alt(cashflow_provenance="sourced"), alt(cashflows=["-1", "3"])]}, "need a 'source'"),
                 ({"alternatives": [alt(), alt()]}, "identical cash flows"), ({"rate": "0.5"}, "inside rate_range"), ({"rate_range": ["0.3", "0.1"]}, "low < high"), ({"rate_range": ["-0.995", "0.2"]}, "low < high"),
                 ({"decision_rule": "maximize_profit"}, "the system will not choose one"), ({"currency": "dollars"}, "three-letter"), ({"alternatives": [alt(name="a\nb"), alt(cashflows=["-1", "3"])]}, "one line"),
                 ({"alternatives": [alt(id="Z"), alt(id="Z", cashflows=["-1", "3"])]}, "id must be unique"), ({"bonus": 1}, "unknown input"), ({"rate": None}, "required numbers")]
        for kw, frag in cases: self.assertIn(frag, self.errs(**kw), frag)
    def test_bad_input_blocks_before_anything_runs(self):
        p, d = run(req(decision_rule="maximize_profit")); self.assertEqual(d.status, "blocked"); self.assertFalse(any(e["stage"] == "execution" for e in p.events))

class Numbers(unittest.TestCase):
    def test_hand_checked_crossover_and_values(self):
        a = C.build(CROSS); x = a["crossovers"]
        self.assertEqual(len(x), 1); self.assertLess(abs(D(x[0]["rate"]) - D("0.1")), D("1e-15")); self.assertEqual((x[0]["below"], x[0]["above"]), ("A2", "A1"))   # below 10% Beta leads, above it Alpha
        self.assertLess(abs(D(a["npv_at_base"]["A1"]) - (-100 + D(110) / D("1.05"))), D("1e-20")); self.assertLess(abs(D(a["npv_at_base"]["A2"]) - (-100 + D(121) / D("1.05") ** 2)), D("1e-20"))
        self.assertEqual(a["ranking_at_base"], [["A2"], ["A1"]]); self.assertEqual((a["audit"]["low_end_top"], a["audit"]["high_end_top"]), (["A2"], ["A1"]))
    def test_two_roots_are_both_found(self):          # -100(1+r)^2 + 230(1+r) - 132 = 0 at r = 0.1 and r = 0.2
        a = C.build(two(["-100", "230", "-132"], ["0", "0"], rng=("0", "0.3"), rate="0.15")); rs = sorted(D(c["rate"]) for c in a["crossovers"])
        self.assertEqual(len(rs), 2); self.assertLess(abs(rs[0] - D("0.1")), D("1e-15")); self.assertLess(abs(rs[1] - D("0.2")), D("1e-15"))
    def test_no_crossover_when_one_dominates(self):
        a = C.build(two(["-100", "60", "60"], ["-100", "50", "50"])); self.assertEqual(a["crossovers"], []); self.assertTrue(a["recommendation"]["stable_across_range"])
    def test_rule_controls_the_recommendation(self):
        self.assertIsNone(C.build(two(["-100", "110", "0"], ["-100", "0", "121"], rule=None))["recommendation"])
        r = C.build(CROSS)["recommendation"]; self.assertEqual((r["rule"], r["preferred_at_base"], r["stable_across_range"], r["top_over_range"]), ("highest_npv", ["A2"], False, ["A1", "A2"]))
    def test_exact_tie_is_reported_as_a_tie(self):
        a = C.build(two(["-100", "100", "10"], ["-100", "10", "100"], rate="0", rng=("0", "0.3"))); self.assertTrue(a["recommendation"]["tied"]); self.assertEqual(a["ranking_at_base"], [["A1", "A2"]])

class EndToEnd(unittest.TestCase):
    def test_delivery_and_report(self):
        p, d = run(req()); self.assertEqual((d.status, d.tier), ("delivered", "T2")); head, listing = d.report.split("\n\n", 1)
        for frag in ("covers 2 alternatives", "8.00%", "from 2.00% to 25.00%", "Expand the shop has a net present value of USD", "changes at a discount rate of", "Under your stated decision rule (highest net present value)",
                     "the alternative in first place changes within your range", "1 alternatives rest on assumed cash flows", "The discount rate itself is an assumption", "synthetic and illustrative only", "the system adds none of them"): self.assertIn(frag, head)
        self.assertIn("[F1] A supermarket chain opened a bakery counter nearby — synthetic (illustrative only)", listing); self.assertIn("cash flows: -12000, 3000, 4000, 5000, 6000", listing)
        self.assertNotRegex(head.lower(), r"\bcauses?\b|\bshould\b|\bwill (win|succeed)\b"); self.assertEqual(d.appendix["template"]["review_status"], "pending_named_reviewer")
        self.assertTrue(all(v == "passed" for v in stage_states(p.events, True).values()), stage_states(p.events, True))
    def test_every_digit_in_the_narrative_comes_from_an_artifact(self):
        _, d = run(req()); head = d.report.split("\n\n", 1)[0]; names = "".join(n["name"] for n in d.appendix["analysis"]["alternatives"])
        import re; digits = re.findall(r"\d+(?:\.\d+)?", head)
        self.assertTrue(digits); self.assertNotIn("Option", head)
        # remove every rendered artifact value; nothing numeric may remain
        from bp.quantity import Quantity
        p = Pipeline(); p.run(req(), yes); shown = [a.value.display() for a in p.store.all()]; rest = head
        for sd in sorted(set(shown), key=len, reverse=True): rest = rest.replace(sd, "")
        self.assertEqual(re.findall(r"\d", rest), [])
    def test_user_names_with_digits_and_token_lookalikes_are_shown_not_executed(self):
        r = req(); r["inputs"]["alternatives"][0]["name"] = "Plan 2 {{ref:rate:rate:cross_section}} {{txt:A2}}"
        _, d = run(r); self.assertEqual(d.status, "delivered"); self.assertIn("Plan 2 {{ref:rate:rate:cross_section}} {{txt:A2}} has a net present value", d.report)
    def test_no_rule_means_no_recommendation_text(self):
        _, d = run(req(decision_rule=None)); self.assertIn("so no alternative is recommended", d.report); self.assertNotIn("ranks first", d.report)
    def test_negative_npv_flag_and_currency_formatting(self):
        _, d = run({"objective": "x", "method": "case_decision", "inputs": two(["-100", "10", "10"], ["-50", "100", "10"])}); self.assertIn("have a negative net present value", d.report.split("\n\n")[0])
        self.assertIn("USD (", d.report)
    def test_session_plan_and_frozen_spec(self):
        s = SessionManager().create(req()); pl = s.plan
        self.assertEqual((pl["tier"], pl["tier_label"]), ("T2", "custom analysis (T2); expert review pending")); self.assertEqual(pl["sensitivity"], {"rate": ["0.02", "0.25"]}); self.assertEqual(pl["planned_checks"], list(C.NAMES))
        self.assertIn("Decision rule", [a["question"] for a in pl["ambiguities"]]); s.confirm(True); d = s.to_dict()
        self.assertEqual([(x["id"], x["source"]) for x in d["spec"]["frameworks_selected"]], [("QNT-FIN-01", "requested_template")]); self.assertEqual(d["spec"]["sensitivity"], {"rate": ["0.02", "0.25"]}); self.assertEqual(d["stage_states"]["sensitivity"], "passed")
    def test_changing_the_decision_rule_changes_the_frozen_spec(self):
        a = SessionManager().create(req()); a.confirm(True); b = SessionManager().create(req(decision_rule=None)); b.confirm(True); self.assertNotEqual(a.to_dict()["spec"]["hash"], b.to_dict()["spec"]["hash"])

class Defects(unittest.TestCase):
    def bad(self, mutate, r=None):
        t = T.TEMPLATES["case_decision"]; orig = t["build"]
        def broken(inp): a = orig(inp); mutate(a); return a
        T.TEMPLATES["case_decision"] = {**t, "build": broken}
        try: return run(r or req())[1]
        finally: T.TEMPLATES["case_decision"] = t
    def test_defective_builders_are_blocked(self):
        def npv(a): a["npv_at_base"]["A1"] = str(D(a["npv_at_base"]["A1"]) + 1)
        def drop(a): a["crossovers"] = []
        def off(a): a["crossovers"][0]["rate"] = str(D(a["crossovers"][0]["rate"]) + D("0.001"))
        def swap(a): c = a["crossovers"][0]; c["below"], c["above"] = c["above"], c["below"]
        def rank(a): a["ranking_at_base"] = list(reversed(a["ranking_at_base"]))
        def invent_alt(a): a["alternatives"].append({"id": "A9", "name": "Invented plan", "description": "", "supports": ["F1"], "cashflows": ["-1", "2"], "provenance": "user", "source": None})
        def alter_text(a): a["facts"][0]["text"] += " (embellished)"
        def alter_cf(a): a["alternatives"][0]["cashflows"][1] = "9999"
        def stable(a): a["recommendation"]["stable_across_range"] = True
        def prefer(a): a["recommendation"]["preferred_at_base"] = ["A2"] if a["recommendation"]["preferred_at_base"] == ["A1"] else ["A1"]
        def unflag(a): a["audit"]["assumed_cashflows"] = []
        for name, fn in dict(npv=npv, drop=drop, off=off, swap=swap, rank=rank, invent_alt=invent_alt, alter_text=alter_text, alter_cf=alter_cf, stable=stable, prefer=prefer, unflag=unflag).items():
            d = self.bad(fn); self.assertEqual(d.status, "blocked", name); self.assertIn("checks failed", d.blocked_reason)
    def test_recommendation_invented_without_a_rule_is_blocked(self):
        d = self.bad(lambda a: a.update(recommendation={"rule": "highest_npv", "preferred_at_base": ["A1"], "tied": False, "top_over_range": ["A1"], "stable_across_range": True}), req(decision_rule=None)); self.assertEqual(d.status, "blocked")

class SandboxAndApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.sb = SubprocessSandbox(timeout=90)
    def test_sandbox_equals_in_process_and_reperforms(self):
        d1 = run(req())[1]; p, d2 = run(req(), self.sb); self.assertEqual(d1.report, d2.report); self.assertEqual(d2.appendix["sandbox"]["network"], "blocked")
        b = d2.appendix["reperform"]; r = reperform(b, self.sb); self.assertTrue(r["verified"])
        t = json.loads(json.dumps(b)); t["inputs"]["alternatives"][0]["cashflows"][1] = "3001"; self.assertFalse(reperform(t, self.sb)["verified"])
    def test_registered_and_described(self):
        d = T.describe("case_decision"); self.assertEqual((d["tier"], d["planned_checks"]), ("T2", list(C.NAMES))); self.assertEqual(C.validate(d["example_request"]["inputs"]), [])
if __name__ == "__main__": unittest.main()
