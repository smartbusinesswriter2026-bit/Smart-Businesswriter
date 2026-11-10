"""The chart reader: what a student typed or uploaded, and what it understood."""

import base64
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from bp import ingest  # noqa: E402
from bp.product import api, visual_input  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "web" / "assets" / "samples"


class ReaderCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-visual-input-")
        self.previous = {name: os.environ.get(name)
                         for name in ("BP_STATE_DIR", "BP_INTAKE_DIR")}
        os.environ["BP_STATE_DIR"] = self.root
        os.environ["BP_INTAKE_DIR"] = os.path.join(self.root, "intake")
        self.previous_reader = visual_input.TABLE_READER
        visual_input.set_table_reader(ingest.read_table)

    def tearDown(self):
        visual_input.set_table_reader(self.previous_reader)
        for name, value in self.previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(self.root, ignore_errors=True)

    def upload(self, mode, path, **extra):
        raw = pathlib.Path(path).read_bytes()
        payload = {"mode": mode, "filename": pathlib.Path(path).name,
                   "content_base64": base64.b64encode(raw).decode("ascii")}
        payload.update(extra)
        return visual_input.interpret(payload)


class NumberTest(unittest.TestCase):

    def test_plain_and_grouped_numbers(self):
        self.assertEqual(visual_input.parse_number("120000")["value"], "120000")
        self.assertEqual(visual_input.parse_number("120,000")["value"], "120000")
        self.assertEqual(visual_input.parse_number("120 000")["value"], "120000")
        self.assertEqual(visual_input.parse_number("$120,000")["value"], "120000")
        self.assertEqual(visual_input.parse_number("€1.200,50")["value"], "1200.5")
        self.assertEqual(visual_input.parse_number("(1,200)")["value"], "-1200")
        self.assertEqual(visual_input.parse_number("−1200")["value"], "-1200")
        self.assertEqual(visual_input.parse_number("12%")["value"], "12")
        self.assertEqual(visual_input.parse_number("12%")["unit"], "%")
        self.assertEqual(visual_input.parse_number("1.2k")["value"], "1200")
        self.assertEqual(visual_input.parse_number("1.2M")["value"], "1200000")
        self.assertEqual(visual_input.parse_number("1,23,456")["value"], "123456")

    def test_a_three_digit_separator_is_flagged(self):
        number = visual_input.parse_number("1,200")
        self.assertEqual(number["value"], "1200")
        self.assertTrue(number["ambiguous"])
        self.assertEqual(visual_input.parse_number("1.20")["value"], "1.2")

    def test_junk_is_refused(self):
        for text in ("abc", "12abc", "1.2.3", "", "NaN", "Infinity"):
            self.assertIsNone(visual_input.parse_number(text), text)


