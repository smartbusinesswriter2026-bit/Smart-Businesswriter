"""The chat paper carries the matrix figures for SWOT, Ansoff, Value Chain and VRIO."""

import io
import re
import unittest
import zipfile
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import chat  # noqa: E402

BRIEF = ("A grocery chain is considering entering the Saudi market and needs to assess the "
         "political, economic, social, technological, environmental and legal context.")


def academic(query, databases=None, limit=20, year_from=None):
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower())[-60:]
    return {"results": [{
        "title": "Evidence on " + query[:60],
        "abstract": "The source reports a relevant change in the external environment. A second sentence.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of External Analysis", "doi": "10.1/" + slug,
        "url": "https://doi.org/10.1/" + slug, "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def _research(state):
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return chat.research(chat.confirm_plan(state))


def _answer(state, pairs):
    for question_id, value in pairs:
        state = chat.answer(state, question_id, value)
    return state


def swot_state():
    state = chat.start(BRIEF + " Use a SWOT.", framework="swot")
    state = _answer(state, (("decision", "Should the chain expand?"),
                            ("strengths", "repeat customers; brand loyalty"),
                            ("weaknesses", "thin margins"),
                            ("geography", "Middle East"), ("period", "5"), ("style", "apa")))
    return _research(state)


def ansoff_state():
    state = chat.start(BRIEF + " Use an Ansoff matrix.", framework="ansoff")
    state = _answer(state, (("decision", "Which growth path?"), ("firm", "the grocery chain"),
                            ("geography", "Middle East"), ("period", "5"), ("style", "apa")))
    return _research(state)


def value_chain_state():
    state = chat.start(BRIEF + " Use a value chain.", framework="value_chain")
    state = _answer(state, (("decision", "Which activity matters?"), ("firm", "the grocery chain"),
                            ("geography", "Middle East"), ("period", "5"), ("style", "apa")))
    return _research(state)


def vrio_state():
    state = chat.start(BRIEF + " Use VRIO.", framework="vrio")
    state = _answer(state, (("decision", "Which resource matters?"),
                            ("resources", "the bakery network; supplier relationships"),
                            ("valuable", "the bakery network is valuable"),
                            ("rare", "the supplier relationships are rare"),
                            ("costly", "imitation is costly"),
                            ("organized", "the firm is organised"),
                            ("style", "apa")))
    return _research(state)


def figure_of(state):
    for section in state["draft"]["outline"]:
        if section.get("figure"):
            return section["figure"]
    return None


class MatrixChatTest(unittest.TestCase):
    def test_a_swot_paper_carries_a_two_by_two_figure(self):
        state = swot_state()
        chat.draft(state)
        figure = figure_of(state)
        self.assertIsNotNone(figure)
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), 2)

    def test_the_strengths_cell_carries_the_students_own_words(self):
        state = swot_state()
        chat.draft(state)
        figure = figure_of(state)
        cell = figure["grids"][0]["rows"][0][0]
        self.assertEqual(cell["label"], "Strengths")
        self.assertTrue(cell["bullets"])
        self.assertIn("repeat customers", " ".join(cell["bullets"]).lower())

    def test_the_opportunities_cell_carries_the_source_title_and_citation(self):
        state = swot_state()
        chat.draft(state)
        figure = figure_of(state)
        cell = figure["grids"][0]["rows"][1][0]
        self.assertEqual(cell["label"], "Opportunities")
        self.assertTrue(cell["bullets"])
        self.assertTrue(any("(" in bullet for bullet in cell["bullets"]))

    def test_an_ansoff_paper_carries_the_axes(self):
        state = ansoff_state()
        chat.draft(state)
        figure = figure_of(state)
        self.assertEqual(figure["grids"][0]["axis_x"], ("Existing products", "New products"))
        self.assertEqual(figure["grids"][0]["axis_y"], ("Existing markets", "New markets"))

    def test_a_vrio_paper_carries_four_columns(self):
        state = vrio_state()
        chat.draft(state)
        figure = figure_of(state)
        self.assertEqual(len(figure["grids"][0]["rows"][0]), 4)

    def test_a_value_chain_paper_carries_the_two_rows(self):
        state = value_chain_state()
        chat.draft(state)
        figure = figure_of(state)
        self.assertEqual(len(figure["grids"]), 2)

    def test_the_word_paper_contains_the_table(self):
        state = swot_state()
        chat.draft(state, implications="A cautious expansion.")
        data = chat.docx_bytes(state)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            body = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("<w:tbl>", body)
        self.assertIn("Figure 1. SWOT matrix", body)


if __name__ == "__main__":
    unittest.main()
