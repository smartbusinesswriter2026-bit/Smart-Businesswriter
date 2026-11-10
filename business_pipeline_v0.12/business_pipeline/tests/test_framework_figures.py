"""Framework charts use the existing chart/diagram modules, and only recorded values."""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import framework_figures  # noqa: E402


BAR = {"kind": "bar", "title": "Score by S",
       "points": [{"label": "Sort", "value": "3"},
                  {"label": "Set in order", "value": "2"},
                  {"label": "Shine", "value": "4"}]}


class FrameworkFigureTest(unittest.TestCase):
    def test_a_bar_chart_is_a_normal_figure_with_a_digest(self):
        figure = framework_figures.build(BAR, caption="Score by S")
        self.assertEqual(figure["kind"], "chart")
        self.assertEqual(figure["spec"]["kind"], "bar")
        self.assertEqual(len(figure["rows"]), 3)
        self.assertTrue(figure.get("digest"))
        self.assertTrue((figure.get("asset") or {}).get("svg"))

    def test_a_value_the_record_does_not_hold_is_refused(self):
        with self.assertRaises(framework_figures.ChartError) as refused:
            framework_figures.validate_chart(BAR, allowed_values=[1, 2, 3])
        self.assertIn("does not hold", str(refused.exception))

    def test_a_pareto_needs_a_cumulative(self):
        chart = {"kind": "pareto", "title": "RPN by failure mode",
                 "points": [{"label": "Seal leaks", "value": "120"}]}
        with self.assertRaises(framework_figures.ChartError) as refused:
            framework_figures.build(chart, caption="RPN by failure mode")
        self.assertIn("cumulative", str(refused.exception).lower())

    def test_a_tree_uses_the_diagram_module(self):
        chart = {"kind": "tree", "title": "Why-chain",
                 "root": "Seal leaks", "children": ["Worn tool", "Wrong torque"]}
        figure = framework_figures.build(chart, caption="Why chain")
        self.assertEqual(figure["kind"], "diagram")
        self.assertEqual(figure["spec"]["kind"], "tree")
        self.assertEqual(len(figure["spec"]["children"]), 2)

    def test_a_caption_with_a_digit_is_refused(self):
        with self.assertRaises(framework_figures.ChartError):
            framework_figures.build(BAR, caption="5S score by S")

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(framework_figures.ChartError):
            framework_figures.build({"kind": "bubble", "title": "x", "points": []})


if __name__ == "__main__":
    unittest.main()
