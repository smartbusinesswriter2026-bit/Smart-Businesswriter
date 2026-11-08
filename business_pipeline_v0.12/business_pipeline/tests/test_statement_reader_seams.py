"""The reader's seams: one period model, distinct expense lines, and no prose posted as an account.

Every test here is a behaviour that was wrong before, measured against the real reader.
The narrative in `test_the_texts_own_dates_drive_the_period` is the worked case: a business
that states its own dates and no period phrase, which the reader used to refuse.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods, statement_chart, statement_extract as se  # noqa: E402
from bp.product import statements  # noqa: E402


def attach():
    statements.attach_core(
        solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
        diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
            {"journal": None, "trial_balance": rows, "places": places}),
        ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
        dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs))


class PeriodModelTest(unittest.TestCase):
    """A period is a range; a date is a point."""

    def test_a_stated_period_phrase_declares_the_period(self):
        period, source, _quote = statements.period_of(
            "Prepare the financial statements of Alder Trading for the year ended 31 December 2025.")
        self.assertEqual(period, {"start": "2025-01-01", "end": "2025-12-31"})
        self.assertEqual(source, "declared")

    def test_a_mid_year_end_names_the_year_that_ends_there(self):
        period, _source, _quote = statements.period_of(
            "Prepare the financial statements for the year ended 30 June 2025.")
        self.assertEqual(period, {"start": "2024-07-01", "end": "2025-06-30"})

    def test_a_lone_transaction_date_is_not_a_period_end(self):
        period, source, _quote = statements.period_of(
            "On 1 January 2025 the owner invested 50,000 cash in the business.")
        self.assertEqual(period, {"start": "2025-01-01", "end": "2025-12-31"})
        self.assertNotEqual(period["start"], period["end"])
        self.assertEqual(source, "derived")

    def test_a_balance_date_still_names_the_year_it_sits_in(self):
        period, source, _quote = statements.period_of(
            "The following trial balance was extracted at 31 December 2026.")
        self.assertEqual(period, {"start": "2026-01-01", "end": "2026-12-31"})
        self.assertEqual(source, "declared")

    def test_a_fiscal_year_with_both_ends_stated_is_one_period(self):
        text = ("The following trial balance was extracted at 31 December 2025 for the year "
                "1 January 2025 to 31 December 2025.")
        self.assertEqual(statements.periods_in(text), {"2025-12-31"})

    def test_two_periods_are_still_refused(self):
        text = ("Trial balance at 31 December 2026.\nCash 5,000\nCapital 5,000\n"
                "Trial balance at 31 December 2025.\nCash 4,000\nCapital 4,000")
        with self.assertRaises(statements.StatementRefused) as caught:
            statements.preflight(text)
        self.assertIn("more than one period", str(caught.exception))

    def test_a_month_day_date_is_not_a_second_figure(self):
        text = ("On 2 January 2025 the business purchased a delivery van for 30,000 cash.\n"
                "Depreciation of 5,000 was charged on the van.")
        self.assertEqual(statements.column_lines(text), [])

    def test_a_year_inside_a_label_is_not_a_second_figure(self):
        text = "Loan 2026 5,000"
        self.assertEqual(statements.column_lines(text), [])

    def test_two_figures_on_one_line_are_still_a_comparative(self):
        text = "Cash 5,000 7,000"
        self.assertEqual(statements.column_lines(text), ["Cash 5,000 7,000"])


class AccountVocabularyTest(unittest.TestCase):
    """A label names an account, or it names nothing."""

    def test_salaries_and_rent_are_separate_lines(self):
        placed = statements.place("Salaries")
        self.assertEqual(placed["placement"]["line"], "Salaries expense")
        placed = statements.place("Rent")
        self.assertEqual(placed["placement"]["line"], "Rent expense")

    def test_prose_is_not_rewritten_into_an_account(self):
        self.assertIsNone(statements._extract_account_name("Compute the net income for Alder Trading"))
        self.assertEqual(statements._extract_account_name("revenue"), "Revenue")
        self.assertEqual(statements._extract_account_name("Meridian Ltd reports: revenue"), "Revenue")

    def test_a_sentence_is_not_posted_as_an_account(self):
        text = ("The following trial balance was extracted at 31 December 2026.\n"
                "The owner invested 50,000 cash in the business.\n"
                "Cash 50,000\nCapital 50,000")
        rows, skipped = statements.parse_rows(text)
        self.assertEqual([row["label"] for row in rows], ["Cash", "Capital"])
        self.assertEqual(len(skipped), 2)

    def test_a_date_is_not_an_amount(self):
        rows, _skipped = statements.parse_rows("Cash 5,000 at 31 December 2026")
        self.assertEqual(rows[0]["written"], "5,000")
        self.assertEqual(rows[0]["label"], "Cash")


class ChartTest(unittest.TestCase):
    """One chart, carrying every code the readers post to."""

    def test_the_chart_carries_every_detector_code(self):
        from bp import statement_detect as sd
        slots = {"amount": 1, "cost": 1, "life": 5, "asset_account": "1500", "rate": 1,
                 "months_expired": 1, "total_months": 12, "beginning_inventory": 0, "purchases": 1,
                 "ending_inventory": 0, "receivables": 1, "prior_allowance": 0, "tax_rate": 0.25,
                 "pretax_income": 1, "units_this_period": 1, "total_estimated_units": 1, "residual": 0,
                 "accumulated": 0}
        posted = set()
        for _detector_id, template in sd.TEMPLATES.items():
            try:
                lines = template(dict(slots))
            except Exception:
                continue
            for account, _side, _amount in lines:
                posted.add(account)
        self.assertTrue(posted, "the detector templates posted nothing")
        self.assertEqual(posted - statement_chart.codes(), set())

    def test_the_plan_chart_is_the_one_chart(self):
        from bp import statement_plan
        self.assertEqual([dict(a) for a in statement_plan.DEFAULT_CHART],
                         [dict(a) for a in statement_chart.CHART])

    def test_the_chart_is_valid(self):
        from bp import statement_plan
        self.assertEqual(statement_plan.validate_chart(list(statement_chart.CHART)), [])


class GroundingTest(unittest.TestCase):
    """A figure is in the text, or it is proved by the text."""

    def _payload(self, amount):
        return {"entries": [{"date": "2025-01-01", "description": "credit sales", "kind": "original",
                             "source_text": "the balance on credit",
                             "lines": [{"account": "4000", "credit": amount},
                                       {"account": "1100", "debit": amount}]}]}

    def _chart(self):
        return [{"code": "4000", "name": "Revenue", "type": "income", "line": "Revenue"},
                {"code": "1100", "name": "Trade receivables", "type": "asset", "line": "Trade receivables"}]

    def test_a_stated_partition_is_grounded(self):
        text = "The business made sales of 90,000, of which 55,000 was cash and the balance on credit."
        errors = se.validate(self._payload(35000), text, self._chart(), 2, default_date="2025-01-01")
        self.assertEqual(errors, [])

    def test_a_derived_difference_is_not_refused_by_grounding(self):
        text = ("The business paid rent of 6,000 in January and bought equipment for 9,000 in March.")
        errors = se.validate(self._payload(3000), text, self._chart(), 2, default_date="2025-01-01")
        self.assertFalse(any("does not appear in the problem text" in e for e in errors), errors)

    def test_a_derived_figure_is_not_refused_by_grounding(self):
        text = "The business made sales of 90,000."
        errors = se.validate(self._payload(35000), text, self._chart(), 2, default_date="2025-01-01")
        self.assertFalse(any("does not appear in the problem text" in e for e in errors), errors)


class WorkedCaseTest(unittest.TestCase):
    """The case the notebook names: the text's own dates drive the period."""

    TEXT = ("Alder Trading opened on 1 January 2025. The owner invested 50,000 cash in the business "
            "for shares on 1 January 2025. The business purchased a delivery van for 30,000 cash on "
            "2 January 2025. It paid 6,000 cash rent on 3 March 2025. It paid 8,000 cash salaries on "
            "31 March 2025.")

    def test_the_period_comes_from_the_dates_in_the_text(self):
        period, source, _quote = statements.period_of(self.TEXT)
        self.assertEqual(period, {"start": "2025-01-01", "end": "2025-12-31"})
        self.assertEqual(source, "derived")

    def test_the_text_is_not_refused_as_a_comparative(self):
        statements.preflight(self.TEXT)          # raises if it is refused

    def test_the_transactions_read_into_one_period(self):
        from bp import statement_detect as sd
        found = sd.detect(self.TEXT)
        self.assertTrue(found, "the detector layer found nothing in the worked case")
        self.assertTrue(any(m.detector_id == "rent_payment" for m in found), found)
        self.assertTrue(any(m.detector_id == "salaries_payment" for m in found), found)


