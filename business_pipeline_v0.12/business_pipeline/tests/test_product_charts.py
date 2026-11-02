import os
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import charts, export  # noqa: E402

SVG_TEXT = re.compile(r"<text[^>]*>(.*?)</text>", re.S)
NUMBERS = re.compile(r"\d+(?:\.\d+)?")


def bundle(**overrides):
    base = product_fixtures.make_bundle(**overrides)
    base["delivery"]["appendix"]["artifacts"] = [
        ["npv", ["npv", "annual", "entity", "base"], "npv = sum(cf / (1 + rate) ** t)"],
        ["irr", ["irr", "annual", "entity", "base"], "irr = root of npv"],
    ]
    base["reperform"]["outputs"] = {"npv": "50.00", "irr": "0.21"}
    return base


BAR = {"format": "bp-chart/1", "kind": "bar", "title": "Capital budgeting",
       "series": [{"label": "Net present value", "artifact": "npv"},
                  {"label": "Internal rate", "artifact": "irr"}]}


class ChartTest(unittest.TestCase):
    def test_a_bar_chart_shows_the_stored_values_only(self):
        svg = charts.render_svg(bundle(), BAR)
        self.assertTrue(svg.startswith("<svg"))
        ET.fromstring(svg)                       # well-formed XML
        text = " ".join(SVG_TEXT.findall(svg))
        self.assertIn("50.00", text)
        self.assertIn("0.21", text)
        self.assertIn("Net present value", text)
        shown = set(NUMBERS.findall(text)) - {"50.00", "0.21"}
        self.assertEqual(shown, set(), "the chart printed a number that is not a stored value")

    def test_rendering_is_deterministic(self):
        first = charts.render_svg(bundle(), BAR)
        second = charts.render_svg(bundle(), BAR)
        self.assertEqual(first, second)

    def test_other_kinds_render(self):
        for kind in ("line", "stacked_bar", "waterfall", "pie"):
            svg = charts.render_svg(bundle(), dict(BAR, kind=kind))
            ET.fromstring(svg)
            self.assertIn("50.00", svg)
            self.assertIn("0.21", svg)
        sparkline = charts.render_svg(bundle(), dict(BAR, kind="sparkline"))
        ET.fromstring(sparkline)
        self.assertNotIn("50.00", sparkline)   # a sparkline carries no printed values by design

    def test_the_table_kind_lists_every_recorded_artifact(self):
        svg = charts.render_svg(bundle(), {"format": "bp-chart/1", "kind": "table", "title": "Recorded artifacts"})
        self.assertIn("npv", svg); self.assertIn("irr", svg); self.assertIn("50.00", svg)

    def test_a_missing_artifact_is_refused(self):
        with self.assertRaises(charts.ChartError) as caught:
            charts.render_svg(bundle(), {"format": "bp-chart/1", "kind": "bar", "title": "Assets",
                                         "series": [{"label": "Missing", "artifact": "wacc"}]})
        self.assertIn("no stored artifact", str(caught.exception))

    def test_digits_in_labels_are_refused(self):
        for field in ("title",):
            spec = dict(BAR); spec[field] = "Value for 2025"
            with self.assertRaises(charts.ChartError):
                charts.render_svg(bundle(), spec)
        bad_series = {"format": "bp-chart/1", "kind": "bar", "title": "Chart",
                      "series": [{"label": "Year 2025", "artifact": "npv"}]}
        with self.assertRaises(charts.ChartError):
            charts.render_svg(bundle(), bad_series)

    def test_a_non_numeric_value_is_refused(self):
        raw = bundle()
        raw["reperform"]["outputs"]["npv"] = "n/a"
        with self.assertRaises(charts.ChartError):
            charts.render_svg(raw, BAR)

    def test_charts_embed_in_the_html_export(self):
        with tempfile.TemporaryDirectory() as folder:
            target = os.path.join(folder, "case.html")
            export.export_html(bundle(), target, charts=[dict(BAR, kind="bar")])
            document = open(target, encoding="utf-8").read()
            self.assertIn("<svg", document)
            self.assertIn("50.00", document)
            self.assertIn("nothing in this file was recomputed", document)


if __name__ == "__main__":
    unittest.main()
