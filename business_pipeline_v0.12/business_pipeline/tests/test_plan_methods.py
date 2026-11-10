"""The four plan building blocks, tested structurally (no case hard-coded)."""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from bp import methods  # noqa: E402


def run(name, inputs):
    return methods.LIBRARY[name].impl(inputs)


class EscalatedSeriesTest(unittest.TestCase):
    def test_a_monthly_amount_steps_once_a_year_and_compounds(self):
        out = run("escalated_series", {"start": "4200", "rate": "0.04", "periods": "36",
                                       "escalate_after": "12", "every": "12"})
        self.assertEqual(out["value_1"], 4200)
        self.assertEqual(out["value_12"], 4200)
        self.assertEqual(out["value_13"], 4200 * methods.D("1.04"))
        self.assertEqual(out["value_25"], 4200 * methods.D("1.04") ** 2)
        self.assertEqual(out["total"], sum(out["value_%d" % i] for i in range(1, 37)))

    def test_a_zero_rate_repeats_the_start(self):
        out = run("escalated_series", {"start": "100", "rate": "0", "periods": "5"})
        self.assertTrue(all(out["value_%d" % i] == 100 for i in range(1, 6)))

    def test_a_negative_rate_below_minus_one_is_refused(self):
        with self.assertRaises(methods.DataError):
            run("escalated_series", {"start": "100", "rate": "-1.5", "periods": "3"})


class TrafficRevenueTest(unittest.TestCase):
    def test_revenue_is_the_declared_product_each_period(self):
        out = run("revenue_from_traffic", {"days_open": "26", "average_ticket": "9.50",
                                           "daily_transactions": ["55", "65", "75"]})
        self.assertEqual(out["revenue_1"], 26 * methods.D("9.50") * 55)
        self.assertEqual(out["revenue_3"], 26 * methods.D("9.50") * 75)
        self.assertEqual(out["total_revenue"], sum(out["revenue_%d" % i] for i in (1, 2, 3)))

    def test_negative_transactions_are_refused(self):
        with self.assertRaises(methods.DataError):
            run("revenue_from_traffic", {"days_open": "26", "average_ticket": "9.50",
                                         "daily_transactions": ["55", "-1"]})


class LineTotalsTest(unittest.TestCase):
    def test_the_total_and_every_category_foot(self):
        out = run("line_totals", {"lines": [
            {"label": "Lease improvements", "amount": "55000", "category": "premises"},
            {"label": "Kitchen", "amount": "50000", "category": "equipment"},
            {"label": "Rent deposit", "amount": "8400", "category": "premises"},
        ]})
        self.assertEqual(out["total"], 113400)
        self.assertEqual(out["category_premises"], 63400)
        self.assertEqual(out["category_equipment"], 50000)
        self.assertEqual(out["n_lines"], 3)

    def test_a_line_without_an_amount_is_refused(self):
        with self.assertRaises(methods.DataError):
            run("line_totals", {"lines": [{"label": "Rent", "amount": "not a number"}]})


class SimplePaybackTest(unittest.TestCase):
    def test_recovery_is_interpolated_inside_the_recovering_period(self):
        out = run("simple_payback", {"initial": "60000", "cashflows": ["20000", "25000", "30000"]})
        self.assertEqual(out["payback_periods"], methods.D("2.5"))
        self.assertEqual(out["recovered_in_period"], 3)

    def test_an_investment_the_flows_never_recover_is_refused(self):
        with self.assertRaises(methods.DataError):
            run("simple_payback", {"initial": "100000", "cashflows": ["1000", "2000"]})


class MethodContractTest(unittest.TestCase):
    def test_every_method_declares_its_schema_and_tests(self):
        for name in ("escalated_series", "revenue_from_traffic", "line_totals", "simple_payback"):
            method = methods.LIBRARY[name]
            self.assertTrue(method.input_schema, name)
            self.assertTrue(method.test_names, name)
            self.assertEqual(mode(method.tier), "T1", name)


def mode(tier):
    return tier


if __name__ == "__main__":
    unittest.main()
