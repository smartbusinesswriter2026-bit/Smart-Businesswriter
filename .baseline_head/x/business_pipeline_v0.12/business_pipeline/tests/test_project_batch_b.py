"""Batch B of the project-scheduling gaps: multi-project scheduling and schedule risk.

Hand-checked examples:

* two projects share a crew of two. Alpha (higher priority) takes the crew for
  periods 0-4, so beta waits: X runs 4-6 and Y 6-8, an overall finish of 8.
* the seeded simulation of the three-activity network gives a mean near 7.71,
  P80 near 8.46 and about 92.9% of runs within the nine-period target.
"""

import sys
import unittest

sys.path.insert(0, "src")
from bp import server  # noqa: E402
from bp.methods import DataError, LIBRARY  # noqa: E402
from bp.orchestrator import Pipeline  # noqa: E402

MULTI = {
    "resources": [{"name": "crew", "capacity": "2"}],
    "projects": [
        {"name": "alpha", "priority": "1", "activities": [
            {"id": "A", "duration": "2", "resource": "crew", "demand": "2", "predecessors": ""},
            {"id": "B", "duration": "2", "resource": "crew", "demand": "2", "predecessors": "A"}]},
        {"name": "beta", "priority": "2", "activities": [
            {"id": "X", "duration": "2", "resource": "crew", "demand": "1", "predecessors": ""},
            {"id": "Y", "duration": "2", "resource": "crew", "demand": "1", "predecessors": "X"}]}]}

RISK = {
    "iterations": "1000", "seed": "42", "target_duration": "9",
    "activities": [
        {"id": "A", "optimistic": "2", "most_likely": "3", "pessimistic": "5", "predecessors": ""},
        {"id": "B", "optimistic": "3", "most_likely": "4", "pessimistic": "6", "predecessors": "A"},
        {"id": "C", "optimistic": "1", "most_likely": "2", "pessimistic": "4", "predecessors": "A"}]}


def run(method_id, inputs):
    method = LIBRARY[method_id]
    return method.impl(inputs), method.tests(inputs, method.impl)


class ArithmeticTest(unittest.TestCase):
    def test_the_shared_crew_sequences_the_second_project(self):
        out, checks = run("multi_project_schedule", MULTI)
        self.assertEqual(out["overall_duration"], 8)
        self.assertEqual(out["finish_alpha"], 4)
        self.assertEqual(out["finish_beta"], 8)
        self.assertEqual(out["delay_beta"], 4)
        self.assertEqual(out["start_beta_X"], 4)
        self.assertEqual(out["start_beta_Y"], 6)
        self.assertTrue(all(ok for _, ok in checks), checks)

    def test_the_seeded_simulation_is_reproducible(self):
        first, checks = run("schedule_risk", RISK)
        second, _ = run("schedule_risk", RISK)
        self.assertAlmostEqual(float(first["mean_duration"]), 7.709254, places=5)
        self.assertAlmostEqual(float(first["p50_duration"]), 7.680388, places=5)
        self.assertAlmostEqual(float(first["p80_duration"]), 8.460928, places=5)
        self.assertAlmostEqual(float(first["p90_duration"]), 8.859843, places=5)
        self.assertAlmostEqual(float(first["probability_within_target"]), 0.929, places=6)
        self.assertEqual(first, second)
        self.assertTrue(all(ok for _, ok in checks), checks)

    def test_a_different_seed_changes_the_sample(self):
        other = {**RISK, "seed": "43"}
        first, _ = run("schedule_risk", RISK)
        second, _ = run("schedule_risk", other)
        self.assertNotEqual(first["p80_duration"], second["p80_duration"])


class RefusalTest(unittest.TestCase):
    def test_a_duplicate_project_name_is_refused(self):
        bad = {**MULTI, "projects": [MULTI["projects"][0], dict(MULTI["projects"][1], name="alpha")]}
        with self.assertRaises(DataError):
            LIBRARY["multi_project_schedule"].impl(bad)

    def test_a_demand_above_capacity_is_refused(self):
        bad = {**MULTI, "projects": [{"name": "alpha", "priority": "1", "activities": [
            {"id": "A", "duration": "2", "resource": "crew", "demand": "3", "predecessors": ""}]}]}
        with self.assertRaises(DataError):
            LIBRARY["multi_project_schedule"].impl(bad)

    def test_an_impossible_three_point_estimate_is_refused(self):
        bad = {**RISK, "activities": [{"id": "A", "optimistic": "5", "most_likely": "3",
                                       "pessimistic": "2", "predecessors": ""}]}
        with self.assertRaises(DataError):
            LIBRARY["schedule_risk"].impl(bad)

    def test_a_cycle_is_refused(self):
        bad = {**RISK, "activities": [
            {"id": "A", "optimistic": "1", "most_likely": "2", "pessimistic": "3", "predecessors": "B"},
            {"id": "B", "optimistic": "1", "most_likely": "2", "pessimistic": "3", "predecessors": "A"}]}
        with self.assertRaises(DataError):
            LIBRARY["schedule_risk"].impl(bad)


class PresetTest(unittest.TestCase):
    def test_every_preset_delivers_through_the_pipeline(self):
        for key in ("multiproject", "schedrisk"):
            result = Pipeline().run(server.PRESETS[key], lambda _s: True)
            self.assertEqual(result.status, "delivered", key)
            checks = result.appendix.get("tests", [])
            self.assertTrue(all((item[1] if isinstance(item, (list, tuple)) else bool(item)) for item in checks),
                            (key, checks))


if __name__ == "__main__":
    unittest.main()
