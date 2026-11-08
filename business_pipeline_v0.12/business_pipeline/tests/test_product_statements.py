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
from bp.product import statements, statements_verify  # noqa: E402


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


class RequestTest(unittest.TestCase):
    """Tip 3: the request picks what is rendered; the ledger is always built in full.

    Compute scope is not output scope.  A "balance sheet only" request still computes the income
    statement and the equity roll, and the record says so; a "cash flow only" request drags in the
    whole stack.  What the student sees is only what they asked for.
    """

    @classmethod
    def setUpClass(cls):
        attach()
        cls.full = statements.solve(TB)
        cls.is_only = statements.solve(TB + "\nShow only the income statement.")
        cls.bs_only = statements.solve(TB + "\nPrepare the balance sheet only.")
        cls.cf_only = statements.solve(TB + "\nI only want the cash flow statement.")

    def test_the_default_is_still_the_full_set(self):
        self.assertEqual(self.full["requested"], ["IS", "RE", "BS", "CF"])
        self.assertEqual(self.full["computed"], ["IS", "RE", "BS", "CF"])
        self.assertEqual(self.full["hidden"], [])

    def test_an_income_statement_request_stands_alone(self):
        record = self.is_only
        self.assertTrue(record["solved"], record.get("refusal"))
        self.assertEqual(record["requested"], ["IS"])
        self.assertEqual(record["computed"], ["IS"])
        self.assertEqual(record["hidden"], [])
        self.assertIn("INCOME STATEMENT", record["statements"]["income_statement"])
        self.assertEqual(record["statements"]["balance_sheet"], "")
        self.assertEqual(record["statements"]["equity"], "")
        self.assertIsNone(record["statements"]["cash_flow"])
        self.assertIsNone(record["statements"]["cash_flow_withheld_because"])
        self.assertNotIn("BALANCE SHEET", record["statements_only"])

    def test_a_balance_sheet_request_computes_what_it_needs_and_hides_it(self):
        record = self.bs_only
        self.assertTrue(record["solved"], record.get("refusal"))
        self.assertEqual(record["requested"], ["BS"])
        self.assertEqual(record["computed"], ["IS", "RE", "BS"],
                         "a balance sheet drags in net income and the equity roll")
        self.assertEqual(record["hidden"], ["IS", "RE"])
        self.assertIn("BALANCE SHEET", record["statements"]["balance_sheet"])
        self.assertEqual(record["statements"]["income_statement"], "")
        self.assertEqual(record["statements"]["equity"], "")
        self.assertNotIn("INCOME STATEMENT", record["statements_only"])

    def test_a_cash_flow_request_requires_the_whole_ledger_and_is_withheld_here(self):
        record = self.cf_only
        self.assertEqual(record["requested"], ["CF"])
        self.assertEqual(record["computed"], ["IS", "RE", "BS", "CF"],
                         "the cash flow statement is downstream of everything")
        self.assertEqual(record["hidden"], ["IS", "RE", "BS"])
        self.assertIsNone(record["statements"]["cash_flow"])
        self.assertIn("prior balance sheet", record["statements"]["cash_flow_withheld_because"])
        self.assertEqual(record["warnings"][0]["statement"], "CF")

    def test_the_numbers_do_not_drift_between_a_partial_and_a_full_run(self):
        self.assertEqual(self.is_only["core"]["scalars"], self.full["core"]["scalars"])
        self.assertEqual(self.bs_only["core"]["scalars"], self.full["core"]["scalars"])
        self.assertEqual(self.is_only["statements"]["income_statement"],
                         self.full["statements"]["income_statement"])
        self.assertEqual(self.bs_only["statements"]["balance_sheet"],
                         self.full["statements"]["balance_sheet"])

    def test_an_explicit_request_wins_over_the_instruction_text(self):
        record = statements.solve(TB + "\nShow only the balance sheet.", statements=["IS"])
        self.assertEqual(record["requested"], ["IS"])

    def test_the_record_keys_and_short_codes_are_both_accepted(self):
        record = statements.solve(TB, statements=["income_statement", "cash-flow"])
        self.assertEqual(record["requested"], ["IS", "CF"])
        for code in ("IS", "RE", "BS", "CF"):
            self.assertEqual(statements._statement_code(code.lower()), code, code)
        with self.assertRaises(statements.StatementError):
            statements.solve(TB, statements=["PL"])

    def test_detection_needs_a_request_not_just_a_mention(self):
        self.assertIsNone(statements.wants_statements(TB))
        self.assertIsNone(statements.wants_statements("The balance sheet showed cash of 5,000."))
        self.assertEqual(statements.wants_statements("only the balance sheet"), ("BS",))
        self.assertEqual(statements.wants_statements("prepare the income statement and balance sheet"),
                         ("IS", "BS"))
        self.assertEqual(statements.wants_statements("give me the cash flow statement"), ("CF",))

    def test_the_product_dependency_table_matches_the_plan_layer(self):
        from bp import statement_plan  # the test may import the core; the product package may not
        self.assertEqual({code: tuple(requires["requires"])
                          for code, requires in statement_plan.PROJECTIONS.items()},
                         {code: tuple(requires) for code, requires in statements.PROJECTIONS.items()})
        self.assertEqual(statement_plan.dependency_closure(["BS"]), ["IS", "RE", "BS"])
        self.assertEqual(statement_plan.dependency_closure(["IS"]), ["IS"])
        self.assertEqual(statement_plan.dependency_closure(["CF"]), ["IS", "RE", "BS", "CF"])


