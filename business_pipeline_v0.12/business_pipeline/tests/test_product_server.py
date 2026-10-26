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
        cls.prev = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = cls.dir
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()
        if cls.prev is None: os.environ.pop("BP_CASES_DIR", None)
        else: os.environ["BP_CASES_DIR"] = cls.prev
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

    def test_existing_routes_are_unchanged(self):
        status, presets = self.call("GET", "/api/presets")
        self.assertEqual(status, 200); self.assertIn("npv", presets); self.assertIn("dcf", presets)
        self.assertEqual(self.call("DELETE", "/api/presets")[0], 404)


if __name__ == "__main__":
    unittest.main()
