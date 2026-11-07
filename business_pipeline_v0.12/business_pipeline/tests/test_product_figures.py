"""The figure record, the auto-triggers, and a chart in a Word paper.

The point of these tests is the promise, not the pixels: a figure is drawn only
from stored values, it is referenced by id, it is caught when the record moves,
and it reaches a .docx as a real picture - or, with no rasterizer installed, as
the stored values themselves.
"""

import base64
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
from bp.product import charts, chat, docx, figure_plan, figures, paper  # noqa: E402

#: A real 1x1 PNG, so the test exercises the picture path without a rasterizer.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

BAR = {"format": "bp-chart/1", "kind": "bar", "title": "Recorded results",
       "series": [{"label": "Net present value", "artifact": "npv"},
                  {"label": "Internal rate", "artifact": "irr"}]}

DIAGRAM = {"format": "bp-diagram/1", "kind": "process", "title": "Review cycle",
           "items": [{"label": "Draft"}, {"label": "Review"}]}


def bundle():
    base = product_fixtures.make_bundle()
    base["delivery"]["appendix"]["artifacts"] = [
        ["npv", ["npv", "annual", "entity", "base"], "npv = sum(cf / (1 + rate) ** t)"],
        ["irr", ["irr", "annual", "entity", "base"], "irr = root of npv"],
    ]
    base["reperform"]["outputs"] = {"npv": "50.00", "irr": "0.21"}
    return base


def schedule_bundle():
    base = product_fixtures.make_bundle()
    metrics = ("es_A", "ef_A", "float_A", "critical_A",
               "es_B", "ef_B", "float_B", "critical_B")
    base["delivery"]["appendix"]["artifacts"] = [
        [metric, [metric, "days", "entity", "base"], ""] for metric in metrics]
    base["reperform"]["outputs"] = {
        "es_A": "0", "ef_A": "3", "float_A": "0", "critical_A": "1",
        "es_B": "3", "ef_B": "7", "float_B": "2", "critical_B": "0"}
    return base


class RecordTest(unittest.TestCase):

    def test_a_chart_figure_carries_its_sources_and_a_reason(self):
        figure = figures.make("chart", BAR, caption="Recorded results",
                              why="the block records two points")
        self.assertEqual(figure["sources"], ["npv", "irr"])
        self.assertTrue(figure["id"].startswith("fig_"))
        self.assertEqual(figures.validate(figure)["caption"], "Recorded results")

    def test_a_caption_may_not_carry_a_number(self):
        with self.assertRaises(figures.FigureError):
            figures.make("chart", BAR, caption="Revenue grew 18 percent",
                         why="the block records two points")

    def test_a_figure_without_a_reason_is_refused(self):
        with self.assertRaises(figures.FigureError):
            figures.make("chart", BAR, caption="Recorded results", why="")

    def test_a_diagram_may_not_smuggle_a_number(self):
        bad = {"format": "bp-diagram/1", "kind": "process", "title": "Phase 2",
               "items": [{"label": "Draft"}, {"label": "Review"}]}
        with self.assertRaises(Exception):
            figures.make("diagram", bad, caption="Review cycle", why="the process has two steps")

    def test_the_same_spec_and_caption_name_the_same_figure(self):
        first = figures.make("chart", BAR, caption="Recorded results", why="two points")
        second = figures.make("chart", BAR, caption="Recorded results", why="two points")
        self.assertEqual(first["id"], second["id"])

    def test_text_includes_the_spec_so_a_template_instruction_cannot_hide(self):
        figure = figures.make("chart", BAR, caption="Recorded results", why="two points")
        self.assertIn("Recorded results", figures.text(figure))
        self.assertIn("Net present value", figures.text(figure))

    def test_the_digest_moves_when_a_stored_value_moves(self):
        record = figures.make("chart", BAR, caption="Recorded results", why="two points")
        figures.stamp(record, bundle())
        self.assertFalse(figures.stale(record, bundle()))
        moved = bundle()
        moved["reperform"]["outputs"] = {"npv": "51.00", "irr": "0.21"}
        self.assertTrue(figures.stale(record, moved))

    def test_the_registry_round_trips(self):
        record = figures.make("chart", BAR, caption="Recorded results", why="two points")
        registry = figures.Registry.from_list([record])
        self.assertEqual(len(registry), 1)
        self.assertEqual(registry.get(record["id"])["caption"], "Recorded results")

    def test_render_attaches_the_svg_and_the_stored_values(self):
        record = figures.render(
            figures.make("chart", BAR, caption="Recorded results", why="two points"),
            bundle())
        self.assertIn("<svg", record["asset"]["svg"])
        self.assertEqual(record["rows"], [("Net present value", "50.00"),
                                          ("Internal rate", "0.21")])


