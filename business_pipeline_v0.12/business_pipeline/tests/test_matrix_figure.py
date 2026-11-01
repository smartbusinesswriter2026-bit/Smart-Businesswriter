"""The figure slot on a paper section and the Word table that draws it."""

import io
import unittest
import zipfile

import sys
sys.path.insert(0, "src")

from bp.product import docx, matrix, paper  # noqa: E402


def _body(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return archive.read("word/document.xml").decode("utf-8")


FIGURE = {
    "kind": "quadrant",
    "caption": "SWOT matrix",
    "note": "Strengths and weaknesses are the firm's own.",
    "grids": [{
        "title": None,
        "rows": [
            [{"label": "Strengths", "bullets": ["Own bakery network"], "gap": None},
             {"label": "Weaknesses", "bullets": [], "gap": "No weaknesses were supplied."}],
            [{"label": "Opportunities", "bullets": ["Retail growth"], "gap": None},
             {"label": "Threats", "bullets": [], "gap": "No threats were supplied."}],
        ],
        "axis_x": None,
        "axis_y": None,
        "col_widths": [0.5, 0.5],
    }],
}


class FigureSlotTest(unittest.TestCase):
    def test_a_section_carries_a_figure(self):
        item = paper.section("SWOT", paper.H1, [], figure=FIGURE)
        self.assertIs(item["figure"], FIGURE)
        self.assertEqual(item["lines"], [])

    def test_a_section_without_a_figure_has_none(self):
        self.assertIsNone(paper.section("Intro", paper.H1, ["Body."])["figure"])

    def test_figure_text_joins_every_string_in_the_figure(self):
        text = paper.figure_text(FIGURE)
        self.assertIn("Strengths", text)
        self.assertIn("Own bakery network", text)
        self.assertIn("No threats were supplied.", text)


class FigureCheckTest(unittest.TestCase):
    def test_template_text_in_a_figure_blocks_the_export(self):
        sections = [
            {"heading": "Introduction", "level": 1, "lines": ["Body."]},
            {"heading": "SWOT", "level": 1, "lines": [], "figure": dict(
                FIGURE, grids=[{"title": None, "rows": [[
                    {"label": "Strengths", "bullets": ["(your analysis)"], "gap": None},
                    {"label": "Weaknesses", "bullets": [], "gap": None}]],
                    "axis_x": None, "axis_y": None, "col_widths": [0.5, 0.5]}])},
            {"heading": "Conclusion", "level": 1, "lines": ["Done."]},
            {"heading": "References", "level": 1, "lines": ["Ref."]},
        ]
        issues = paper.check(sections, framework="swot", implications="A position.")
        self.assertTrue(any(issue["type"] == "meta_text" for issue in issues["issues"]), issues)


class FigureDocxTest(unittest.TestCase):
    def setUp(self):
        self.body = _body(docx.render_academic(
            "SWOT analysis", [{"heading": "SWOT", "level": 1, "lines": [], "figure": FIGURE}],
            "apa"))

    def test_the_figure_is_a_real_word_table(self):
        self.assertIn("<w:tbl>", self.body)
        self.assertIn("<w:gridCol", self.body)

    def test_the_figure_carries_its_apa_label_and_caption(self):
        self.assertIn("Figure 1", self.body)
        self.assertIn("SWOT matrix", self.body)

    def test_a_cell_with_no_bullets_shows_its_named_gap_not_an_empty_box(self):
        self.assertIn("No threats were supplied.", self.body)

    def test_figures_are_numbered_in_document_order(self):
        body = _body(docx.render_academic("Title", [
            {"heading": "SWOT", "level": 1, "lines": [], "figure": FIGURE},
            {"heading": "Ansoff", "level": 1, "lines": [], "figure": FIGURE}], "apa"))
        self.assertIn("Figure 1", body)
        self.assertIn("Figure 2", body)

    def test_a_paper_with_no_figure_renders_no_table(self):
        body = _body(docx.render_academic("Title", [
            {"heading": "Introduction", "level": 1, "lines": ["Body."]}], "apa"))
        self.assertNotIn("<w:tbl>", body)

    def test_the_same_sections_render_identical_bytes(self):
        first = docx.render_academic("SWOT analysis", [
            {"heading": "SWOT", "level": 1, "lines": [], "figure": FIGURE}], "apa")
        second = docx.render_academic("SWOT analysis", [
            {"heading": "SWOT", "level": 1, "lines": [], "figure": FIGURE}], "apa")
        self.assertEqual(first, second)


class LayoutRegistryTest(unittest.TestCase):
    def test_every_wave_one_template_has_a_layout(self):
        for template in ("template_swot", "template_ansoff", "template_value_chain",
                         "template_vrio", "template_mckinsey_7s", "template_bcg",
                         "template_ge_mckinsey", "template_blue_ocean_errc"):
            self.assertIsNotNone(matrix.layout_for(template), template)

    def test_a_template_without_a_layout_returns_none(self):
        self.assertIsNone(matrix.layout_for("template_pestel"))

    def test_the_swot_layout_is_a_two_by_two_with_no_axes(self):
        figure = matrix.build("template_swot", {})
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), 2)
        self.assertIsNone(figure["grids"][0]["axis_x"])
        self.assertIsNone(figure["grids"][0]["axis_y"])

    def test_the_ansoff_layout_carries_both_axes_in_the_canonical_order(self):
        figure = matrix.build("template_ansoff", {})
        grid = figure["grids"][0]
        self.assertEqual(grid["axis_x"], ("Existing products", "New products"))
        self.assertEqual(grid["axis_y"], ("Existing markets", "New markets"))
        self.assertEqual(grid["rows"][0][0]["label"], "Market development")
        self.assertEqual(grid["rows"][1][0]["label"], "Market penetration")

    def test_the_value_chain_layout_has_a_support_row_and_a_primary_row(self):
        figure = matrix.build("template_value_chain", {})
        grids = figure["grids"]
        self.assertEqual(len(grids), 2)
        self.assertEqual(grids[0]["title"], "Support activities")
        self.assertEqual(grids[1]["title"], "Primary activities")
        self.assertEqual(len(grids[0]["rows"][0]), 4)
        self.assertEqual(len(grids[1]["rows"][0]), 5)

    def test_the_mckinsey_layout_puts_shared_values_between_the_other_six(self):
        figure = matrix.build("template_mckinsey_7s", {})
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][0]["role"], "hub")
        self.assertEqual(rows[1][0]["span"], 3)

    def test_the_ge_mckinsey_layout_is_a_three_by_three(self):
        figure = matrix.build("template_ge_mckinsey", {})
        rows = figure["grids"][0]["rows"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(len(row) == 3 for row in rows))

    def test_a_cell_with_no_content_shows_its_gap_and_is_never_blank(self):
        cells = {"S": {"label": "Strengths", "bullets": [], "gap": "No strengths were supplied."}}
        figure = matrix.build("template_swot", cells)
        cell = figure["grids"][0]["rows"][0][0]
        self.assertEqual(cell["gap"], "No strengths were supplied.")
        self.assertEqual(cell["bullets"], [])

    def test_the_alias_map_lets_the_chat_keys_find_the_profile_keys(self):
        cells = {"strengths": {"label": "Strengths", "bullets": ["Own network"], "gap": None}}
        figure = matrix.build("template_swot", cells)
        self.assertEqual(figure["grids"][0]["rows"][0][0]["bullets"], ["Own network"])

    def test_a_template_without_a_layout_builds_none(self):
        self.assertIsNone(matrix.build("template_pestel", {}))


class ExportGateTest(unittest.TestCase):
    def test_a_paper_whose_figure_carries_template_text_cannot_be_exported(self):
        sections = [
            {"heading": "Introduction", "level": 1, "lines": ["Body."]},
            {"heading": "SWOT", "level": 1, "lines": [], "figure": dict(
                FIGURE, grids=[{"title": None, "rows": [[
                    {"label": "Strengths", "bullets": ["not supplied yet"], "gap": None},
                    {"label": "Weaknesses", "bullets": [], "gap": None}]],
                    "axis_x": None, "axis_y": None, "col_widths": [0.5, 0.5]}])},
            {"heading": "Conclusion", "level": 1, "lines": ["Done."]},
            {"heading": "References", "level": 1, "lines": ["Ref."]},
        ]
        issues = paper.check(sections, framework="swot", implications="A position.")
        self.assertTrue(any(issue["type"] == "meta_text" for issue in issues["issues"]), issues)


if __name__ == "__main__":
    unittest.main()
