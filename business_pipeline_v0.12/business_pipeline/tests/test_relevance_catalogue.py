"""Tests for the RRA catalogue snapshot adapter."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.relevance_base import RelevanceTestCase  # noqa: E402

from bp.product.relevance import (build_catalogue_snapshot, check_drift,  # noqa: E402
                                  load_catalogue_snapshot, write_catalogue_snapshot)
import bp.product.relevance.catalogue_snapshot as cs  # noqa: E402


class CatalogueSnapshotTest(RelevanceTestCase):
    def test_the_snapshot_holds_the_system_catalogue(self):
        snapshot, err = build_catalogue_snapshot()
        self.assertEqual(err, "")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["format"], "bp-catalogue-snapshot/1")
        self.assertGreater(len(snapshot["capabilities"]), 0)
        self.assertGreater(len(snapshot["frameworks"]), 0)
        self.assertGreater(len(snapshot["methods"]), 0)
        self.assertIn("hash", snapshot)

    def test_the_snapshot_is_written_and_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(cs, "_repo_root", return_value=Path(tmp)):
                (Path(tmp) / "qa" / "relevance").mkdir(parents=True, exist_ok=True)
                path, err = write_catalogue_snapshot()
                self.assertEqual(err, "")
                self.assertIsNotNone(path)
                snapshot = load_catalogue_snapshot()
                self.assertIsNotNone(snapshot)
                self.assertGreater(len(snapshot["capabilities"]), 0)

    def test_the_stored_snapshot_is_in_sync(self):
        drifted, detail = check_drift()
        self.assertFalse(drifted, detail)
        self.assertIn("in sync", detail)

    def test_every_entry_carries_its_key_and_label(self):
        snapshot, err = build_catalogue_snapshot()
        self.assertEqual(err, "")
        for capability in snapshot["capabilities"][:5]:
            self.assertIn("key", capability)
            self.assertIn("label", capability)
        for framework in snapshot["frameworks"][:5]:
            self.assertIn("key", framework)
            self.assertIn("label", framework)
        for method in snapshot["methods"][:5]:
            self.assertIn("method_id", method)


if __name__ == "__main__":
    unittest.main()