class RouteTest(unittest.TestCase):
    """The more specific reading wins, and a route that computes nothing does not answer."""

    TRIAL_BALANCE = ("The following trial balance was extracted at 31 December 2026.\n"
                     "Equipment 30,000\nCash 15,900\nTrade receivables 18,400\n"
                     "Inventory 22,600\nCost of sales 84,000\nWages 19,000\nRent 8,000\n"
                     "Utilities 3,200\nDepreciation 3,000\nInterest expense 1,200\n"
                     "Trade payables 14,800 Cr\nLoan 12,000 Cr\nCapital 20,000 Cr\n"
                     "Retained earnings 8,000 Cr\nSales 140,000 Cr\nOther income 1,500 Cr\n"
                     "Accumulated depreciation 9,000 Cr")

    def setUp(self):
        attach()

    def test_a_trial_balance_keeps_its_route_when_the_student_also_asks_for_ratios(self):
        # The analysis route reads the same figures as balances, so it ignores the
        # contra accounts: it printed total assets 86,900 where the trial-balance
        # route prints 77,900, and it hid the income statement.  A trial balance
        # is a trial balance even when the student also asks for ratios.
        record = statements.solve(self.TRIAL_BALANCE + "\nAlso compute the liquidity ratios.")
        self.assertEqual(record.get("problem_type"), "trial_balance")
        self.assertIn("IS", record.get("computed") or [])
        self.assertEqual((record.get("core") or {}).get("scalars", {}).get("total_assets"), "77900")
        ratios = (record.get("ratios") or {}).get("computed") or []
        self.assertEqual(len(ratios), 13, ratios)

    def test_a_trial_balance_with_a_preference_dividend_keeps_its_route(self):
        # "Preference dividends" is one of the EPS detectors' cues.  The EPS route
        # used to take the instruction, and the trial balance lost its balance
        # sheet: the record came back with an income statement and nothing else.
        #
        # The route is what is at stake here.  The line itself is a separate
        # finding: "Preference dividends" is not yet in the reader's account
        # vocabulary, so it is named as unplaceable rather than posted - the
        # trial balance then does not balance, and the tile says so.
        text = ("The following trial balance was extracted at 31 December 2026.\n"
                "Cash 30,000\nTrade receivables 10,000\nInventory 12,000\n"
                "Trade payables 8,000 Cr\nPreference dividends 2,000 Cr\n"
                "Capital 40,000 Cr\nSales 2,000 Cr")
        record = statements.solve(text)
        self.assertEqual(record.get("problem_type"), "trial_balance")
        self.assertNotEqual(record.get("problem_type"), "eps")
        missing = [item.get("what") for item in (record.get("reading") or {}).get("missing") or []]
        # The reader now places preference dividends as a distribution; the route is
        # still a trial balance, and the line is not lost in the missing list.
        self.assertFalse(any("Preference dividends" in str(item) for item in missing), missing)

    def test_a_route_that_computed_nothing_does_not_answer(self):
        # The financial-computations engine is tried before the reader.  When it
        # holds nothing to say it must hand the instruction back, not answer with
        # a sheet of gaps.  The instruction below names a section (the cash
        # conversion cycle) and no figures, so the engine has nothing to compute
        # and the tile refuses instead of answering.
        with self.assertRaises(statements.StatementError) as raised:
            statements.solve("Compute the cash conversion cycle for the period.")
        self.assertNotIn("financial_computations", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
