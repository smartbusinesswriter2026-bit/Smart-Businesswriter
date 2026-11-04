"""The additive case-store route dispatch (product layer).

Pure dispatch: the product layer never edits the frozen server, so these
tests call `handle()` directly.  No route computes anything - a stored bundle
comes back exactly as it was stored.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import api  # noqa: E402


class CaseApiTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-cases-api-test-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def _post(self, bundle=None):
        return api.handle("POST", "/api/cases", product_fixtures.make_bundle() if bundle is None else bundle)

    # -- listing ------------------------------------------------------------
    def test_get_cases_lists_the_stored_cases(self):
        status, payload = self._post()
        self.assertEqual(status, 201)
        status, payload = api.handle("GET", "/api/cases")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["cases"]), 1)
        self.assertEqual(payload["cases"][0]["id"], json.loads(json.dumps(payload["cases"][0]))["id"])

    def test_get_cases_is_empty_when_nothing_is_stored(self):
        status, payload = api.handle("GET", "/api/cases")
        self.assertEqual(status, 200)
        self.assertEqual(payload["cases"], [])

    # -- storing and reading ------------------------------------------------
    def test_post_stores_the_bundle_and_returns_it(self):
        bundle = product_fixtures.make_bundle()
        status, payload = self._post(bundle)
        self.assertEqual(status, 201)
        self.assertRegex(payload["id"], r"^[0-9a-f]{12}$")
        self.assertEqual(payload["delivery"]["report"], bundle["delivery"]["report"])
        self.assertEqual(payload["session"], bundle["session"])

    def test_post_stores_exactly_what_it_is_given(self):
        bundle = product_fixtures.make_bundle()
        status, stored = self._post(bundle)
        self.assertEqual(status, 201)
        path = os.path.join(self.root, stored["id"] + ".json")
        with open(path, encoding="utf-8") as stream:
            on_disk = json.load(stream)
        self.assertEqual(on_disk["delivery"], bundle["delivery"])
        self.assertEqual(on_disk["session"], bundle["session"])
        self.assertEqual(on_disk["reperform"], bundle["reperform"])
        self.assertEqual(on_disk["spec_hash"], bundle["spec_hash"])

    def test_get_returns_the_stored_bundle_verbatim(self):
        status, stored = self._post()
        status, payload = api.handle("GET", "/api/cases/" + stored["id"])
        self.assertEqual(status, 200)
        path = os.path.join(self.root, stored["id"] + ".json")
        with open(path, encoding="utf-8") as stream:
            on_disk = json.load(stream)
        self.assertEqual(payload, on_disk)
        self.assertEqual(payload["delivery"]["report"], product_fixtures.REPORT)

    def test_get_does_not_recompute_anything(self):
        status, stored = self._post()
        status, payload = api.handle("GET", "/api/cases/" + stored["id"])
        self.assertIn("50.00", payload["delivery"]["report"])
        self.assertEqual(payload["reperform"]["outputs"]["npv"], "50.00")

    # -- deleting -----------------------------------------------------------
    def test_delete_removes_the_case(self):
        status, stored = self._post()
        status, payload = api.handle("DELETE", "/api/cases/" + stored["id"])
        self.assertEqual(status, 200)
        self.assertEqual(payload["deleted"], stored["id"])
        status, payload = api.handle("GET", "/api/cases/" + stored["id"])
        self.assertEqual(status, 404)

    # -- refusals -----------------------------------------------------------
    def test_an_unknown_case_is_not_found(self):
        status, payload = api.handle("GET", "/api/cases/0123456789ab")
        self.assertEqual(status, 404)
        self.assertIn("error", payload)
        status, payload = api.handle("DELETE", "/api/cases/0123456789ab")
        self.assertEqual(status, 404)

    def test_an_invalid_id_is_refused(self):
        for bad in ["nope", "ABCDEF123456", "../escape"]:
            status, payload = api.handle("GET", "/api/cases/" + bad)
            self.assertEqual(status, 422, bad)
            self.assertIn("error", payload)

    def test_an_invalid_body_is_refused(self):
        status, payload = api.handle("POST", "/api/cases", {"title": "only a title"})
        self.assertEqual(status, 422)
        self.assertIn("error", payload)
        status, payload = api.handle("POST", "/api/cases", "not an object")
        self.assertEqual(status, 422)

    def test_an_unknown_route_is_not_found(self):
        status, payload = api.handle("GET", "/api/case")
        self.assertEqual(status, 404)
        status, payload = api.handle("GET", "/api/other/thing")
        self.assertEqual(status, 404)

    def test_a_wrong_method_is_not_allowed(self):
        status, payload = api.handle("PUT", "/api/cases", {})
        self.assertEqual(status, 405)
        self.assertIn("error", payload)
        status, payload = api.handle("POST", "/api/cases/0123456789ab", {})
        self.assertEqual(status, 405)

    def test_a_trailing_slash_and_query_string_are_tolerated(self):
        status, stored = self._post()
        status, payload = api.handle("GET", "/api/cases/?limit=10")
        self.assertEqual(status, 200)
        status, payload = api.handle("GET", "/api/cases/" + stored["id"] + "/")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
