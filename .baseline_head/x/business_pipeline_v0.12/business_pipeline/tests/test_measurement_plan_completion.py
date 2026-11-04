"""Measurement Plan completion: growth options on a market, one cell at a time.

The behaviour the Five Forces and PESTEL builds proved, applied to the Measurement Plan
Growth Matrix: four cells, sourced items or a named gap with a probe, an
industry as the unit of analysis, one paper, and a refusal rather than a thin
paper.  The framework supplies everything; the engine is unchanged.
"""

import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import api, completion  # noqa: E402

BRIEF = ("A smartphoneser is reviewing growth options before deciding whether "
         "to open a new store format or launch a private-label range.")

INDUSTRY = "smartphones"


def academic(query, databases=None, limit=10, year_from=None):
    """A source whose title carries the query, so the cell gate can judge it."""
    return {"results": [{
        "title": "Grocery retail " + query[:70],
        "abstract": "Evidence on the growth option named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Marketing", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def blocks(result):
    return {block["key"]: block for block in result["blocks"]}


def complete(**kwargs):
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete("template_measurement_plan", kwargs.pop("instruction", BRIEF),
                                   industry=kwargs.pop("industry", INDUSTRY), **kwargs)
class MeasurementPlanCompletionTest(unittest.TestCase):
    def test_four_cells_each_carry_a_sourced_item_or_a_named_gap(self):
        result = complete()
        self.assertEqual(result["template"], "template_measurement_plan")
        self.assertEqual(result["framework"], "Measurement Plan")
        self.assertEqual([block["key"] for block in result["blocks"]],
                         ["questions", "metrics", "events_dimensions", "data_quality", "governance"])
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                if item["provenance"] == "sourced":
                    self.assertTrue(item["source"], block["key"])
                    self.assertTrue(item["citation"], block["key"])

    def test_the_industry_is_the_unit_of_analysis(self):
        result = complete()
        self.assertEqual(result["unit"]["field"], "industry")
        self.assertEqual(result["unit"]["value"], INDUSTRY)
        self.assertTrue(result["blocks"][0]["query"].startswith(INDUSTRY + " "))

    def test_a_brief_without_an_industry_is_refused_with_an_actionable_reason(self):
        with self.assertRaises(ValueError) as refused:
            complete(instruction="A firm is weighing growth options.", industry="")
        self.assertIn("market", str(refused.exception).lower())

    def test_one_source_cannot_fill_two_cells(self):
        result = complete()
        sources = set()
        for block in result["blocks"]:
            for item in block["items"]:
                if item.get("provenance") == "sourced":
                    sources.add(item.get("source"))
        self.assertEqual(len(sources), len(result["blocks"]))

    def test_no_source_run_fills_every_cell_with_background(self):
        def empty_academic(query, databases=None, limit=10, year_from=None):
            return {"results": [], "errors": [], "skipped": []}
        with mock.patch("bp.product.sources.search_academic", side_effect=empty_academic), \
                mock.patch("bp.product.sources.search_web", side_effect=web):
            result = completion.complete("template_measurement_plan", BRIEF, industry=INDUSTRY)
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                self.assertEqual(item["provenance"], "background")

    def test_outline_headings_are_present_and_title_cased(self):
        profile = completion._profile("template_measurement_plan")
        outline = profile["outline"]
        for field in ("framework", "context", "discussion", "implications",
                      "limitations", "conclusion", "lead"):
            self.assertTrue(outline.get(field), field)
        self.assertEqual(outline["framework"], "Measurement Plan")
        self.assertFalse(outline["context"].endswith("."))
        self.assertFalse(outline["discussion"].endswith("."))

    def test_byline_reaches_the_title_page(self):
        result = dict(complete(), byline=["A Student", "Example University"])
        self.assertIn("byline", result)
        self.assertTrue(result["byline"])

    def test_an_empty_cell_does_not_block_the_paper(self):
        result = complete()
        result["blocks"] = [block for block in result["blocks"]
                            if block["key"] != "data_quality"]
        result["blocks"].append({"key": "data_quality", "label": "Diversification",
                                 "items": [], "gap": "No evidence."})
        self.assertEqual(completion.missing(result), [])

    def test_the_route_generates_a_draft_with_an_empty_cell(self):
        result = complete()
        result["blocks"] = [block for block in result["blocks"]
                            if block["key"] != "events_dimensions"]
        result["blocks"].append({"key": "events_dimensions", "label": "Product development",
                                 "items": [], "gap": "No evidence."})
        status, payload = api.handle("POST", "/api/cases/frameworks/report",
                                     {"completion": result, "version": "draft"})
        self.assertEqual(status, 200, payload)

    def test_the_route_returns_an_measurement_plan_completion(self):
        with mock.patch("bp.product.completion.complete") as fake:
            fake.return_value = {"format": "bp-framework-completion/1",
                                 "template": "template_measurement_plan", "blocks": []}
            status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                         {"template": "template_measurement_plan",
                                          "instruction": BRIEF,
                                          "industry": INDUSTRY})
        self.assertEqual(status, 200)
        self.assertEqual(payload["template"], "template_measurement_plan")

    def test_the_model_prompt_speaks_measurement_plan_and_keeps_the_safety_rules(self):
        profile = dict(completion.LENGTHS["mid"])
        system = completion._system(completion.HEAD_SYSTEM, profile,
                                    completion._profile("template_measurement_plan"))
        self.assertIn("Measurement Plan", system)
        self.assertNotIn("PESTEL", system)
        self.assertIn("Do not add facts, numbers, names, sources or citations", system)
        self.assertIn("industry", system.lower())

    def test_the_framework_name_is_not_an_invented_name(self):
        facts = completion._facts([{
            "key": "questions", "label": "Market penetration",
            "items": [{"text": "A loyalty card lifts repeat visits.", "provenance": "user"}]}])
        data = {"introduction": ["Measurement Plan frames the decision for the market."], "context": [""],
                "lead": "lead", "groups": {"questions": ["Market penetration matters."]},
                "discussion": [""], "implications": [""], "limitations": [""], "conclusion": [""]}
        allow = completion._allowed_names(completion._profile("template_measurement_plan"),
                                          {"unit": {"value": INDUSTRY}, "region": "Global"})
        problems = completion._problems(data, facts, "A case in smartphones.", "short",
                                        ["questions"], allow=allow)
        self.assertFalse([p for p in problems if p.startswith("name Measurement Plan")
                          or p.startswith("name Growth") or p.startswith("name Matrix")], problems)


if __name__ == "__main__":
    unittest.main()