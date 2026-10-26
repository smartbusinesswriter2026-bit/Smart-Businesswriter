"""The local durable case store (product layer).

Stdlib only, no network, no third-party import.  The store keeps one JSON
bundle per case, writes atomically, refuses ids that are not 12 lowercase hex
characters, refuses path traversal, and refuses to load a corrupt bundle.
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
from bp.product import cases  # noqa: E402


class CaseStoreTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-cases-test-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    # -- round trip ---------------------------------------------------------
    def test_saved_case_loads_back_unchanged(self):
        bundle = product_fixtures.make_bundle()
        case_id = cases.save(bundle)
        self.assertRegex(case_id, r"^[0-9a-f]{12}$")
        stored = cases.load(case_id)
        self.assertEqual(stored["format"], "bp-case/1")
        self.assertEqual(stored["id"], case_id)
        self.assertEqual(stored["title"], bundle["title"])
        self.assertEqual(stored["session"], bundle["session"])
        self.assertEqual(stored["delivery"], bundle["delivery"])
        self.assertEqual(stored["reperform"], bundle["reperform"])
        self.assertTrue(stored["created_at"].endswith("+00:00"))

    def test_the_file_on_disk_is_the_document_that_comes_back(self):
        case_id = cases.save(product_fixtures.make_bundle())
        path = os.path.join(self.root, case_id + ".json")
        with open(path, encoding="utf-8") as stream:
            on_disk = json.load(stream)
        self.assertEqual(on_disk, cases.load(case_id))

    def test_stored_numbers_and_strings_are_not_rounded_or_rewritten(self):
        bundle = product_fixtures.make_bundle()
        case_id = cases.save(bundle)
        stored = cases.load(case_id)
        self.assertIn("50.00", stored["delivery"]["report"])
        self.assertIn("0.10", stored["delivery"]["report"])
        self.assertEqual(stored["reperform"]["outputs"]["npv"], "50.00")
        self.assertEqual(stored["delivery"]["appendix"]["artifacts"][0][0], "npv")

    def test_a_supplied_id_is_kept_and_a_generated_one_is_used_otherwise(self):
        given = "0123456789ab"
        self.assertEqual(cases.save(product_fixtures.make_bundle(id=given)), given)
        self.assertNotEqual(cases.save(product_fixtures.make_bundle()), given)

    def test_saving_twice_leaves_one_file_per_case(self):
        cases.save(product_fixtures.make_bundle())
        cases.save(product_fixtures.make_bundle())
        self.assertEqual(len(cases.list_cases()), 2)

    # -- refusals -----------------------------------------------------------
    def test_a_bundle_missing_required_keys_is_refused(self):
        bundle = product_fixtures.make_bundle()
        del bundle["tier"]
        with self.assertRaises(ValueError) as caught:
            cases.save(bundle)
        self.assertIn("tier", str(caught.exception))

    def test_an_unsupported_format_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            cases.save(product_fixtures.make_bundle(format="bp-case/99"))
        self.assertIn("format", str(caught.exception))

    def test_a_non_object_bundle_is_refused(self):
        with self.assertRaises(ValueError):
            cases.save(["not", "a", "bundle"])

    def test_bad_ids_are_refused_everywhere(self):
        for bad in ["", "short", "ABCDEF123456", "0123456789AB", "../escape", "0123456789ab/../..",
                    "../../etc/passwd", "0123456789ab.json", None, 12, ["0123456789ab"]]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                cases.load(bad)
            with self.assertRaises(ValueError, msg=repr(bad)):
                cases.delete(bad)

    def test_path_traversal_cannot_leave_the_case_directory(self):
        with self.assertRaises(ValueError):
            cases.load("..%2f..%2fetc")
        with self.assertRaises(ValueError):
            cases.save(product_fixtures.make_bundle(id="../../evil"))

    def test_a_corrupt_file_refuses_to_load(self):
        case_id = cases.save(product_fixtures.make_bundle())
        path = os.path.join(self.root, case_id + ".json")
        with open(path, "w", encoding="utf-8") as stream:
            stream.write("{ this is not json")
        with self.assertRaises(ValueError) as caught:
            cases.load(case_id)
        self.assertIn(case_id, str(caught.exception))

    def test_a_bundle_missing_required_keys_on_disk_refuses_to_load(self):
        case_id = cases.save(product_fixtures.make_bundle())
        path = os.path.join(self.root, case_id + ".json")
        with open(path, encoding="utf-8") as stream:
            document = json.load(stream)
        del document["delivery"]
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(document, stream)
        with self.assertRaises(ValueError) as caught:
            cases.load(case_id)
        self.assertIn("delivery", str(caught.exception))

    def test_an_unknown_id_is_reported_as_not_found(self):
        with self.assertRaises(cases.CaseNotFound):
            cases.load("0123456789ab")

    # -- listing and deleting ----------------------------------------------
    def test_list_cases_returns_the_stored_summaries(self):
        case_id = cases.save(product_fixtures.make_bundle())
        listed = cases.list_cases()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["id"], case_id)
        self.assertEqual(listed[0]["title"], "Should we invest?")
        self.assertEqual(listed[0]["method"], "npv")
        self.assertEqual(listed[0]["tier"], "T1")
        self.assertFalse(listed[0]["corrupt"])

    def test_list_cases_is_empty_when_nothing_is_stored(self):
        self.assertEqual(cases.list_cases(), [])

    def test_a_corrupt_file_is_visible_in_the_listing(self):
        case_id = cases.save(product_fixtures.make_bundle())
        with open(os.path.join(self.root, case_id + ".json"), "w", encoding="utf-8") as stream:
            stream.write("not json at all")
        listed = cases.list_cases()
        self.assertEqual(len(listed), 1)
        self.assertTrue(listed[0]["corrupt"])
        self.assertIn("error", listed[0])

    def test_delete_removes_the_case(self):
        case_id = cases.save(product_fixtures.make_bundle())
        self.assertTrue(cases.delete(case_id))
        self.assertEqual(cases.list_cases(), [])
        with self.assertRaises(cases.CaseNotFound):
            cases.load(case_id)
        with self.assertRaises(cases.CaseNotFound):
            cases.delete(case_id)

    # -- mechanics ----------------------------------------------------------
    def test_writes_leave_no_temporary_files_behind(self):
        cases.save(product_fixtures.make_bundle())
        self.assertEqual(sorted(os.listdir(self.root)), sorted(
            name for name in os.listdir(self.root) if name.endswith(".json")))
        self.assertFalse([name for name in os.listdir(self.root) if name.startswith(".tmp")])

    def test_the_store_writes_where_it_was_told(self):
        self.assertEqual(str(cases.cases_dir()), str(self.root))

    def test_without_the_environment_variable_the_store_uses_the_repo_cases_folder(self):
        os.environ.pop("BP_CASES_DIR", None)
        default = cases.cases_dir()
        self.assertEqual(default.name, "cases")
        self.assertEqual(default.parent.name, "business_pipeline")
        self.assertTrue(default.is_absolute())

    def test_a_case_id_is_twelve_lowercase_hex_characters(self):
        case_id = cases.save(product_fixtures.make_bundle())
        self.assertEqual(len(case_id), 12)
        self.assertTrue(all(character in "0123456789abcdef" for character in case_id))


if __name__ == "__main__":
    unittest.main()