class PlanTest(unittest.TestCase):

    def test_a_schedule_becomes_a_gantt_from_the_stored_dates(self):
        proposed = figure_plan.propose(schedule_bundle())
        self.assertEqual(len(proposed), 1)
        self.assertEqual(proposed[0]["spec"]["kind"], "gantt")
        self.assertIn("early start", proposed[0]["why"])

    def test_a_single_scalar_draws_nothing(self):
        plan = {"blocks": [{"label": "Result", "key": "result",
                            "series": [{"label": "Net present value", "artifact": "npv"}]}]}
        proposed, skipped = figure_plan.explain(bundle(), plan)
        self.assertEqual(proposed, [])
        self.assertEqual(skipped[0]["block"], "Result")

    def test_a_declared_series_draws_a_line(self):
        plan = {"blocks": [{"label": "Trend", "section": "Results",
                            "series": [{"label": "Net present value", "artifact": "npv"},
                                       {"label": "Internal rate", "artifact": "irr"}]}]}
        proposed = figure_plan.propose(bundle(), plan)
        self.assertEqual(proposed[0]["spec"]["kind"], "bar")  # two points is a comparison, not a trend
        self.assertEqual(proposed[0]["place"], "Results")

    def test_a_figure_is_placed_under_the_section_it_names(self):
        record = figures.make("chart", BAR, caption="Recorded results",
                              why="two points", place="Results")
        sections = [paper.section("Results", paper.H1, []),
                    paper.section("Conclusion", paper.H1, [])]
        placed_sections, placed, unplaced = figure_plan.attach(sections, [record])
        self.assertEqual(len(placed), 1)
        self.assertEqual(unplaced, [])
        self.assertEqual(placed_sections[0]["figure"]["id"], record["id"])

    def test_a_figure_for_a_missing_section_is_reported_not_dropped(self):
        record = figures.make("chart", BAR, caption="Recorded results",
                              why="two points", place="Nowhere")
        sections = [paper.section("Results", paper.H1, [])]
        _, placed, unplaced = figure_plan.attach(sections, [record])
        self.assertEqual(placed, [])
        self.assertEqual(unplaced[0]["id"], record["id"])


