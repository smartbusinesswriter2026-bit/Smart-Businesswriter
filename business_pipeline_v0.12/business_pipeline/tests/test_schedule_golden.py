"""Schedule arithmetic against an independent golden fixture.

Every method in the library has a golden fixture generated offline by a different implementation. The
schedule engines had only property and invariant tests, which prove internal consistency but not that the
amounts are the amounts. This closes that gap: `tests/fixtures/schedule_golden.json` is produced by
`generate_schedule_golden.py`, which uses exact fractions rather than Decimal and does not import the code
under test.

The comparison is exact. A schedule amount is a currency figure at declared places; a tolerance would hide
exactly the rounding bug the fixture exists to catch.
"""

import json
import os
import sys
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp import schedules   # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "schedule_golden.json")


def load_cases():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)["cases"]


def charges(rows):
    """The amount charged to the expense/revenue account in each entry."""
    return [D(r["lines"][0]["debit"]) for r in rows]


def run_case(case):
    kind, spec = case["kind"], dict(case["spec"])
    if kind == "depreciation":
        return charges(schedules.depreciation(spec))
    if kind == "prepayment":
        # the first entry is the payment; the rest are the releases
        return charges(schedules.prepayment(spec)[1:])
    if kind == "deferred_income":
        return charges(schedules.deferred_income(spec)[1:])
    raise AssertionError("unknown golden kind %r" % kind)


class ScheduleAmountsMatchTheIndependentRoute(unittest.TestCase):
    def test_every_case(self):
        cases = load_cases()
        self.assertEqual(len(cases), 6, "the fixture should cover six schedule cases")
        for case in cases:
            with self.subTest(case["name"]):
                got = run_case(case)
                want = [D(x) for x in case["expected"]]
                self.assertEqual(got, want,
                                 "%s: %s != %s" % (case["name"], got, want))

    def test_the_fixture_records_its_generator_and_route(self):
        with open(FIXTURE, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertIn("generate_schedule_golden.py", doc["generator"])
        self.assertEqual(doc["numeric_route"], "fractions.Fraction")

    def test_the_totals_match_the_declared_amounts(self):
        """The fixture pins the per-period amounts; this pins what they add up to."""
        for case in load_cases():
            with self.subTest(case["name"]):
                spec = case["spec"]
                if case["kind"] == "depreciation":
                    expected_total = D(spec["cost"]) - D(spec["residual"])
                else:
                    expected_total = D(spec["total"])
                self.assertEqual(sum(run_case(case), D(0)), expected_total)


if __name__ == "__main__":
    unittest.main()
