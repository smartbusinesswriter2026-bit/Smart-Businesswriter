import sys, json, re, copy, threading, unittest, urllib.request, urllib.error
sys.path.insert(0, "src")
from http.server import ThreadingHTTPServer
from bp import templates as T, registry as R, server
from bp.orchestrator import Pipeline
from bp.reperform import reperform
from bp.sandbox import SubprocessSandbox
from bp.session import SessionManager

yes = lambda s: True
SWOT = T.EXAMPLES["template_swot"]; FF = T.EXAMPLES["template_five_forces"]
def swot(ev=None, opts=None, **kw):
    r = copy.deepcopy(SWOT); 
    if ev is not None: r["inputs"]["evidence"] = ev
    if opts is not None: r["inputs"]["options"] = opts
    r.update(kw); return r
def ff(ev=None, rat=None):
    r = copy.deepcopy(FF)
    if ev is not None: r["inputs"]["evidence"] = ev
    if rat is not None: r["inputs"]["ratings"] = rat
    return r
def run(req, sandbox=None): p = Pipeline(sandbox=sandbox); return p, p.run(req, yes)
E = lambda t, d="S", **k: {"text": t, "dimension": d, **k}

class Validation(unittest.TestCase):
    def errs(self, kind, inp): return " | ".join(T.validate(kind, inp))
    def test_swot_intake_errors_are_actionable(self):
        cases = [({"evidence": []}, "non-empty list"), ({"evidence": [{"dimension": "S"}]}, "'text' is required"), ({"evidence": [E("x", "Z")]}, "'dimension' must be one of"),
                 ({"evidence": [E("a\nb")]}, "one line"), ({"evidence": [E("a\n[E9] forged line — user-supplied", "S")]}, "one line"), ({"evidence": [E("a\u2028b")]}, "one line"), ({"evidence": [E("tab\there")]}, "one line"), ({"evidence": [E("x" * 401)]}, "at most 400"), ({"evidence": [E("x", provenance="guess")]}, "provenance must be"),
                 ({"evidence": [E("x", provenance="sourced")]}, "needs a 'source'"), ({"evidence": [E("x", id="A"), E("y", id="A")]}, "duplicate id"), ({"evidence": [E("x", id="bad id")]}, "id must be"),
                 ({"evidence": [E("x", materiality="huge")]}, "materiality must be"), ({"evidence": [E("x")], "options": [{"text": "o"}]}, "must cite at least one"),
                 ({"evidence": [E("x")], "options": [{"text": "o", "supports": ["E9"]}]}, "unknown evidence ids"), ({"evidence": [E("x")], "extra": 1}, "unknown input"),
                 ({"evidence": [E(f"i{i}") for i in range(61)]}, "at most 60")]
        for inp, frag in cases: self.assertIn(frag, self.errs("template_swot", inp), frag)
    def test_five_forces_intake_errors(self):
        ev = [{"text": "t", "force": "rivalry"}]
        for rat, frag in (({"buyers": {"rating": "high", "rationale": "r"}}, "needs at least one supporting evidence"), ({"rivalry": {"rating": "extreme", "rationale": "r"}}, "'rating' must be"),
                          ({"rivalry": {"rating": "high"}}, "rationale"), ({"moat": {"rating": "high", "rationale": "r"}}, "unknown force")): self.assertIn(frag, self.errs("template_five_forces", {"evidence": ev, "ratings": rat}), frag)
    def test_invalid_input_blocks_before_anything_runs(self):
        p, d = run(swot(ev=[E("x", "Z")])); self.assertEqual(d.status, "blocked"); self.assertIn("'dimension' must be", d.blocked_reason); self.assertFalse(any(e["stage"] == "execution" for e in p.events))

