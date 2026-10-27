"""Depreciation beyond straight-line: reducing balance and units of production.

`depreciation(spec)` now dispatches on a declared `method`. The properties that must hold for
**every** method, because they are what makes a depreciation schedule safe to post:

- the charge never takes the carrying amount below the declared residual;
- the schedule sums exactly to cost minus residual, with the final charge absorbing rounding;
- each period produces one balanced Dr expense / Cr accumulated-depreciation entry.

Plus the things that are specific to the new methods: a reducing-balance rate is declared and not
derived; units of production charges the period's own usage and absorbs the remainder in the last
period that actually produced, not in a trailing idle period.

The trap at the end shows the two methods genuinely differ, so "the method works" is not a test
of straight-line under another name.
"""

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


BASE = dict(cost="10000", residual="1000", places=2, start="2026-01",
            dep_account="5100", accum_account="1100")


def spec(**over):
    s = dict(BASE)
    s.update(over)
    return s


def charges(rows):
    return [D(r["lines"][0]["debit"]) for r in rows]


class EveryMethodHoldsTheSameProperties(unittest.TestCase):
    def _check(self, rows):
        total = sum(charges(rows), D(0))
        self.assertEqual(total, D("9000"), "the schedule must sum to cost minus residual")
        for r in rows:
            self.assertEqual(D(r["lines"][0]["debit"]), D(r["lines"][1]["credit"]))
            self.assertGreaterEqual(D(r["lines"][0]["debit"]), D(0))

    def test_straight_line(self):
        self._check(schedules.depreciation(spec(life=4)))

    def test_reducing_balance(self):
        self._check(schedules.depreciation(spec(method="reducing_balance", life=4, rate="0.4")))

    def test_units_of_production(self):
        self._check(schedules.depreciation(
            spec(method="units_of_production", total_units="1000",
                 units_per_period=[250, 250, 250, 250])))

    def test_an_omitted_method_is_straight_line(self):
        without = schedules.depreciation(spec(life=4))
        explicit = schedules.depreciation(spec(life=4, method="straight_line"))
        self.assertEqual(charges(without), charges(explicit))


class ReducingBalance(unittest.TestCase):
    def test_it_charges_the_rate_against_the_carrying_amount(self):
        rows = schedules.depreciation(spec(method="reducing_balance", life=4, rate="0.4"))
        c = charges(rows)
        self.assertEqual(c[0], D("4000.00"))          # 40% of 10,000
        self.assertEqual(c[1], D("2400.00"))          # 40% of 6,000
        self.assertEqual(c[2], D("1440.00"))          # 40% of 3,600
        self.assertEqual(c[3], D("1160.00"))          # remainder to reach the residual
        self.assertEqual(sum(c, D(0)), D("9000"))

    def test_it_never_drops_below_the_residual(self):
        rows = schedules.depreciation(spec(method="reducing_balance", life=6, rate="0.9"))
        carrying = D("10000")
        for amount in charges(rows):
            carrying -= amount
            self.assertGreaterEqual(carrying, D("1000"))

    def test_rate_outside_zero_to_one_is_refused(self):
        for rate in ("0", "1", "1.5", "-0.2"):
            with self.assertRaises(schedules.ScheduleError):
                schedules.depreciation(spec(method="reducing_balance", life=4, rate=rate))

    def test_a_rounded_to_zero_charge_is_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.depreciation(spec(cost="0.10", residual="0", method="reducing_balance",
                                        life=4, rate="0.01"))


