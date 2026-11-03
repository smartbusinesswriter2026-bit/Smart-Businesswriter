"""The statements tile: one instruction, the statements, the working (product layer).

No socket and no model are used here: the frozen core is attached exactly as `bp.server` attaches it,
and the deterministic reader does the reading.  The model path is `test_product_statements_council`.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp.product import statements  # noqa: E402


def attach():
    statements.attach_core(
        solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
        diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
            {"journal": None, "trial_balance": rows, "places": places}),
        ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
        dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs))


TB = ("The following trial balance was extracted at 31 December 2026.\n"
      "Cash 7,000\nTrade receivables 3,000\nInventory 1,500\nEquipment 10,000\n"
      "Accumulated depreciation 2,000\nTrade payables 2,500\nCapital 13,000\n"
      "Sales 9,000\nPurchases 4,000\nRent 1,000")


class SolveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        attach()
        cls.record = statements.solve(TB)

    def test_a_trial_balance_solves_and_every_applicable_check_passes(self):
        record = self.record
        self.assertTrue(record["solved"], record.get("refusal"))
        self.assertEqual(record["problem_type"], "trial_balance")
        self.assertEqual(record["core"]["scalars"]["net_income"], "4000")
        self.assertEqual(record["core"]["scalars"]["total_assets"], "19500")
        self.assertEqual([check["name"] for check in record["checks"] if not check["ok"]], [])
        self.assertEqual(record["core"]["scalars"]["checks_na"], "2")

    def test_the_cash_flow_is_withheld_and_says_why(self):
        self.assertIsNone(self.record["statements"]["cash_flow"])
        self.assertIn("prior balance sheet", self.record["statements"]["cash_flow_withheld_because"])

    def test_the_statements_are_the_cores_own_text(self):
        self.assertIn("BALANCE SHEET", self.record["statements"]["balance_sheet"])
        self.assertIn("Property, plant and equipment", self.record["statements"]["balance_sheet"])
        self.assertIn("STATEMENT OF CHANGES IN EQUITY", self.record["statements"]["equity"])
        self.assertIn("INCOME STATEMENT", self.record["statements"]["income_statement"])

    def test_an_out_of_balance_trial_balance_is_diagnosed_and_never_plugged(self):
        record = statements.solve("The following trial balance was extracted at 31 December 2026.\n"
                                  "Cash 5,000\nCapital 4,500")
        self.assertFalse(record["solved"])
        self.assertIn("do not build", record["refusal"])
        self.assertIsNone(record["statements"])
        self.assertEqual(record["diagnosis"]["difference"], "500")
        self.assertEqual(record["diagnosis"]["findings"][0]["kind"], "submitted-does-not-balance")
        self.assertIn("cannot_prove", record["diagnosis"])

    def test_an_incomplete_record_derives_the_capital_with_its_identity(self):
        record = statements.solve("This is an incomplete record; find the capital.\n"
                                  "Cash 7,000\nTrade receivables 3,000\nPurchases 4,000\n"
                                  "Rent 1,000\nSales 7,000\nTrade payables 2,500")
        self.assertTrue(record["solved"], record.get("refusal"))
        self.assertEqual(record["problem_type"], "incomplete_records")
        derived = record["working"]["derivations"]
        self.assertEqual([item["figure"] for item in derived], ["Capital"])
        self.assertTrue(derived[0]["derived"])
        self.assertIn("capital = assets - liabilities", derived[0]["identity"])
        self.assertEqual(record["core"]["scalars"]["net_income"], "2000")
        self.assertEqual([check["name"] for check in record["checks"] if not check["ok"]], [])

    def test_a_line_without_a_figure_is_named_not_dropped(self):
        record = statements.solve(TB + "\nThe stock was counted after the year end.")
        self.assertTrue(record["solved"])
        named = " ".join(item["what"] for item in record["working"]["missing"])
        self.assertIn("counted after the year end", named)

    def test_ratios_are_computed_only_when_the_instruction_asks(self):
        self.assertIsNone(self.record["ratios"])
        asked = statements.solve(TB + "\nAlso compute the liquidity and profitability ratios.")
        self.assertTrue(asked["ratios"]["requested"])
        self.assertGreaterEqual(len(asked["ratios"]["computed"]), 10)

    def test_an_unsupported_ratio_is_named_with_the_input_it_needs(self):
        asked = statements.solve(TB + "\nGive me the market to book ratio and the ratios.")
        named = {row["ratio"]: row for row in asked["ratios"]["named_unsupported"]}
        self.assertIn("market_to_book", named)
        self.assertIn("share_price", named["market_to_book"]["needs"])

    def test_a_philippine_currency_or_place_is_refused_with_a_reason(self):
        for text in ("Prepare this in PHP: Cash 5,000, Capital 5,000.",
                     "The business is in Manila. Cash 5,000, Capital 5,000."):
            with self.assertRaises(statements.StatementError) as caught:
                statements.solve(text)
            self.assertIn("USD", str(caught.exception))

    def test_no_philippine_string_reaches_the_output(self):
        blob = repr(self.record)
        for term in ("PHP", "PSE", "Philippin", "Manila", "\u20b1"):
            self.assertNotIn(term, blob, term + " reached the record")

    def test_the_toggle_changes_presentation_and_no_figure(self):
        presented = self.record["statements_only"]
        self.assertIn("INCOME STATEMENT", presented)
        self.assertNotIn("JOURNAL", presented)
        for figure in ("4,000.00", "19,500.00", "9,000.00"):
            self.assertIn(figure, presented, figure + " is missing from the submission view")
        self.assertEqual(statements.statements_only(self.record["statements"]), presented)

    def test_the_working_carries_the_journal_and_the_t_accounts(self):
        self.assertIn("JOURNAL", self.record["working"]["journal"])
        self.assertTrue(self.record["working"]["t_accounts"])
        self.assertIn("ACCOUNT", next(iter(self.record["working"]["t_accounts"].values())))

    def test_the_record_replays(self):
        report = statements.replay(self.record)
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["statements_match"])
        self.assertTrue(report["record_hash_match"])

    def test_the_tile_cannot_be_asked_to_fill_a_field_or_plug_a_difference(self):
        """The trap: no request shape and no code path lets a caller supply or close a total."""
        import inspect
        source = inspect.getsource(statements.solve)
        for word in ("override", "plug", "supplied_total"):
            self.assertNotIn(word, source, word + " appears in the solver")
        record = statements.solve("The following trial balance was extracted at 31 December 2026.\n"
                                  "Cash 5,000\nCapital 4,500")
        self.assertFalse(record["solved"], "a difference must never be closed by the tile")

    def test_a_contested_label_is_decided_and_recorded(self):
        """An owner's loan matches 'loan' and 'owner': the literal rule wins and the record says so."""
        placed = statements.place("Loan from owner")
        self.assertTrue(placed["contested"])
        self.assertEqual(placed["placement"]["line"], "Borrowings")
        self.assertEqual([hit["line"] for hit in placed["candidates"]], ["Borrowings", "Capital"])

    def test_an_unknown_label_is_reported_rather_than_guessed(self):
        placed = statements.place("Suspense account")
        self.assertEqual(placed["candidates"], [])
        self.assertIsNone(placed["placement"])


