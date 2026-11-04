import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, "src")
from bp.product import diagrams  # noqa: E402

PROCESS = {"format": "bp-diagram/1", "kind": "process", "title": "Decision path",
           "items": [{"label": "Collect evidence"}, {"label": "Freeze the model"}, {"label": "Deliver"}]}
MATRIX = {"format": "bp-diagram/1", "kind": "matrix2x2", "title": "Portfolio view",
          "x_axis": "Certainty", "y_axis": "Size",
          "quadrants": {"top_left": "Bet", "top_right": "Core", "bottom_left": "Exit", "bottom_right": "Option"}}
TREE = {"format": "bp-diagram/1", "kind": "tree", "title": "Object breakdown",
        "root": "Business case", "children": [{"label": "Evidence"}, {"label": "Analysis"}, {"label": "Decision"}]}


class DiagramTest(unittest.TestCase):
    def test_every_kind_renders_well_formed_svg_from_labels_only(self):
        cases = [PROCESS, MATRIX, TREE,
                 {"format": "bp-diagram/1", "kind": "pyramid", "title": "Hierarchy",
                  "items": [{"label": "Vision"}, {"label": "Strategy"}, {"label": "Tactics"}]},
                 {"format": "bp-diagram/1", "kind": "funnel", "title": "Pipeline",
                  "items": [{"label": "Leads"}, {"label": "Qualified"}, {"label": "Won"}]}]
        for spec in cases:
            svg = diagrams.render_svg(spec)
            ET.fromstring(svg)
            self.assertIn("<svg", svg)
            self.assertIn("Structure only", svg)
        self.assertIn("Collect evidence", diagrams.render_svg(PROCESS))
        self.assertIn("Core", diagrams.render_svg(MATRIX))
        self.assertIn("Evidence", diagrams.render_svg(TREE))

    def test_rendering_is_deterministic(self):
        self.assertEqual(diagrams.render_svg(PROCESS), diagrams.render_svg(PROCESS))

    def test_digits_in_labels_are_refused(self):
        bad = {"format": "bp-diagram/1", "kind": "process", "title": "Path",
               "items": [{"label": "Step one"}, {"label": "Step 2025"}]}
        with self.assertRaises(diagrams.DiagramError):
            diagrams.render_svg(bad)
        with self.assertRaises(diagrams.DiagramError):
            diagrams.render_svg({**PROCESS, "title": "Path 2"})

    def test_malformed_specs_are_refused(self):
        for bad in ({}, {"format": "bp-diagram/1", "kind": "unknown", "title": "x"},
                    {"format": "bp-diagram/1", "kind": "process", "title": "x"},
                    {"format": "bp-diagram/1", "kind": "matrix2x2", "title": "x"},
                    {"format": "bp-diagram/1", "kind": "tree", "title": "x"}):
            with self.assertRaises(diagrams.DiagramError):
                diagrams.render_svg(bad)

    def test_export_writes_an_svg_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "diagram.svg")
            written = diagrams.export_svg(PROCESS, path)
            self.assertEqual(written, path)
            self.assertTrue(open(path, encoding="utf-8").read().startswith("<svg"))


if __name__ == "__main__":
    unittest.main()