class WordImageTest(unittest.TestCase):

    def _parts(self, data):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def test_a_rendered_chart_reaches_the_paper_as_a_picture(self):
        figure = {"caption": "Recorded results", "note": "Source: stored artifacts",
                  "asset": {"png": PNG_1X1}, "rows": [("Net present value", "50.00")]}
        sections = [{"heading": "Results", "level": 1, "lines": ["A line."], "figure": figure}]
        parts = self._parts(docx.render_academic("A paper", sections))
        self.assertIn("word/media/figure1.png", parts)
        self.assertIn(b'Extension="png"', parts["[Content_Types].xml"])
        self.assertIn(b"relationships/image", parts["word/_rels/document.xml.rels"])
        body = parts["word/document.xml"]
        self.assertIn(b"<w:drawing>", body)
        self.assertIn(b"r:embed=\"rId3\"", body)
        ET.fromstring(body)  # the document is well-formed

    def test_without_a_rasterizer_the_stored_values_still_reach_the_paper(self):
        figure = {"caption": "Recorded results", "note": "",
                  "asset": {"png": None}, "rows": [("Net present value", "50.00")]}
        sections = [{"heading": "Results", "level": 1, "lines": [], "figure": figure}]
        parts = self._parts(docx.render_academic("A paper", sections))
        body = parts["word/document.xml"]
        self.assertNotIn(b"<w:drawing>", body)
        self.assertIn(b"50.00", body)
        self.assertIn(b"Values as recorded.", body)
        self.assertNotIn("word/media/figure1.png", parts)

    def test_two_charts_get_two_media_parts_and_two_relationships(self):
        one = {"caption": "First", "asset": {"png": PNG_1X1}, "rows": []}
        two = {"caption": "Second", "asset": {"png": PNG_1X1}, "rows": []}
        sections = [{"heading": "One", "level": 1, "lines": [], "figure": one},
                    {"heading": "Two", "level": 1, "lines": [], "figure": two}]
        parts = self._parts(docx.render_academic("A paper", sections))
        self.assertIn("word/media/figure1.png", parts)
        self.assertIn("word/media/figure2.png", parts)
        rels = parts["word/_rels/document.xml.rels"]
        self.assertIn(b"rId3", rels)
        self.assertIn(b"rId4", rels)


class IntegrationTest(unittest.TestCase):

    def test_a_bundle_with_a_schedule_draws_its_figure_without_being_asked(self):
        sections = [{"heading": "Schedule", "level": 1, "lines": ["A line."]}]
        data = docx.render_academic("A paper", sections, bundle=schedule_bundle())
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            body = archive.read("word/document.xml")
        self.assertIn(b"Figure 1. Project schedule", body)

    def test_a_figure_for_a_section_the_paper_lacks_is_not_dropped_in(self):
        sections = [{"heading": "Introduction", "level": 1, "lines": ["A line."]}]
        data = docx.render_academic("A paper", sections, bundle=schedule_bundle())
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            body = archive.read("word/document.xml")
        self.assertNotIn(b"Figure 1.", body)

    def test_specs_splits_charts_and_diagrams(self):
        chart = figures.make("chart", BAR, caption="Recorded results", why="two points")
        diagram = figures.make("diagram", DIAGRAM, caption="Review cycle", why="two steps")
        charts, diagrams = figures.specs([chart, diagram])
        self.assertEqual(len(charts), 1)
        self.assertEqual(len(diagrams), 1)

    def test_rendering_twice_with_a_bundle_is_stable(self):
        sections = [{"heading": "Schedule", "level": 1, "lines": []}]
        one = docx.render_academic("A paper", sections, bundle=schedule_bundle())
        two = docx.render_academic("A paper", sections, bundle=schedule_bundle())
        self.assertEqual(one, two)

    def test_a_figure_that_cannot_be_drawn_is_reported_not_fatal(self):
        plan = {"blocks": [{"label": "Trend", "section": "Results",
                            "figure": {"format": "bp-chart/1", "kind": "bar", "title": "Trend",
                                       "series": [{"label": "Missing", "artifact": "nope"}]}}]}
        sections = [{"heading": "Results", "level": 1, "lines": []}]
        sections, report = figure_plan.build(bundle(), sections, plan)
        self.assertEqual(report["placed"], [])
        self.assertTrue(report["skipped"])
        self.assertIsNone(sections[0].get("figure"))


