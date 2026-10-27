"""Allowance for doubtful debts: an estimate, measured against what the books already hold.

The estimate is the owner's judgement - nothing here decides what the allowance should be. What the
engine must get right is the *movement*:

- `charge` books a declared expense (Dr expense / Cr allowance);
- `target` books the movement needed to reach a wanted closing balance, which requires the ledger, and
  a target below the existing balance is a **reversal** (Dr allowance / Cr expense) rather than an error;
- `write_off` removes a specific debt (Dr allowance / Cr receivable) and cannot exceed the receivables
  actually held.

The ordering trap is the important one: a write-off reduces the allowance, so a `target` must be
measured **after** the write-off. Measured before, the engine would over-provide by exactly the
write-off amount - a mistake that looks right because every entry still balances.
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


BASE = dict(places=2, date="2026-03-31", receivable_account="1100",
            allowance_account="1110", expense_account="5300")


def sched(**over):
    s = dict(BASE)
    s.update(over)
    return s


def engagement(**over):
    """An engagement with 5,000 of receivables and an existing 200 allowance already in the books."""
    s = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
    s["chart"] += [
        {"code": "1100", "name": "Trade receivables", "type": "asset", "line": "Receivables"},
        {"code": "1110", "name": "Allowance for doubtful debts", "type": "asset", "line": "Allowance", "contra": True},
        {"code": "5300", "name": "Bad debt expense", "type": "expense", "line": "Bad debts"},
    ]
    s["entries"] += [
        {"date": "2026-02-01", "description": "credit sales",
         "lines": [{"account": "1100", "debit": "5000"}, {"account": "4000", "credit": "5000"}]},
        {"date": "2026-02-28", "description": "opening provision",
         "lines": [{"account": "5300", "debit": "200"}, {"account": "1110", "credit": "200"}]},
    ]
    schedule = dict(sched())
    schedule.update(over)
    s["schedules"] = [dict(schedule, kind="bad_debt")]
    return s


def ledgers_of(out):
    return {lg["code"]: lg for lg in out["_appendix"]["ledgers"]}


class ChargeMethod(unittest.TestCase):
    def test_a_declared_charge_is_expensed_against_the_allowance(self):
        rows = schedules.bad_debt(sched(charge="400"))
        self.assertEqual(len(rows), 1)
        lines = rows[0]["lines"]
        self.assertEqual((lines[0]["account"], lines[0]["debit"]), ("5300", "400"))
        self.assertEqual((lines[1]["account"], lines[1]["credit"]), ("1110", "400"))

    def test_a_zero_charge_posts_nothing(self):
        self.assertEqual(schedules.bad_debt(sched(charge="0")), [])


class TargetMethod(unittest.TestCase):
    def test_the_movement_reaches_the_wanted_closing_balance(self):
        out = accounts_mod.build(engagement(target="500"))
        self.assertEqual(D(ledgers_of(out)["1110"]["closing_balance"]), D("500"))

    def test_a_target_below_the_existing_balance_reverses_the_allowance(self):
        out = accounts_mod.build(engagement(target="120"))     # existing 200
        self.assertEqual(D(ledgers_of(out)["1110"]["closing_balance"]), D("120"))
        rows = [r for r in out["_appendix"]["journal"] if r["description"] == "allowance reduced"]
        self.assertTrue(rows, "a reduction must be posted, and named as a reduction")
        lines = rows[0]["lines"]
        self.assertEqual((lines[0]["account"], lines[0]["debit"]), ("1110", "80"))
        self.assertEqual((lines[1]["account"], lines[1]["credit"]), ("5300", "80"))

    def test_a_target_equal_to_the_existing_balance_posts_nothing(self):
        out = accounts_mod.build(engagement(target="200"))
        self.assertEqual(D(ledgers_of(out)["1110"]["closing_balance"]), D("200"))
        self.assertFalse([r for r in out["_appendix"]["journal"] if "allowance" in r["description"]])


class WriteOff(unittest.TestCase):
    def test_a_write_off_clears_the_receivable_against_the_allowance(self):
        out = accounts_mod.build(engagement(charge="0", write_off="150"))
        lg = ledgers_of(out)
        self.assertEqual(D(lg["1100"]["closing_balance"]), D("4850"))
        self.assertEqual(D(lg["1110"]["closing_balance"]), D("50"))

    def test_a_write_off_beyond_the_allowance_is_refused_with_a_reason(self):
        """Writing off more than the allowance holds leaves it abnormal, and the closing step refuses
        an abnormal balance anyway. This schedule catches it first and says what to do instead."""
        with self.assertRaises(accounts_mod.EngagementError) as ctx:
            accounts_mod.build(engagement(charge="0", write_off="300"))
        self.assertIn("more than the allowance held", str(ctx.exception))
        self.assertIn("write the debt off to expense", str(ctx.exception))

    def test_a_target_that_restores_the_allowance_makes_a_large_write_off_acceptable(self):
        out = accounts_mod.build(engagement(target="300", write_off="300"))
        self.assertEqual(D(ledgers_of(out)["1110"]["closing_balance"]), D("300"))

    def test_a_write_off_larger_than_the_receivables_is_refused(self):
        with self.assertRaises(accounts_mod.EngagementError) as ctx:
            accounts_mod.build(engagement(charge="0", write_off="9000"))
        self.assertIn("write-off", str(ctx.exception))


class OrderingTrap(unittest.TestCase):
    def test_the_target_is_measured_after_the_write_off(self):
        """Measured before the write-off, the allowance would close at 400 instead of 500 - and every
        entry would still balance, so only the closing balance catches the mistake."""
        out = accounts_mod.build(engagement(target="500", write_off="100"))
        closing = D(ledgers_of(out)["1110"]["closing_balance"])
        self.assertEqual(closing, D("500"))
        self.assertNotEqual(closing, D("500") - D("100"),
                            "measuring the target before the write-off would leave 400")


class Refusals(unittest.TestCase):
    def test_both_target_and_charge_are_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.bad_debt(sched(target="500", charge="400"))

    def test_neither_target_nor_charge_is_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.bad_debt(sched())

    def test_negative_amounts_are_refused(self):
        for over in (dict(charge="-1"), dict(target="-1"), dict(charge="0", write_off="-1")):
            with self.assertRaises(schedules.ScheduleError, msg=str(over)):
                schedules.bad_debt(sched(**over))

    def test_a_bad_date_is_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.bad_debt(sched(date="2026-03", charge="1"))


class ItBalances(unittest.TestCase):
    def test_the_statement_balances_with_an_allowance(self):
        out = accounts_mod.build(engagement(target="500", write_off="100"))
        st = out["_appendix"]["statements"]
        self.assertEqual(D(st["total_assets"]), D(st["total_liabilities"]) + D(st["equity_with_current_earnings"]))

    def test_the_allowance_reduces_net_receivables(self):
        out = accounts_mod.build(engagement(target="500", write_off="100"))
        lg = ledgers_of(out)
        net = D(lg["1100"]["closing_balance"]) - D(lg["1110"]["closing_balance"])
        self.assertEqual(net, D("4400"))          # 5,000 - 100 written off - 500 allowance


if __name__ == "__main__":
    unittest.main()
