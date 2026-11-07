"""One visual language, and the optional engines that read it.

The theme is the single place a colour or a type size is written.  The adapters
turn a validated diagram spec into Graphviz or Mermaid source; they are pure
functions, so they are tested without the tools installed.  A renderer that is
absent must fall back to the builtin SVG, never fail.
"""

import os
import sys
import unittest

sys.path.insert(0, "src")

from bp.product import charts, diagrams, renderers, theme  # noqa: E402

PROCESS = {"format": "bp-diagram/1", "kind": "process", "title": "Review cycle",
           "items": [{"label": "Draft"}, {"label": "Review"}, {"label": "Approve"}]}

TREE = {"format": "bp-diagram/1", "kind": "tree", "title": "Costs",
        "root": "Total cost", "children": [{"label": "Fixed"}, {"label": "Variable"}]}

MATRIX = {"format": "bp-diagram/1", "kind": "matrix2x2", "title": "Position",
          "quadrants": {"top_left": "A", "top_right": "B",
                        "bottom_left": "C", "bottom_right": "D"}}


class ThemeTest(unittest.TestCase):

    def test_the_series_colours_are_the_builtin_palette(self):
        self.assertEqual(theme.SERIES, tuple(charts.PALETTE))

    def test_the_tokens_carry_the_required_roles(self):
        palette = theme.TOKENS["palette"]
        for key in ("paper", "ink", "muted", "axis", "grid", "accent",
                    "positive", "negative", "neutral", "series"):
            self.assertIn(key, palette)

    def test_graphviz_attributes_come_from_the_tokens(self):
        attrs = theme.graphviz_attrs()
        self.assertEqual(attrs["node"]["fillcolor"], theme.TOKENS["palette"]["accent"])
        self.assertEqual(attrs["graph"]["bgcolor"], theme.TOKENS["palette"]["paper"])

    def test_the_pptx_colours_drop_the_hash(self):
        colours = theme.pptx_colors()
        self.assertFalse(colours["accent"].startswith("#"))
        self.assertEqual(len(colours["series"]), len(theme.SERIES))


class DotTest(unittest.TestCase):

    def test_a_process_becomes_a_chain(self):
        source = renderers.dot_source(PROCESS)
        self.assertIn("digraph process", source)
        self.assertIn('label="Draft"', source)
        self.assertIn("n0 -> n1", source)
        self.assertIn("n1 -> n2", source)

    def test_a_tree_becomes_a_root_and_children(self):
        source = renderers.dot_source(TREE)
        self.assertIn('label="Total cost"', source)
        self.assertIn("root -> c0", source)
        self.assertIn("root -> c1", source)

    def test_a_grid_has_no_dot_program(self):
        self.assertIsNone(renderers.dot_source(MATRIX))

    def test_a_bad_spec_returns_none_rather_than_raising(self):
        self.assertIsNone(renderers.dot_source(None))
        self.assertIsNone(renderers.dot_source({"kind": "process", "items": []}))


class MermaidTest(unittest.TestCase):

    def test_a_process_becomes_a_flowchart(self):
        source = renderers.mermaid_source(PROCESS)
        self.assertTrue(source.startswith("flowchart TD"))
        self.assertIn('n0["Draft"]', source)
        self.assertIn("n0 --> n1", source)

    def test_a_tree_becomes_a_root_and_children(self):
        source = renderers.mermaid_source(TREE)
        self.assertIn('r["Total cost"]', source)
        self.assertIn("r --> c0", source)

    def test_a_funnel_has_no_mermaid_program(self):
        self.assertIsNone(renderers.mermaid_source(
            {"kind": "funnel", "title": "Sales", "items": [{"label": "A"}, {"label": "B"}]}))

    def test_a_quote_in_a_label_cannot_break_the_source(self):
        spec = {"kind": "process", "title": "Review",
                "items": [{"label": 'Say "go"'}, {"label": "Stop"}]}
        source = renderers.mermaid_source(spec)
        self.assertIn("Say 'go'", source)


class FallbackTest(unittest.TestCase):

    def test_a_diagram_still_draws_when_no_engine_is_installed(self):
        figure = {"kind": "diagram", "spec": PROCESS}
        markup = renderers.svg(figure)
        self.assertIn("<svg", markup)

    def test_available_reports_the_builtin_renderer_always(self):
        self.assertTrue(renderers.available()["builtin"])

    def test_plotly_is_absent_or_a_template(self):
        template = theme.plotly_template()
        if renderers.available()["plotly"]:
            self.assertIsNotNone(template)
        else:
            self.assertIsNone(template)


if __name__ == "__main__":
    unittest.main()
