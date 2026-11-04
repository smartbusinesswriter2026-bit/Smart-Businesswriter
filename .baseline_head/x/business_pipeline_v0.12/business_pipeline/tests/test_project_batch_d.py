"""Generic Monte Carlo for non-schedule decisions: NPV and profit simulations.

Hand checks are distribution-free: the seeded sample is fixed, so the reported
mean, percentiles and positive share are reproducible; the checks verify the
bounds of every draw, the percentile order and the counted probability.
"""

import sys
import unittest

sys.path.insert(0, "src")
from bp import server  # noqa: E402
from bp.methods import DataError, LIBRARY  # noqa: E402
from bp.orchestrator import Pipeline  # noqa: E402

NPV = {"model": "npv", "iterations": "2000", "seed": "7", "discount_rate": "0.10",
       "cashflows": [
           {"name": "outlay", "period": "0", "distribution": "fixed", "value": "-1000"},
           {"name": "year_one", "period": "1", "distribution": "triangular", "low": "200", "mode": "400", "high": "600"},
           {"name": "year_two", "period": "2", "distribution": "triangular", "low": "200", "mode": "400", "high": "600"},
           {"name": "year_three", "period": "3", "distribution": "triangular", "low": "200", "mode": "400", "high": "600"}]}

PROFIT = {"model": "profit", "iterations": "1000", "seed": "11", "fixed_cost": "500",
          "variables": [
              {"name": "price", "distribution": "triangular", "low": "8", "mode": "10", "high": "12"},
              {"name": "variable_cost", "distribution": "uniform", "low": "3", "high": "5"},
              {"name": "volume", "distribution": "triangular", "low": "80", "mode": "100", "high": "130"}]}


def run(inputs):
    method = LIBRARY["monte_carlo"]
    return method.impl(inputs), method.tests(inputs, method.impl)


class ArithmeticTest(unittest.TestCase):
    def test_the_npv_simulation_is_seeded_and_reproducible(self):
        first, checks = run(NPV)
        second, _ = run(NPV)
        self.assertAlmostEqual(float(first["mean_result"]), -9.1953867, places=4)
        self.assertAlmostEqual(float(first["p50_result"]), -9.6274885, places=4)
        self.assertAlmostEqual(float(first["p90_result"]), 143.5660091, places=4)
        self.assertAlmostEqual(float(first["probability_positive"]), 0.465, places=6)
        self.assertEqual(first, second)
        self.assertTrue(all(ok for _, ok in checks), checks)

    def test_the_profit_simulation_uses_the_declared_distributions(self):
        out, checks = run(PROFIT)
        self.assertAlmostEqual(float(out["mean_result"]), 120.7629138, places=4)
        self.assertAlmostEqual(float(out["probability_positive"]), 0.842, places=6)
        self.assertGreaterEqual(float(out["sample_min_price"]), 8.0)
        self.assertLessEqual(float(out["sample_max_price"]), 12.0)
        self.assertTrue(all(ok for _, ok in checks), checks)

    def test_a_different_seed_changes_the_sample(self):
        first, _ = run(NPV)
        second, _ = run({**NPV, "seed": "8"})
        self.assertNotEqual(first["mean_result"], second["mean_result"])


class RefusalTest(unittest.TestCase):
    def test_a_triangular_distribution_needs_ordered_values(self):
        bad = {**NPV, "cashflows": [{"name": "x", "period": "0", "distribution": "triangular",
                                     "low": "10", "mode": "5", "high": "20"}]}
        with self.assertRaises(DataError):
            LIBRARY["monte_carlo"].impl(bad)

    def test_iterations_are_capped(self):
        with self.assertRaises(DataError):
            LIBRARY["monte_carlo"].impl({**NPV, "iterations": "5001"})

    def test_profit_needs_all_three_variables(self):
        with self.assertRaises(DataError):
            LIBRARY["monte_carlo"].impl({**PROFIT, "variables": PROFIT["variables"][:2]})


class PresetTest(unittest.TestCase):
    def test_the_preset_delivers_through_the_pipeline(self):
        result = Pipeline().run(server.PRESETS["montecarlo"], lambda _s: True)
        self.assertEqual(result.status, "delivered", result.blocked_reason)
        checks = result.appendix.get("tests", [])
        self.assertTrue(all((item[1] if isinstance(item, (list, tuple)) else bool(item)) for item in checks), checks)


if __name__ == "__main__":
    unittest.main()
