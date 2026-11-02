"""Statement of changes in equity: opening + movements = closing, per account, and it ties to the balance sheet.

The statement exists to show *why* equity moved, so two properties carry it:

1. **per account**: opening balance + the movements it lists = its closing balance;
2. **in total**: total closing equity equals the equity the balance sheet reports. A statement of changes
   in equity that disagrees with the balance sheet is decoration.

Movements are classified from the chart - the account's `role` and the *types* of the counterpart
accounts on a closing entry - never from the entry's description. The test that renames a closing entry
to something misleading proves that, because a description-based classifier would reclassify a profit as
a dividend.
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

from bp import ledger      # noqa: E402
from bp import report      # noqa: E402
from bp.server import PRESETS  # noqa: E402


def base_spec(dividends=False):
    s = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
    if dividends:
        s["chart"].append({"code": "3200", "name": "Dividends", "type": "equity",
                           "line": "Dividends", "role": "dividends"})
        s["entries"].append({"date": "2026-03-20", "description": "dividend declared",
                             "lines": [{"account": "3200", "debit": "300"},
                                       {"account": "1000", "credit": "300"}]})
    return s


def journal_for(spec):
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


class TheIdentityHolds(unittest.TestCase):
    def test_opening_plus_movements_equals_closing_for_every_account(self):
        eq = ledger.changes_in_equity(journal_for(base_spec(dividends=True)))
        for row in eq["accounts"]:
            moved = sum((D(m["amount"]) for m in row["movements"]), D(0))
            self.assertEqual(D(row["opening"]) + moved, D(row["closing"]),
                             "%s does not roll forward" % row["code"])

    def test_the_running_balance_in_the_statement_ends_at_the_closing_balance(self):
        eq = ledger.changes_in_equity(journal_for(base_spec(dividends=True)))
        for row in eq["accounts"]:
            if row["movements"]:
                self.assertEqual(D(row["movements"][-1]["balance"]), D(row["closing"]))

    def test_total_closing_equity_equals_the_balance_sheet(self):
        j = journal_for(base_spec(dividends=True))
        eq = ledger.changes_in_equity(j)
        st = ledger.statements(j)
        self.assertEqual(D(eq["total_closing"]), D(st["equity_with_current_earnings"]))

    def test_total_movement_is_closing_less_opening(self):
        eq = ledger.changes_in_equity(journal_for(base_spec(dividends=True)))
        self.assertEqual(D(eq["total_movement"]), D(eq["total_closing"]) - D(eq["total_opening"]))


class Classification(unittest.TestCase):
    def test_profit_for_the_period_equals_net_income(self):
        eq = ledger.changes_in_equity(journal_for(base_spec()))
        self.assertEqual(D(eq["by_kind"].get("profit for the period", "0")), D("1650"))

    def test_dividends_are_classified_as_dividends_and_are_negative(self):
        eq = ledger.changes_in_equity(journal_for(base_spec(dividends=True)))
        self.assertIn("dividends", eq["by_kind"])
        self.assertEqual(D(eq["by_kind"]["dividends"]), D("-300"))

    def test_capital_is_classified_as_capital(self):
        spec = base_spec()
        spec["entries"].append({"date": "2026-02-15", "description": "further capital",
                                "lines": [{"account": "1000", "debit": "1000"},
                                          {"account": "3000", "credit": "1000"}]})
        eq = ledger.changes_in_equity(journal_for(spec))
        self.assertEqual(D(eq["by_kind"].get("capital", "0")), D("1000"))

    def test_a_misleading_description_does_not_reclassify_a_movement(self):
        import dataclasses
        j = journal_for(base_spec(dividends=True))
        before = ledger.changes_in_equity(j)["by_kind"]

        # same journal, but every closing entry is now described as a dividend
        renamed = ledger.Journal(j.chart, j.start, j.end, j.currency)
        for e in j.entries:
            renamed.post(dataclasses.replace(e, description="dividends actually") if e.closing else e)
        after = ledger.changes_in_equity(renamed)["by_kind"]

        self.assertEqual(before, after,
                         "classification must come from the chart, not from the entry's description")


class Rendering(unittest.TestCase):
    def test_the_rendered_statement_shows_opening_movement_and_closing(self):
        text = report.statement_of_equity(ledger.changes_in_equity(journal_for(base_spec(dividends=True))))
        self.assertIn("STATEMENT OF CHANGES IN EQUITY", text)
        self.assertIn("Opening balance", text)
        self.assertIn("Closing balance", text)
        self.assertIn("Total closing", text)
        self.assertIn("(closing)", text)


class TrapTest(unittest.TestCase):
    def test_dropping_a_movement_breaks_the_identity(self):
        """Proof the per-account identity can fail: remove one movement and opening + listed
        movements no longer reaches the closing balance."""
        eq = ledger.changes_in_equity(journal_for(base_spec(dividends=True)))
        re_row = next(r for r in eq["accounts"] if r["role"] == "retained_earnings")
        self.assertTrue(re_row["movements"])
        forged = [m for m in re_row["movements"][1:]]
        moved = sum((D(m["amount"]) for m in forged), D(0))
        self.assertNotEqual(D(re_row["opening"]) + moved, D(re_row["closing"]))


if __name__ == "__main__":
    unittest.main()
