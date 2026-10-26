import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import cases, ops, versions  # noqa: E402


class OpsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-ops-test-")
        self.previous = {key: os.environ.get(key) for key in ("BP_CASES_DIR", "BP_STATE_DIR", "BP_REQUEST_LOG")}
        os.environ["BP_CASES_DIR"] = os.path.join(self.root, "cases")
        os.environ["BP_STATE_DIR"] = os.path.join(self.root, "state")
        os.environ["BP_REQUEST_LOG"] = os.path.join(self.root, "state", "requests.jsonl")

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self.root, ignore_errors=True)

    def make_case(self):
        case_id, version = versions.append(product_fixtures.make_bundle())
        return case_id, version

    def test_health_reports_the_store_and_the_log(self):
        case_id, version = self.make_case()
        report = ops.health({"sandbox": "on"})
        self.assertEqual(report["format"], "bp-ops/1")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["case_store"]["cases"], 1)
        self.assertEqual(report["case_store"]["versions"], 1)
        self.assertTrue(report["request_log"]["enabled"])
        self.assertEqual(report["sandbox"], "on")

    def test_the_request_log_records_no_query_and_no_body(self):
        self.assertTrue(ops.log_request("POST", "/api/cases/0123456789ab?token=secret", 201, 12.5))
        line = json.loads(open(os.environ["BP_REQUEST_LOG"], encoding="utf-8").read().strip())
        self.assertEqual(line["path"], "/api/cases/0123456789ab")
        self.assertNotIn("secret", json.dumps(line))
        self.assertEqual((line["method"], line["status"]), ("POST", 201))
        self.assertTrue(ops.log_request("GET", "/api/health", 200, 1.0))
        self.assertEqual(len(open(os.environ["BP_REQUEST_LOG"], encoding="utf-8").read().strip().splitlines()), 2)

    def test_the_log_is_off_unless_configured(self):
        os.environ.pop("BP_REQUEST_LOG", None)
        self.assertIsNone(ops.request_log_path())
        self.assertFalse(ops.log_request("GET", "/api/health", 200, 1.0))

    def test_the_log_can_be_disabled(self):
        os.environ["BP_REQUEST_LOG"] = ""
        self.assertFalse(ops.log_request("GET", "/api/health", 200, 1.0))

    def test_backup_and_restore_round_trip(self):
        case_id, _ = self.make_case()
        info = ops.backup()
        self.assertTrue(os.path.isfile(info["archive"]))
        self.assertEqual(info["files"], 1)
        with zipfile.ZipFile(info["archive"]) as bundle: self.assertIn("bp-backup-manifest.json", bundle.namelist())
        shutil.rmtree(os.environ["BP_CASES_DIR"])
        restored = ops.restore(info["archive"])
        self.assertEqual(restored["restored"], 1)
        self.assertEqual(versions.get(case_id, 1)["bundle"]["title"], "Should we invest?")

    def test_restore_refuses_to_overwrite_existing_cases(self):
        self.make_case()
        info = ops.backup()
        with self.assertRaises(ValueError) as caught:
            ops.restore(info["archive"])
        self.assertIn("already exist", str(caught.exception))
        restored = ops.restore(info["archive"], overwrite=True)
        self.assertTrue(restored["overwrote_existing"])
        self.assertEqual(len(cases.list_cases()), 0)  # versioned cases are not flat cases

    def test_a_traversing_or_non_json_archive_is_refused(self):
        archive = os.path.join(self.root, "evil.zip")
        with zipfile.ZipFile(archive, "w") as bundle: bundle.writestr("../escape.json", "{}")
        with self.assertRaises(ValueError):
            ops.restore(archive)
        archive2 = os.path.join(self.root, "evil2.zip")
        with zipfile.ZipFile(archive2, "w") as bundle: bundle.writestr("note.txt", "hello")
        with self.assertRaises(ValueError):
            ops.restore(archive2)

    def test_a_corrupt_archive_is_refused(self):
        path = os.path.join(self.root, "broken.zip")
        open(path, "wb").write(b"not a zip")
        with self.assertRaises(ValueError):
            ops.restore(path)

    def test_list_backups_reports_the_archives(self):
        ops.backup()
        rows = ops.list_backups()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["archive"].endswith(".zip"))


if __name__ == "__main__":
    unittest.main()
