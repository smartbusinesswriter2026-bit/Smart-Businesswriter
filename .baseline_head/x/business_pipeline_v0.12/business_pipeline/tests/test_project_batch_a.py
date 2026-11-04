"""Batch A of the project-scheduling gaps: levelling, crashing and calendars.

Each method is a declared-input T1 calculation with a float second route and
five frozen checks.  The examples below are hand-checked:

* levelling delays C by two periods because B already uses the whole crew;
* crashing buys two periods of B and one of A to reach seven at a cost of 130;
* the calendar skips periods 3, 4, 8 and 9, so B runs over periods 2 and 5.
"""

import sys
import unittest

sys.path.insert(0, "src")
from bp import server  # noqa: E402
from bp.methods import DataError, LIBRARY  # noqa: E402
from bp.orchestrator import Pipeline  # noqa: E402

LEVELING = {
    "resources": [{"name": "crew", "capacity": "2"}],
    "activities": [
        {"id": "A", "duration": "2", "resource": "crew", "demand": "2", "predecessors": ""},
        {"id": "B", "duration": "2", "resource": "crew", "demand": "2", "predecessors": "A"},
        {"id": "C", "duration": "2", "resource": "crew", "demand": "1", "predecessors": "A"},
        {"id": "D", "duration": "1", "resource": "crew", "demand": "1", "predecessors": "B,C"}]}

CRASHING = {
    "target_duration": "7",
    "activities": [
        {"id": "A", "normal_duration": "5", "crash_duration": "3", "crash_cost": "100", "predecessors": ""},
        {"id": "B", "normal_duration": "4", "crash_duration": "2", "crash_cost": "80", "predecessors": "A"},
        {"id": "C", "normal_duration": "3", "crash_duration": "3", "crash_cost": "0", "predecessors": "A"}]}

CALENDAR = {
    "working_periods": "0,1,2,5,6,7,10,11,12",
    "activities": [
        {"id": "A", "duration": "2", "predecessors": ""},
        {"id": "B", "duration": "2", "predecessors": "A"},
        {"id": "C", "duration": "1", "predecessors": "B"},
        {"id": "D", "duration": "1", "predecessors": "A"}]}


def run(method_id, inputs):
    method = LIBRARY[method_id]
    return method.impl(inputs), method.tests(inputs, method.impl)


class ArithmeticTest(unittest.TestCase):
    def test_resource_levelling_delays_the_second_activity(self):
        out, checks = run("resource_leveling", LEVELING)
        self.assertEqual(out["cpm_duration"], 5)
        self.assertEqual(out["levelled_duration"], 7)
        self.assertEqual(out["levelling_delay"], 2)
        self.assertEqual(out["overallocated_periods_before"], 2)
        self.assertEqual(out["overallocated_periods_after"], 0)
        self.assertEqual(out["lv_start_C"], 4)
        self.assertTrue(all(ok for _, ok in checks), checks)

    def test_crashing_reaches_the_target_at_the_declared_cost(self):
        out, checks = run("project_crashing", CRASHING)
        self.assertEqual(out["normal_duration"], 9)
        self.assertEqual(out["crashed_duration"], 7)
        self.assertEqual(out["crash_periods_B"], 2)
        self.assertEqual(out["crash_periods_A"], 1)
        self.assertEqual(out["total_crash_cost"], 130)
        self.assertTrue(all(ok for _, ok in checks), checks)

    def test_calendar_schedule_skips_the_declared_non_working_periods(self):
        out, checks = run("calendar_schedule", CALENDAR)
        self.assertEqual(out["project_duration"], 7)
        self.assertEqual(out["es_B"], 2)
        self.assertEqual(out["ef_B"], 6)
        self.assertEqual(out["float_D"], 4)
        self.assertEqual(out["critical_count"], 3)
        self.assertTrue(all(ok for _, ok in checks), checks)


class RefusalTest(unittest.TestCase):
    def test_an_activity_above_the_resource_capacity_is_refused(self):
        inputs = {**LEVELING, "activities": [dict(LEVELING["activities"][0], demand="3")]}
        with self.assertRaises(DataError):
            LIBRARY["resource_leveling"].impl(inputs)

    def test_a_target_below_the_fully_crashed_duration_is_refused(self):
        with self.assertRaises(DataError):
            LIBRARY["project_crashing"].impl({**CRASHING, "target_duration": "5"})

    def test_an_unknown_predecessor_is_refused(self):
        inputs = {**CALENDAR, "activities": [dict(CALENDAR["activities"][0], predecessors="Z")]}
        with self.assertRaises(DataError):
            LIBRARY["calendar_schedule"].impl(inputs)

    def test_a_calendar_too_short_for_the_work_is_refused(self):
        with self.assertRaises(DataError):
            LIBRARY["calendar_schedule"].impl({**CALENDAR, "working_periods": "0,1", "activities":
                                               [{"id": "A", "duration": "3", "predecessors": ""}]})


class PresetTest(unittest.TestCase):
    def test_every_preset_delivers_through_the_pipeline(self):
        for key in ("leveling", "crashing", "calendar"):
            result = Pipeline().run(server.PRESETS[key], lambda _s: True)
            self.assertEqual(result.status, "delivered", key)
            checks = result.appendix.get("tests", [])
            self.assertTrue(all((item[1] if isinstance(item, (list, tuple)) else bool(item)) for item in checks),
                            (key, checks))


if __name__ == "__main__":
    unittest.main()