class ScopeTest(unittest.TestCase):
    """What the tile refuses, because a merged statement from two sets of books looks plausible."""
    @classmethod
    def setUpClass(cls):
        attach()

    def refused(self, text):
        with self.assertRaises(statements.StatementRefused) as caught:
            statements.solve(text)
        return str(caught.exception)

    def test_a_second_set_of_balances_is_refused_and_not_merged(self):
        alpha = "Trial balance at 31 December 2026.\nCash 5,000\nCapital 5,000"
        beta = "Trial balance at 31 December 2026.\nCash 2,000\nCapital 2,000"
        # each entity balances on its own, so no arithmetic invariant can catch the pair: the merged
        # trial balance balances too, which is exactly why the refusal has to be about the shape
        self.assertTrue(statements.solve(alpha)["solved"])
        self.assertTrue(statements.solve(beta)["solved"])
        message = self.refused("The following trial balances were extracted at 31 December 2026.\n"
                               "Alpha Ltd\nCash 5,000\nCapital 5,000\n"
                               "Beta Ltd\nCash 2,000\nCapital 2,000")
        self.assertIn("appears twice", message)
        self.assertIn("one set at a time", message)

    def test_two_accounts_on_one_statement_line_still_solve(self):
        record = statements.solve("Trial balance at 31 December 2026.\n"
                                  "Cash 5,000\nBank 1,000\nCapital 6,000")
        self.assertTrue(record["solved"], record.get("refusal"))
        self.assertEqual(record["core"]["scalars"]["total_assets"], "6000")
        lines = [account["line"] for account in record["spec"]["chart"]]
        self.assertEqual(lines.count("Cash"), 2, "both accounts report on the Cash line")
        self.assertEqual(len({account["code"] for account in record["spec"]["chart"]}), len(lines),
                         "two accounts on one line still get distinct codes")

    def test_a_comparative_column_is_refused(self):
        message = self.refused("Trial balance at 31 December 2026.\nCash 5,000 7,000\nCapital 5,000 7,000")
        self.assertIn("two figures on one line", message)
        self.assertIn("comparative", message)

    def test_two_periods_are_refused(self):
        message = self.refused("Trial balance at 31 December 2026.\nCash 5,000\nCapital 5,000\n"
                               "Trial balance at 31 December 2025.\nCash 4,000\nCapital 4,000")
        self.assertIn("more than one period", message)
        self.assertIn("Comparatives are not supported", message)

    def test_consolidated_statements_are_refused(self):
        message = self.refused("Prepare the consolidated financial statements. Cash 5,000. Capital 5,000.")
        self.assertIn("consolidated", message)
        self.assertIn("outside this tile", message)

    def test_a_year_inside_a_label_is_not_mistaken_for_a_comparative(self):
        record = statements.solve("Trial balance at 31 December 2026.\n"
                                  "Cash 5,000\nCapital 4,000\nLoan 2026 1,000")
        self.assertTrue(record["solved"], record.get("refusal"))
        self.assertEqual(record["core"]["scalars"]["total_assets"], "5000")


if __name__ == "__main__":
    unittest.main()
