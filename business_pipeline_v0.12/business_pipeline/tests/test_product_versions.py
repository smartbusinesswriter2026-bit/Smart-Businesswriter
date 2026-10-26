import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import versions  # noqa: E402


def versioned(npv="50.00", outputs_hash=None, report=None, method_version=None, **overrides):
    """A realistic bundle whose recorded npv output can be varied per version."""
    bundle = product_fixtures.make_bundle(**overrides)
    bundle["reperform"]["outputs"] = {"npv": npv}
    if outputs_hash is not None:
        bundle["outputs_hash"] = outputs_hash
    if report is not None:
        bundle["delivery"]["report"] = report
    if method_version is not None:
        bundle["delivery"]["appendix"]["method"]["version"] = method_version
    return bundle


class VersionStoreTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-versions-test-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_appending_versions_never_overwrites_an_older_one(self):
        case_id, first = versions.append(versioned(npv="50.00", outputs_hash="sha256:out-1"))
        self.assertEqual(first, 1)
        case_id, second = versions.append(versioned(npv="60.00", outputs_hash="sha256:out-2"), case_id)
        self.assertEqual((case_id, second), (case_id, 2))
        self.assertEqual(versions.get(case_id, 1)["bundle"]["reperform"]["outputs"]["npv"], "50.00")
        self.assertEqual(versions.latest(case_id)["version"], 2)
        self.assertEqual([entry["version"] for entry in versions.list_versions(case_id)], [1, 2])
        self.assertEqual([entry["outputs_hash"] for entry in versions.list_versions(case_id)],
                         ["sha256:out-1", "sha256:out-2"])

    def test_each_version_is_immutable_on_disk(self):
        case_id, _ = versions.append(versioned())
        path = os.path.join(self.root, case_id, "v001.json")
        before = open(path, encoding="utf-8").read()
        versions.append(versioned(npv="60.00"), case_id)
        self.assertEqual(open(path, encoding="utf-8").read(), before)

    def test_a_missing_version_refuses_clearly(self):
        case_id, _ = versions.append(versioned())
        with self.assertRaises(versions.VersionNotFound):
            versions.get(case_id, 2)
        with self.assertRaises(versions.VersionNotFound):
            versions.get("0123456789ab", 1)
        with self.assertRaises(versions.VersionNotFound):
            versions.latest("0123456789ab")

    def test_bad_ids_and_versions_are_refused(self):
        for bad in ("", "short", "ABCDEF123456", "../escape", "0123456789ab/../.."):
            with self.assertRaises(ValueError):
                versions.append(versioned(), bad)
        case_id, _ = versions.append(versioned())
        for bad in (0, -1, True, "1", 1.5):
            with self.assertRaises(ValueError):
                versions.get(case_id, bad)

    def test_corrupted_or_tampered_versions_are_detected(self):
        case_id, _ = versions.append(versioned())
        path = os.path.join(self.root, case_id, "v001.json")
        document = json.load(open(path, encoding="utf-8"))
        document["bundle"]["reperform"]["outputs"]["npv"] = "999.99"
        json.dump(document, open(path, "w", encoding="utf-8"))
        with self.assertRaises(versions.VersionCorrupt):
            versions.get(case_id, 1)
        self.assertTrue(versions.list_versions(case_id)[0]["corrupt"])

    def test_a_legacy_flat_case_is_adopted_as_version_one(self):
        from bp.product import cases
        case_id = cases.save(versioned())
        case_id, version = versions.append(versioned(npv="60.00"), case_id)
        self.assertEqual(version, 2)
        self.assertEqual(versions.get(case_id, 1)["bundle"]["reperform"]["outputs"]["npv"], "50.00")
        self.assertEqual(versions.latest(case_id)["version"], 2)

    def test_delete_removes_the_whole_chain(self):
        case_id, _ = versions.append(versioned())
        versions.append(versioned(npv="60.00"), case_id)
        self.assertTrue(versions.delete_case(case_id))
        self.assertFalse(os.path.exists(os.path.join(self.root, case_id)))
        self.assertEqual(versions.list_versions(case_id), [])


if __name__ == "__main__":
    unittest.main()
