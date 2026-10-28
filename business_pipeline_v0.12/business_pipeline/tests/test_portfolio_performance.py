"""Portfolio performance: chained time-weighted return, flows, benchmark and refusals."""

import os
import sys
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp.methods import DataError  # noqa: E402

INPUT = {
    "periods": [
        {"label": "week 1", "start_nav": "1000", "end_nav": "1100", "flow": "0"},
        {"label": "week 2", "start_nav": "1100", "end_nav": "1210", "flow": "0"},
    ],
    "benchmark_start": ["100", "100"],
    "benchmark_end": ["102", "103"],
}


class PortfolioPerformanceTest(unittest.TestCase):
    def setUp(self):
        self.method = methods.LIBRARY["portfolio_performance"]

    def test_the_return_chains_each_period(self):
        out = self.method.impl(INPUT)
        self.assertEqual(out["n_periods"], D(2))
        self.assertEqual(out["twr"], D("0.21"))
        self.assertEqual(out["start_nav"], D(1000))
        self.assertEqual(out["final_nav"], D(1210))
        self.assertEqual(out["best_period"], D("0.1"))
        self.assertEqual(out["worst_period"], D("0.1"))

    def test_a_flow_is_in_the_base_not_the_return(self):
        out = self.method.impl({"periods": [
            {"label": "only", "start_nav": "1000", "end_nav": "1210", "flow": "100"}]})
        self.assertEqual(out["twr"], D("0.1"))
        self.assertEqual(out["total_flow"], D(100))

    def test_the_benchmark_chains_the_same_way(self):
        out = self.method.impl(INPUT)
        self.assertEqual(out["benchmark_return"], D("0.0506"))
        self.assertEqual(out["active_return"], D("0.21") - D("0.0506"))

    def test_every_declared_check_passes(self):
        results = self.method.tests(INPUT, self.method.impl)
        self.assertEqual([name for name, _ in results], list(self.method.test_names))
        self.assertTrue(all(ok for _, ok in results), results)

    def test_a_loss_is_reported_as_a_loss(self):
        out = self.method.impl({"periods": [
            {"label": "week 1", "start_nav": "1000", "end_nav": "900", "flow": "0"}]})
        self.assertEqual(out["twr"], D("-0.1"))
        self.assertEqual(out["best_period"], D("-0.1"))

    def test_bad_periods_are_refused(self):
        for change in (
            {"periods": []},
            {"periods": [{"label": "", "start_nav": "1000", "end_nav": "1100", "flow": "0"}]},
            {"periods": [{"label": "w", "start_nav": "1000", "end_nav": "1100", "flow": "0"},
                         {"label": "w", "start_nav": "1100", "end_nav": "1200", "flow": "0"}]},
            {"periods": [{"label": "w", "start_nav": "0", "end_nav": "1100", "flow": "0"}]},
            {"periods": [{"label": "w", "start_nav": "1000", "end_nav": "-1", "flow": "0"}]},
            {"periods": [{"label": "w", "start_nav": "1000", "end_nav": "900", "flow": "-1000"}]},
            {"benchmark_start": ["100"], "benchmark_end": ["101"]},
        ):
            with self.assertRaises(DataError):
                self.method.impl({**INPUT, **change})

    def test_schema_and_profile_accept_the_student_input(self):
        self.assertEqual(methods.validate_inputs(self.method, INPUT), [])
        self.assertEqual(self.method.profile(INPUT), [])


if __name__ == "__main__":
    unittest.main()