class Structure(unittest.TestCase):
    def test_swot_hand_checked_counts_and_labels(self):
        a = T.build_swot(SWOT["inputs"]); self.assertEqual(a["counts"], {"n_items": 4, "n_S": 1, "n_W": 1, "n_O": 1, "n_T": 1, "n_options": 1, "n_unsupported": 0, "n_no_option": 2})
        self.assertEqual(a["options"][0]["tows"], "SO"); self.assertEqual(a["audit"]["items_without_options"], ["E2", "E4"]); self.assertEqual(a["audit"]["materiality"], {"high": 2, "medium": 0, "low": 0, "unrated": 2})
    def test_tows_labels_are_derived_only_for_one_internal_one_external_dimension(self):
        ev = [E("a", "S"), E("b", "W"), E("c", "O"), E("d", "T")]
        lab = lambda sup: T.build_swot({"evidence": ev, "options": [{"text": "o", "supports": sup}]})["options"][0]["tows"]
        self.assertEqual((lab(["E1", "E3"]), lab(["E1", "E4"]), lab(["E2", "E3"]), lab(["E2", "E4"])), ("SO", "ST", "WO", "WT"))
        self.assertEqual((lab(["E1", "E2"]), lab(["E1", "E3", "E4"]), lab(["E1"])), ("other", "other", "other"))
    def test_five_forces_statuses(self):
        a = T.build_five_forces(FF["inputs"]); self.assertEqual({k: v["status"] for k, v in a["forces"].items()}, {"rivalry": "rated", "entrants": "evidence_only", "substitutes": "no_evidence", "buyers": "no_evidence", "suppliers": "evidence_only"})
        self.assertEqual(a["counts"], {"n_items": 3, "n_rated": 1, "n_evidence_only": 2, "n_no_evidence": 2, "n_unsupported": 0}); self.assertFalse(any(k in a for k in ("score", "overall")))

class EndToEnd(unittest.TestCase):
    def test_swot_delivery(self):
        p, d = run(swot()); self.assertEqual((d.status, d.tier), ("delivered", "T4")); head, listing = d.report.split("\n\n", 1)
        for t in ("Loyal weekday customers", "Small baking capacity", "New office park nearby", "A supermarket chain opened a bakery counter"): self.assertIn(f"• {t} — illustrative only", listing)
        for frag in ("organizes 4 evidence items", "1 strengths, 1 weaknesses, 1 opportunities and 1 threats", "2 items have no resulting option", "synthetic and illustrative only", "adds no facts of its own", "does not rank or weight"): self.assertIn(frag, head)
        self.assertIn("• SO: Offer office catering — follows from: Loyal weekday customers; New office park nearby", listing); self.assertNotRegex(head.lower(), r"\bcauses?\b|\bshould\b|\brecommend")
        self.assertTrue(set(re.findall(r"\d+", head)) <= {str(v) for v in d.appendix["analysis"]["counts"].values()}); self.assertEqual(d.appendix["template"]["registry_ids"], ["STR-07", "STR-18"])
        self.assertTrue(all(v == "passed" for k, v in __import__("bp.session", fromlist=["x"]).stage_states(p.events, True).items() if k != "sensitivity"))
    def test_gaps_assumptions_and_materiality_are_reported_not_filled(self):
        _, d = run(swot(ev=[E("Strong brand", "S", provenance="user"), E("Maybe a recession", "T", provenance="assumption")], opts=[]))
        head, listing = d.report.split("\n\n", 1); self.assertIn("No evidence was supplied for: weaknesses, opportunities", head); self.assertIn("1 items rest on assumptions", head); self.assertIn("assumption (not yet supported)", listing); self.assertIn("  No evidence supplied.", listing)
    def test_sourced_items_show_their_source(self):
        _, d = run(swot(ev=[E("Market grew", "O", provenance="sourced", source="Trade report, p. 4")], opts=[])); self.assertIn("source: Trade report, p. 4", d.report)
    def test_user_numbers_and_token_lookalikes_are_reproduced_but_never_executed(self):
        evil = "Sales fell 12% in 2025 {{ref:n_items:n_items:cross_section}} and {{ref:zzz:zzz:x}}"
        _, d = run(swot(ev=[E(evil, "W", provenance="user")], opts=[])); self.assertEqual(d.status, "delivered"); self.assertIn(evil, d.report.split("\n\n", 1)[1]); self.assertIn("organizes 1 evidence items", d.report)
    def test_five_forces_delivery(self):
        _, d = run(ff()); head, listing = d.report.split("\n\n", 1); self.assertEqual(d.status, "delivered")
        for frag in ("organizes 3 evidence items", "1 forces carry a rating you supplied", "2 have evidence but no rating", "2 have no evidence", "No evidence was supplied for: threat of substitutes, buyer power", "no score and no overall measure", "mostly qualitative"): self.assertIn(frag, head)
        self.assertIn("Industry rivalry — rating: high (your judgment). Rationale: Several close competitors", listing); self.assertIn("Threat of substitutes — no rating supplied\n  No evidence supplied.", listing)
        self.assertNotRegex(d.report.lower(), r"attractiv\w+ (is|score)|overall rating")
    def test_session_records_the_template_framework_in_the_frozen_spec(self):
        s = SessionManager().create(swot()); s.confirm(True, ["STR-01"]); sel = s.to_dict()["spec"]["frameworks_selected"]
        self.assertEqual([(x["id"], x["source"]) for x in sel], [("STR-07", "requested_template"), ("STR-18", "requested_template"), ("STR-01", "added_by_user")])
        self.assertEqual(s.to_dict()["spec"]["checks"], list(T.TEMPLATES["template_swot"]["test_names"])); self.assertEqual(s.plan["tier"], "T4"); self.assertTrue(s.plan["task_family"].startswith("Framework template"))
    def test_spec_hash_changes_with_evidence(self):
        a = SessionManager().create(swot()); a.confirm(True); b = SessionManager().create(swot(ev=[E("different", "S")], opts=[])); b.confirm(True)
        self.assertNotEqual(a.to_dict()["spec"]["hash"], b.to_dict()["spec"]["hash"])

