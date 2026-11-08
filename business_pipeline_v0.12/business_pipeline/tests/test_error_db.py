"""The error database the growth loop reads: lessons, search and the growth brief."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")

from bp.product import error_db  # noqa: E402


class ErrorDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-errdb-")
        self.previous_log = os.environ.get("BP_OPS_LOG")
        self.previous_db = os.environ.get("BP_ERROR_DB")
        os.environ["BP_OPS_LOG"] = os.path.join(self.root, "ops")
        os.environ["BP_ERROR_DB"] = os.path.join(self.root, "errors.sqlite3")

    def tearDown(self):
        for name, value in (("BP_OPS_LOG", self.previous_log),
                            ("BP_ERROR_DB", self.previous_db)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_registry_builds_a_searchable_database(self):
        built = error_db.rebuild()
        self.assertGreaterEqual(built["lessons"], 1)
        self.assertTrue(os.path.isfile(os.environ["BP_ERROR_DB"]))
        summary = error_db.summary()
        self.assertGreaterEqual(summary["lessons"], 1)
        self.assertIn("db", summary)

    def test_a_query_finds_the_lesson_that_paid_for_the_bug(self):
        error_db.rebuild()
        rows = error_db.search("comma separator")
        self.assertTrue(rows)
        self.assertIn("parser.thousands_separator", [row["id"] for row in rows])
        self.assertTrue(rows[0]["avoid"])

    def test_the_growth_brief_names_the_lesson_and_the_open_causes(self):
        error_db.rebuild()
        brief = error_db.growth_brief(subject="economics", tile="unemployment", limit=3)
        self.assertIn("Known mistakes to avoid", brief)
        self.assertIn("Avoid:", brief)


if __name__ == "__main__":
    unittest.main()