class LineTest(unittest.TestCase):

    def test_every_separator(self):
        text = ("Q1, 10\nQ2\t20\nQ3: 30\nQ4 | 40\nQ5 ; 50\nQ6  60\nQ7 70")
        points, skipped, _warnings = visual_input.parse_lines(text)
        self.assertEqual([point["label"] for point in points],
                         ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"])
        self.assertEqual([point["value"] for point in points],
                         ["10", "20", "30", "40", "50", "60", "70"])
        self.assertEqual(skipped, [])

    def test_multi_word_label_and_bare_number(self):
        points, skipped, warnings = visual_input.parse_lines(
            "North Region 120000\n480000\nRevenue by quarter")
        self.assertEqual([(point["label"], point["value"]) for point in points],
                         [("North Region", "120000"), ("Item 2", "480000")])
        self.assertTrue(points[1]["label_auto"])
        self.assertEqual(skipped[0]["line"], 3)
        self.assertIn("Item 2", warnings[0])

    def test_a_year_is_a_label_not_a_second_value(self):
        points, skipped, _warnings = visual_input.parse_lines("2024 120000")
        self.assertEqual([(point["label"], point["value"]) for point in points],
                         [("2024", "120000")])
        self.assertEqual(skipped, [])

    def test_two_values_without_a_label_are_refused(self):
        points, skipped, _warnings = visual_input.parse_lines("120000 240000")
        self.assertEqual(points, [])
        self.assertIn("more than one number", skipped[0]["reason"])

    def test_a_third_number_on_a_plain_line_is_refused(self):
        points, skipped, _warnings = visual_input.parse_lines("Q1 120000 240000")
        self.assertEqual(points, [])
        self.assertIn("more than one number", skipped[0]["reason"])

    def test_pareto_needs_a_running_total(self):
        points, skipped, _warnings = visual_input.parse_lines("A, 10\nB, 20", True)
        self.assertEqual(points, [])
        self.assertEqual(len(skipped), 2)
        self.assertIn("running total", skipped[0]["reason"])

    def test_pareto_reads_three_numbers(self):
        points, skipped, _warnings = visual_input.parse_lines(
            "A, 10, 10\nB, 20, 30\nC, 5, 35", True)
        self.assertEqual([(point["value"], point["cumulative"]) for point in points],
                         [("10", "10"), ("20", "30"), ("5", "35")])
        self.assertEqual(skipped, [])

    def test_scatter_reads_x_and_y(self):
        points, skipped, _warnings = visual_input.parse_lines(
            "Ad spend, 1200, 45000\nFootfall, 800, 30000", False, True, False)
        self.assertEqual([(point["label"], point["x"], point["value"]) for point in points],
                         [("Ad spend", "1200", "45000"), ("Footfall", "800", "30000")])
        self.assertEqual(skipped, [])

    def test_scatter_refuses_a_third_number(self):
        points, skipped, _warnings = visual_input.parse_lines(
            "A, 1, 10, 99", False, True, False)
        self.assertEqual(points, [])
        self.assertIn("more than two numbers", skipped[0]["reason"])

    def test_scatter_needs_a_pair(self):
        points, skipped, _warnings = visual_input.parse_lines(
            "A, 1\nB, 2", False, True, False)
        self.assertEqual(points, [])
        self.assertEqual(len(skipped), 2)
        self.assertIn("x value and a y value", skipped[0]["reason"])

    def test_candlestick_reads_open_high_low_close(self):
        points, skipped, _warnings = visual_input.parse_lines(
            "Day one, 100, 120, 90, 110\nDay two, 110, 115, 100, 105", False, False, True)
        self.assertEqual([(point["label"], point["open"], point["high"], point["low"],
                           point["close"], point["value"]) for point in points],
                         [("Day one", "100", "120", "90", "110", "110"),
                          ("Day two", "110", "115", "100", "105", "105")])
        self.assertEqual(skipped, [])

    def test_candlestick_refuses_a_high_below_the_low(self):
        points, skipped, _warnings = visual_input.parse_lines(
            "Day one, 100, 80, 90, 110", False, False, True)
        self.assertEqual(points, [])
        self.assertIn("high is below the low", skipped[0]["reason"])

    def test_candlestick_refuses_an_open_outside_the_range(self):
        points, skipped, _warnings = visual_input.parse_lines(
            "Day one, 100, 120, 90, 130", False, False, True)
        self.assertEqual(points, [])
        self.assertIn("outside the high-low range", skipped[0]["reason"])

    def test_candlestick_needs_four_prices(self):
        points, skipped, _warnings = visual_input.parse_lines(
            "Day one, 100, 120, 90", False, False, True)
        self.assertEqual(points, [])
        self.assertIn("open, high, low and close", skipped[0]["reason"])


class ReportTest(unittest.TestCase):

    def report(self, text, kind="bar", title="Revenue"):
        return visual_input.interpret({"mode": "typed", "text": text,
                                       "kind": kind, "title": title})

    def test_a_clean_typed_report(self):
        report = self.report("Q1, 120000\nQ2 240000\nQ3: 360000")
        self.assertTrue(report["ok"])
        self.assertEqual(len(report["points"]), 3)
        self.assertEqual(report["kind"]["value"], "bar")
        self.assertTrue(any("bar chart" in line for line in report["plan"]))
        self.assertIn("Q1\t120000", report["normalized_text"])

    def test_one_point_is_not_a_chart(self):
        report = self.report("480000")
        self.assertFalse(report["ok"])
        self.assertTrue(any("two points" in reason for reason in report["blocked"]))

    def test_no_numbers_is_blocked(self):
        report = self.report("Revenue by quarter")
        self.assertFalse(report["ok"])
        self.assertTrue(any("no figures" in reason for reason in report["blocked"]))

    def test_a_negative_pie_is_blocked(self):
        report = self.report("A, 10\nB, -5", "pie")
        self.assertFalse(report["ok"])
        self.assertTrue(any("positive values" in reason for reason in report["blocked"]))

    def test_a_pareto_without_a_running_total_is_blocked(self):
        report = self.report("A, 10\nB, 20", "pareto")
        self.assertFalse(report["ok"])
        self.assertTrue(any("running total" in reason for reason in report["blocked"]))

    def test_a_falling_running_total_is_blocked(self):
        report = self.report("A, 10, 10\nB, 20, 30\nC, 5, 20", "pareto")
        self.assertFalse(report["ok"])
        self.assertTrue(any("falls" in reason for reason in report["blocked"]))

    def test_a_title_is_a_need_not_a_block(self):
        report = visual_input.interpret({"mode": "typed", "text": "Q1, 1\nQ2, 2",
                                         "kind": "bar", "title": ""})
        self.assertTrue(report["ok"])
        self.assertIn("Give the chart a title.", report["needs"])

    def test_a_scatter_report_names_the_pair(self):
        report = self.report("Ad spend, 1200, 45000\nFootfall, 800, 30000", "scatter")
        self.assertTrue(report["ok"])
        self.assertEqual(report["normalized_text"],
                         "Ad spend\t1200\t45000\nFootfall\t800\t30000")
        self.assertTrue(any("scatter plot" in line for line in report["plan"]))

    def test_a_scatter_without_x_values_is_blocked(self):
        report = self.report("A, 10\nB, 20", "scatter")
        self.assertFalse(report["ok"])
        self.assertTrue(any("label, x, y" in reason for reason in report["blocked"]))

    def test_a_candlestick_report_reads_four_prices(self):
        report = self.report("Day one, 100, 120, 90, 110\n"
                             "Day two, 110, 115, 100, 105", "candlestick")
        self.assertTrue(report["ok"])
        self.assertEqual(report["points"][0]["close"], "110")
        self.assertTrue(any("candlestick" in line for line in report["plan"]))

    def test_a_candlestick_with_an_impossible_bar_is_blocked(self):
        report = self.report("Day one, 100, 120, 90, 130\n"
                             "Day two, 110, 115, 100, 105", "candlestick")
        self.assertFalse(report["ok"])
        self.assertIn("outside the high-low range", report["skipped"][0]["reason"])

    def test_an_area_report_draws_the_same_values(self):
        report = self.report("Q1, 120\nQ2, 150\nQ3, 130", "area")
        self.assertTrue(report["ok"])
        self.assertTrue(any("area chart" in line for line in report["plan"]))


class TableTest(unittest.TestCase):

    def table(self, columns, rows):
        return {"filename": "sales.csv", "sha256": "a" * 64,
                "columns": [{"name": name} for name in columns], "rows": rows}

    def test_a_header_table(self):
        read = visual_input.read_table(
            self.table(["Quarter", "Revenue"],
                       [["Q1", "120000"], ["Q2", "240000"], ["Q3", "oops"]]),
            "sales.csv", "a" * 64, "bar")
        self.assertEqual([(point["label"], point["value"]) for point in read["points"]],
                         [("Q1", "120000"), ("Q2", "240000")])
        self.assertEqual(read["skipped"][0]["line"], 4)
        self.assertEqual(read["columns"]["label"], "Quarter")
        self.assertEqual(read["columns"]["value"], "Revenue")

    def test_a_headerless_table_keeps_its_first_row(self):
        read = visual_input.read_table(
            self.table(["Q1", "120000"], [["Q2", "240000"], ["Q3", "360000"]]),
            "sales.csv", "a" * 64, "bar")
        self.assertEqual([(point["label"], point["value"]) for point in read["points"]],
                         [("Q1", "120000"), ("Q2", "240000"), ("Q3", "360000")])
        self.assertTrue(read["headerless"])

    def test_more_than_one_number_column_is_named(self):
        read = visual_input.read_table(
            self.table(["Quarter", "Revenue", "Cost"],
                       [["Q1", "120000", "70000"], ["Q2", "240000", "140000"]]),
            "sales.csv", "a" * 64, "bar")
        self.assertEqual(read["columns"]["value"], "Revenue")
        self.assertTrue(any("Cost" in warning for warning in read["warnings"]))
        read = visual_input.read_table(
            self.table(["Quarter", "Revenue", "Cost"],
                       [["Q1", "120000", "70000"], ["Q2", "240000", "140000"]]),
            "sales.csv", "a" * 64, "bar", value_column="Cost")
        self.assertEqual(read["columns"]["value"], "Cost")
        self.assertEqual(read["points"][0]["value"], "70000")

    def test_a_pareto_table_uses_the_running_total_column(self):
        read = visual_input.read_table(
            self.table(["Item", "Value", "Running"],
                       [["A", "10", "10"], ["B", "20", "30"], ["C", "5", "35"]]),
            "sales.csv", "a" * 64, "pareto")
        self.assertEqual(read["columns"]["cumulative"], "Running")
        self.assertEqual([(point["value"], point["cumulative"]) for point in read["points"]],
                         [("10", "10"), ("20", "30"), ("5", "35")])
        self.assertTrue(any("Running" in warning for warning in read["warnings"]))

    def test_word_table_rows_keep_the_table_shape(self):
        table = visual_input.table_from_rows(
            [["Quarter", "Revenue"], ["Q1", "120000"], ["Q2", "240000"]],
            "instruction.docx", "a" * 64)
        read = visual_input.read_table(table, "instruction.docx", "a" * 64, "bar")
        self.assertEqual([(point["label"], point["value"]) for point in read["points"]],
                         [("Q1", "120000"), ("Q2", "240000")])
        self.assertEqual(read["columns"]["label"], "Quarter")


class FileTest(ReaderCase):

    def test_the_csv_sample(self):
        report = self.upload("data", SAMPLES / "chart-data.csv", kind="bar",
                             title="Revenue")
        self.assertTrue(report["ok"])
        self.assertEqual(len(report["points"]), 4)
        self.assertEqual(report["columns"]["label"], "Quarter")

    def test_the_xlsx_sample(self):
        report = self.upload("data", SAMPLES / "chart-data.xlsx", kind="bar",
                             title="Revenue")
        self.assertTrue(report["ok"])
        self.assertEqual(len(report["points"]), 4)
        self.assertEqual(report["sheet"], "Revenue")

    def test_the_instruction_sample(self):
        report = self.upload("instruction", SAMPLES / "chart-instruction.docx")
        self.assertTrue(report["ok"])
        self.assertEqual(report["title"]["value"], "Revenue by quarter")
        self.assertEqual(report["kind"]["value"], "bar")
        self.assertEqual(len(report["points"]), 4)
        self.assertTrue(any("12%" in warning for warning in report["warnings"]))

    def test_a_text_instruction_with_no_figures_is_blocked(self):
        path = os.path.join(self.root, "empty.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("Make a chart of the company's revenue. The figures are in the annual report.")
        report = self.upload("instruction", path)
        self.assertFalse(report["ok"])
        self.assertTrue(any("no figures" in reason for reason in report["blocked"]))

    def test_a_text_instruction_that_asks_for_a_scatter(self):
        path = os.path.join(self.root, "scatter.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("Draw a scatter plot of sales against ad spend.\n"
                         "Ad spend, 1200, 45000\nFootfall, 800, 30000\n")
        report = self.upload("instruction", path)
        self.assertTrue(report["ok"])
        self.assertEqual(report["kind"]["value"], "scatter")
        self.assertEqual(report["points"][0]["x"], "1200")
        self.assertEqual(report["points"][0]["value"], "45000")

    def test_a_text_instruction_that_asks_for_a_candlestick(self):
        path = os.path.join(self.root, "candles.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("Show the candlestick chart for the week.\n"
                         "Day one, 100, 120, 90, 110\nDay two, 110, 115, 100, 105\n")
        report = self.upload("instruction", path)
        self.assertTrue(report["ok"])
        self.assertEqual(report["kind"]["value"], "candlestick")
        self.assertEqual(report["points"][1]["close"], "105")

    def test_a_bad_base64_is_refused(self):
        with self.assertRaises(visual_input.VisualInputError):
            visual_input.interpret({"mode": "data", "filename": "x.csv",
                                    "content_base64": "not base64"})


class RouteTest(ReaderCase):

    def test_the_read_route(self):
        code, body = api.handle("POST", "/api/cases/visuals/read",
                                {"mode": "typed", "text": "Q1, 1\nQ2, 2",
                                 "kind": "bar", "title": "Revenue"})
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["format"], visual_input.FORMAT)

    def test_a_malformed_read_is_422(self):
        code, body = api.handle("POST", "/api/cases/visuals/read",
                                {"mode": "typed", "text": ""})
        self.assertEqual(code, 422)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