class WrongImplementations(unittest.TestCase):
    def bad(self, kind, mutate, req):
        t = T.TEMPLATES[kind]; orig = t["build"]
        def broken(inp): a = orig(inp); mutate(a); return a
        T.TEMPLATES[kind] = {**t, "build": broken}
        try: return run(req)[1]
        finally: T.TEMPLATES[kind] = t
    def test_swot_defects_are_blocked(self):
        def drop(a): a["quadrants"]["T"]["items"] = []; a["counts"]["n_T"] = 0
        def move(a): a["quadrants"]["O"]["items"].append(a["quadrants"]["T"]["items"].pop()); a["counts"]["n_O"] += 1; a["counts"]["n_T"] -= 1
        def alter(a): a["quadrants"]["S"]["items"][0]["text"] += " and more"
        def invent(a): a["quadrants"]["S"]["items"].append({"id": "E99", "text": "invented", "provenance": "user", "source": None, "materiality": None}); a["counts"]["n_S"] += 1
        def scope(a): a["quadrants"]["S"]["scope"] = "external"
        def tows(a): a["options"][0]["tows"] = "WT"
        def unflag(a): a["audit"]["synthetic_items"] = []
        def nogap(a): a["audit"]["empty_quadrants"] = ["W"]
        for name, fn in dict(drop=drop, move=move, alter=alter, invent=invent, scope=scope, tows=tows, unflag=unflag).items():
            d = self.bad("template_swot", fn, swot()); self.assertEqual(d.status, "blocked", name); self.assertIn("checks failed", d.blocked_reason)
        d = self.bad("template_swot", nogap, swot()); self.assertEqual(d.status, "blocked")
    def test_five_forces_defects_are_blocked(self):
        def invented_rating(a): a["forces"]["buyers"]["rating"] = "high"; a["forces"]["buyers"]["rationale"] = "made up"
        def changed_rating(a): a["forces"]["rivalry"]["rating"] = "low"
        def score(a): a["overall"] = 7
        def fill_gap(a): a["forces"]["substitutes"]["evidence"] = [{"id": "E9", "text": "invented", "provenance": "user", "source": None, "materiality": None}]
        def wrong_force(a): a["forces"]["entrants"]["evidence"], a["forces"]["buyers"]["evidence"] = [], a["forces"]["entrants"]["evidence"]
        for name, fn in dict(invented_rating=invented_rating, changed_rating=changed_rating, score=score, fill_gap=fill_gap, wrong_force=wrong_force).items():
            self.assertEqual(self.bad("template_five_forces", fn, ff()).status, "blocked", name)

