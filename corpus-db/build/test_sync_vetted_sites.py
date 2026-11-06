"""The vetted-site mirror: the registry reaches SQLite without becoming it.

    python corpus-db/build/test_sync_vetted_sites.py
"""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import corpus_lib as lib  # noqa: E402
import sync_vetted_sites  # noqa: E402


class VettedSiteMirrorTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="vetted-sites-test-")
        self.connection = lib.connect(os.path.join(self.directory, "corpus.sqlite"))
        lib.apply_schema(self.connection)

    def tearDown(self):
        self.connection.close()
        shutil.rmtree(self.directory, ignore_errors=True)

    def test_the_registry_is_mirrored_idempotently(self):
        first = sync_vetted_sites.sync(self.connection)
        second = sync_vetted_sites.sync(self.connection)
        self.assertEqual(first["sites"], second["sites"])
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM vetted_sites").fetchone()[0],
            first["sites"])
        self.assertGreater(first["sites"], 100)

    def test_the_ethics_topic_is_present_with_its_primary_sources(self):
        sync_vetted_sites.sync(self.connection)
        domains = {row[0] for row in self.connection.execute(
            "SELECT domain FROM vetted_sites WHERE topics LIKE '%ethics%'")}
        self.assertIn("plato.stanford.edu", domains)
        self.assertIn("iep.utm.edu", domains)
        self.assertIn("ibe.org.uk", domains)
        self.assertIn("transparency.org", domains)

    def test_a_stale_row_is_removed_unless_kept(self):
        sync_vetted_sites.sync(self.connection)
        self.connection.execute(
            "INSERT INTO vetted_sites (site_id, label, domain, topics, updated_at)"
            " VALUES ('stale', 'Stale', 'stale.example', '[]', ?)", (lib.now(),))
        self.connection.commit()
        sync_vetted_sites.sync(self.connection)
        self.assertIsNone(self.connection.execute(
            "SELECT 1 FROM vetted_sites WHERE site_id = 'stale'").fetchone())

        self.connection.execute(
            "INSERT INTO vetted_sites (site_id, label, domain, topics, updated_at)"
            " VALUES ('stale', 'Stale', 'stale.example', '[]', ?)", (lib.now(),))
        self.connection.commit()
        sync_vetted_sites.sync(self.connection, keep_stale=True)
        self.assertIsNotNone(self.connection.execute(
            "SELECT 1 FROM vetted_sites WHERE site_id = 'stale'").fetchone())


if __name__ == "__main__":
    unittest.main()
