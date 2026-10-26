import sys, json, threading, unittest, urllib.request
sys.path.insert(0, "src")
from http.server import ThreadingHTTPServer
from bp.session import SessionManager, stage_states, STATES
from bp import server, methods
from bp.orchestrator import STAGES
from test_pipeline import REQ

class S(unittest.TestCase):
    def test_plan_before_execution_nothing_computed(self):
        s = SessionManager().create(REQ); d = s.to_dict()
        self.assertEqual(d["status"], "awaiting_confirmation"); self.assertIsNone(d["delivery"])
        self.assertEqual(d["stage_states"]["formalization"], "awaiting_user")
        self.assertEqual(d["stage_states"]["execution"], "planned")
        self.assertFalse(any(e["stage"] == "execution" for e in d["events"]))
        self.assertEqual(d["work_plan"]["planned_checks"], list(methods.LIBRARY["npv"].test_names))
        self.assertIsNone(d["spec"]["hash"])
    def test_confirm_runs_and_states_from_events(self):
        s = SessionManager().create(REQ); s.confirm(True); d = s.to_dict()
        self.assertEqual(d["status"], "delivered"); self.assertTrue(d["spec"]["hash"])
        self.assertTrue(all(v == "passed" for v in d["stage_states"].values()), d["stage_states"])
        json.dumps(d)  # fully serializable
    def test_reject_blocks_and_marks_rest_not_run(self):
        s = SessionManager().create(REQ); s.confirm(False); d = s.to_dict()
        self.assertEqual(d["stage_states"]["formalization"], "blocked"); self.assertEqual(d["stage_states"]["execution"], "not_run")
        with self.assertRaises(ValueError): s.confirm(True)
    def test_declared_test_names_match_real_tests(self):
        for m in methods.LIBRARY.values():
            inp = {"npv": REQ["inputs"], "breakeven": {"fixed": "1000", "price": "20", "variable": "10"}, "descriptive_stats": {"values": ["1", "2", "4"], "missing_codes": []},
               "pearson": {"x": ["1","2","3","4","5"], "y": ["2","4","5","4","5"]}, "spearman": {"x": ["1","2","3","4","5"], "y": ["1","4","9","16","10"]},
               "welch_t": {"groups": {"a": ["1","2","3","4","5"], "b": ["2","4","6","8","10"]}}, "mann_whitney": {"groups": {"a": ["1","2","3","4","5"], "b": ["2","4","6","8","10"]}},
               "anova": {"groups": {"a": ["1","2","3","4","5"], "b": ["2","4","6","8","10"], "c": ["1","2","3","4","5"]}}, "kruskal_wallis": {"groups": {"a": ["1","2","3","4","5"], "b": ["2","4","6","8","10"], "c": ["3","1","5","2","4"]}},
               "chi_square": {"table": [[10, 20, 30], [20, 40, 60]]},
               "ols": {"y": ["52","55","61","58","70","72","69","80"], "predictors": {"a": ["1","2","3","4","5","6","7","8"], "b": ["6","7","5","8","6","7","8","6"]}}}[{"ols_robust": "ols"}.get(m.name, m.name)]
            self.assertEqual(tuple(n for n, _ in m.tests(inp, m.impl)), m.test_names)
    def test_malformed_input_blocks_not_crashes(self):
        s = SessionManager().create({**REQ, "inputs": {"rate": "abc", "cashflows": ["1", "2"]}})
        self.assertEqual(s.to_dict()["status"], "blocked")
    def test_missing_field_rejected(self):
        with self.assertRaises(ValueError): SessionManager().create({"method": "npv"})
    def test_skipped_sensitivity_is_not_run(self):
        r = {k: v for k, v in REQ.items() if k != "sensitivity"}
        s = SessionManager().create(r); s.confirm(True); self.assertEqual(s.to_dict()["stage_states"]["sensitivity"], "not_run")

class API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H); cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown(); cls.srv.server_close()
    def call(self, path, body=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r: return r.status, r.read()
        except urllib.error.HTTPError as e: return e.code, e.read()
    def test_full_flow(self):
        c, b = self.call("/api/sessions", REQ); self.assertEqual(c, 201); s = json.loads(b)
        c, b = self.call(f"/api/sessions/{s['id']}/confirm", {}); d = json.loads(b)
        self.assertEqual(d["status"], "delivered"); self.assertIn("USD (5.26)", d["delivery"]["report"])
        c, b = self.call(f"/api/sessions/{s['id']}"); self.assertEqual(json.loads(b)["status"], "delivered")
    def test_errors(self):
        self.assertEqual(self.call("/api/sessions", {"method": "npv"})[0], 400)
        self.assertEqual(self.call("/api/sessions/nope")[0], 404)
    def test_index_served(self):
        c, b = self.call("/"); self.assertEqual(c, 200); self.assertIn(b"Draft work plan", b)
if __name__ == "__main__": unittest.main()
