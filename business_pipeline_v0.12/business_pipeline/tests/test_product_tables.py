"""Business tables: cells are stored strings, never a typed number.

A table is a figure, so it is referenced by id, placed by section and reused by the
deck.  What it must never do is carry a number nobody recorded, so a cell is either
a digit-free label or a reference to a stored artifact.
"""

import io
import os
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import deck, docx, figures, tables  # noqa: E402

SPEC = {
    "format": "bp-table/1",
    "title": "Risk register",
    "columns": ["Risk", "Owner", "Likelihood"],
    "rows": [
        {"cells": ["Supplier concentration", "Operations", {"artifact": "npv"}]},
        {"cells": ["Currency exposure", "Finance", {"artifact": "irr"}]},
    ],
}


def bundle():
    base = product_fixtures.make_bundle()
    base["delivery"]["appendix"]["artifacts"] = [
        ["npv", ["npv", "annual", "entity", "base"], "npv = sum(cf / (1 + rate) ** t)"],
        ["irr", ["irr", "annual", "entity", "base"], "irr = root of npv"],
    ]
    base["reperform"]["outputs"] = {"npv": "50.00", "irr": "0.21"}
    return base


class SpecTest(unittest.TestCase):

    def test_a_table_needs_two_columns_and_a_row(self):
        with self.assertRaises(tables.TableError):
            tables.validate_spec({"format": "bp-table/1", "title": "T", "columns": ["A"], "rows": []})

    def test_a_label_may_not_carry_a_number(self):
        bad = {"format": "bp-table/1", "title": "Risk register", "columns": ["Risk", "Score"],
               "rows": [{"cells": ["Supplier concentration", "4"]}]}
        with self.assertRaises(tables.TableError):
            tables.validate_spec(bad)

    def test_every_row_fills_every_column(self):
        bad = {"format": "bp-table/1", "title": "Risk register", "columns": ["A", "B"],
               "rows": [{"cells": ["one"]}]}
        with self.assertRaises(tables.TableError):
            tables.validate_spec(bad)

    def test_an_artifact_cell_is_resolved_from_the_record(self):
        table = tables.resolve(SPEC, bundle())
        self.assertEqual(table["rows"][0], ["Supplier concentration", "Operations", "50.00"])
        self.assertEqual(table["rows"][1][2], "0.21")

    def test_a_missing_artifact_says_not_recorded(self):
        spec = {"format": "bp-table/1", "title": "Risk register", "columns": ["Risk", "Score"],
                "rows": [{"cells": ["Supplier concentration", {"artifact": "nope"}]}]}
        self.assertEqual(tables.resolve(spec, bundle())["rows"][0][1], "not recorded")

    def test_the_spec_names_its_sources(self):
        self.assertEqual(tables.sources(SPEC), ["npv", "irr"])


class FigureTest(unittest.TestCase):

    def test_a_table_is_a_figure_with_sources(self):
        record = figures.make("table", SPEC, caption="Risk register", why="two rows")
        self.assertEqual(record["kind"], "table")
        self.assertEqual(record["sources"], ["npv", "irr"])
        self.assertIn("Risk register", figures.text(record))

    def test_render_resolves_the_table_and_asks_for_no_picture(self):
        record = figures.render(figures.make("table", SPEC, caption="Risk register", why="two rows"),
                                bundle())
        self.assertEqual(record["table"]["rows"][0][2], "50.00")
        self.assertIsNone(record["asset"]["png"])


class WordTest(unittest.TestCase):

    def test_a_table_figure_reaches_the_paper_as_a_word_table(self):
        record = figures.render(figures.make("table", SPEC, caption="Risk register", why="two rows"),
                                bundle())
        data = docx.render_academic("A paper", [
            {"heading": "Risks", "level": 1, "lines": ["A line."], "figure": record}])
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            body = archive.read("word/document.xml")
        self.assertIn(b"<w:tbl>", body)
        self.assertIn(b"Supplier concentration", body)
        self.assertIn(b"50.00", body)
        self.assertIn(b"Figure 1. Risk register", body)
        ET.fromstring(body)


class DeckTest(unittest.TestCase):

    def test_a_table_slide_carries_a_native_table(self):
        record = figures.render(figures.make("table", SPEC, caption="Risk register", why="two rows"),
                                bundle())
        built = {"format": deck.DECK_FORMAT, "slides": [
            deck.slide("title", claim="A deck"),
            deck.slide("table", claim="The register", table=record["id"]),
        ]}
        data = deck.render(built, {record["id"]: record})
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            slide = archive.read("ppt/slides/slide2.xml")
        self.assertIn(b"<a:tbl>", slide)
        self.assertIn(b"Supplier concentration", slide)
        self.assertIn(b"50.00", slide)

    def test_a_table_slide_naming_a_missing_figure_is_refused(self):
        built = {"format": deck.DECK_FORMAT, "slides": [
            deck.slide("title", claim="A deck"),
            deck.slide("table", claim="The register", table="fig_missing"),
        ]}
        with self.assertRaises(deck.DeckError):
            deck.validate(built, [])


if __name__ == "__main__":
    unittest.main()
