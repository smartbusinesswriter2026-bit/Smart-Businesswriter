"""The automated-testing paper previews: real papers, real instructions, no invented sources."""

import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, "src")

from bp import methods  # noqa: E402
from bp.product import paper_batch  # noqa: E402

PRESETS = {
    "breakeven": {
        "objective": "How many units must we sell to break even?",
        "method": "breakeven",
        "inputs": {"fixed": "1000", "price": "20", "variable": "10"},
    },
    "ratios": {
        "objective": "Compute the key ratios from our financial statements",
        "method": "ratio_analysis",
        "inputs": {"current_assets": "5000", "current_liabilities": "2000"},
    },
}

HIT = {
    "doc_id": "doc-breakeven",
    "title": "Managerial Accounting for Decision Makers",
    "authors": "Doe, J.",
    "year": 2020,
    "venue": "Open Textbook Library",
    "abstract": (
        "Break-even analysis compares the contribution margin with fixed costs so a manager can see how many "
        "units must be sold to cover them. The method reports the break-even quantity and the revenue at that "
        "quantity, and it does not forecast demand."
    ),
    "database": "Proprietary corpus",
}


def _fake_search(query, databases=None, limit=20, year_from=None):
    return {"results": [dict(HIT)], "errors": [], "cached": False}


WEAK = {
    "doc_id": "doc-weak",
    "title": "A General Business Text",
    "authors": "",
    "year": None,
    "abstract": "A break-even is discussed in this chapter on general commerce.",
    "database": "Proprietary corpus",
}


def _weak_search(query, databases=None, limit=20, year_from=None):
    return {"results": [dict(WEAK)], "errors": [], "cached": False}


def _docx_text(data):
    xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
    out = []
    for para in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        text = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", para, re.S))
        if text.strip():
            out.append(text)
    return "\n".join(out)


class PaperPreviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paper_batch.configure(lambda method, inputs: methods.LIBRARY[method].impl(inputs),
                              methods.describe, PRESETS)
        paper_batch.sections(refresh=True)

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-paper-preview-")
        self.previous_store = paper_batch._STORE
        paper_batch._STORE = os.path.join(self.root, "paper_previews")
        os.makedirs(paper_batch._STORE, exist_ok=True)

    def tearDown(self):
        paper_batch._STORE = self.previous_store
        shutil.rmtree(self.root, ignore_errors=True)

    def test_every_subject_is_a_section_with_tile_groups(self):
        data = paper_batch.sections()
        self.assertEqual(len(data["subjects"]), 11)
        accounting = next(s for s in data["subjects"] if s["id"] == "accounting")
        self.assertGreaterEqual(len(accounting["groups"]), 5)
        labels = [g["label"] for g in accounting["groups"]]
        self.assertIn("Statement analysis", labels)
        economics = next(s for s in data["subjects"] if s["id"] == "economics")
        self.assertIn("Market basics", [g["label"] for g in economics["groups"]])

    def test_a_tile_without_a_frozen_method_is_named_not_faked(self):
        result = paper_batch.generate_one("management", "case_decision")
        self.assertEqual(result["status"], "needs_input")
        self.assertIn("decision framework", result["error"])

    @mock.patch.object(paper_batch.source_finder, "search_academic", side_effect=_fake_search)
    def test_the_paper_computes_the_tile_and_cites_only_the_corpus_page(self, _search):
        result = paper_batch.generate_one("accounting", "breakeven")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["bytes"].startswith(b"PK"))
        text = _docx_text(result["bytes"])
        self.assertIn("Break-even point", text)
        self.assertIn("Declared inputs: fixed 1,000; price 20; variable 10", text)
        self.assertIn("References", text)
        self.assertIn("Managerial Accounting for Decision Makers", text)
        self.assertIn("Doe, 2020", text)
        self.assertNotIn("No framework", text)
        self.assertNotIn("No named framework is used", text)
        self.assertIn("no named framework", text)

    @mock.patch.object(paper_batch.source_finder, "search_academic", side_effect=_weak_search)
    def test_a_weak_page_is_labelled_background_not_a_citation(self, _search):
        result = paper_batch.generate_one("accounting", "breakeven")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sources"], 0)
        self.assertEqual(result["background"], 1)
        text = _docx_text(result["bytes"])
        self.assertIn("Background Reading (not cited)", text)
        self.assertIn("A General Business Text", text)
        self.assertIn("No sources were used", text)
        self.assertNotIn("Doe, 2020", text)

    @mock.patch.object(paper_batch.source_finder, "search_academic", side_effect=_fake_search)
    def test_a_run_exports_a_zip_and_the_prefilled_instructions(self, _search):
        started = paper_batch.start_run("accounting", ["breakeven"], style="apa", length=1200)
        deadline = time.time() + 60
        while time.time() < deadline:
            state = paper_batch.status(started["run_id"])
            if state["status"] != "running":
                break
            time.sleep(0.2)
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["results"][0]["status"], "ok")
        data, name = paper_batch.download(started["run_id"], "zip")
        self.assertTrue(name.endswith(".zip"))
        archive = zipfile.ZipFile(io.BytesIO(data))
        names = archive.namelist()
        self.assertIn("manifest.json", names)
        self.assertIn("instructions.md", names)
        self.assertTrue(any(name.endswith(".docx") for name in names))
        instructions = archive.read("instructions.md").decode("utf-8")
        self.assertIn("How many units must we sell to break even?", instructions)
        self.assertIn("Instruction:", instructions)
        combined, _ = paper_batch.download(started["run_id"], "docx")
        self.assertTrue(combined.startswith(b"PK"))


if __name__ == "__main__":
    unittest.main()
