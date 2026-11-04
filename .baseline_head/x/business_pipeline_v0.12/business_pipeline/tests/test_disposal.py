"""Asset disposal: clear the cost and the accumulated depreciation, book the proceeds, take the gain or loss.

A disposal is the one schedule that must see the books. The gain or loss is proceeds less net book
value, and net book value is only real if it is read from the ledger rather than declared twice. So
`cost` and `accumulated` are declared *and* cross-checked against the journal, and a mismatch is
refused: a disposal that cleared the wrong amount would leave a residue on the asset or on its
accumulated depreciation and quietly break A = L + E.

Revaluation is deliberately absent: it needs a declared policy for where the surplus goes, which is an
owner decision, not something to invent.
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


def equipment_spec(cost="3000", accumulated="800", proceeds="2500"):
    s = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
    s["chart"] += [
        {"code": "1200", "name": "Equipment", "type": "asset", "line": "Equipment"},
        {"code": "1210", "name": "Accumulated depreciation", "type": "asset", "line": "Accum. dep.", "contra": True},
        {"code": "4100", "name": "Gain on disposal", "type": "income", "line": "Gain"},
        {"code": "5200", "name": "Loss on disposal", "type": "expense", "line": "Loss"},
    ]
    s["entries"] += [
        {"date": "2026-02-01", "description": "buy equipment",
         "lines": [{"account": "1200", "debit": cost}, {"account": "1000", "credit": cost}]},
        {"date": "2026-02-28", "description": "depreciation on equipment",
         "lines": [{"account": "5200", "debit": accumulated}, {"account": "1210", "credit": accumulated}]},
    ]
    s["schedules"] = [{"kind": "disposal", "date": "2026-03-15",
                       "cost": cost, "accumulated": accumulated, "proceeds": proceeds,
                       "asset_account": "1200", "accum_account": "1210",
                       "proceeds_account": "1000", "gain_account": "4100", "loss_account": "5200"}]
    return s


def disposal_entry(out):
    return next(r for r in out["_appendix"]["journal"] if r["description"] == "disposal")


def lines_of(row):
    """{account: (side, Decimal amount)} — the appendix serialises amounts to strings."""
    return {l["account"]: (l["side"], D(l["debit"] if l["side"] == "D" else l["credit"]))
            for l in row["lines"]}


class TheEntryIsCorrect(unittest.TestCase):
    def test_a_gain_is_credited(self):
        out = accounts_mod.build(equipment_spec())            # NBV 2200, proceeds 2500, gain 300
        row = disposal_entry(out)
        lines = lines_of(row)
        self.assertEqual(lines["1000"], ("D", D("2500")))
        self.assertEqual(lines["1210"], ("D", D("800")))
        self.assertEqual(lines["1200"], ("C", D("3000")))
        self.assertEqual(lines["4100"], ("C", D("300")))
        self.assertEqual(row["debits"], row["credits"])

    def test_a_loss_is_debited(self):
        out = accounts_mod.build(equipment_spec(proceeds="1800"))   # NBV 2200, loss 400
        row = disposal_entry(out)
        lines = lines_of(row)
        self.assertEqual(lines["5200"], ("D", D("400")))
        self.assertNotIn("4100", lines)

    def test_breaking_even_has_no_gain_or_loss_line(self):
        out = accounts_mod.build(equipment_spec(proceeds="2200"))
        row = disposal_entry(out)
        accounts_used = {l["account"] for l in row["lines"]}
        self.assertNotIn("4100", accounts_used)
        self.assertNotIn("5200", accounts_used)
        self.assertEqual(len(row["lines"]), 3)

    def test_a_scrapped_asset_takes_the_full_net_book_value_as_a_loss(self):
        out = accounts_mod.build(equipment_spec(proceeds="0"))
        row = disposal_entry(out)
        lines = lines_of(row)
        self.assertEqual(lines["5200"], ("D", D("2200")))
        self.assertEqual(row["debits"], row["credits"])


class ItSeesTheBooks(unittest.TestCase):
    def test_the_statement_still_balances_after_a_disposal(self):
        out = accounts_mod.build(equipment_spec())
        st = out["_appendix"]["statements"]
        self.assertEqual(D(st["total_assets"]), D(st["total_liabilities"]) + D(st["equity_with_current_earnings"]))

    def test_a_declared_cost_that_the_ledger_does_not_hold_is_refused(self):
        spec = equipment_spec()
        spec["schedules"][0]["cost"] = "3500"
        with self.assertRaises(accounts_mod.EngagementError) as ctx:
            accounts_mod.build(spec)
        self.assertIn("the ledger holds", str(ctx.exception))

    def test_a_declared_accumulated_that_the_ledger_does_not_hold_is_refused(self):
        spec = equipment_spec()
        spec["schedules"][0]["accumulated"] = "500"
        with self.assertRaises(accounts_mod.EngagementError) as ctx:
            accounts_mod.build(spec)
        self.assertIn("accumulated depreciation", str(ctx.exception))


class Refusals(unittest.TestCase):
    def _sched(self, **over):
        base = dict(cost="3000", accumulated="800", proceeds="2500", date="2026-03-15", places=2,
                    asset_account="1200", accum_account="1210", proceeds_account="1000",
                    gain_account="4100", loss_account="5200")
        base.update(over)
        return base

    def test_bad_date_is_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.disposal(self._sched(date="2026-03"))

    def test_negative_proceeds_are_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.disposal(self._sched(proceeds="-1"))

    def test_accumulated_above_cost_is_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.disposal(self._sched(accumulated="4000"))

    def test_cost_must_be_positive(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.disposal(self._sched(cost="0", accumulated="0"))

    def test_a_missing_account_field_is_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.disposal(self._sched(gain_account=""))


class TrapTest(unittest.TestCase):
    def test_clearing_the_wrong_accumulated_would_leave_a_residue(self):
        """Proof the cross-check matters: post a disposal whose accumulated figure is too low and the
        accumulated-depreciation account keeps a residue, while the declared figure says it is gone."""
        spec = equipment_spec()
        # bypass the schedule and post the same entry with the wrong accumulated amount
        spec["schedules"] = []
        spec["entries"].append({"date": "2026-03-15", "description": "disposal",
                                "lines": [{"account": "1000", "debit": "2500"},
                                          {"account": "1210", "debit": "500"},
                                          {"account": "1200", "credit": "3000"}]})
        out = accounts_mod.build(spec)
        ledgers = {lg["code"]: lg for lg in out["_appendix"]["ledgers"]}
        self.assertEqual(D(ledgers["1210"]["closing_balance"]), D("300"))
        self.assertEqual(D(ledgers["1200"]["closing_balance"]), D(0))
        # the schedule path refuses exactly this: declared 800 when the ledger holds 800 is fine,
        # but declared 500 against a ledger holding 800 is refused
        bad = equipment_spec()
        bad["schedules"][0]["accumulated"] = "500"
        with self.assertRaises(accounts_mod.EngagementError):
            accounts_mod.build(bad)


if __name__ == "__main__":
    unittest.main()
