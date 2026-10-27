"""Prepayments and deferred income: the two deferrals, which are exact mirrors.

A prepayment pays cash now for an expense later; deferred income takes cash now for revenue later.
Both must do two things and both must be visible:

1. move the cash and create a balance-sheet balance on the transaction date;
2. release that balance to the income statement over the periods it covers, with the final release
   absorbing the rounding remainder so the balance ends at **exactly zero**.

A deferral that never fully releases leaves an asset that is not an asset (or a liability that is not
a liability) sitting on the balance sheet, so "ends at zero" is the load-bearing assertion here.

The trap at the end removes the final release and shows the residue that would remain, so the
assertion is not vacuous.
"""

import copy
import os
import sys
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp import accounts as accounts_mod   # noqa: E402
from bp import schedules                  # noqa: E402
from bp.server import PRESETS             # noqa: E402


def pre(**over):
    s = dict(total="1200", periods=4, places=2, start="2026-01", date="2026-01-05",
             prepaid_account="1300", expense_account="5000", cash_account="1000")
    s.update(over)
    return s


def deferred(**over):
    s = dict(total="900", periods=3, places=2, start="2026-01", date="2026-01-10",
             cash_account="1000", deferred_account="2100", revenue_account="4000")
    s.update(over)
    return s


def amount(line):
    return D(line.get("debit") or line.get("credit"))


class Prepayment(unittest.TestCase):
    def test_payment_then_one_release_per_period(self):
        rows = schedules.prepayment(pre())
        self.assertEqual(len(rows), 5)                      # one payment + four releases
        self.assertEqual(rows[0]["date"], "2026-01-05")
        self.assertEqual(rows[0]["lines"][0]["account"], "1300")
        self.assertEqual(D(rows[0]["lines"][0]["debit"]), D("1200"))
        self.assertEqual(len(rows[1:]), 4)

    def test_the_prepaid_account_ends_at_exactly_zero(self):
        rows = schedules.prepayment(pre())
        released = sum(D(r["lines"][1]["credit"]) for r in rows[1:])
        self.assertEqual(released, D("1200"))

    def test_the_expense_carries_exactly_what_was_paid(self):
        rows = schedules.prepayment(pre())
        charged = sum(D(r["lines"][0]["debit"]) for r in rows[1:])
        self.assertEqual(charged, D("1200"))

    def test_the_remainder_lands_in_the_final_release(self):
        rows = schedules.prepayment(pre(total="1000", periods=3))
        releases = [D(r["lines"][0]["debit"]) for r in rows[1:]]
        self.assertEqual(releases, [D("333.33"), D("333.33"), D("333.34")])
        self.assertEqual(sum(releases, D(0)), D("1000"))


class DeferredIncome(unittest.TestCase):
    def test_receipt_then_one_recognition_per_period(self):
        rows = schedules.deferred_income(deferred())
        self.assertEqual(len(rows), 4)                      # one receipt + three recognitions
        self.assertEqual(rows[0]["date"], "2026-01-10")
        self.assertEqual(rows[0]["lines"][0]["account"], "1000")
        self.assertEqual(D(rows[0]["lines"][1]["credit"]), D("900"))

    def test_the_deferred_liability_ends_at_exactly_zero(self):
        rows = schedules.deferred_income(deferred())
        recognised = sum(D(r["lines"][0]["debit"]) for r in rows[1:])
        self.assertEqual(recognised, D("900"))

    def test_revenue_carries_exactly_what_was_received(self):
        rows = schedules.deferred_income(deferred())
        earned = sum(D(r["lines"][1]["credit"]) for r in rows[1:])
        self.assertEqual(earned, D("900"))


class Refusals(unittest.TestCase):
    def test_prepayment_refusals(self):
        for over in (dict(total="0"), dict(total="-5"), dict(periods=0), dict(periods="3"),
                     dict(date="2026-01"), dict(start="2026"), dict(date="2026-03-01")):
            with self.assertRaises(schedules.ScheduleError, msg=str(over)):
                schedules.prepayment(pre(**over))

    def test_deferred_income_refusals(self):
        for over in (dict(total="0"), dict(periods=0), dict(date="bad"), dict(date="2026-05-01")):
            with self.assertRaises(schedules.ScheduleError, msg=str(over)):
                schedules.deferred_income(deferred(**over))

    def test_a_release_that_rounds_to_zero_is_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.prepayment(pre(total="0.01", periods=4))


class ItPostsInsideAnEngagement(unittest.TestCase):
    def _spec(self):
        s = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
        s["chart"] += [
            {"code": "1300", "name": "Prepaid rent", "type": "asset", "line": "Prepayments"},
            {"code": "2100", "name": "Deferred income", "type": "liability", "line": "Deferred income"},
        ]
        s["schedules"] = [
            {"kind": "prepayment", "total": "900", "periods": 3, "places": 2, "start": "2026-01",
             "date": "2026-01-05", "prepaid_account": "1300", "expense_account": "5000", "cash_account": "1000"},
            {"kind": "deferred_income", "total": "600", "periods": 3, "places": 2, "start": "2026-01",
             "date": "2026-01-10", "cash_account": "1000", "deferred_account": "2100", "revenue_account": "4000"},
        ]
        return s

    def test_the_engagement_balances_and_both_deferrals_clear(self):
        out = accounts_mod.build(self._spec())
        st = out["_appendix"]["statements"]
        self.assertEqual(D(st["total_assets"]), D(st["total_liabilities"]) + D(st["equity_with_current_earnings"]))
        ledgers = {lg["code"]: lg for lg in out["_appendix"]["ledgers"]}
        self.assertEqual(D(ledgers["1300"]["closing_balance"]), D(0), "prepaid must clear by period end")
        self.assertEqual(D(ledgers["2100"]["closing_balance"]), D(0), "deferred income must clear by period end")

    def test_the_t_accounts_show_the_payment_and_the_release(self):
        out = accounts_mod.build(self._spec())
        ledgers = {lg["code"]: lg for lg in out["_appendix"]["ledgers"]}
        prepaid = ledgers["1300"]
        descriptions = [r["entry"] for r in prepaid["movements"]]
        self.assertTrue(any("released" in d for d in descriptions),
                        "the release must be visible in the prepaid T-account, not just netted away")


class TrapTest(unittest.TestCase):
    def test_dropping_the_final_release_would_leave_a_residue(self):
        rows = schedules.prepayment(pre(total="1000", periods=3))
        without_last = rows[:-1]
        released = sum(D(r["lines"][1]["credit"]) for r in without_last[1:])
        self.assertEqual(released, D("666.66"))
        self.assertNotEqual(released, D("1000"),
                            "without the final release the prepaid balance would not be nil")


if __name__ == "__main__":
    unittest.main()