class UnitsOfProduction(unittest.TestCase):
    def test_it_charges_the_period_usage(self):
        rows = schedules.depreciation(spec(method="units_of_production", total_units="1000",
                                           units_per_period=[100, 400, 500]))
        self.assertEqual(charges(rows), [D("900.00"), D("3600.00"), D("4500.00")])

    def test_the_remainder_lands_in_the_last_period_that_produced(self):
        rows = schedules.depreciation(spec(method="units_of_production", total_units="3",
                                           units_per_period=[1, 1, 1, 0, 0]))
        c = charges(rows)
        self.assertEqual(len(c), 5)
        self.assertEqual(sum(c[:3], D(0)), D("9000"), "the three producing periods must absorb it all")
        self.assertEqual(c[3], D(0))
        self.assertEqual(c[4], D(0))

    def test_units_above_total_are_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.depreciation(spec(method="units_of_production", total_units="100",
                                        units_per_period=[60, 60]))

    def test_all_zero_units_are_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.depreciation(spec(method="units_of_production", total_units="100",
                                        units_per_period=[0, 0]))

    def test_negative_units_are_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.depreciation(spec(method="units_of_production", total_units="100",
                                        units_per_period=[50, -10]))


class Refusals(unittest.TestCase):
    def test_unknown_method_is_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.depreciation(spec(method="sum_of_digits", life=4))

    def test_policy_changes_are_refused_outside_straight_line(self):
        change = [{"at_period": 3, "life": 6}]
        with self.assertRaises(schedules.ScheduleError):
            schedules.depreciation(spec(method="reducing_balance", life=4, rate="0.4", changes=change))

    def test_straight_line_still_accepts_a_policy_change(self):
        rows = schedules.depreciation(spec(life=4, changes=[{"at_period": 3, "life": 6}]))
        self.assertEqual(len(rows), 6)


class TrapTest(unittest.TestCase):
    def test_the_methods_actually_differ(self):
        sl = charges(schedules.depreciation(spec(life=4)))
        rb = charges(schedules.depreciation(spec(method="reducing_balance", life=4, rate="0.4")))
        self.assertNotEqual(sl, rb, "a new method that reproduced straight-line would prove nothing")
        self.assertEqual(sl[0], D("2250.00"))
        self.assertEqual(rb[0], D("4000.00"))


class ItPostsInsideAnEngagement(unittest.TestCase):
    """The schedule must survive the whole pipeline, not just the unit call."""

    def _engagement(self, method_spec):
        import copy
        from bp import accounts as accounts_mod
        from bp.server import PRESETS
        s = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
        s["chart"].append({"code": "1100", "name": "Accumulated depreciation",
                           "type": "asset", "line": "Accum. dep.", "contra": True})
        s["chart"].append({"code": "5100", "name": "Depreciation expense",
                           "type": "expense", "line": "Depreciation"})
        schedule = dict(cost="3000", residual="0", start="2026-01", places=2,
                        dep_account="5100", accum_account="1100")
        schedule.update(method_spec)
        s["schedules"] = [dict(schedule, kind="depreciation")]
        out = accounts_mod.build(s)
        return out, out["_appendix"]["statements"]

    def _assert_balances(self, st):
        self.assertEqual(D(st["total_assets"]),
                         D(st["total_liabilities"]) + D(st["equity_with_current_earnings"]))

    def test_a_reducing_balance_schedule_posts_and_balances(self):
        out, st = self._engagement({"method": "reducing_balance", "life": 3, "rate": "0.5"})
        self._assert_balances(st)
        # net income is the pre-closing figure: 1,650 of trading profit less 3,000 depreciation
        self.assertEqual(D(out["net_income"]), D("-1350"))
        ledgers = {lg["code"]: lg for lg in out["_appendix"]["ledgers"]}
        self.assertEqual(D(ledgers["1100"]["closing_balance"]), D("3000"))
        self.assertEqual(D(ledgers["5100"]["closing_balance"]), D(0), "the expense account closes to nil")

    def test_a_units_schedule_posts_and_balances(self):
        out, st = self._engagement({"method": "units_of_production", "total_units": "300",
                                    "units_per_period": [100, 100, 100]})
        self._assert_balances(st)
        self.assertEqual(D(out["net_income"]), D("-1350"))
        ledgers = {lg["code"]: lg for lg in out["_appendix"]["ledgers"]}
        self.assertEqual(D(ledgers["1100"]["closing_balance"]), D("3000"))


if __name__ == "__main__":
    unittest.main()
