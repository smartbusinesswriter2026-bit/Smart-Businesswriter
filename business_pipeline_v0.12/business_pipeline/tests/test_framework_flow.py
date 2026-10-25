import sys, json, threading, unittest, urllib.request, urllib.error
sys.path.insert(0, "src")
from http.server import ThreadingHTTPServer
from bp import server, registry as R
from bp.session import SessionManager
from test_pipeline import REQ

CASE = server.PRESETS["case"]

class Flow(unittest.TestCase):
    def test_plan_carries_suggestions_with_registry_version(self):
        s = SessionManager().create(CASE); sg = s.plan["framework_suggestions"]
        self.assertIn("STR-01", [x["id"] for x in sg["frameworks"]]); self.assertEqual(sg["registry"]["hash"], R.load()["hash"]); self.assertEqual(s.plan["task_family"], "Framework guidance (no computed answer)")
        self.assertEqual(s.plan["tier"], "T4")
    def test_nothing_is_applied_unless_selected(self):
        s = SessionManager().create(CASE); s.confirm(True); d = s.to_dict()
        self.assertEqual(d["spec"]["frameworks_selected"], []); self.assertEqual(d["delivery"]["tier"], "T4"); self.assertIn("No framework was selected", d["delivery"]["report"])
    def test_selection_is_frozen_into_the_spec_and_changes_its_hash(self):
        a = SessionManager().create(CASE); a.confirm(True); b = SessionManager().create(CASE); b.confirm(True, ["STR-01", "THE-02"])
        da, db = a.to_dict(), b.to_dict(); self.assertNotEqual(da["spec"]["hash"], db["spec"]["hash"])
        self.assertEqual([(x["id"], x["source"], x["role"]) for x in db["spec"]["frameworks_selected"]], [("STR-01", "suggested", "selected"), ("THE-02", "added_by_user", "supporting_theory")])
        rep = db["delivery"]["report"]; self.assertIn("Five Forces", rep); self.assertIn("not as a template", rep); self.assertTrue(rep.startswith("No computed answer"))
        self.assertEqual(db["delivery"]["appendix"]["registry"]["hash"], R.load()["hash"])
    def test_named_in_request_is_recorded_as_named_by_user(self):
        s = SessionManager().create({"objective": "Use SWOT because we must weigh internal strengths and weaknesses against external opportunities and threats."}); s.confirm(True, ["STR-07"])
        self.assertEqual(s.to_dict()["spec"]["frameworks_selected"][0]["source"], "named_by_user")
    def test_invalid_selection_rejected_and_session_stays_open(self):
        s = SessionManager().create(CASE)
        for bad in (["NOPE-1"], "STR-01", [1], ["STR-01"] * 2 + [f"STR-0{i}" for i in range(2, 8)]):
            with self.assertRaises(ValueError): s.confirm(True, bad)
        self.assertEqual(s.status, "awaiting_confirmation"); s.confirm(True, ["STR-01"]); self.assertEqual(s.status, "delivered")
        with self.assertRaises(ValueError): s.confirm(True, [])
    def test_reject_records_nothing(self):
        s = SessionManager().create(CASE); s.confirm(False, ["STR-01"]); self.assertEqual(s.to_dict()["spec"]["frameworks_selected"], [])
    def test_framework_only_stage_states(self):
        s = SessionManager().create(CASE); s.confirm(True, ["STR-01"]); st = s.to_dict()["stage_states"]
        self.assertEqual(st["method_selection"], "passed"); self.assertEqual(st["execution"], "not_run"); self.assertEqual(st["delivery"], "not_run")
    def test_selected_framework_does_not_change_a_computed_result(self):
        a = SessionManager().create(REQ); a.confirm(True); b = SessionManager().create(REQ); b.confirm(True, ["STR-07"])
        self.assertEqual(a.to_dict()["delivery"]["report"], b.to_dict()["delivery"]["report"])
        ap = b.to_dict()["delivery"]["appendix"]; self.assertEqual(ap["frameworks_selected"][0]["id"], "STR-07"); self.assertIn("did not change the computation", ap["frameworks_note"])
    def test_request_without_method_or_inputs_is_accepted_and_empty_objective_is_not(self):
        SessionManager().create({"objective": "Which strategy?"})
        for bad in ({}, {"objective": "  "}, {"objective": "x", "inputs": []}):
            with self.assertRaises(ValueError): SessionManager().create(bad)
    def test_computed_request_also_gets_suggestions_without_forcing_any(self):
        s = SessionManager().create({**REQ, "objective": "Should we invest? Calculate the net present value."}); sg = s.plan["framework_suggestions"]
        self.assertTrue(any(x["id"] == "QNT-FIN-01" and x["linked_methods"][0]["method_id"] == "npv" for x in sg["quantitative"]))

class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = server.M; server.M = SessionManager(); cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H); cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown(); cls.srv.server_close(); server.M = cls.old
    def call(self, path, body=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
    def test_search_detail_and_errors(self):
        c, b = self.call("/api/frameworks?q=five%20forces"); self.assertEqual((c, b["results"][0]["id"]), (200, "STR-01")); self.assertEqual(b["registry"]["hash"], R.load()["hash"])
        self.assertEqual(self.call("/api/frameworks?q=x&type=Z")[0], 400); self.assertEqual(self.call("/api/frameworks/NOPE-1")[0], 404)
        c, b = self.call("/api/frameworks/IMP-01"); self.assertEqual((c, b["id"]), (200, "CHG-07"))
        c, b = self.call("/api/frameworks?q=maslow&type=T"); self.assertTrue(b["results"] and all(x["type"] == "T" for x in b["results"]))
    def test_confirm_with_frameworks_over_http(self):
        c, s = self.call("/api/sessions", CASE); self.assertEqual(c, 201); self.assertIn("framework_suggestions", s["work_plan"])
        c, d = self.call(f"/api/sessions/{s['id']}/confirm", {"frameworks": ["STR-01"]}); self.assertEqual((c, d["status"]), (200, "delivered")); self.assertEqual(d["spec"]["frameworks_selected"][0]["id"], "STR-01")
        c, s2 = self.call("/api/sessions", CASE); self.assertEqual(self.call(f"/api/sessions/{s2['id']}/confirm", {"frameworks": "STR-01"})[0], 400); self.assertEqual(self.call(f"/api/sessions/{s2['id']}/confirm", [])[0], 400)
    def test_ui_has_framework_section(self):
        req = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/").read().decode(); self.assertIn("Frameworks, models and methods", req); self.assertIn("Nothing is applied unless ticked", req)
if __name__ == "__main__": unittest.main()
