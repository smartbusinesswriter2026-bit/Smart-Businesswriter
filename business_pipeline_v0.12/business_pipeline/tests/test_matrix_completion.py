"""The matrix frameworks reach the paper as a grid, not as a list of paragraphs."""

import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import completion, matrix  # noqa: E402

BRIEF = ("A grocery retailer is reviewing growth options before deciding whether "
         "to open a new store format or launch a private-label range.")
INDUSTRY = "grocery retail"


def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": "Grocery retail " + query[:70],
        "abstract": "Evidence on the growth option named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Marketing", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def complete(template, **kwargs):
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, kwargs.pop("instruction", BRIEF),
                                   industry=kwargs.pop("industry", INDUSTRY),
                                   country=kwargs.pop("country", None), **kwargs)


def figure_of(report):
    for section in report["sections"]:
        if section.get("figure"):
            return section["figure"]
    return None


class MatrixCompletionTest(unittest.TestCase):
    def test_ansoff_reaches_the_paper_as_a_two_by_two(self):
        report = completion.draft(complete("template_ansoff"))
        figure = figure_of(report)
        self.assertIsNotNone(figure)
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), 2)

    def test_the_framework_heading_carries_the_figure(self):
        report = completion.draft(complete("template_ansoff"))
        headings = [section["heading"] for section in report["sections"] if section.get("figure")]
        self.assertTrue(headings)
        self.assertIn("Ansoff", headings[0])

    def test_a_sourced_cell_carries_the_source_identity_not_a_blank(self):
        report = completion.draft(complete("template_ansoff"))
        figure = figure_of(report)
        cell = figure["grids"][0]["rows"][0][0]
        self.assertTrue(cell["bullets"] or cell["gap"])
        self.assertTrue(cell["label"])

    def test_an_empty_cell_shows_the_named_gap_and_the_probe(self):
        result = complete("template_ansoff")
        for block in result["blocks"]:
            block["items"] = []
            block["gap"] = "No evidence was found for this cell."
        report = completion.draft(result)
        figure = figure_of(report)
        for row in figure["grids"][0]["rows"]:
            for cell in row:
                self.assertTrue(cell["gap"], cell["label"])
                self.assertEqual(cell["bullets"], [])

    def test_the_value_chain_keeps_the_support_row_above_the_primary_row(self):
        report = completion.draft(complete("template_value_chain"))
        figure = figure_of(report)
        titles = [grid["title"] for grid in figure["grids"]]
        self.assertEqual(titles, ["Support activities", "Primary activities"])

    def test_the_ge_mckinsey_paper_carries_a_three_by_three(self):
        report = completion.draft(complete("template_ge_mckinsey"))
        figure = figure_of(report)
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(len(row) == 3 for row in rows))

    def test_a_framework_without_a_grid_carries_no_figure(self):
        report = completion.draft(complete("template_pestel", country="Saudi Arabia"))
        self.assertIsNone(figure_of(report))

    def test_the_word_paper_contains_the_table(self):
        result = complete("template_ansoff")
        data = completion.draft_bytes(result)
        self.assertIn(b"<w:tbl>", data)

    def test_an_empty_cell_does_not_block_the_paper(self):
        result = complete("template_ansoff")
        result["blocks"] = [block for block in result["blocks"]
                            if block["key"] != "diversification"]
        result["blocks"].append({"key": "diversification", "label": "Diversification",
                                 "items": [], "gap": "No evidence."})
        self.assertEqual(completion.missing(result), [])


if __name__ == "__main__":
    unittest.main()
