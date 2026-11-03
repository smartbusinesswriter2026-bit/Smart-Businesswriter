"""The statements routes on the case route: solve, read, export, replay, and the failing cases."""

import ast
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp.product import api, statements  # noqa: E402

TB = ("The following trial balance was extracted at 31 December 2026.\n"
      "Cash 7,000\nTrade receivables 3,000\nCapital 10,000")
BAD = ("The following trial balance was extracted at 31 December 2026.\n"
       "Cash 5,000\nCapital 4,500")
PRODUCT_DIR = os.path.join(ROOT, "src", "bp", "product")


def attach():
    statements.attach_core(
        solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
        diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
            {"journal": None, "trial_balance": rows, "places": places}),
        ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
        dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs))


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-statements-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root
        attach()

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def post(self, text, **extra):
        body = {"instruction": text}
        body.update(extra)
        return api.handle("POST", "/api/cases/statements", body)

    def test_the_collection_solves_stores_and_returns_the_record(self):
        status, record = self.post(TB)
        self.assertEqual(status, 201, record)
        self.assertTrue(record["solved"])
        self.assertEqual(len(record["id"]), 12)
        status, again = api.handle("GET", "/api/cases/statements/" + record["id"])
        self.assertEqual(status, 200)
        self.assertEqual(again["plan_hash"], record["plan_hash"])
        self.assertEqual(again["format"], "bp-statements/1")

    def test_an_instruction_the_tile_cannot_read_is_a_named_refusal(self):
        status, payload = self.post("hello there")
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_a_problem_that_does_not_balance_is_stored_with_its_diagnosis(self):
        status, payload = self.post(BAD)
        self.assertEqual(status, 422)
        self.assertFalse(payload["solved"])
        self.assertEqual(payload["diagnosis"]["difference"], "500")
        self.assertIsNone(payload["statements"])

    def test_the_export_is_the_statements_only_by_default(self):
        _status, record = self.post(TB)
        status, payload = api.handle("POST", "/api/cases/statements/" + record["id"] + "/export", {})
        self.assertEqual(status, 200)
        self.assertEqual(payload["view"], "statements_only")
        self.assertIn("BALANCE SHEET", payload["text"])
        self.assertNotIn("JOURNAL", payload["text"])
        self.assertTrue(payload["filename"].endswith(".txt"))

    def test_the_working_export_carries_the_journal(self):
        _status, record = self.post(TB)
        status, payload = api.handle("POST", "/api/cases/statements/" + record["id"] + "/export",
                                     {"format": "working"})
        self.assertEqual(status, 200)
        self.assertIn("JOURNAL", payload["text"])

    def test_a_refused_record_cannot_be_exported(self):
        _status, record = self.post(BAD)
        status, payload = api.handle("POST", "/api/cases/statements/" + record["id"] + "/export", {})
        self.assertEqual(status, 409)
        self.assertIn("there is nothing to export", payload["error"])

    def test_an_unknown_record_is_not_found_and_a_bad_verb_is_refused(self):
        self.assertEqual(api.handle("GET", "/api/cases/statements/0123456789ab")[0], 404)
        self.assertEqual(api.handle("DELETE", "/api/cases/statements/0123456789ab")[0], 405)
        self.assertEqual(api.handle("GET", "/api/cases/statements/not-an-id")[0], 404)

    def test_the_replay_route_reproduces_the_record(self):
        _status, record = self.post(TB)
        status, payload = api.handle("POST", "/api/cases/statements/" + record["id"] + "/replay", {})
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["record_hash_match"])

    def test_the_collection_lists_the_record(self):
        _status, record = self.post(TB)
        status, payload = api.handle("GET", "/api/cases/statements")
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in payload["records"]], [record["id"]])

    def test_no_input_shape_produces_a_server_error(self):
        """Every refusal is a 4xx: a crash is not something a student can act on."""
        shapes = ["hello there", "",
                  "Trial balance at 31 December 2026.\nCash 5,000\nCapital 5,000\nCash 2,000",
                  "Trial balance at 31 December 2026.\nCash 5,000 7,000\nCapital 5,000 7,000",
                  "Trial balance at 31 December 2026.\nCash 5,000\nCapital 4,000",
                  "Prepare the consolidated statements. Cash 5,000. Capital 5,000.",
                  "Trial balance at 31 December 2026.\nCash\nCapital",
                  "Cash 5,000"]
        for text in shapes:
            with self.subTest(text=text[:40]):
                status, payload = self.post(text)
                self.assertLess(status, 500, "%s produced %s: %s" % (text[:40], status, payload))
                # a 400 carries "error"; a 422 is a refusal record, which carries "refusal" and the
                # diagnosis.  Either way the student is told why.
                self.assertTrue(payload.get("error") or payload.get("refusal"),
                                "a refusal must say why: %s" % status)

    def test_the_statements_modules_import_no_frozen_core_module(self):
        for name in ("statements.py", "statements_verify.py", "statements_council.py"):
            with open(os.path.join(PRODUCT_DIR, name), encoding="utf-8") as stream:
                tree = ast.parse(stream.read(), filename=name)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and not node.level:
                    module = node.module or ""
                    self.assertFalse(module == "bp" or module.startswith("bp."),
                                     name + " imports the frozen core (" + module + ")")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(alias.name == "bp" or alias.name.startswith("bp."),
                                         name + " imports the frozen core (" + alias.name + ")")


if __name__ == "__main__":
    unittest.main()