class FiguresRouteTest(unittest.TestCase):

    def setUp(self):
        import tempfile
        from bp.product import api
        self.api = api
        self.root = tempfile.mkdtemp(prefix="bp-figures-api-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        import shutil
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def _store(self):
        status, stored = self.api.handle("POST", "/api/cases", bundle())
        self.assertEqual(status, 201)
        return stored["id"]

    def test_a_figure_is_previewed_and_not_stored_until_confirmed(self):
        case_id = self._store()
        status, payload = self.api.handle(
            "POST", "/api/cases/%s/figures" % case_id,
            {"chart": BAR, "caption": "Recorded results"})
        self.assertEqual(status, 200)
        self.assertIn("<svg", payload["svg"])
        self.assertFalse(payload.get("saved"))
        status, listed = self.api.handle("GET", "/api/cases/%s/figures" % case_id)
        self.assertEqual(listed["figures"], [])

    def test_confirm_stores_the_record_without_its_bytes(self):
        case_id = self._store()
        status, payload = self.api.handle(
            "POST", "/api/cases/%s/figures" % case_id,
            {"chart": BAR, "caption": "Recorded results", "confirm": True})
        self.assertEqual(status, 200)
        self.assertTrue(payload["saved"])
        status, listed = self.api.handle("GET", "/api/cases/%s/figures" % case_id)
        self.assertEqual(len(listed["figures"]), 1)
        self.assertNotIn("asset", listed["figures"][0])
        self.assertIn("digest", listed["figures"][0])

    def test_a_caption_with_a_number_is_refused(self):
        case_id = self._store()
        status, payload = self.api.handle(
            "POST", "/api/cases/%s/figures" % case_id,
            {"chart": BAR, "caption": "Revenue grew 18 percent"})
        self.assertEqual(status, 422)
        self.assertIn("digit", payload["error"])


class ChatPaperTest(unittest.TestCase):

    def _state(self, computation, values, brief=None):
        from bp import methods
        import tests.test_capabilities as caps

        chat.set_method_compute(lambda name, inputs: methods.LIBRARY[name].impl(inputs),
                                methods.describe)
        state = caps.draftable(caps.answer_all(chat.start(
            brief or caps.BRIEF, "management", "pestel")))
        chat.attach_computation(state, computation, values)
        return chat.draft(state, accepted_ids=[],
                          implications="The declared figures set the result.")

    def test_a_declared_series_reaches_the_paper_as_a_chart_when_ticked(self):
        state = self._state(
            "npv", {"rate": "0.10", "cashflows": ["-100000", "40000", "40000", "40000", "40000"]},
            "The grocery chain appraises a branch in the Saudi market with a net present value "
            "on the declared cash flows.")
        proposed = chat.figure_selection(state)["proposed"]
        self.assertEqual(len(proposed), 1)
        chat.set_figure(state, proposed[0]["id"], True)
        data = chat.docx_bytes(state)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            body = archive.read("word/document.xml")
        self.assertTrue([name for name in names if name.startswith("word/media/")], names)
        self.assertIn(b"<w:drawing>", body)

    def test_incomparable_outputs_draw_no_chart_and_the_paper_still_exports(self):
        state = self._state("breakeven",
                            {"fixed": "40000", "price": "25", "variable": "12"})
        self.assertEqual(chat._figure_plan(state)["blocks"], [])
        data = chat.docx_bytes(state)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
        self.assertFalse([name for name in names if name.startswith("word/media/")], names)

    def test_a_ratio_paper_charts_the_comparable_group(self):
        state = self._state("ratio_analysis", {
            "current_assets": "5000", "current_liabilities": "2000", "cash": "800",
            "inventory": "1200", "receivables": "1500", "payables": "900",
            "total_assets": "12000", "total_liabilities": "7000", "equity": "5000",
            "revenue": "20000", "cost_of_sales": "12000", "operating_profit": "3000",
            "net_income": "1800", "interest_expense": "400"})
        blocks = chat._figure_plan(state)["blocks"]
        self.assertEqual(len(blocks), 1)
        labels = [item["label"] for item in blocks[0]["series"]]
        self.assertEqual(sorted(labels), ["Inventory Days", "Payables Days", "Receivables Days"])


class SavedFigureTest(unittest.TestCase):

    def _bundle_with_figure(self):
        base = bundle()
        record = figures.make("chart", BAR, caption="Recorded results", why="two points")
        base["figures"] = [{key: record[key] for key in
                            ("id", "format", "kind", "spec", "caption", "note", "why",
                             "origin", "place", "sources")}]
        return base

    def test_a_saved_figure_reaches_the_submission_paper(self):
        import shutil
        import tempfile
        from bp.product import deliverables

        root = tempfile.mkdtemp()
        try:
            path = os.path.join(root, "submission.docx")
            deliverables.write_export(self._bundle_with_figure(), "submission", "docx", path)
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                body = archive.read("word/document.xml")
            self.assertTrue([name for name in names if name.startswith("word/media/")], names)
            self.assertIn(b"<w:drawing>", body)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_saved_figure_reaches_the_workbook(self):
        import shutil
        import tempfile
        from bp.product import deliverables

        root = tempfile.mkdtemp()
        try:
            path = os.path.join(root, "workbook.xlsx")
            deliverables.write_export(self._bundle_with_figure(), "workpapers", "xlsx", path)
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
            self.assertTrue([name for name in names if name.startswith("xl/media/")], names)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_case_without_figures_keeps_the_report_it_had(self):
        from bp.product import docx
        plain = docx.render_bytes("A report", [("Result", ["A line."])])
        with_figures = docx.render_bytes("A report", [("Result", ["A line."])], figures=[])
        self.assertEqual(plain, with_figures)


if __name__ == "__main__":
    unittest.main()

class LabelRuleTest(unittest.TestCase):
    """A label may carry a digit only when it is the recorded value it names."""

    def _bundle(self):
        base = bundle()
        base["delivery"]["appendix"]["artifacts"].append(
            ["sprint_no", ["sprint_no", "count", "entity", "base"], ""])
        base["reperform"]["outputs"]["sprint_no"] = "3"
        return base

    def test_a_label_may_carry_a_recorded_number(self):
        spec = {"format": "bp-chart/1", "kind": "bar", "title": "Velocity",
                "series": [{"label": "Sprint 3", "label_artifact": "sprint_no",
                            "artifact": "npv"}]}
        self.assertIn("<svg", charts.render_svg(self._bundle(), spec))

    def test_a_label_that_does_not_match_the_record_is_refused(self):
        spec = {"format": "bp-chart/1", "kind": "bar", "title": "Velocity",
                "series": [{"label": "Sprint 4", "label_artifact": "sprint_no",
                            "artifact": "npv"}]}
        with self.assertRaises(charts.ChartError):
            charts.render_svg(self._bundle(), spec)

    def test_a_typed_number_is_still_refused(self):
        spec = {"format": "bp-chart/1", "kind": "bar", "title": "Velocity",
                "series": [{"label": "Sprint 3", "artifact": "npv"}]}
        with self.assertRaises(charts.ChartError):
            charts.render_svg(self._bundle(), spec)

class MultiSeriesTest(unittest.TestCase):
    """Two lines on one scale: a burndown, a burnup or a control chart."""

    def _bundle(self):
        base = bundle()
        artifacts = base["delivery"]["appendix"]["artifacts"]
        outputs = base["reperform"]["outputs"]
        for index in (1, 2, 3):
            for prefix, value in (("remaining", 30 - 5 * index), ("ideal", 30 - 6 * index)):
                key = "%s_%d" % (prefix, index)
                artifacts.append([key, [key, "", "entity", "base"], ""])
                outputs[key] = str(value)
            artifacts.append(["day_%d" % index, ["day_%d" % index, "", "entity", "base"], ""])
            outputs["day_%d" % index] = str(index)
        return base

    def _spec(self):
        series = []
        for group, prefix in (("Remaining", "remaining"), ("Ideal", "ideal")):
            for index in (1, 2, 3):
                series.append({"label": "Day %d" % index, "label_artifact": "day_%d" % index,
                               "artifact": "%s_%d" % (prefix, index), "group": group})
        return {"format": "bp-chart/1", "kind": "line", "title": "Sprint burndown",
                "series": series}

    def test_two_groups_draw_two_lines(self):
        svg = charts.render_svg(self._bundle(), self._spec())
        self.assertEqual(svg.count("<polyline"), 2)
        self.assertIn("Remaining", svg)
        self.assertIn("Ideal", svg)

    def test_the_label_rule_still_holds_in_a_group(self):
        spec = self._spec()
        spec["series"][0]["label"] = "Day 9"
        with self.assertRaises(charts.ChartError):
            charts.render_svg(self._bundle(), spec)

class ChatDeckTest(unittest.TestCase):
    """The drafted paper exports as a pitch deck, with the paper's own notes."""

    def test_the_chat_paper_exports_as_a_pitch_deck(self):
        from bp import methods
        import tests.test_capabilities as caps

        chat.set_method_compute(lambda name, inputs: methods.LIBRARY[name].impl(inputs),
                                methods.describe)
        state = caps.draftable(caps.answer_all(chat.start(caps.BRIEF, "management", "pestel")))
        chat.attach_computation(state, "breakeven",
                                {"fixed": "40000", "price": "25", "variable": "12"})
        state = chat.draft(state, accepted_ids=[],
                           implications="The branch must reach the break-even volume.")
        data = chat.pptx_bytes(state)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
        self.assertIn("ppt/presentation.xml", names)
        self.assertTrue([name for name in names if name.startswith("ppt/notesSlides/")], names)

    @unittest.skipUnless(__import__("bp.product.renderers", fromlist=["chrome"]).chrome(),
                         "no Chrome on this machine")
    def test_the_chat_paper_exports_as_a_pdf(self):
        from bp import methods
        import tests.test_capabilities as caps

        chat.set_method_compute(lambda name, inputs: methods.LIBRARY[name].impl(inputs),
                                methods.describe)
        state = caps.draftable(caps.answer_all(chat.start(caps.BRIEF, "management", "pestel")))
        state = chat.draft(state, accepted_ids=[],
                           implications="The branch must reach the break-even volume.")
        data = chat.pdf_bytes(state)
        self.assertTrue(data.startswith(b"%PDF-"))

class FigureTickTest(unittest.TestCase):
    """The system proposes a figure only when the data earns one, and the student ticks it."""

    def _state(self):
        from bp import methods
        import tests.test_capabilities as caps

        chat.set_method_compute(lambda name, inputs: methods.LIBRARY[name].impl(inputs),
                                methods.describe)
        state = caps.draftable(caps.answer_all(chat.start(
            "The grocery chain appraises a branch with a net present value on the declared cash flows.",
            "management", "pestel")))
        chat.attach_computation(state, "npv", {
            "rate": "0.10", "cashflows": ["-100000", "40000", "40000", "40000", "40000"]})
        return chat.draft(state, accepted_ids=[],
                          implications="The branch clears its cost of capital.")

    def test_a_figure_is_proposed_but_not_included_until_ticked(self):
        state = self._state()
        selection = chat.figure_selection(state)
        self.assertEqual(len(selection["proposed"]), 1)
        self.assertEqual(selection["selected"], [])
        data = chat.docx_bytes(state)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
        self.assertFalse([name for name in names if name.startswith("word/media/")], names)

    def test_ticking_includes_it_and_unticking_records_an_exclusion(self):
        state = self._state()
        ident = chat.figure_selection(state)["proposed"][0]["id"]
        chat.set_figure(state, ident, True)
        self.assertIn(ident, chat.figure_selection(state)["selected"])
        chat.set_figure(state, ident, False, "the table already shows the values")
        selection = chat.figure_selection(state)
        self.assertEqual(selection["selected"], [])
        self.assertEqual(selection["not_included"][0]["reason"],
                         "the table already shows the values")

    def test_an_unknown_figure_is_refused(self):
        state = self._state()
        with self.assertRaises(chat.ChatError):
            chat.set_figure(state, "fig_nope", True)

    def test_the_plan_carries_the_figure_selection(self):
        state = self._state()
        ident = chat.figure_selection(state)["proposed"][0]["id"]
        chat.set_figure(state, ident, True)
        self.assertEqual(chat._plan(state)["figures"]["selected"], [ident])