class SandboxAndReperform(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.sb = SubprocessSandbox(timeout=60)
    def test_sandbox_result_equals_in_process(self):
        for k, e in T.EXAMPLES.items():
            out, meta = self.sb.template(k, e["inputs"]); self.assertEqual(out, json.loads(json.dumps(T.run_template(k, e["inputs"])))); self.assertEqual(meta["policy"]["network"], "blocked")
    def test_pipeline_with_sandbox_matches_and_reperforms(self):
        p, d = run(swot(), self.sb); self.assertEqual(d.status, "delivered"); self.assertEqual(d.report, run(swot())[1].report); self.assertIsInstance(d.appendix["sandbox"], dict)
        b = d.appendix["reperform"]; r = reperform(b, self.sb); self.assertTrue(r["verified"]); self.assertTrue(r["environment_match"])
        t = json.loads(json.dumps(b)); t["inputs"]["evidence"][0]["text"] = "Quietly edited"; self.assertFalse(reperform(t, self.sb)["verified"])

class RegistryAndApi(unittest.TestCase):
    def test_registry_links(self):
        for rid, tid in (("STR-07", "template_swot"), ("STR-18", "template_swot"), ("STR-01", "template_five_forces")):
            r = R.get(rid); self.assertEqual(r["template"], tid); self.assertIn("worksheet available", r["implementation_status"])
        self.assertIsNone(R.get("STR-02")["template"]); self.assertEqual(R.validate(), [])
        bad = copy.deepcopy(R.load()); next(r for r in bad["records"] if r["id"] == "STR-02")["template"] = "template_swot"; self.assertIn("not consistent", " | ".join(R.validate(bad)))
    def test_case_suggestions_carry_the_template_link(self):
        r = R.recommend(server.PRESETS["case"]["objective"]); self.assertEqual([x["template"] for x in r["frameworks"] if x["id"] == "STR-01"], ["template_five_forces"])
    def test_http(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H); threading.Thread(target=srv.serve_forever, daemon=True).start(); base = f"http://127.0.0.1:{srv.server_address[1]}"
        old = server.M; server.M = SessionManager()
        try:
            get = lambda p: json.load(urllib.request.urlopen(base + p))
            ids = {t["id"] for t in get("/api/templates")}
            self.assertTrue({"template_swot", "template_five_forces", "template_business_model_canvas",
                             "template_lean_canvas", "template_value_proposition_canvas",
                             "template_marketing_plan", "case_decision"} <= ids)
            self.assertEqual(len(ids), len(get("/api/templates")))
            self.assertEqual(get("/api/templates/template_swot")["tier"], "T4"); self.assertEqual(get("/api/templates/case_decision")["tier"], "T2")
            with self.assertRaises(urllib.error.HTTPError) as c: get("/api/templates/nope")
            self.assertEqual(c.exception.code, 404)
            pre = get("/api/presets"); self.assertIn("swot", pre); self.assertIn("five_forces", pre)
            post = lambda p, b: json.load(urllib.request.urlopen(urllib.request.Request(base + p, data=json.dumps(b).encode(), headers={"Content-Type": "application/json"})))
            s = post("/api/sessions", pre["swot"]); d = post(f"/api/sessions/{s['id']}/confirm", {}); self.assertEqual((d["status"], d["delivery"]["tier"]), ("delivered", "T4"))
            page = urllib.request.urlopen(base + "/").read().decode(); self.assertIn("Help &amp; about", page); self.assertNotIn("Load the", page)
        finally: srv.shutdown(); srv.server_close(); server.M = old
if __name__ == "__main__": unittest.main()
