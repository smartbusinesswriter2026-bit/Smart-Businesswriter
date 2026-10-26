import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import api  # noqa: E402


def versioned(npv="50.00", outputs_hash="sha256:out-def"):
    bundle = product_fixtures.make_bundle(outputs_hash=outputs_hash)
    bundle["reperform"]["outputs"] = {"npv": npv}
    return bundle


class ProductRouteTest(unittest.TestCase):
    """The version/compare/sign-off routes are reachable through the same pure dispatch."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-product-routes-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def make_case(self):
        status, metadata = api.handle("POST", "/api/cases/0123456789ab/versions", versioned())
        self.assertEqual(status, 201)
        build = versioned("60.00", "sha256:out-2")
        status, second = api.handle("POST", "/api/cases/0123456789ab/versions", build)
        self.assertEqual(status, 201)
        self.assertEqual(second["version"], 2)
        return metadata["case_id"]

    def test_versions_can_be_appended_listed_and_read(self):
        case_id = self.make_case()
        status, listed = api.handle("GET", "/api/cases/%s/versions" % case_id)
        self.assertEqual(status, 200)
        self.assertEqual([entry["version"] for entry in listed["versions"]], [1, 2])
        status, document = api.handle("GET", "/api/cases/%s/versions/1" % case_id)
        self.assertEqual(status, 200)
        self.assertEqual(document["bundle"]["reperform"]["outputs"]["npv"], "50.00")
        self.assertEqual(api.handle("GET", "/api/cases/%s/versions/9" % case_id)[0], 404)

    def test_compare_returns_the_stored_values(self):
        case_id = self.make_case()
        status, result = api.handle("GET", "/api/cases/%s/compare" % case_id)
        self.assertEqual(status, 200)
        self.assertEqual(result["rows"][0]["values"], {"1": "50.00", "2": "60.00"})
        status, selected = api.handle("GET", "/api/cases/%s/compare?versions=2" % case_id)
        self.assertEqual(status, 422)  # one version is not a comparison
        status, bad = api.handle("GET", "/api/cases/%s/compare?versions=a,b" % case_id)
        self.assertEqual(status, 422)

    def test_signoff_round_trip(self):
        case_id = self.make_case()
        body = {"version": 1, "reviewer": "A. Reviewer", "role": "analyst", "decision": "reviewed"}
        status, record = api.handle("POST", "/api/cases/%s/signoff" % case_id, body)
        self.assertEqual(status, 201)
        self.assertEqual(record["signature_text"], __import__("bp.product.signoff", fromlist=["SIGNATURE_TEXT"]).SIGNATURE_TEXT)
        status, listed = api.handle("GET", "/api/cases/%s/signoff?version=1" % case_id)
        self.assertEqual(status, 200)
        self.assertEqual(len(listed["signoffs"]), 1)
        self.assertEqual(api.handle("POST", "/api/cases/%s/signoff" % case_id, {"reviewer": "X"})[0], 422)
        self.assertEqual(api.handle("POST", "/api/cases/%s/signoff" % case_id, {"version": 9, "reviewer": "X"})[0], 404)

    def test_render_and_export_routes(self):
        case_id = "0123456789ab"
        bundle = versioned()
        bundle["delivery"]["appendix"]["artifacts"] = [["npv", ["npv", "annual", "entity", "base"], "npv formula"]]
        self.assertEqual(api.handle("POST", "/api/cases/%s/versions" % case_id, bundle)[0], 201)
        chart = {"format": "bp-chart/1", "kind": "bar", "title": "Capital budgeting",
                 "series": [{"label": "Net present value", "artifact": "npv"}]}
        status, rendered = api.handle("POST", "/api/cases/%s/render" % case_id, {"chart": chart})
        self.assertEqual(status, 200); self.assertIn("<svg", rendered["svg"]); self.assertIn("50.00", rendered["svg"])
        self.assertEqual(api.handle("POST", "/api/cases/%s/render" % case_id,
                                    {"chart": {**chart, "title": "Year 2025"}})[0], 422)
        self.assertEqual(api.handle("POST", "/api/cases/%s/render" % case_id, {})[0], 422)
        with tempfile.TemporaryDirectory() as folder:
            for kind, suffix in (("csv", "csv"), ("spreadsheetml", "xml"), ("html", "html")):
                destination = os.path.join(folder, "case." + suffix)
                status, result = api.handle("POST", "/api/cases/%s/export" % case_id,
                                            {"kind": kind, "destination": destination})
                self.assertEqual(status, 200, result)
                self.assertTrue(os.path.isfile(destination), kind)
            self.assertEqual(api.handle("POST", "/api/cases/%s/export" % case_id,
                                        {"kind": "pdf", "destination": os.path.join(folder, "x.pdf")})[0], 422)

    def test_deleting_a_case_removes_its_versions(self):
        case_id = self.make_case()
        status, deleted = api.handle("DELETE", "/api/cases/%s" % case_id)
        self.assertEqual((status, deleted), (200, {"deleted": case_id}))
        self.assertEqual(api.handle("GET", "/api/cases/%s/versions" % case_id)[0], 200)
        self.assertEqual(api.handle("GET", "/api/cases/%s" % case_id)[0], 404)


if __name__ == "__main__":
    unittest.main()
