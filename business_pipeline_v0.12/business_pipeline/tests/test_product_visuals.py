"""Standalone visuals: a figure without a paper.

The store is the visual's own; the source is named; the chart is proposed by rule
and confirmed by the student; the export is one file.
"""

import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp import methods  # noqa: E402
from bp.product import api, cases as case_store, chat, renderers, visuals  # noqa: E402

DECLARED = {"kind": "declared", "points": [
    {"label": "Q1", "value": "120000"}, {"label": "Q2", "value": "240000"},
    {"label": "Q3", "value": "360000"}, {"label": "Q4", "value": "480000"}]}


class StoreCase(unittest.TestCase):
    """A temporary case store and state directory, restored after each test."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-visuals-")
        self.previous = os.environ.get("BP_CASES_DIR")
        self.previous_state = os.environ.get("BP_STATE_DIR")
        os.environ["BP_CASES_DIR"] = self.root
        os.environ["BP_STATE_DIR"] = self.root

    def tearDown(self):
        for name, value in (("BP_CASES_DIR", self.previous),
                            ("BP_STATE_DIR", self.previous_state)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(self.root, ignore_errors=True)


class StoreTest(StoreCase):

    def test_a_visual_is_built_stored_listed_and_deleted(self):
        record = visuals.build({"title": "Revenue by quarter", "source": DECLARED, "kind": "line"})
        self.assertTrue(record["id"].startswith("vis_"))
        self.assertEqual(record["source"]["label"], "Figures you declared")
        self.assertEqual(visuals.load(record["id"])["title"], "Revenue by quarter")
        self.assertEqual(visuals.listing()["visuals"][0]["id"], record["id"])
        visuals.delete(record["id"])
        self.assertEqual(visuals.listing()["visuals"], [])

    def test_a_declared_point_needs_a_label_and_a_number(self):
        with self.assertRaises(visuals.VisualError):
            visuals.build({"title": "Bad", "source": {"kind": "declared",
                                                      "points": [{"label": "Q1"}]}})

    def test_an_unknown_source_kind_is_refused(self):
        with self.assertRaises(visuals.VisualError):
            visuals.build({"title": "Bad", "source": {"kind": "magic"}})

    def test_a_visual_needs_a_title(self):
        with self.assertRaises(visuals.VisualError):
            visuals.build({"source": DECLARED})


class ProposalTest(StoreCase):

    def test_the_words_choose_the_chart(self):
        plan = visuals.propose(DECLARED, "revenue trend by quarter")
        self.assertEqual(plan["proposals"][0]["kind"], "line")
        self.assertIn("line", plan["proposals"][0]["why"])

    def test_a_mix_points_at_a_pie(self):
        plan = visuals.propose(DECLARED, "revenue mix by product")
        self.assertEqual(plan["proposals"][0]["kind"], "pie")

    def test_a_fall_points_at_a_waterfall(self):
        source = {"kind": "declared", "points": [
            {"label": "Opening", "value": "900"}, {"label": "Churn", "value": "-140"},
            {"label": "Closing", "value": "760"}]}
        plan = visuals.propose(source, "how the base moved")
        self.assertEqual(plan["proposals"][0]["kind"], "waterfall")

    def test_at_most_three_kinds_are_offered(self):
        self.assertLessEqual(len(visuals.propose(DECLARED, "")["proposals"]), 3)


class SourceTest(StoreCase):

    def test_a_calculation_runs_the_frozen_method(self):
        visuals.set_method_compute(lambda name, inputs: methods.LIBRARY[name].impl(inputs))
        try:
            record = visuals.build({
                "title": "Break-even",
                "source": {"kind": "calculation", "method": "breakeven",
                           "inputs": {"fixed": "40000", "price": "25", "variable": "12"}}})
        finally:
            visuals.set_method_compute(None)
        self.assertIn("Computed by breakeven", record["source"]["label"])
        self.assertTrue(record["figures"][0]["sources"])

    def test_a_calculation_without_the_core_is_refused(self):
        visuals.set_method_compute(None)
        with self.assertRaises(visuals.VisualError):
            visuals.build({"title": "Break-even",
                           "source": {"kind": "calculation", "method": "breakeven",
                                      "inputs": {}}})

    def test_a_declared_visual_can_name_the_file_it_was_read_from(self):
        record = visuals.build({
            "title": "From a file", "kind": "bar",
            "source": {"kind": "declared",
                       "points": [{"label": "Q1", "value": "1"},
                                  {"label": "Q2", "value": "2"}],
                       "file": {"id": "abc", "filename": "sales.csv",
                                "sha256": "a" * 64,
                                "columns": {"label": "Quarter", "value": "Revenue"}}}})
        self.assertEqual(record["source"]["label"], "Figures read from sales.csv")
        self.assertEqual(record["source"]["file"]["filename"], "sales.csv")
        self.assertIn("sales.csv", record["figures"][0]["note"])
        self.assertIn("sales.csv",
                      record["bundle"]["delivery"]["appendix"]["artifacts"][0][2])

    def test_a_case_source_reads_the_recorded_artifacts(self):
        bundle = product_fixtures.make_bundle()
        bundle["delivery"]["appendix"]["artifacts"] = [
            ["npv", ["npv", "annual", "entity", "base"], ""],
            ["irr", ["irr", "annual", "entity", "base"], ""]]
        bundle["reperform"]["outputs"] = {"npv": "50.00", "irr": "0.21"}
        case_id = case_store.save(bundle)
        record = visuals.build({"title": "Recorded results",
                                "source": {"kind": "case", "case_id": case_id,
                                           "artifacts": ["npv", "irr"]}})
        self.assertEqual(record["source"]["case_id"], case_id)
        self.assertEqual(record["source"]["label"], "Recorded in this case")


class ExportTest(StoreCase):

    def setUp(self):
        super().setUp()
        self.record = visuals.build({"title": "Revenue by quarter", "source": DECLARED,
                                     "kind": "line"})

    def test_png_and_svg(self):
        data, name, _mime = visuals.export(self.record, "png")
        self.assertTrue(data.startswith(b"\x89PNG"))
        self.assertTrue(name.endswith(".png"))
        svg, _name, _mime = visuals.export(self.record, "svg")
        self.assertIn(b"<svg", svg)

    def test_a_word_figure_sheet(self):
        data, _name, _mime = visuals.export(self.record, "docx")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
        self.assertIn("word/document.xml", names)
        self.assertTrue([name for name in names if name.startswith("word/media/")], names)

    def test_a_one_slide_powerpoint(self):
        data, _name, _mime = visuals.export(self.record, "pptx")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
        self.assertIn("ppt/presentation.xml", names)
        self.assertIn("ppt/slides/slide2.xml", names)

    @unittest.skipUnless(renderers.chrome(), "no Chrome on this machine")
    def test_a_pdf(self):
        data, _name, _mime = visuals.export(self.record, "pdf")
        self.assertTrue(data.startswith(b"%PDF-"))

    def test_an_unknown_format_is_refused(self):
        with self.assertRaises(visuals.VisualError):
            visuals.export(self.record, "gif")


class RouteTest(StoreCase):

    def test_the_routes_create_list_read_and_export(self):
        status, plan = api.handle("POST", "/api/cases/visuals/plan",
                                  {"source": DECLARED, "words": "revenue trend"})
        self.assertEqual(status, 200)
        self.assertEqual(plan["proposals"][0]["kind"], "line")

        status, record = api.handle("POST", "/api/cases/visuals",
                                    {"title": "Revenue by quarter", "source": DECLARED,
                                     "kind": "line"})
        self.assertEqual(status, 201)
        visual_id = record["id"]

        status, listed = api.handle("GET", "/api/cases/visuals")
        self.assertEqual(status, 200)
        self.assertEqual(listed["visuals"][0]["id"], visual_id)

        status, _one = api.handle("GET", "/api/cases/visuals/" + visual_id)
        self.assertEqual(status, 200)

        status, payload = api.handle("POST", "/api/cases/visuals/" + visual_id + "/export",
                                     {"format": "pptx"})
        self.assertEqual(status, 200)
        self.assertTrue(payload["data"])
        self.assertEqual(payload["mime"],
                         "application/vnd.openxmlformats-officedocument.presentationml.presentation")

    def test_a_preview_is_drawn_but_not_stored(self):
        status, payload = api.handle("POST", "/api/cases/visuals",
                                     {"title": "Revenue", "source": DECLARED, "preview": True})
        self.assertEqual(status, 200)
        self.assertIn("<svg", payload["svg"])
        self.assertEqual(visuals.listing()["visuals"], [])

    def test_an_unknown_visual_is_not_found(self):
        status, _ = api.handle("GET", "/api/cases/visuals/vis_000000000000")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()

class AttachTest(StoreCase):
    """A standalone visual can be pulled into a paper and its deck."""

    def _state(self):
        from bp import methods
        import tests.test_capabilities as caps

        chat.set_method_compute(lambda name, inputs: methods.LIBRARY[name].impl(inputs),
                                methods.describe)
        state = caps.draftable(caps.answer_all(chat.start(
            "Should we enter the Saudi market? Use SWOT.", "management", "swot")))
        return chat.draft(state, accepted_ids=[], implications="The position is defensible.")

    def test_a_visual_reaches_the_paper_and_its_deck(self):
        record = visuals.build({"title": "Revenue by quarter", "source": DECLARED,
                                "kind": "line"})
        state = self._state()
        chat.attach_visual(state, record["id"])
        data = chat.docx_bytes(state)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
        self.assertTrue([name for name in names if name.startswith("word/media/")], names)
        deck = chat.pptx_bytes(state)
        with zipfile.ZipFile(io.BytesIO(deck)) as archive:
            deck_names = archive.namelist()
        self.assertTrue([name for name in deck_names if name.startswith("ppt/media/")], deck_names)

    def test_detaching_removes_it(self):
        record = visuals.build({"title": "Revenue by quarter", "source": DECLARED,
                                "kind": "line"})
        state = self._state()
        chat.attach_visual(state, record["id"])
        self.assertEqual(len(state.get("attached_visuals") or {}), 1)
        chat.detach_visual(state, record["id"])
        self.assertEqual(state.get("attached_visuals"), {})

    def test_an_unknown_visual_cannot_be_attached(self):
        state = self._state()
        with self.assertRaises(visuals.VisualError):
            chat.attach_visual(state, "vis_000000000000")


PARETO = {"kind": "declared", "points": [
    {"label": "Late delivery", "value": "42", "cumulative": "42"},
    {"label": "Damaged stock", "value": "27", "cumulative": "69"},
    {"label": "Wrong item", "value": "18", "cumulative": "87"},
    {"label": "Other", "value": "13", "cumulative": "100"}]}


class ParetoVisualTest(StoreCase):
    """A pareto is two declared columns: the value and the running total."""

    def test_a_declared_pareto_builds_and_draws_both_series(self):
        record = visuals.build({"title": "Complaint causes", "source": PARETO, "kind": "pareto"})
        self.assertEqual(record["figures"][0]["spec"]["kind"], "pareto")
        svg = visuals.export(record, "svg")[0].decode("utf-8")
        self.assertIn("<polyline", svg)
        self.assertIn("100", svg)

    def test_a_pareto_without_running_totals_is_refused(self):
        with self.assertRaises(visuals.VisualError):
            visuals.build({"title": "Complaint causes", "source": DECLARED, "kind": "pareto"})

    def test_the_words_can_point_at_a_pareto(self):
        plan = visuals.propose(PARETO, "the vital few causes")
        self.assertEqual(plan["proposals"][0]["kind"], "pareto")

    def test_a_pareto_is_not_proposed_without_running_totals(self):
        plan = visuals.propose(DECLARED, "the vital few causes")
        self.assertNotIn("pareto", [row["kind"] for row in plan["proposals"]])


class StatisticalChartTest(StoreCase):
    """Area, scatter and candlestick draw stored values only."""

    SCATTER = {"kind": "declared", "points": [
        {"label": "Ad spend", "value": "45000", "x": "1200"},
        {"label": "Footfall", "value": "30000", "x": "800"},
        {"label": "Referral", "value": "52000", "x": "1500"}]}

    CANDLES = {"kind": "declared", "points": [
        {"label": "Day one", "value": "110", "open": "100", "high": "120",
         "low": "90", "close": "110"},
        {"label": "Day two", "value": "105", "open": "110", "high": "115",
         "low": "100", "close": "105"}]}

    def test_an_area_chart_builds_and_draws_the_trend(self):
        record = visuals.build({"title": "Revenue trend", "source": DECLARED, "kind": "area"})
        self.assertEqual(record["figures"][0]["spec"]["kind"], "area")
        svg = visuals.export(record, "svg")[0].decode("utf-8")
        self.assertIn("<polygon", svg)
        self.assertIn("120000", svg)

    def test_a_scatter_builds_and_draws_both_values(self):
        record = visuals.build({"title": "Ad spend and sales", "source": self.SCATTER,
                                "kind": "scatter"})
        spec = record["figures"][0]["spec"]
        self.assertEqual(spec["kind"], "scatter")
        self.assertTrue(all(entry.get("x_artifact") for entry in spec["series"]))
        svg = visuals.export(record, "svg")[0].decode("utf-8")
        self.assertIn("<circle", svg)

    def test_a_scatter_without_x_values_is_refused(self):
        with self.assertRaises(visuals.VisualError):
            visuals.build({"title": "Ad spend and sales", "source": DECLARED,
                           "kind": "scatter"})

    def test_a_candlestick_builds_and_draws_four_prices(self):
        record = visuals.build({"title": "Share price", "source": self.CANDLES,
                                "kind": "candlestick"})
        spec = record["figures"][0]["spec"]
        self.assertEqual(spec["kind"], "candlestick")
        self.assertTrue(all(entry.get(key) for entry in spec["series"]
                            for key in ("open", "high", "low", "close")))
        svg = visuals.export(record, "svg")[0].decode("utf-8")
        self.assertIn("<rect", svg)

    def test_a_candlestick_without_four_prices_is_refused(self):
        with self.assertRaises(visuals.VisualError):
            visuals.build({"title": "Share price", "source": DECLARED, "kind": "candlestick"})

    def test_the_words_can_point_at_a_scatter(self):
        plan = visuals.propose(self.SCATTER, "the relationship between ad spend and sales")
        self.assertEqual(plan["proposals"][0]["kind"], "scatter")

    def test_the_words_can_point_at_a_candlestick(self):
        plan = visuals.propose(self.CANDLES, "the share price open high low close")
        self.assertEqual(plan["proposals"][0]["kind"], "candlestick")


class DiagramVisualTest(StoreCase):

    def test_a_swot_diagram_builds_lists_and_exports(self):
        spec = {"format": "bp-diagram/1", "kind": "matrix2x2", "title": "SWOT",
                "quadrants": {"top_left": "Strengths", "top_right": "Weaknesses",
                              "bottom_left": "Opportunities", "bottom_right": "Threats"}}
        record = visuals.build({"title": "SWOT",
                                "source": {"kind": "diagram", "spec": spec}})
        self.assertEqual(record["kind"], "matrix2x2")
        self.assertEqual(record["source"]["label"], "Your framework")
        self.assertEqual(visuals.listing()["visuals"][0]["kinds"], ["matrix2x2"])
        preview = visuals.preview({"title": "SWOT",
                                   "source": {"kind": "diagram", "spec": spec}})
        self.assertIn("<svg", preview["svg"])
        data, name, mime = visuals.export(record, "svg")
        self.assertEqual(mime, "image/svg+xml")
        self.assertIn(b"<svg", data)
        self.assertTrue(name.endswith(".svg"))

    def test_a_diagram_label_may_not_carry_a_digit(self):
        spec = {"format": "bp-diagram/1", "kind": "process", "title": "Bad",
                "items": [{"label": "4Ps"}, {"label": "Pricing"}]}
        with self.assertRaises(visuals.VisualError):
            visuals.build({"title": "Bad",
                           "source": {"kind": "diagram", "spec": spec}})


class GanttVisualTest(StoreCase):

    def test_a_gantt_builds_with_date_labels_and_exports(self):
        source = {"kind": "gantt", "activities": [
            {"label": "Research", "start": "0", "end": "4",
             "start_label": "Jan 1", "end_label": "Jan 5"},
            {"label": "Draft", "start": "4", "end": "11",
             "start_label": "Jan 5", "end_label": "Jan 12"}]}
        record = visuals.build({"title": "Timeline", "source": source})
        self.assertEqual(record["kind"], "gantt")
        self.assertEqual(record["source"]["label"], "Your project timeline")
        self.assertEqual(visuals.listing()["visuals"][0]["kinds"], ["gantt"])
        preview = visuals.preview({"title": "Timeline", "source": source})
        self.assertIn("<svg", preview["svg"])
        self.assertIn("Jan 1", preview["svg"])
        data, _name, mime = visuals.export(record, "svg")
        self.assertEqual(mime, "image/svg+xml")
        self.assertIn(b"Jan 1", data)

    def test_a_task_that_ends_before_it_starts_is_refused(self):
        with self.assertRaises(visuals.VisualError):
            visuals.build({"title": "Bad", "source": {"kind": "gantt", "activities": [
                {"label": "A", "start": "5", "end": "2"}]}})


class FigureSheetTest(StoreCase):
    """Several visuals on one page, in the order the student gave them."""

    def test_two_visuals_become_one_document_and_one_route(self):
        one = visuals.build({"title": "Revenue by quarter", "source": DECLARED, "kind": "line"})
        two = visuals.build({"title": "Revenue as bars", "source": DECLARED, "kind": "bar"})
        data, name, mime = visuals.export_sheet([one["id"], two["id"]], "docx", "Board pack")
        self.assertEqual(name, "Board pack.docx")
        self.assertIn("wordprocessingml", mime)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            media = [entry for entry in archive.namelist() if entry.startswith("word/media/")]
        self.assertEqual(len(media), 2)
        status, body = api.handle("POST", "/api/cases/visuals/sheet",
                                  {"ids": [one["id"], two["id"]], "title": "Board pack"})
        self.assertEqual(status, 200)
        self.assertEqual(body["filename"], "Board pack.docx")
        self.assertTrue(body["data"])

    def test_an_empty_sheet_is_refused(self):
        with self.assertRaises(visuals.VisualError):
            visuals.export_sheet([])

    def test_a_sheet_exports_as_docx_only(self):
        one = visuals.build({"title": "Revenue by quarter", "source": DECLARED, "kind": "line"})
        with self.assertRaises(visuals.VisualError):
            visuals.export_sheet([one["id"]], "pdf")

    def test_an_unknown_visual_is_refused(self):
        with self.assertRaises(visuals.VisualError):
            visuals.export_sheet(["vis_000000000000"])
