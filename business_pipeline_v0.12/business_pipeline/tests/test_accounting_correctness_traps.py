"""Trap tests for two accounting correctness bugs fixed together.

1. A contra-income account (sales returns) was closed on the wrong side, so it stayed open after
   closing and retained earnings was over-credited. The closing entry now posts on the side
   opposite each account's normal side and balances into retained earnings whichever side the net
   falls on.
2. A stated balance-sheet total ("current liabilities 25,000") with no components was ignored and
   the analysis computed zero. A stated total is now used when its components are absent, and
   components still win when both are present (nothing is double-counted).
"""

import os
import sys
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import ledger as L  # noqa: E402
from bp.product import income_statement as is_mod  # noqa: E402


class ContraIncomeClosingTest(unittest.TestCase):
    def test_a_contra_income_account_closes_and_retained_earnings_ties(self):
        chart = L.Chart([
            L.Account("1000", "Cash", "asset", "Cash"),
            L.Account("3000", "Capital", "equity", "Capital", role="capital"),
            L.Account("3100", "Retained earnings", "equity", "Retained earnings",
                      role="retained_earnings"),
            L.Account("4000", "Sales", "income", "Revenue"),
            L.Account("4100", "Sales returns", "income", "Sales returns", contra=True),
        ])
        journal = L.Journal(chart, "2026-01-01", "2026-12-31", "USD")
        journal.post(L.Entry.make("2026-01-01", "opening", [
            {"account": "1000", "debit": "1000"},
            {"account": "3000", "credit": "1000"}], opening=True))
        journal.post(L.Entry.make("2026-03-01", "sale", [
            {"account": "1000", "debit": "200000"},
            {"account": "4000", "credit": "200000"}]))
        journal.post(L.Entry.make("2026-03-02", "return", [
            {"account": "4100", "debit": "5000"},
            {"account": "1000", "credit": "5000"}]))
        pre = L.statements(journal)
        for entry in L.closing_entries(journal, pre):
            journal.post(L.Entry.make(entry["date"], entry["description"], entry["lines"],
                                      closing=entry["closing"]))
        report = L.retained_earnings_rollforward(journal, pre)
        self.assertTrue(all(ok for _name, ok, _detail in report), report)
        self.assertEqual(L.closing_balances(journal)["3100"], D(195000))


class StatedTotalsTest(unittest.TestCase):
    def test_a_stated_total_is_used_when_no_components(self):
        lines, _tax = is_mod.parse_problem("Current assets 50,000\nCurrent liabilities 25,000")
        result = is_mod.compute_balance_sheet_analysis(lines)
        self.assertEqual(result.current_assets, D(50000))
        self.assertEqual(result.current_liabilities, D(25000))
        self.assertEqual(result.current_ratio, D("2"))

    def test_components_win_over_a_stated_total(self):
        lines, _tax = is_mod.parse_problem(
            "Current assets 50,000\nInventory 20,000\nTrade receivables 25,000\n"
            "Current liabilities 25,000")
        result = is_mod.compute_balance_sheet_analysis(lines)
        self.assertEqual(result.current_assets, D(45000))
        self.assertEqual(result.current_liabilities, D(25000))
        self.assertEqual(result.current_ratio, D("1.8"))


if __name__ == "__main__":
    unittest.main()
