"""Five Forces completion: research fills blanks, gaps stay gaps."""

import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import api, completion  # noqa: E402


def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": "Saudi grocery competition and entry barriers",
        "abstract": "Competition in the Saudi grocery market is shaped by entry barriers and buyer pressure. A second sentence.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Retail", "doi": "10.1/" + str(abs(hash(query)) % 100000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "No web result.", "sites": []}


class CompletionTest(unittest.TestCase):
    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_every_force_gets_an_item_or_a_named_gap(self, _a, _w):
        result = completion.complete(
            "template_five_forces",
            "A grocery chain is considering acquiring a cold-chain provider in Saudi Arabia. Complete a Five Forces analysis.")
        self.assertEqual(len(result["blocks"]), 5)
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                if item["provenance"] == "sourced":
                    self.assertTrue(item["source"])

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", return_value={"results": [], "errors": [], "skipped": []})
    def test_no_evidence_is_a_gap_not_invented_text(self, _a, _w):
        result = completion.complete(
            "template_five_forces",
            "A grocery chain is considering a cold-chain acquisition in Saudi Arabia.")
        self.assertEqual(sum(1 for block in result["blocks"] if block["gap"]), 5)
        self.assertTrue(all(not block["items"] for block in result["blocks"]))

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_a_student_item_is_preserved(self, _a, _w):
        result = completion.complete(
            "template_five_forces",
            "A grocery chain is considering a cold-chain acquisition in Saudi Arabia.",
            student_items=[{"force": "rivalry", "text": "The local market has three large chains."}])
        rivalry = next(block for block in result["blocks"] if block["key"] == "rivalry")
        self.assertEqual(rivalry["items"][0]["text"], "The local market has three large chains.")
        self.assertEqual(rivalry["items"][0]["provenance"], "student")

    def test_the_draft_has_a_hierarchy_and_only_sourced_references(self):
        result = {"instruction": "A grocery chain is considering a cold-chain acquisition in Saudi Arabia.",
                  "blocks": [{"key": "rivalry", "label": "Industry rivalry", "gap": None,
                              "items": [{"text": "Competition is intense.", "provenance": "sourced",
                                         "source": "Lovelace, A. (2024). Retail competition. Journal, 1(1), 1-2.",
                                         "citation": "(Lovelace, 2024)"}]},
                             {"key": "entrants", "label": "Threat of new entrants", "gap": "No source found.",
                              "items": []}]}
        report = completion.draft(result)
        levels = {section["heading"]: section["level"] for section in report["sections"]}
        self.assertEqual(levels["Five Forces"], 1)
        self.assertEqual(levels["Industry rivalry"], 2)
        self.assertEqual(levels["Limitations"], 2)
        self.assertIn("Lovelace", " ".join(report["sections"][-1]["lines"]))
        data = completion.draft_bytes(result)
        self.assertTrue(data.startswith(b"PK"))

    def test_a_company_without_an_industry_is_refused(self):
        with self.assertRaises(ValueError) as refused:
            completion.complete("template_five_forces",
                                "apple considering for an entry in iran")
        self.assertIn("industry", str(refused.exception).lower())

    @mock.patch("bp.product.completion._model_sections")
    def test_the_full_version_uses_model_prose_and_keeps_citations(self, model):
        model.return_value = (
            {"introduction": "This paper examines the industry.", "forces": {"rivalry": "Competition is intense."},
             "discussion": "The force shapes the entry context.", "conclusion": "The analysis is limited."},
            "text", {"rivalry": ["(Lovelace, 2024)"]})
        result = {"instruction": "A case in Saudi Arabia.",
                  "blocks": [{"key": "rivalry", "label": "Industry rivalry",
                              "items": [{"text": "Competition is intense.", "provenance": "sourced",
                                         "source": "Lovelace, A. (2024). Retail competition.",
                                         "citation": "(Lovelace, 2024)"}]}]}
        report = completion.draft(result, "apa", "full")
        self.assertTrue(report["model_used"])
        rivalry = next(section for section in report["sections"] if section["heading"] == "Industry rivalry")
        self.assertIn("(Lovelace, 2024)", rivalry["lines"][0])

    def test_student_items_stay_student_evidence_not_assumptions(self):
        result = {"instruction": "A grocery chain considers a cold-chain acquisition in Saudi Arabia.",
                  "blocks": [{"key": "buyers", "label": "Buyer power",
                              "items": [{"text": "Buyers negotiate on price.", "provenance": "user"}]}]}
        report = completion.draft(result, "apa", "draft")
        buyers = next(section for section in report["sections"] if section["heading"] == "Buyer power")
        self.assertEqual(buyers["lines"][0], "Buyers negotiate on price.")
        self.assertNotIn("Case assumption", buyers["lines"][0])

    def test_another_template_is_refused(self):
        with self.assertRaises(ValueError):
            completion.complete("template_swot", "A grocery chain is entering Saudi Arabia.")

    @mock.patch("bp.product.completion.complete")
    def test_the_route_returns_the_completion(self, complete):
        complete.return_value = {"format": "bp-framework-completion/1", "blocks": []}
        status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                     {"template": "template_five_forces", "instruction": "A grocery case in Saudi Arabia."})
        self.assertEqual(status, 200)
        self.assertEqual(payload["blocks"], [])


if __name__ == "__main__":
    unittest.main()
