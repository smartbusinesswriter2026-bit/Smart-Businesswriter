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
from bp.product import signoff, versions  # noqa: E402


def versioned(npv="50.00"):
    bundle = product_fixtures.make_bundle()
    bundle["reperform"]["outputs"] = {"npv": npv}
    return bundle


class SignoffTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-signoff-test-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_records_the_owner_approved_wording_and_the_signed_hashes(self):
        case_id, _ = versions.append(versioned())
        record = signoff.record(case_id, 1, "A. Reviewer", role="analyst", scope="npv case", decision="reviewed")
        self.assertEqual(record["signature_text"], signoff.SIGNATURE_TEXT)
        self.assertEqual(record["reviewer"], {"name": "A. Reviewer", "role": "analyst"})
        self.assertEqual(record["decision"], "reviewed")
        self.assertTrue(record["spec_hash"] and record["outputs_hash"] and record["bundle_hash"])
        listed = signoff.list_for(case_id, 1)
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["integrity"], {"checked": True, "matches": True})

    def test_signoffs_are_append_only(self):
        case_id, _ = versions.append(versioned())
        first = signoff.record(case_id, 1, "A. Reviewer")
        path = os.path.join(self.root, case_id, "signoff", "v001-001.json")
        before = open(path, encoding="utf-8").read()
        signoff.record(case_id, 1, "B. Reviewer", decision="not_reviewed")
        self.assertEqual(open(path, encoding="utf-8").read(), before)
        self.assertEqual(len(signoff.list_for(case_id, 1)), 2)

    def test_blank_reviewer_unknown_decision_and_missing_version_are_refused(self):
        case_id, _ = versions.append(versioned())
        for reviewer in ("", "   ", None, 5):
            with self.assertRaises(ValueError):
                signoff.record(case_id, 1, reviewer)
        with self.assertRaises(ValueError):
            signoff.record(case_id, 1, "A. Reviewer", decision="approved")
        with self.assertRaises(versions.VersionNotFound):
            signoff.record(case_id, 7, "A. Reviewer")

    def test_a_tampered_version_makes_the_signoff_not_match(self):
        case_id, _ = versions.append(versioned())
        signoff.record(case_id, 1, "A. Reviewer")
        path = os.path.join(self.root, case_id, "v001.json")
        document = json.load(open(path, encoding="utf-8"))
        document["bundle"]["reperform"]["outputs"]["npv"] = "999.99"
        json.dump(document, open(path, "w", encoding="utf-8"))
        listed = signoff.list_for(case_id, 1)
        self.assertFalse(listed[0]["integrity"]["matches"])
        with self.assertRaises(versions.VersionCorrupt):
            signoff.record(case_id, 1, "C. Reviewer")

    def test_summary_reports_review_state_per_version(self):
        case_id, _ = versions.append(versioned())
        versions.append(versioned("60.00"), case_id)
        signoff.record(case_id, 1, "A. Reviewer")
        summary = signoff.summary(case_id)
        self.assertEqual([item["version"] for item in summary], [1, 2])
        self.assertEqual([item["signoffs"] for item in summary], [1, 0])
        self.assertEqual([item["reviewed"] for item in summary], [True, False])


if __name__ == "__main__":
    unittest.main()
