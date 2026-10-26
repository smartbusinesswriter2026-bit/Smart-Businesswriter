import sys, os, json, threading, tempfile, unittest, urllib.request, urllib.error
sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402
from bp import server  # noqa: E402


class ProductRoutes(unittest.TestCase):
    """The review wiring: the product dispatch is reachable through the frozen server (B-080/B-085).

    The routes are additive and must not change any existing route. Every number they return is the
    stored value, never a recomputation.
    """

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="bp-server-cases-")
        cls.prev = {key: os.environ.get(key) for key in ("BP_CASES_DIR", "BP_STATE_DIR", "BP_REQUEST_LOG")}
        os.environ["BP_CASES_DIR"] = cls.dir
        os.environ["BP_STATE_DIR"] = os.path.join(cls.dir, "state")
        os.environ["BP_REQUEST_LOG"] = os.path.join(cls.dir, "state", "requests.jsonl")
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()
        for key, value in cls.prev.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        import shutil
        shutil.rmtree(cls.dir, ignore_errors=True)

    def call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as stream: return stream.status, json.loads(stream.read())
        except urllib.error.HTTPError as error: return error.code, json.loads(error.read())

    def test_case_routes_round_trip_over_http(self):
        bundle = product_fixtures.make_bundle()
        status, stored = self.call("POST", "/api/cases", bundle)
        self.assertEqual(status, 201); case_id = stored["id"]
        status, listed = self.call("GET", "/api/cases")
        self.assertEqual(status, 200); self.assertEqual([item["id"] for item in listed["cases"]], [case_id])
        status, loaded = self.call("GET", "/api/cases/" + case_id)
        self.assertEqual(status, 200); self.assertEqual(loaded["id"], case_id)
        self.assertEqual(loaded["delivery"]["report"], bundle["delivery"]["report"])
        status, deleted = self.call("DELETE", "/api/cases/" + case_id)
        self.assertEqual((status, deleted), (200, {"deleted": case_id}))
        self.assertEqual(self.call("GET", "/api/cases/" + case_id)[0], 404)

    def test_unknown_and_malformed_cases_are_refused(self):
        self.assertEqual(self.call("GET", "/api/cases/" + "0" * 12)[0], 404)
        self.assertEqual(self.call("GET", "/api/cases/BAD")[0], 422)
        self.assertEqual(self.call("POST", "/api/cases", {})[0], 422)
        self.assertEqual(self.call("POST", "/api/cases", {"format": "bp-case/1"})[0], 422)

    def test_version_compare_and_signoff_routes_are_reachable_over_http(self):
        import uuid
        case_id = uuid.uuid4().hex[:12]
        bundle = product_fixtures.make_bundle()
        status, first = self.call("POST", "/api/cases/%s/versions" % case_id, bundle)
        self.assertEqual((status, first["version"]), (201, 1))
        status, second = self.call("POST", "/api/cases/%s/versions" % case_id, bundle)
        self.assertEqual((status, second["version"]), (201, 2))
        status, versions = self.call("GET", "/api/cases/%s/versions" % case_id)
        self.assertEqual(status, 200); self.assertEqual([v["version"] for v in versions["versions"]], [1, 2])
        status, comparison = self.call("GET", "/api/cases/%s/compare?versions=1,2" % case_id)
        self.assertEqual(status, 200); self.assertEqual(comparison["rows"][0]["values"], {"1": "50.00", "2": "50.00"})
        status, record = self.call("POST", "/api/cases/%s/signoff" % case_id, {"version": 1, "reviewer": "A. Reviewer"})
        self.assertEqual(status, 201); self.assertEqual(record["decision"], "reviewed")
        status, listed = self.call("GET", "/api/cases/%s/signoff?version=1" % case_id)
        self.assertEqual(status, 200); self.assertEqual(len(listed["signoffs"]), 1)

    def test_subject_and_calculator_routes_are_reachable_over_http(self):
        status, gallery = self.call("GET", "/api/cases/subjects")
        self.assertEqual(status, 200); self.assertEqual(len(gallery["subjects"]), 9)
        status, page = self.call("GET", "/api/cases/subjects/finance")
        self.assertEqual(status, 200); self.assertIn("npv", {tool["method"] for tool in page["tools"]})
        status, calculator = self.call("GET", "/api/cases/calculator")
        self.assertEqual(status, 200); self.assertEqual(calculator["format"], "bp-calculator/1")
        self.assertEqual(self.call("GET", "/api/cases/subjects/astrology")[0], 404)

    def test_health_backup_and_restore_routes(self):
        case_id = "0123456789ab"
        self.assertEqual(self.call("POST", "/api/cases/%s/versions" % case_id, product_fixtures.make_bundle())[0], 201)
        status, health = self.call("GET", "/api/health")
        self.assertEqual(status, 200); self.assertEqual(health["format"], "bp-ops/1")
        self.assertIn("sandbox", health); self.assertGreaterEqual(health["case_store"]["versions"], 1)
        status, info = self.call("POST", "/api/cases/backup", {})
        self.assertEqual(status, 201); self.assertTrue(os.path.isfile(info["archive"]))
        status, listed = self.call("GET", "/api/cases/backups")
        self.assertEqual(status, 200); self.assertTrue(any(row["archive"] == info["archive"] for row in listed["backups"]))
        self.assertEqual(self.call("POST", "/api/cases/restore", {})[0], 422)
        status, restored = self.call("POST", "/api/cases/restore", {"archive": info["archive"], "overwrite": True})
        self.assertEqual(status, 200, restored); self.assertGreaterEqual(restored["restored"], 1)

    def test_the_request_log_records_no_case_content(self):
        body = product_fixtures.make_bundle()
        self.call("POST", "/api/cases", body)
        log = os.environ["BP_REQUEST_LOG"]
        self.assertTrue(os.path.isfile(log), "the request log was not written")
        text = open(log, encoding="utf-8").read()
        self.assertIn('"path": "/api/cases"', text)
        self.assertNotIn("The net present value is 50.00", text)     # no report text
        self.assertNotIn("cashflows", text)                          # no input body
        self.assertNotIn('"title"', text)                            # no case metadata

    def test_existing_routes_are_unchanged(self):
        status, presets = self.call("GET", "/api/presets")
        self.assertEqual(status, 200); self.assertIn("npv", presets); self.assertIn("dcf", presets)
        self.assertEqual(self.call("DELETE", "/api/presets")[0], 404)


if __name__ == "__main__":
    unittest.main()
