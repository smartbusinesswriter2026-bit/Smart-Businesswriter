"""Trap tests for the deterministic reader fixes.

Four shapes the handoff measured as failures now behave:

1. a bare list of accounts and balances (no "trial balance" cue) is a trial balance;
2. an exam preamble on the same line no longer hides the accounts (a sentence boundary is not a
   decimal or a dot leader);
3. a foreign currency in the text is refused with the USD message, not with "no account";
4. a ratio problem no longer crashes on an undefined `tier1_gaps`.

the adjustments narrative still needs the model reader and is not claimed here.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp import statement_plan  # noqa: E402
from bp.product import statements  # noqa: E402


def attach():
    statements.reset_core()
    statements.attach_core(
        solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
        diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
            {"journal": None, "trial_balance": rows, "places": places}),
        ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
        dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
        build=lambda plan: statement_plan.build(plan))


class ReaderFixesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        attach()

    @classmethod
    def tearDownClass(cls):
        statements.reset_core()

    def solve(self, text):
        return statements.solve(text, currency="USD")

    def test_a_bare_account_list_is_a_trial_balance(self):
        record = self.solve("Cash 10,000\nTrade receivables 5,000\nCapital 15,000")
        self.assertTrue(record["solved"], record.get("refusal"))
        self.assertEqual(record["problem_type"], "trial_balance")

    def test_an_exam_preamble_does_not_hide_the_accounts(self):
        record = self.solve(
            "BUS101 Final Examination. Question 3. The following balances were extracted at "
            "31 December 2026. Cash 10,000. Capital 10,000.")
        self.assertTrue(record["solved"], record.get("refusal"))
        self.assertEqual(record["problem_type"], "trial_balance")

    def test_a_foreign_currency_is_refused_with_the_usd_message(self):
        with self.assertRaises(statements.StatementError) as caught:
            self.solve("Cash 10,000 EUR\nCapital 10,000 EUR")
        self.assertIn("USD", str(caught.exception))

    def test_a_ratio_problem_does_not_crash(self):
        record = self.solve(
            "Compute the current ratio from these figures: current assets 50,000, "
            "current liabilities 25,000, net income 10,000, equity 40,000.")
        self.assertTrue(record["solved"], record.get("refusal"))

    ADJUSTED = """The following balances were extracted at 31 December 2025.
Cash 30,000
Trade receivables 10,000
Prepayments 6,000
Equipment 40,000
Rent 8,000
Salaries 15,000
Trade payables 9,000
Capital 30,000
Sales 70,000
Prepaid insurance of 6,000 for 12 months starting 1 February 2025.
Accrued salaries of 3,000 are unpaid at year end.
Depreciate equipment 40,000 over 5 years.
Bad debts estimated at 3% of trade receivables.
Income tax rate 25%."""

    def test_a_multi_adjustment_narrative_solves_without_the_word_adjustments(self):
        record = self.solve(self.ADJUSTED)
        self.assertTrue(record["solved"], record.get("refusal"))
        for check in record["checks"]:
            self.assertTrue(check["ok"], check)
        rendered = record.get("statements_only") or ""
        self.assertIn("Depreciation", rendered)
        self.assertIn("8,000.00", rendered)      # 40,000 / 5 years
        self.assertIn("5,500.00", rendered)      # 6,000 x 11/12 prepaid expired
        self.assertIn("7,550.00", rendered)      # 25% of the adjusted pre-tax income

    def test_an_adjustment_only_narrative_names_the_missing_trial_balance(self):
        with self.assertRaises(statements.StatementError) as caught:
            self.solve("Prepaid insurance of 6,000 for 12 months starting 1 February 2025. "
                       "Accrued salaries of 3,000 are unpaid.")
        self.assertIn("unadjusted trial balance", str(caught.exception))

    def test_an_integrated_transaction_and_adjustment_narrative_solves(self):
        record = self.solve(
            "On 1 January 2025 the owner invested 50,000 cash in the business for shares. "
            "Bought equipment for 20,000 cash. Earned 30,000 cash sales. Paid 5,000 rent. "
            "Depreciate equipment 20,000 over 5 years. Accrued salaries of 2,000 are unpaid.")
        self.assertTrue(record["solved"], record.get("refusal"))
        for check in record["checks"]:
            self.assertTrue(check["ok"], check)
        rendered = record.get("statements_only") or ""
        self.assertIn("19,000.00", rendered)    # net income after both adjustments
        self.assertIn("4,000.00", rendered)     # depreciation, 20,000 / 5


if __name__ == "__main__":
    unittest.main()
