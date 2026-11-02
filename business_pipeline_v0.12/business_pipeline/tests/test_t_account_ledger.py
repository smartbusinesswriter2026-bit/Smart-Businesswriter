"""T-accounts: one account's postings, running balance and closing balance.

The subject pages can show a T-account, but the running balance is a reading of the
account rather than a presentation choice, so it is computed in `bp.ledger` and only
rendered by `bp.report`. These tests hold that line:

- every account's T-account must foot to the trial balance (debits and credits, not
  just the net), so a ledger view can never disagree with the statements;
- opening + movement must equal the closing balance;
- postings must read chronologically even though opening entries are posted first and
  closing entries last;
- closing entries must be visible, so an income account that reaches zero explains why;
- a contra account keeps its normal side and still reduces its section.

The trap test at the end shows the footing check can fail: a ledger that drops the
opening balances does not foot, so "it foots" is a real assertion and not a tautology.
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
from bp import ledger                     # noqa: E402
from bp import report                     # noqa: E402
from bp.server import PRESETS             # noqa: E402


def base_spec():
    return copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])


def build(spec=None):
    return accounts_mod.build(spec if spec is not None else base_spec())


def journal_for(spec):
    """The journal `build()` would post for this spec, with opening and closing entries.

    Tests need the live Decimal objects: `_appendix["ledgers"]` is serialised to strings
    on its way to the API, which is right for the wire and wrong for arithmetic.
    """
    chart = ledger.Chart([ledger.Account(**a) for a in spec["chart"]])
    p = spec["period"]
    j = ledger.Journal(chart, p["start"], p["end"], spec["currency"])
    for e in spec.get("opening", []):
        j.post(ledger.Entry.make(p["start"], e.get("description", "opening"), e["lines"], 2, opening=True))
    for e in spec.get("entries", []):
        j.post(ledger.Entry.make(e["date"], e["description"], e["lines"], 2))
    pre = ledger.statements(j)
    for e in ledger.closing_entries(j, pre):
        j.post(ledger.Entry.make(e["date"], e["description"], e["lines"], 2, closing=e["closing"]))
    return j


class FootsToTheTrialBalance(unittest.TestCase):
    def test_every_account_ledger_foots_to_the_trial_balance(self):
        j = journal_for(base_spec())
        balances = j.balances()
        for lg in ledger.account_ledgers(j):
            d, c = balances[lg["code"]]
            self.assertEqual(lg["closing_debits"], d, "%s debit total does not foot" % lg["code"])
            self.assertEqual(lg["closing_credits"], c, "%s credit total does not foot" % lg["code"])


class ArithmeticHolds(unittest.TestCase):
    def test_opening_plus_movement_is_the_closing_balance(self):
        for lg in accounts_mod.build(base_spec())["_appendix"]["ledgers"]:
            opening = D(lg["opening_balance"])
            movement = D(lg["movement_debits"]) - D(lg["movement_credits"])
            sign = 1 if lg["normal"] == "D" else -1
            self.assertEqual(opening + sign * movement,
                             D(lg["closing_balance"]),
                             "%s: opening + movement != closing" % lg["code"])

    def test_running_balance_recomputes_from_the_rows(self):
        for lg in accounts_mod.build(base_spec())["_appendix"]["ledgers"]:
            running = D(lg["opening_balance"])
            sign = 1 if lg["normal"] == "D" else -1
            for row in lg["movements"]:
                running += sign * (D(row["debit"]) - D(row["credit"]))
                self.assertEqual(running, D(row["balance"]),
                                 "%s: running balance drifts at %s" % (lg["code"], row["date"]))
            self.assertEqual(running, D(lg["closing_balance"]))


class OrderingAndClosing(unittest.TestCase):
    def test_postings_read_chronologically(self):
        for lg in accounts_mod.build(base_spec())["_appendix"]["ledgers"]:
            dates = [r["date"] for r in lg["movements"]]
            self.assertEqual(dates, sorted(dates), "%s: movements are not in date order" % lg["code"])

    def test_closing_entries_are_visible_and_zero_the_income_account(self):
        ledgers = {lg["code"]: lg for lg in accounts_mod.build(base_spec())["_appendix"]["ledgers"]}
        sales = ledgers["4000"]
        self.assertTrue(sales["movements"], "the sales account should have postings")
        self.assertTrue(any(r["closing"] for r in sales["movements"]),
                        "the close of an income account must be visible in its T-account")
        self.assertEqual(D(sales["closing_balance"]), D(0),
                         "after closing, the income account should read zero")


class ContraAndEmpty(unittest.TestCase):
    def test_a_contra_account_keeps_its_normal_side(self):
        spec = base_spec()
        spec["chart"].append({"code": "1100", "name": "Accumulated depreciation",
                              "type": "asset", "line": "Accum. dep.", "contra": True})
        spec["chart"].append({"code": "5100", "name": "Depreciation expense",
                              "type": "expense", "line": "Depreciation"})
        spec["entries"].append({"date": "2026-03-31", "description": "depreciation",
                                "lines": [{"account": "5100", "debit": "300"},
                                          {"account": "1100", "credit": "300"}]})
        ledgers = {lg["code"]: lg for lg in accounts_mod.build(spec)["_appendix"]["ledgers"]}
        acc = ledgers["1100"]
        self.assertEqual(acc["normal"], "C", "a contra asset is credit-normal")
        self.assertTrue(acc["contra"])
        self.assertEqual(D(acc["closing_balance"]), D("300"))

    def test_an_account_with_no_postings_is_still_present_and_empty(self):
        spec = base_spec()
        spec["chart"].append({"code": "1200", "name": "Unused", "type": "asset", "line": "Unused"})
        ledgers = {lg["code"]: lg for lg in accounts_mod.build(spec)["_appendix"]["ledgers"]}
        unused = ledgers["1200"]
        self.assertEqual(unused["movements"], [])
        self.assertEqual(D(unused["closing_balance"]), D(0))
        rendered = report.t_account(ledger.account_ledger(journal_for(spec), "1200"))
        self.assertIn("no movement in the period", rendered)


class TrapTest(unittest.TestCase):
    def test_a_ledger_that_drops_opening_balances_does_not_foot(self):
        """Proof the footing assertion is not vacuous: if a ledger view left the opening
        balances out, it would no longer agree with the trial balance it is meant to explain."""
        spec = base_spec()
        chart = ledger.Chart([ledger.Account(**a) for a in spec["chart"]])
        p = spec["period"]
        j = ledger.Journal(chart, p["start"], p["end"], spec["currency"])
        for e in spec["opening"]:
            j.post(ledger.Entry.make(p["start"], e.get("description", "opening"), e["lines"], 2, opening=True))
        for e in spec["entries"]:
            j.post(ledger.Entry.make(e["date"], e["description"], e["lines"], 2))

        lg = ledger.account_ledger(j, "1000")
        d, _c = j.balances()["1000"]
        self.assertEqual(lg["closing_debits"], d)

        forged = dict(lg, closing_debits=lg["closing_debits"] - lg["opening_debit"])
        self.assertNotEqual(forged["closing_debits"], d,
                            "a ledger that omits the opening balance must not foot to the trial balance")


if __name__ == "__main__":
    unittest.main()