class OutputVerifierTest(unittest.TestCase):
    """A single-statement record is complete when that statement is present, and only then."""

    @staticmethod
    def blank():
        return {"income_statement": "", "balance_sheet": "", "equity": "", "cash_flow": None,
                "cash_flow_withheld_because": None}

    def test_one_requested_statement_is_a_complete_record(self):
        record = self.blank()
        record["income_statement"] = "INCOME STATEMENT"
        self.assertEqual(statements_verify.verify_output(record, ["IS"]), [])

    def test_a_missing_requested_statement_is_a_problem(self):
        problems = statements_verify.verify_output(self.blank(), ["IS"])
        self.assertEqual([problem["check"] for problem in problems], ["output"])
        self.assertIn("requested but is empty", problems[0]["detail"])

    def test_a_statement_computed_but_not_requested_must_not_be_rendered(self):
        record = self.blank()
        record["income_statement"] = "INCOME STATEMENT"
        record["balance_sheet"] = "BALANCE SHEET"
        problems = statements_verify.verify_output(record, ["IS"])
        self.assertTrue(any("not requested" in problem["detail"] for problem in problems))

    def test_a_withheld_cash_flow_needs_its_reason(self):
        record = self.blank()
        self.assertTrue(statements_verify.verify_output(record, ["CF"]),
                        "an empty cash flow with no reason is a silent gap")
        record["cash_flow_withheld_because"] = "one trial balance; no prior period to compare"
        self.assertEqual(statements_verify.verify_output(record, ["CF"]), [])


