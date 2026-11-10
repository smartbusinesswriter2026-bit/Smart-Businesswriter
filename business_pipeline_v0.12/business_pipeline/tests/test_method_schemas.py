"""Phase 1 schema truth: finance methods are typed, and non-numeric input is refused.

The 67 finance methods used to declare every input as ``string``, so a value like
``"abc"`` passed validation and only crashed inside the method.  The ratified type
overlay restores the numeric contract and ``validate_inputs`` now refuses it before
any method runs.
"""

import unittest

from bp import methods


class FinanceSchemaTest(unittest.TestCase):
    def test_a_finance_method_declares_numeric_types(self):
        self.assertEqual(methods.describe("current_ratio")["input_schema"]["current_assets"]["type"],
                         "decimal")
        self.assertEqual(methods.describe("future_value")["input_schema"]["rate"]["type"], "rate")
        self.assertEqual(methods.describe("future_value")["input_schema"]["periods"]["type"], "integer")

    def test_a_non_numeric_string_is_refused_before_the_method_runs(self):
        errors = methods.validate_inputs(
            methods.LIBRARY["current_ratio"],
            {"current_assets": "abc", "current_liabilities": "50"})
        self.assertTrue(any("not a valid number" in e for e in errors), errors)

    def test_a_whole_number_is_required_for_an_integer_input(self):
        errors = methods.validate_inputs(
            methods.LIBRARY["future_value"],
            {"pv": "100", "rate": "0.1", "periods": "3.5"})
        self.assertTrue(any("whole number" in e for e in errors), errors)

    def test_a_list_cashflow_input_accepts_a_list(self):
        self.assertEqual(
            methods.validate_inputs(
                methods.LIBRARY["npv_simple"],
                {"rate": "0.1", "cashflows": ["100", "200", "300"]}),
            [])

    def test_no_finance_input_remains_untyped_string(self):
        # A finance method's inputs are numeric or a numeric list now; a bare
        # "string" would mean a number is still treated as free text.
        for method_id in ("current_ratio", "future_value", "dupont", "altman_z_score",
                          "simple_interest", "wacc_simple", "npv_simple", "eps"):
            schema = methods.describe(method_id)["input_schema"]
            for name, spec in schema.items():
                self.assertNotEqual(spec["type"], "string", (method_id, name))


if __name__ == "__main__":
    unittest.main()
