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

BOARD = {"format": "bp-diagram/1", "kind": "board", "title": "Sprint board",
         "columns": [
             {"label": "To do", "cards": [{"label": "Login flow"}, {"label": "Search filters"}]},
             {"label": "In progress", "cards": [{"label": "Checkout"}]},
             {"label": "Done", "cards": [{"label": "Signup"}]},
         ]}


class BoardTest(unittest.TestCase):
    """A board is columns of cards: a sprint board, a Kanban board or a retrospective."""

    def test_a_board_renders_every_column_and_card(self):
        svg = diagrams.render_svg(BOARD)
        self.assertIn("<svg", svg)
        for label in ("To do", "In progress", "Done", "Login flow", "Checkout", "Signup"):
            self.assertIn(label, svg)
        ET.fromstring(svg)

    def test_a_board_needs_two_columns(self):
        with self.assertRaises(diagrams.DiagramError):
            diagrams.render_svg({"format": "bp-diagram/1", "kind": "board",
                                 "title": "Sprint board",
                                 "columns": [{"label": "To do", "cards": []}]})

    def test_an_empty_column_is_allowed(self):
        svg = diagrams.render_svg({"format": "bp-diagram/1", "kind": "board",
                                   "title": "Sprint board",
                                   "columns": [{"label": "To do", "cards": []},
                                               {"label": "Done", "cards": [{"label": "Signup"}]}]})
        self.assertIn("To do", svg)

    def test_a_card_label_may_not_carry_a_number(self):
        with self.assertRaises(diagrams.DiagramError):
            diagrams.render_svg({"format": "bp-diagram/1", "kind": "board",
                                 "title": "Sprint board",
                                 "columns": [{"label": "To do", "cards": [{"label": "Sprint 3"}]},
                                             {"label": "Done", "cards": []}]})

JOURNEY = {"format": "bp-diagram/1", "kind": "journey", "title": "Customer journey",
           "stages": [{"label": "Awareness"}, {"label": "Consideration"},
                      {"label": "Purchase"}, {"label": "Retention"}],
           "lanes": [
               {"label": "Actions", "cells": ["Sees an advert", "Compares options",
                                              "Places the order", "Uses the product"]},
               {"label": "Pain points", "cells": ["Unclear pricing", "", "Slow checkout", ""]},
           ]}


class JourneyTest(unittest.TestCase):
    """Stages across, lanes down: a journey map, a story map or a roadmap."""

    def test_a_journey_renders_every_stage_and_lane(self):
        svg = diagrams.render_svg(JOURNEY)
        for label in ("Awareness", "Retention", "Actions", "Pain points", "Compares options"):
            self.assertIn(label, svg)
        ET.fromstring(svg)

    def test_an_empty_cell_is_allowed_and_prints_no_word(self):
        svg = diagrams.render_svg(JOURNEY)
        self.assertNotIn("None", svg)

    def test_a_journey_needs_two_stages(self):
        with self.assertRaises(diagrams.DiagramError):
            diagrams.render_svg({"format": "bp-diagram/1", "kind": "journey",
                                 "title": "Journey", "stages": [{"label": "Awareness"}],
                                 "lanes": [{"label": "Actions", "cells": ["x"]}]})

    def test_a_lane_may_not_have_more_cells_than_stages(self):
        with self.assertRaises(diagrams.DiagramError):
            diagrams.render_svg({"format": "bp-diagram/1", "kind": "journey",
                                 "title": "Journey",
                                 "stages": [{"label": "Awareness"}, {"label": "Purchase"}],
                                 "lanes": [{"label": "Actions", "cells": ["a", "b", "c"]}]})

KPI = {"format": "bp-diagram/1", "kind": "kpi", "title": "Sprint KPIs",
       "items": [
           {"label": "Velocity", "value": "velocity", "target": "velocity_target",
            "status": "velocity_status"},
           {"label": "Test coverage", "value": "coverage", "target": "coverage_target"},
       ]}


def kpi_bundle():
    artifacts, outputs = [], {}
    for key, value in (("velocity", "34"), ("velocity_target", "40"),
                       ("velocity_status", "at risk"), ("coverage", "81"),
                       ("coverage_target", "85")):
        artifacts.append([key, [key, "", "entity", "base"], ""])
        outputs[key] = value
    return {"delivery": {"appendix": {"artifacts": artifacts}},
            "reperform": {"outputs": outputs}}


