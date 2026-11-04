"""Batch C of the decision gaps: decision tree, real option and weighted matrix.

Hand-checked examples:

* the decision tree's Launch alternative is 0.6 x 100 + 0.4 x -20 = 52, ahead
  of Pilot's 0.7 x 40 + 0.3 x 5 = 29.5, with a 0.4 loss probability;
* the five-step American call on a value of 100 with a 100 strike, 30%
  volatility and a 5% rate is worth 14.79, with a delta of 0.617;
* the weighted matrix gives 7.4, 7.2 and 7.0, so A ranks first.
"""

import sys
import unittest

sys.path.insert(0, "src")
from bp import server  # noqa: E402
from bp.methods import DataError, LIBRARY  # noqa: E402
from bp.orchestrator import Pipeline  # noqa: E402

TREE = {"tree": {"type": "decision", "alternatives": [
    {"name": "Launch", "node": {"type": "chance", "branches": [
        {"probability": "0.6", "node": {"type": "terminal", "value": "100"}},
        {"probability": "0.4", "node": {"type": "terminal", "value": "-20"}}]}},
    {"name": "Pilot", "node": {"type": "chance", "branches": [
        {"probability": "0.7", "node": {"type": "terminal", "value": "40"}},
        {"probability": "0.3", "node": {"type": "terminal", "value": "5"}}]}}]}}

OPTION = {"underlying_value": "100", "investment_cost": "100", "volatility": "0.30",
          "risk_free_rate": "0.05", "steps": "5", "option_type": "call", "exercise": "american"}

MCDA = {"scale_max": "10", "criteria": [{"name": "cost", "weight": "0.6"}, {"name": "speed", "weight": "0.4"}],
        "alternatives": [{"name": "A", "scores": {"cost": "9", "speed": "5"}},
                         {"name": "B", "scores": {"cost": "6", "speed": "9"}},
                         {"name": "C", "scores": {"cost": "7", "speed": "7"}}]}


def run(method_id, inputs):
    method = LIBRARY[method_id]
    return method.impl(inputs), method.tests(inputs, method.impl)


class ArithmeticTest(unittest.TestCase):
    def test_the_decision_tree_rolls_back_to_the_best_alternative(self):
        out, checks = run("decision_tree", TREE)
        self.assertEqual(out["expected_value"], 52)
        self.assertEqual(out["best_index"], 1)
        self.assertEqual(out["ev_1"], 52)
        self.assertEqual(out["ev_2"], 29.5)
        self.assertAlmostEqual(float(out["loss_probability_1"]), 0.4, places=6)
        self.assertEqual(out["worst_value_1"], -20)
        self.assertTrue(all(ok for _, ok in checks), checks)

    def test_the_real_option_lattice_matches_the_hand_check(self):
        out, checks = run("real_option", OPTION)
        self.assertAlmostEqual(float(out["option_value"]), 14.789285, places=5)
        self.assertAlmostEqual(float(out["delta"]), 0.617058, places=5)
        self.assertEqual(out["intrinsic_value"], 0)
        self.assertTrue(all(ok for _, ok in checks), checks)

    def test_the_weighted_matrix_ranks_the_alternatives(self):
        out, checks = run("multi_criteria", MCDA)
        self.assertEqual(out["best_index"], 1)
        self.assertAlmostEqual(float(out["best_total"]), 7.4, places=6)
        self.assertEqual(tuple(float(out[k]) for k in ("total_1", "total_2", "total_3")), (7.4, 7.2, 7.0))
        self.assertEqual((out["rank_1"], out["rank_2"], out["rank_3"]), (1, 2, 3))
        self.assertTrue(all(ok for _, ok in checks), checks)


class RefusalTest(unittest.TestCase):
    def test_chance_probabilities_must_sum_to_one(self):
        bad = {"tree": {"type": "decision", "alternatives": [{"name": "A", "node": {
            "type": "chance", "branches": [{"probability": "0.6", "node": {"type": "terminal", "value": "10"}},
                                           {"probability": "0.6", "node": {"type": "terminal", "value": "0"}}]}}]}}
        with self.assertRaises(DataError):
            LIBRARY["decision_tree"].impl(bad)

    def test_volatility_must_be_positive(self):
        with self.assertRaises(DataError):
            LIBRARY["real_option"].impl({**OPTION, "volatility": "0"})

    def test_weights_must_sum_to_one(self):
        bad = {**MCDA, "criteria": [{"name": "cost", "weight": "0.6"}, {"name": "speed", "weight": "0.6"}]}
        with self.assertRaises(DataError):
            LIBRARY["multi_criteria"].impl(bad)

    def test_a_score_outside_the_scale_is_refused(self):
        bad = {**MCDA, "alternatives": [{"name": "A", "scores": {"cost": "11", "speed": "5"}},
                                        {"name": "B", "scores": {"cost": "6", "speed": "9"}}]}
        with self.assertRaises(DataError):
            LIBRARY["multi_criteria"].impl(bad)


class PresetTest(unittest.TestCase):
    def test_every_preset_delivers_through_the_pipeline(self):
        for key in ("decisiontree", "realoption", "mcda"):
            result = Pipeline().run(server.PRESETS[key], lambda _s: True)
            self.assertEqual(result.status, "delivered", key)
            checks = result.appendix.get("tests", [])
            self.assertTrue(all((item[1] if isinstance(item, (list, tuple)) else bool(item)) for item in checks),
                            (key, checks))


if __name__ == "__main__":
    unittest.main()
