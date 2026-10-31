"""Tests for the R2 planning, verification and record tools.

Standard library only. Run with:

    python corpus-db/build/test_r2_plan.py

Every test here pins something that went wrong at least once. The case test
pins the defect that made the first sync move 18 of 19 documents: Windows
resolves `Exploring_business.pdf` and `exploring_business.pdf` to one file,
and an R2 key and an rclone filter do not.
"""

import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import r2_plan  # noqa: E402

SCHEMA = """
CREATE TABLE documents (
  doc_id TEXT PRIMARY KEY,
  title TEXT,
  local_path TEXT,
  r2_key TEXT,
  sha256 TEXT,
  pages_total INTEGER
);
CREATE TABLE pages (doc_id TEXT, pdf_page INTEGER);
"""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


class R2PlanTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="r2plan-")
        self.library = os.path.join(self.root, "library")
        os.makedirs(self.library)
        self.db = os.path.join(self.root, "corpus.sqlite")
        connection = sqlite3.connect(self.db)
        connection.executescript(SCHEMA)
        connection.commit()
        connection.close()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def add_document(self, doc_id, file_name, data=b"%PDF-1.7 fake bytes", on_disk_name=None):
        """Put a file in the library and a row in the record."""
        real_name = on_disk_name or file_name
        path = os.path.join(self.library, real_name)
        with open(path, "wb") as handle:
            handle.write(data)
        recorded = os.path.join(self.library, file_name)
        connection = sqlite3.connect(self.db)
        connection.execute(
            "INSERT INTO documents (doc_id, title, local_path, r2_key, sha256)"
            " VALUES (?, ?, ?, NULL, ?)",
            (doc_id, "A title", recorded, sha256_bytes(data)))
        connection.commit()
        connection.close()
        return path

    # ── the plan ──────────────────────────────────────────────────────────
    def test_plan_lists_every_document_with_its_key(self):
        self.add_document("bk-1", "One.pdf")
        self.add_document("bk-2", "Two.pdf")
        plan = r2_plan.build_plan(self.db)
        self.assertEqual(plan["source_root"], os.path.abspath(self.library))
        self.assertEqual(len(plan["entries"]), 2)
        self.assertEqual(sorted(entry["key"] for entry in plan["entries"]),
                         ["pdfs/One.pdf", "pdfs/Two.pdf"])
        self.assertEqual(plan["total_bytes"], 2 * len(b"%PDF-1.7 fake bytes"))

    def test_plan_uses_the_name_on_disk_when_the_record_differs_in_case(self):
        """The defect that moved 18 of 19 documents on the first run."""
        self.add_document("bk-1", "Exploring_business.pdf",
                          on_disk_name="exploring_business.pdf")
        plan = r2_plan.build_plan(self.db)
        self.assertEqual(plan["entries"][0]["rel_path"], "exploring_business.pdf")
        self.assertTrue(plan["entries"][0]["case_corrected"])

    def test_plan_refuses_a_file_that_is_not_on_disk(self):
        self.add_document("bk-1", "One.pdf")
        connection = sqlite3.connect(self.db)
        connection.execute("UPDATE documents SET local_path = ? WHERE doc_id = 'bk-1'",
                           (os.path.join(self.library, "Gone.pdf"),))
        connection.commit()
        connection.close()
        with self.assertRaises(r2_plan.PlanError) as caught:
            r2_plan.build_plan(self.db)
        self.assertIn("not on disk", str(caught.exception))
        self.assertIn("bk-1", str(caught.exception))

    def test_plan_refuses_two_documents_that_name_one_file(self):
        self.add_document("bk-1", "Same.pdf")
        connection = sqlite3.connect(self.db)
        connection.execute(
            "INSERT INTO documents (doc_id, title, local_path, r2_key, sha256)"
            " VALUES ('bk-2', 'Another title', ?, NULL, ?)",
            (os.path.join(self.library, "Same.pdf"), sha256_bytes(b"%PDF-1.7 fake bytes")))
        connection.commit()
        connection.close()
        with self.assertRaises(r2_plan.PlanError) as caught:
            r2_plan.build_plan(self.db)
        self.assertIn("share one file", str(caught.exception))

    def test_file_list_holds_one_relative_path_per_document(self):
        self.add_document("bk-1", "One.pdf")
        self.add_document("bk-2", "Two.pdf")
        plan = r2_plan.build_plan(self.db)
        target = os.path.join(self.root, "files.txt")
        count = r2_plan.write_files_from(plan, target)
        self.assertEqual(count, 2)
        with open(target, "r", encoding="utf-8") as handle:
            lines = [line.strip() for line in handle if line.strip()]
        self.assertEqual(sorted(lines), ["One.pdf", "Two.pdf"])

    # ── the record ───────────────────────────────────────────────────────
    def test_repair_writes_the_name_on_disk_into_the_record(self):
        self.add_document("bk-1", "Exploring_business.pdf",
                          on_disk_name="exploring_business.pdf")
        changes = r2_plan.repair_paths(self.db)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["doc_id"], "bk-1")
        connection = sqlite3.connect(self.db)
        stored = connection.execute(
            "SELECT local_path FROM documents WHERE doc_id = 'bk-1'").fetchone()[0]
        connection.close()
        self.assertTrue(stored.endswith("exploring_business.pdf"))

    def test_repair_leaves_a_correct_path_alone(self):
        self.add_document("bk-1", "One.pdf")
        self.assertEqual(r2_plan.repair_paths(self.db), [])

    def test_record_writes_the_object_key(self):
        self.add_document("bk-1", "One.pdf")
        plan = r2_plan.build_plan(self.db)
        written = r2_plan.record_keys(self.db, plan)
        self.assertEqual(written, 1)
        connection = sqlite3.connect(self.db)
        stored = connection.execute(
            "SELECT r2_key FROM documents WHERE doc_id = 'bk-1'").fetchone()[0]
        connection.close()
        self.assertEqual(stored, "pdfs/One.pdf")

    # ── the bytes ────────────────────────────────────────────────────────
    def test_verify_accepts_bytes_that_match_the_record(self):
        data = b"%PDF-1.7 fake bytes"
        self.add_document("bk-1", "One.pdf", data=data)
        restored = os.path.join(self.root, "restored")
        os.makedirs(restored)
        with open(os.path.join(restored, "One.pdf"), "wb") as handle:
            handle.write(data)
        report = r2_plan.verify_bytes(self.db, self.library, restored)
        self.assertTrue(report["ok"])
        self.assertEqual(report["results"][0]["status"], "ok")

    def test_verify_names_a_file_that_is_not_there(self):
        self.add_document("bk-1", "One.pdf")
        restored = os.path.join(self.root, "restored")
        os.makedirs(restored)
        report = r2_plan.verify_bytes(self.db, self.library, restored)
        self.assertFalse(report["ok"])
        self.assertEqual(report["results"][0]["status"], "missing")

    def test_verify_names_bytes_that_do_not_match(self):
        self.add_document("bk-1", "One.pdf", data=b"%PDF-1.7 the real bytes")
        restored = os.path.join(self.root, "restored")
        os.makedirs(restored)
        with open(os.path.join(restored, "One.pdf"), "wb") as handle:
            handle.write(b"%PDF-1.7 different bytes")
        report = r2_plan.verify_bytes(self.db, self.library, restored)
        self.assertFalse(report["ok"])
        self.assertEqual(report["results"][0]["status"], "hash_mismatch")

    def test_relink_points_the_record_at_the_restored_files(self):
        self.add_document("bk-1", "One.pdf")
        restored = os.path.join(self.root, "restored")
        os.makedirs(restored)
        with open(os.path.join(restored, "One.pdf"), "wb") as handle:
            handle.write(b"%PDF-1.7 fake bytes")
        changed = r2_plan.relink(self.db, self.library, restored)
        self.assertEqual(changed, 1)
        connection = sqlite3.connect(self.db)
        stored = connection.execute(
            "SELECT local_path FROM documents WHERE doc_id = 'bk-1'").fetchone()[0]
        connection.close()
        self.assertEqual(stored, os.path.join(restored, "One.pdf"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