class PlanLayerTest(unittest.TestCase):
    """A narrative goes to the plan layer first; a refusal there is final, a missing model is not."""

    NARRATIVE = "The owner started business on 2 January 2026 with cash of 50,000."

    def setUp(self):
        attach()
        from bp import statement_plan
        self.plan = statement_plan
        self.previous = {key: statements._CORE.get(key) for key in ("extract", "build", "reader")}
        statements.attach_core(
            extract=lambda text, period: {
                "entries": [{"date": "2026-01-02", "description": "Owner invested cash",
                             "lines": [{"account": "1000", "debit": "50000"},
                                       {"account": "3000", "credit": "50000"}]}],
                "adjustments": [], "policy": {"fiscal_year_end": "2026-12-31"}, "unplaceable": []},
            build=lambda plan: statement_plan.build(
                dict(plan, chart=statement_plan.DEFAULT_CHART)),
            reader=lambda text: (_ for _ in ()).throw(
                AssertionError("the council must not be asked when the plan layer can read it")))

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                statements._CORE.pop(key, None)
            else:
                statements._CORE[key] = value

    def test_a_narrative_is_solved_by_the_plan_layer(self):
        record = statements.solve(self.NARRATIVE)
        self.assertTrue(record["solved"], record.get("refusal"))
        self.assertEqual(record["reading_source"], "plan")
        self.assertEqual(record["core"]["scalars"]["total_assets"], "50000")
        self.assertIn("INCOME STATEMENT", record["statements"]["income_statement"])

    def test_the_request_scope_applies_to_a_narrative_too(self):
        record = statements.solve(self.NARRATIVE, statements=["BS"])
        self.assertEqual(record["requested"], ["BS"])
        self.assertEqual(record["computed"], ["IS", "RE", "BS"])
        self.assertEqual(record["hidden"], ["IS", "RE"])
        self.assertEqual(record["statements"]["income_statement"], "")

    def test_a_missing_model_falls_through_to_the_next_reader(self):
        statements.attach_core(extract=lambda text, period: (_ for _ in ()).throw(
            statements.NoModel("no model is configured")))
        statements.attach_core(reader=lambda text: (_ for _ in ()).throw(RuntimeError("council down")))
        with self.assertRaises(statements.StatementError) as caught:
            statements.solve(self.NARRATIVE)
        self.assertIn("no model is configured", str(caught.exception))
        self.assertIn("council down", str(caught.exception))

    def test_a_plan_refusal_is_not_retried_by_another_reader(self):
        statements.attach_core(extract=lambda text, period: (_ for _ in ()).throw(
            statements.StatementError("grounding: months_expired is not in the instruction")))
        with self.assertRaises(statements.StatementError) as caught:
            statements.solve(self.NARRATIVE)
        self.assertIn("grounding", str(caught.exception))


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
        # The market ratio is now defined in the registry, so it is named as not computed with the
        # input it lacks, rather than as an undefined gap.
        self.assertIn("share_price", named["market_to_book"]["reason"])

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


class ParserCauseTest(unittest.TestCase):
    """A journal-entry list and a narrative clause are not a comparative trial balance."""

    JOURNAL = ("Journal-entry format: Urban Threads Ltd recorded the following journal "
               "entries for April: Dr Equipment 3,000 Cr Capital 3,000; "
               "Dr Cash 18,000 Cr Capital 18,000; Dr Inventory 7,500 Cr Accounts Payable "
               "7,500. Prepare the management accounts.")

    def test_a_journal_entry_list_is_a_transactions_problem(self):
        kind, _cue, _sentence = statements.classify(self.JOURNAL)
        self.assertEqual(kind, "transactions")

    def test_a_trial_balance_with_one_side_per_account_stays_a_trial_balance(self):
        text = ("Trial balance as at 31 December: Dr Cash 12,500; "
                "Dr Accounts Receivable 8,300; Cr Accounts Payable 5,200; "
                "Cr Capital 15,600.")
        self.assertEqual(statements.classify(text)[0], "trial_balance")

    def test_a_narrative_clause_with_a_verb_is_not_a_comparative(self):
        self.assertEqual(statements.column_lines(
            "During the year it earned $42,000 service revenue, incurred $28,000 expenses, "
            "and collected $39,000 cash."), [])
        self.assertEqual(statements.column_lines(
            "The owner invested cash of $25,000 and equipment valued at $8,000."), [])

    def test_a_comparative_column_is_still_refused(self):
        self.assertTrue(statements.column_lines("Cash 2025 10,000 2024 8,000"))

    def test_a_transactions_reading_is_not_diagnosed_as_a_trial_balance(self):
        from unittest import mock
        reading = {"problem_type": "transactions", "places": 2, "journal": [{"lines": []}]}
        with mock.patch.object(statements, "_diagnose") as diagnose:
            returned = statements.derive_balancing_figure(reading, [{"label": "Capital"}])
        diagnose.assert_not_called()
        self.assertIs(returned, reading)


if __name__ == "__main__":
    unittest.main()
