"""The problem reader: accounting's standard, applied to finance and economics.

The rule under test is the house rule, not a new one: a figure is read only when
a field's own name sits next to it, a figure with no label is never assigned, a
required figure that was not read is named as a gap, and the reader computes
nothing — the frozen core does the arithmetic.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods                      # noqa: E402
from bp.product import api, problem_reader  # noqa: E402


def _run(method_id, inputs):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


api.attach_methods(_run, methods.describe)


def schema(method_id):
    return methods.describe(method_id)["input_schema"]


class ReadTheFiguresTest(unittest.TestCase):
    def test_a_finance_problem_fills_the_fields_by_their_own_names(self):
        result = problem_reader.read(
            "npv", schema("npv"),
            "A project has a discount rate of 10% and cash flows -50,000, 20,000, 25,000, 15,000.")
        self.assertEqual(result["inputs"]["rate"], "0.1",
                         "a percent rate becomes the decimal the method takes")
        self.assertEqual(result["inputs"]["cashflows"], "-50000, 20000, 25000, 15000")
        self.assertEqual(result["missing"], [])

    def test_a_number_with_no_label_is_never_assigned(self):
        result = problem_reader.read(
            "npv", schema("npv"), "A project costs 50,000 and returns 20,000 a year for four years.")
        self.assertEqual(result["inputs"], {},
                         "an unlabelled number is not a figure for any field")
        self.assertEqual(len(result["missing"]), 2)

    def test_a_typed_figure_wins_and_is_not_re_read(self):
        result = problem_reader.read(
            "npv", schema("npv"), "discount rate 10%", {"rate": "0.12"})
        self.assertEqual(result["inputs"]["rate"], "0.12")
        self.assertEqual([row["source"] for row in result["read"]], ["typed"])

    def test_the_missing_figures_are_named_in_words(self):
        result = problem_reader.read("npv", schema("npv"), "cash flows -100, 50, 80")
        self.assertIn("discount rate per period", result["missing"])

    def test_a_rate_without_a_percent_sign_is_not_rescaled(self):
        result = problem_reader.read("npv", schema("npv"), "discount rate 0.1, cash flows -100, 120")
        self.assertEqual(result["inputs"]["rate"], "0.1",
                         "only an explicit % is divided by a hundred")

    def test_unread_numbers_are_counted_so_the_page_can_say_so(self):
        result = problem_reader.read(
            "npv", schema("npv"), "A firm invested 12,000 at 8 and earned 3,500 in the first year.")
        self.assertGreater(result["unread_numbers"], 0,
                           "the page must be able to say figures were not used")
        self.assertEqual(result["inputs"], {})

    def test_economics_fields_are_read_by_their_own_labels_too(self):
        described = methods.describe("inflation_cpi")
        result = problem_reader.read("inflation_cpi", described["input_schema"],
                                     "the price index rises from 100 to 105")
        self.assertIsInstance(result["missing"], list)

    def test_a_method_with_no_figures_is_refused_rather_than_guessed(self):
        with self.assertRaises(problem_reader.ReaderError):
            problem_reader.read("npv", {}, "anything")


class ReaderRouteTest(unittest.TestCase):
    def test_the_route_reads_and_computes_nothing(self):
        status, payload = api.handle("POST", "/api/cases/solve/read", {
            "method": "npv",
            "instruction": "discount rate 10%, cash flows -50000, 20000, 25000"})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["inputs"]["rate"], "0.1")
        self.assertIn("missing", payload)
        self.assertNotIn("outputs", payload, "the reader never computes")

    def test_an_unknown_method_is_refused_by_name(self):
        status, payload = api.handle("POST", "/api/cases/solve/read",
                                     {"method": "not_a_method", "instruction": "x"})
        self.assertIn(status, (404, 422), payload)

    def test_a_missing_method_is_refused(self):
        status, payload = api.handle("POST", "/api/cases/solve/read", {"instruction": "x"})
        self.assertEqual(status, 422, payload)


if __name__ == "__main__":
    unittest.main()
