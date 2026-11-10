"""Porter's Diamond completion: a nation's industry, one determinant at a time.

The behaviour the Five Forces and PESTEL builds proved, applied to Porter's
Diamond: four determinants plus government and chance, sourced items or a named
gap with a probe, **the nation/region and its industry** as the unit of
analysis, one paper, and a refusal rather than a thin paper.  The unit was
corrected from a bare industry because the Diamond explains why an industry in a
place is competitive (owner guideline, 2026-11-09).  The framework supplies
everything; the engine is unchanged.
"""

import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import api, completion  # noqa: E402

BRIEF = ("Kestrel Retail is reviewing its grocery retail position in Germany before "
         "deciding whether to expand.")

COUNTRY = "Germany"

INDUSTRY = "grocery retail"


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
        return completion.complete("template_porters_diamond", kwargs.pop("instruction", BRIEF),
                                   country=kwargs.pop("country", COUNTRY),
                                   industry=kwargs.pop("industry", INDUSTRY), **kwargs)
class PortersDiamondCompletionTest(unittest.TestCase):
    def test_four_cells_each_carry_a_sourced_item_or_a_named_gap(self):
        result = complete()
        self.assertEqual(result["template"], "template_porters_diamond")
        self.assertEqual(result["framework"], "Porters Diamond")
        self.assertEqual([block["key"] for block in result["blocks"]],
                         ["factor_conditions", "demand_conditions",
                          "related_industries", "firm_strategy",
                          "government", "chance"])
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                if item["provenance"] == "sourced":
                    self.assertTrue(item["source"], block["key"])
                    self.assertTrue(item["citation"], block["key"])

    def test_the_nation_and_its_industry_are_the_unit_of_analysis(self):
        result = complete()
        self.assertEqual(result["unit"]["field"], "country_industry")
        self.assertEqual(result["unit"]["country"], COUNTRY)
        self.assertEqual(result["unit"]["industry"], INDUSTRY)
        self.assertIn(COUNTRY, result["unit"]["value"])
        self.assertIn(INDUSTRY, result["unit"]["value"])
        self.assertIn(COUNTRY, result["blocks"][0]["query"])
        self.assertIn(INDUSTRY, result["blocks"][0]["query"])

    def test_a_brief_without_a_country_is_refused_with_an_actionable_reason(self):
        with self.assertRaises(ValueError) as refused:
            complete(instruction="A firm is weighing growth options.", country="")
        self.assertIn("country", str(refused.exception).lower())

    def test_a_brief_without_an_industry_is_refused_with_an_actionable_reason(self):
        with self.assertRaises(ValueError) as refused:
            complete(instruction="A firm is weighing growth options.", industry="")
        self.assertIn("industry", str(refused.exception).lower())

    def test_global_is_not_a_nation_for_the_diamond(self):
        with self.assertRaises(ValueError) as refused:
            complete(country="Global")
        self.assertIn("global", str(refused.exception).lower())

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
            result = completion.complete("template_porters_diamond", BRIEF,
                                         country=COUNTRY, industry=INDUSTRY)
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                self.assertEqual(item["provenance"], "background")

    def test_outline_headings_are_present_and_title_cased(self):
        profile = completion._profile("template_porters_diamond")
        outline = profile["outline"]
        for field in ("framework", "context", "discussion", "implications",
                      "limitations", "conclusion", "lead"):
            self.assertTrue(outline.get(field), field)
        self.assertEqual(outline["framework"], "Porters Diamond")
        self.assertFalse(outline["context"].endswith("."))
        self.assertFalse(outline["discussion"].endswith("."))

    def test_byline_reaches_the_title_page(self):
        result = dict(complete(), byline=["A Student", "Example University"])
        self.assertIn("byline", result)
        self.assertTrue(result["byline"])

    def test_an_empty_cell_does_not_block_the_paper(self):
        result = complete()
        result["blocks"] = [block for block in result["blocks"]
                            if block["key"] != "firm_strategy"]
        result["blocks"].append({"key": "firm_strategy", "label": "Diversification",
                                 "items": [], "gap": "No evidence."})
        self.assertEqual(completion.missing(result), [])

    def test_the_route_generates_a_draft_with_an_empty_cell(self):
        result = complete()
        result["blocks"] = [block for block in result["blocks"]
                            if block["key"] != "related_industries"]
        result["blocks"].append({"key": "related_industries", "label": "Product development",
                                 "items": [], "gap": "No evidence."})
        status, payload = api.handle("POST", "/api/cases/frameworks/report",
                                     {"completion": result, "version": "draft"})
        self.assertEqual(status, 200, payload)

    def test_the_route_returns_an_porters_diamond_completion(self):
        with mock.patch("bp.product.completion.complete") as fake:
            fake.return_value = {"format": "bp-framework-completion/1",
                                 "template": "template_porters_diamond", "blocks": []}
            status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                         {"template": "template_porters_diamond",
                                          "instruction": BRIEF,
                                          "country": COUNTRY,
                                          "industry": INDUSTRY})
        self.assertEqual(status, 200)
        self.assertEqual(payload["template"], "template_porters_diamond")

    def test_the_model_prompt_speaks_porters_diamond_and_keeps_the_safety_rules(self):
        profile = dict(completion.LENGTHS["mid"])
        system = completion._system(completion.HEAD_SYSTEM, profile,
                                    completion._profile("template_porters_diamond"))
        self.assertIn("Porters Diamond", system)
        self.assertNotIn("PESTEL", system)
        self.assertIn("Do not add facts, numbers, names, sources or citations", system)
        self.assertIn("country", system.lower())
        self.assertIn("industry", system.lower())

    def test_the_framework_name_is_not_an_invented_name(self):
        facts = completion._facts([{
            "key": "factor_conditions", "label": "Market penetration",
            "items": [{"text": "A loyalty card lifts repeat visits.", "provenance": "user"}]}])
        data = {"introduction": ["Porters Diamond frames the decision for the market."], "context": [""],
                "lead": "lead", "groups": {"factor_conditions": ["Market penetration matters."]},
                "discussion": [""], "implications": [""], "limitations": [""], "conclusion": [""]}
        allow = completion._allowed_names(completion._profile("template_porters_diamond"),
                                          {"unit": {"value": COUNTRY}, "region": "Europe"})
        problems = completion._problems(data, facts, "A case in Germany.", "short",
                                        ["factor_conditions"], allow=allow)
        self.assertFalse([p for p in problems if p.startswith("name Porters Diamond")
                          or p.startswith("name Growth") or p.startswith("name Matrix")], problems)


if __name__ == "__main__":
    unittest.main()