class KpiTest(unittest.TestCase):
    """A KPI card shows the recorded value, its target and its recorded status."""

    def test_a_kpi_board_reads_the_recorded_values(self):
        svg = diagrams.render_svg(KPI, kpi_bundle())
        for value in ("Velocity", "34", "Target 40", "Test coverage", "81"):
            self.assertIn(value, svg)
        ET.fromstring(svg)

    def test_a_kpi_board_without_the_record_is_refused(self):
        with self.assertRaises(diagrams.DiagramError):
            diagrams.render_svg(KPI)

    def test_a_kpi_needs_a_stored_value(self):
        with self.assertRaises(diagrams.DiagramError):
            diagrams.render_svg({"format": "bp-diagram/1", "kind": "kpi",
                                 "title": "Sprint KPIs",
                                 "items": [{"label": "Velocity"}]}, kpi_bundle())

    def test_a_missing_artifact_says_not_recorded(self):
        spec = {"format": "bp-diagram/1", "kind": "kpi", "title": "Sprint KPIs",
                "items": [{"label": "Velocity", "value": "nope"}]}
        self.assertIn("not recorded", diagrams.render_svg(spec, kpi_bundle()))


WBS = {"format": "bp-diagram/1", "kind": "wbs", "title": "Launch plan",
       "root": {"label": "Launch", "code": "1", "children": [
           {"label": "Research", "code": "1.1", "children": [
               {"label": "Interviews", "code": "1.1.1"},
               {"label": "Survey", "code": "1.1.2"}]},
           {"label": "Build", "code": "1.2", "children": [
               {"label": "Prototype", "code": "1.2.1"},
               {"label": "Pilot", "code": "1.2.2"}]}]}}


class WorkBreakdownTest(unittest.TestCase):
    """A work breakdown is labels and codes: the codes may carry digits, the labels may not."""

    def test_a_tree_of_work_packages_is_drawn(self):
        svg = diagrams.render_svg(WBS)
        ET.fromstring(svg)
        for label in ("Launch", "Research", "Build", "Interviews", "Pilot"):
            self.assertIn(label, svg)

    def test_the_codes_are_drawn_beside_the_labels(self):
        svg = diagrams.render_svg(WBS)
        for code in ("1.1.1", "1.2.2"):
            self.assertIn(code, svg)

    def test_a_label_may_not_carry_a_digit(self):
        spec = {"format": "bp-diagram/1", "kind": "wbs", "title": "Bad",
                "root": {"label": "Phase 2"}}
        with self.assertRaises(diagrams.DiagramError):
            diagrams.validate_spec(spec)

    def test_a_code_may_carry_a_digit(self):
        kind, _title, payload = diagrams.validate_spec(WBS)
        self.assertEqual(kind, "wbs")
        self.assertEqual(payload["code"], "1")
        self.assertEqual(payload["children"][0]["code"], "1.1")

    def test_a_root_is_required(self):
        with self.assertRaises(diagrams.DiagramError):
            diagrams.validate_spec({"format": "bp-diagram/1", "kind": "wbs", "title": "Bad"})

    def test_children_must_be_objects(self):
        spec = {"format": "bp-diagram/1", "kind": "wbs", "title": "Bad",
                "root": {"label": "Root", "children": ["Not an object"]}}
        with self.assertRaises(diagrams.DiagramError):
            diagrams.validate_spec(spec)

    def test_five_levels_is_the_limit(self):
        node = {"label": "Leaf"}
        for _ in range(6):
            node = {"label": "Level", "children": [node]}
        with self.assertRaises(diagrams.DiagramError):
            diagrams.validate_spec({"format": "bp-diagram/1", "kind": "wbs",
                                    "title": "Deep", "root": node})

    def test_an_empty_code_is_not_a_code(self):
        spec = {"format": "bp-diagram/1", "kind": "wbs", "title": "Bad",
                "root": {"label": "Root", "code": "  "}}
        with self.assertRaises(diagrams.DiagramError):
            diagrams.validate_spec(spec)

    def test_the_svg_export_writes_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "wbs.svg")
            self.assertEqual(diagrams.export_svg(WBS, path), path)
            self.assertIn("<svg", open(path, encoding="utf-8").read())
