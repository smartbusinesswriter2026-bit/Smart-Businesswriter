"""Canvas writing: the standard layouts, the blocks and the register.

The canvas profiles are data; this test holds the layout order the owner's
guideline calls the standard presentation, and the block keys the profile and
the layout must agree on.
"""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import framework_profiles, matrix  # noqa: E402


def figure(template):
    profile = framework_profiles.profile_for(template)
    cells = {block["key"]: {"label": block["label"], "bullets": []}
             for block in profile["blocks"]}
    return matrix.build(template, cells)


class CanvasLayoutTest(unittest.TestCase):
    def test_the_business_model_canvas_has_the_nine_blocks_and_the_standard_grid(self):
        fig = figure("template_business_model_canvas")
        self.assertEqual(fig["kind"], "canvas")
        labels = [cell["label"].lower() for grid in fig["grids"] for row in grid["rows"]
                  for cell in row if cell["label"]]
        for required in ("key partners", "key activities", "key resources",
                         "value propositions", "customer relationships", "channels",
                         "customer segments", "cost structure", "revenue streams"):
            self.assertIn(required, labels)
        self.assertEqual(len(fig["grids"]), 2)

    def test_the_lean_canvas_has_the_nine_blocks_and_the_standard_grid(self):
        fig = figure("template_lean_canvas")
        labels = [cell["label"].lower() for grid in fig["grids"] for row in grid["rows"]
                  for cell in row if cell["label"]]
        for required in ("problem", "solution", "unique value proposition",
                         "unfair advantage", "customer segments", "key metrics",
                         "channels", "cost structure", "revenue streams"):
            self.assertIn(required, labels)

    def test_the_value_proposition_canvas_has_the_two_halves(self):
        fig = figure("template_value_proposition_canvas")
        labels = [cell["label"].lower() for grid in fig["grids"] for row in grid["rows"]
                  for cell in row if cell["label"]]
        for required in ("customer jobs", "pains", "gains", "products and services",
                         "pain relievers", "gain creators"):
            self.assertIn(required, labels)
        self.assertEqual(len(fig["grids"][0]["rows"]), 3)


if __name__ == "__main__":
    unittest.main()
