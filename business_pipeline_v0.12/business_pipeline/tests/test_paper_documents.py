"""The paper store and the document routes (product layer)."""

import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from bp.product import api, paper_store


class PaperStoreTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-docs-")
        self.store = os.path.join(self.root, "documents")
        self.index = os.path.join(self.store, "index.json")
        self.samples = os.path.join(self.root, "samples")
        os.makedirs(self.samples)
        with open(os.path.join(self.samples, "demo-paper.docx"), "wb") as handle:
            handle.write(b"sample-bytes")
        with open(os.path.join(self.samples, "worked-example.zip"), "wb") as handle:
            handle.write(b"zip-bytes")
        self.patch = mock.patch.multiple(paper_store, STORE=self.store, INDEX=self.index,
                                         SAMPLES=self.samples)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_saved_paper_is_listed_and_read_back_byte_for_byte(self):
        record = paper_store.save(b"docx-bytes", "my paper.docx", "My Paper", "Five Forces", "full", 2100)
        self.assertRegex(record["id"], r"^[0-9a-f]{12}$")
        self.assertEqual(record["filename"], "my-paper.docx")
        listing = paper_store.listing()["documents"]
        self.assertEqual(listing[0]["id"], record["id"])
        same, data = paper_store.read(record["id"])
        self.assertEqual(data, b"docx-bytes")
        self.assertEqual(same["title"], "My Paper")
        self.assertEqual(same["words"], 2100)

    def test_the_shipped_samples_are_listed_beside_the_students_papers(self):
        listing = paper_store.listing()["documents"]
        ids = [row["id"] for row in listing]
        self.assertIn("sample-demo-paper", ids)
        record, data = paper_store.read("sample-demo-paper")
        self.assertEqual(data, b"sample-bytes")
        self.assertTrue(record["sample"])

    def test_a_sample_bundle_is_listed_and_served_as_a_zip(self):
        rows = {row["id"]: row for row in paper_store.listing()["documents"]}
        self.assertIn("sample-worked-example", rows)
        self.assertEqual(rows["sample-worked-example"]["mime"], paper_store.ZIP_MIME)
        self.assertTrue(rows["sample-worked-example"]["sample"])
        record, data = paper_store.read("sample-worked-example")
        self.assertEqual(data, b"zip-bytes")

    def test_an_unknown_or_malformed_id_is_refused(self):
        for bad in ("../../secrets", "deadbeef", "sample-../../x", ""):
            with self.assertRaises(paper_store.NotFound):
                paper_store.read(bad)

    def test_the_index_survives_a_corrupt_file(self):
        os.makedirs(self.store, exist_ok=True)
        with open(self.index, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        self.assertEqual(paper_store.listing()["documents"][0]["id"], "sample-demo-paper")


class DocumentRouteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-docs-api-")
        self.store = os.path.join(self.root, "documents")
        self.index = os.path.join(self.store, "index.json")
        self.samples = os.path.join(self.root, "samples")
        os.makedirs(self.samples)
        with open(os.path.join(self.samples, "demo-paper.docx"), "wb") as handle:
            handle.write(b"sample-bytes")
        with open(os.path.join(self.samples, "worked-example.zip"), "wb") as handle:
            handle.write(b"zip-bytes")
        self.patch = mock.patch.multiple(paper_store, STORE=self.store, INDEX=self.index,
                                         SAMPLES=self.samples)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_list_route_returns_the_documents(self):
        code, payload = api.handle("GET", "/api/cases/documents")
        self.assertEqual(code, 200)
        self.assertEqual(payload["documents"][0]["id"], "sample-demo-paper")

    def test_the_download_route_returns_the_word_bytes(self):
        code, payload, ctype = api.handle("GET", "/api/cases/documents/sample-demo-paper")
        self.assertEqual(code, 200)
        self.assertEqual(payload, b"sample-bytes")
        self.assertEqual(ctype, paper_store.MIME)

    def test_a_sample_bundle_downloads_as_a_zip(self):
        code, payload, ctype = api.handle("GET", "/api/cases/documents/sample-worked-example")
        self.assertEqual(code, 200)
        self.assertEqual(payload, b"zip-bytes")
        self.assertEqual(ctype, paper_store.ZIP_MIME)

    def test_an_unknown_document_is_a_404_not_a_path(self):
        code, payload = api.handle("GET", "/api/cases/documents/../../etc/passwd")
        self.assertEqual(code, 404)
        self.assertIn("no such document", payload["error"])

    def test_listing_is_read_only(self):
        code, payload = api.handle("POST", "/api/cases/documents", {})
        self.assertEqual(code, 405)

    @mock.patch("bp.product.api.framework_completion")
    def test_generating_a_paper_saves_it_to_the_store(self, completion):
        completion.draft.return_value = {"title": "A Paper", "sections": [], "style": "apa",
                                         "version": "full", "model_used": True, "words": 2000,
                                         "byline": []}
        completion.draft_bytes.return_value = b"docx-bytes"
        body = {"completion": {"instruction": "A case."}, "style": "apa", "version": "full"}
        code, payload = api.handle("POST", "/api/cases/frameworks/report", body)
        self.assertEqual(code, 200)
        self.assertEqual(payload["document"]["title"], "A Paper")
        record, data = paper_store.read(payload["document"]["id"])
        self.assertEqual(data, b"docx-bytes")


if __name__ == "__main__":
    unittest.main()
