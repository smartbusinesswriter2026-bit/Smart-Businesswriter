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


def schedule_bundle():
    base = product_fixtures.make_bundle()
    metrics = ("es_A", "ef_A", "ls_A", "lf_A", "float_A", "critical_A",
               "es_B", "ef_B", "ls_B", "lf_B", "float_B", "critical_B")
    base["delivery"]["appendix"]["artifacts"] = [
        [metric, [metric, "days", "entity", "base"], ""] for metric in metrics]
    base["reperform"]["outputs"] = {
        "es_A": "0", "ef_A": "3", "ls_A": "0", "lf_A": "3", "float_A": "0", "critical_A": "1",
        "es_B": "3", "ef_B": "7", "ls_B": "5", "lf_B": "9", "float_B": "2", "critical_B": "0"}
    return base


GANTT = {"format": "bp-chart/1", "kind": "gantt", "title": "Project schedule",
         "activities": [{"label": "Survey", "start": "es_A", "end": "ef_A",
                         "float": "float_A", "critical": "critical_A"},
                        {"label": "Build", "start": "es_B", "end": "ef_B",
                         "float": "float_B", "critical": "critical_B"}]}


class GanttTest(unittest.TestCase):
    def test_a_gantt_chart_draws_the_stored_dates_and_critical_path(self):
        svg = charts.render_svg(schedule_bundle(), GANTT)
        ET.fromstring(svg)
        text = " ".join(SVG_TEXT.findall(svg))
        self.assertIn("Survey", text)
        self.assertIn("0 to 3", text)
        self.assertIn("Build", text)
        self.assertIn("3 to 7", text)
        self.assertIn("#e15759", svg)           # the critical bar is marked
        self.assertEqual(svg, charts.render_svg(schedule_bundle(), GANTT))

    def test_a_gantt_chart_draws_declared_dependency_arrows(self):
        spec = {**GANTT, "activities": [
            {"id": "A", "label": "Survey", "start": "es_A", "end": "ef_A"},
            {"id": "B", "label": "Build", "start": "es_B", "end": "ef_B"}],
            "dependencies": [{"from": "A", "to": "B"}]}
        svg = charts.render_svg(schedule_bundle(), spec)
        ET.fromstring(svg)
        self.assertIn("<polyline", svg)
        self.assertEqual(svg, charts.render_svg(schedule_bundle(), spec))
        bad = {**spec, "dependencies": [{"from": "A", "to": "Z"}]}
        with self.assertRaises(charts.ChartError):
            charts.render_svg(schedule_bundle(), bad)

    def test_a_finish_before_the_start_is_refused(self):
        raw = schedule_bundle()
        raw["reperform"]["outputs"]["ef_A"] = "-1"
        with self.assertRaises(charts.ChartError):
            charts.render_svg(raw, GANTT)

    def test_a_missing_activity_artifact_is_refused(self):
        spec = dict(GANTT)
        spec["activities"] = [{"label": "Survey", "start": "es_A", "end": "ef_missing"}]
        with self.assertRaises(charts.ChartError):
            charts.render_svg(schedule_bundle(), spec)

    def test_a_label_with_digits_is_refused(self):
        spec = dict(GANTT)
        spec["activities"] = [{"label": "Activity 1", "start": "es_A", "end": "ef_A"}]
        with self.assertRaises(charts.ChartError):
            charts.render_svg(schedule_bundle(), spec)


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
