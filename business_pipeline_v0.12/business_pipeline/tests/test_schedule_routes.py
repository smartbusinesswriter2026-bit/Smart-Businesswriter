"""The deterministic tier (manual §2A): a stated problem, its exact answer, no model.

Each case states labelled figures and names a schedule.  The answer every test asserts is the
one from the answer key, so a change that makes the tile "solve" a problem with a different
number fails here rather than in front of a student.

The last group asserts the *boundary*: the tier is an accelerator, not a gatekeeper.  A problem it
cannot read, a figure it does not have, or a text that is really a transaction narrative must all
fall through to the model loop — never refuse in its place.
"""

import os
import sys
import unittest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods, schedule_math, statement_plan  # noqa: E402
from bp.product import schedules, statements  # noqa: E402


def attach():
    statements.attach_core(
        solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
        diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
            {"journal": None, "trial_balance": rows, "places": places}),
        ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
        dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
        build=statement_plan.build,
        schedules=schedule_math.compute)


def money(value):
    return Decimal(str(value).replace(",", ""))


COGM = ("Data: Direct materials used 50,000; direct labor 40,000; manufacturing overhead 30,000; "
        "beginning WIP 10,000; ending WIP 12,000; beginning finished goods 15,000; ending finished "
        "goods 18,000; sales 200,000; selling and administrative expenses 35,000.\n"
        "Required: Create a cost of goods manufactured schedule and an income statement.")

CASH_FLOW = ("Data: Net income 50,000; depreciation 10,000; gain on sale of equipment 3,000; "
             "increase in AR 8,000; decrease in inventory 5,000; increase in AP 4,000; purchase of "
             "equipment 25,000; proceeds from sale of equipment 7,000; issue common stock 20,000; "
             "dividends paid 12,000; beginning cash 15,000.\n"
             "Required: Create a statement of cash flows using the indirect method.")

EQUITY = ("Data: Beginning common stock 100,000; beginning retained earnings 40,000; common stock "
          "issued 30,000; net income 25,000; dividends declared/paid 10,000; no other comprehensive "
          "income.\nRequired: Create a statement of changes in equity.")

BANK = ("Data: Bank statement balance 25,000; book cash balance 22,100; deposits in transit 4,000; "
        "outstanding checks 6,000; bank service charge 100; NSF customer check 500; note collected "
        "by bank 1,500.\nRequired: Prepare a bank reconciliation, journal entries, and the cash "
        "balance to report.")

ADJUSTED = ("Data - unadjusted trial balance: Cash 10,000 Dr; AR 20,000 Dr; Supplies 3,000 Dr; "
            "Equipment 40,000 Dr; Accumulated depreciation 8,000 Cr; AP 12,000 Cr; Unearned revenue "
            "5,000 Cr; Common stock 30,000 Cr; Retained earnings 6,000 Cr; Service revenue 45,000 Cr; "
            "Salaries expense 28,000 Dr; Rent expense 5,000 Dr.\n"
            "Adjustments: Supplies on hand 1,000; depreciation 4,000; unearned revenue earned 3,000; "
            "accrued salaries 2,000.\n"
            "Required: Journalize adjustments and create adjusted income statement and balance "
            "sheet.")


class ScheduleAnswerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        attach()

    def test_cost_of_goods_manufactured(self):
        record = statements.solve(COGM)
        scalars = record["core"]["scalars"]
        self.assertEqual(money(scalars["cost_of_goods_manufactured"]), Decimal("118000"))
        self.assertEqual(money(scalars["cost_of_goods_sold"]), Decimal("115000"))
        self.assertEqual(money(scalars["gross_profit"]), Decimal("85000"))
        self.assertEqual(money(scalars["operating_income"]), Decimal("50000"))
        self.assertTrue(all(check["ok"] for check in record["checks"]))

    def test_cash_flow_indirect(self):
        record = statements.solve(CASH_FLOW)
        scalars = record["core"]["scalars"]
        self.assertEqual(money(scalars["net_cash_operating"]), Decimal("58000"))
        self.assertEqual(money(scalars["net_cash_investing"]), Decimal("-18000"))
        self.assertEqual(money(scalars["net_cash_financing"]), Decimal("8000"))
        self.assertEqual(money(scalars["net_change_in_cash"]), Decimal("48000"))
        self.assertEqual(money(scalars["ending_cash"]), Decimal("63000"))
        self.assertTrue(all(check["ok"] for check in record["checks"]))

    def test_statement_of_changes_in_equity(self):
        record = statements.solve(EQUITY)
        self.assertEqual(record["problem_type"], "equity_statement")
        self.assertEqual(money(record["core"]["scalars"]["total_equity_closing"]), Decimal("185000"))
        text = record["statements_only"]
        self.assertIn("130,000.00", text)   # closing common stock
        self.assertIn("55,000.00", text)    # closing retained earnings

    def test_bank_reconciliation(self):
        record = statements.solve(BANK)
        self.assertEqual(money(record["core"]["scalars"]["cash_reported"]), Decimal("23000"))
        text = record["statements_only"]
        self.assertIn("23,000.00", text)
        self.assertEqual(text.count("Dr "), 3)
        self.assertEqual(text.count("Cr "), 3)
        self.assertTrue(all(check["ok"] for check in record["checks"]))

    def test_adjusted_trial_balance(self):
        record = statements.solve(ADJUSTED)
        scalars = record["core"]["scalars"]
        self.assertEqual(money(scalars["net_income"]), Decimal("7000.00"))
        self.assertEqual(money(scalars["total_assets"]), Decimal("59000.00"))
        self.assertEqual(money(scalars["total_liabilities"]), Decimal("16000.00"))
        self.assertEqual(money(scalars["total_equity"]), Decimal("43000.00"))
        self.assertIn("41,000.00", record["statements_only"])   # total expenses


class BoundaryTest(unittest.TestCase):
    """The tier accelerates; it never gates. Manual §2A and hard rule 16."""

    @classmethod
    def setUpClass(cls):
        attach()

    def test_transaction_narrative_is_not_a_schedule(self):
        text = ("The company purchased equipment for 25,000 cash and recorded depreciation of "
                "4,000 at year end. Required: prepare the cash flow statement.")
        self.assertIsNone(schedules.detect(text))

    def test_trial_balance_is_never_a_schedule(self):
        text = ("Cash 10,000 Dr\nSales 10,000 Cr\n"
                "Required: prepare a cost of goods manufactured schedule.")
        self.assertIsNone(schedules.detect(text))

    def test_missing_figure_falls_through_instead_of_refusing(self):
        incomplete = COGM.replace("ending WIP 12,000; ", "")
        self.assertIsNone(statements._solve_schedule("cogm", incomplete))

    def test_failing_check_falls_through_instead_of_answering(self):
        # The bank side cannot agree with the book side: 25,000 + 4,000 - 6,000 = 23,000, but the
        # book side is stated at 30,000 with no adjustment, so no honest answer exists.
        broken = BANK.replace("book cash balance 22,100", "book cash balance 30,000")
        self.assertIsNone(statements._solve_schedule("bank_reconciliation", broken))

    def test_detect_requires_every_required_figure(self):
        self.assertEqual(schedules.detect(COGM), "cogm")
        self.assertIsNone(schedules.detect("Required: create a cost of goods manufactured schedule."))


class LibraryTest(unittest.TestCase):
    """The learning loop reads the fields where gaps are written, in every shape."""

    def setUp(self):
        from bp.product import statement_library
        self.library = statement_library

    def test_gap_report_reads_a_dict_shaped_gap(self):
        marker = "PROBE GAP " + str(os.getpid())
        self.library.record({"id": marker, "instruction": marker, "solved": False,
                             "reading": {"missing": [{"what": marker, "why": "probe"}]}},
                            origin="test")
        report = self.library.gap_report(top=1000)
        seen = [p["item"] for p in report["proposals"]] + [p["item"] for p in report["singles"]]
        self.assertIn(marker, seen)

    def test_gap_report_counts_distinct_problems(self):
        marker = "DISTINCT GAP " + str(os.getpid())
        for n in range(3):
            self.library.record({"id": marker + str(n), "instruction": marker + " " * n,
                                 "solved": False,
                                 "reading": {"missing": [{"what": marker, "why": "probe"}]}},
                                origin="test")
        report = self.library.gap_report(top=1000)
        proposal = next(p for p in report["proposals"] if p["item"] == marker)
        self.assertGreaterEqual(proposal["problems"], 2)

    def test_few_shot_does_not_offer_a_different_kind(self):
        marker = "FEWSHOT " + str(os.getpid())
        self.library.record({"id": marker, "instruction": marker + "trial balance cash sales revenue",
                             "solved": True, "problem_type": "trial_balance",
                             "reading_source": "parser",
                             "spec": {"entries": [{"lines": []}]}}, origin="test")
        hits = self.library.few_shot("trial balance cash sales revenue wanted", kind="bank_reconciliation")
        self.assertEqual([h["text"] for h in hits if marker in h["text"]], [])


DISPOSAL = ("Data: Equipment cost 100,000; residual value 10,000; useful life 5 years; "
            "straight-line depreciation. Sold on Dec. 31 of Year 3 for 35,000.\n"
            "Required: Compute annual depreciation, accumulated depreciation at sale, gain/loss, "
            "and show financial statement effects.")

DISPOSAL2 = ("Data: Equipment cost 200,000; residual value 20,000; useful life 10 years; "
             "straight-line depreciation. Sold on Dec. 31 of Year 4 for 90,000.\n"
             "Required: Compute annual depreciation, accumulated depreciation at sale, gain/loss.")

RATIOS = ("Data: Current assets 50,000; inventory 20,000; current liabilities 25,000; total "
          "assets 150,000; total liabilities 90,000; equity 60,000; sales 300,000; COGS 180,000; "
          "net income 30,000; accounts receivable 25,000.\n"
          "Required: Compute current ratio, quick ratio, debt ratio, gross margin, net margin, ROA, "
          "ROE, asset turnover, receivables turnover, and days sales outstanding.")

RATIOS2 = ("Data: Current assets 80,000; inventory 30,000; current liabilities 40,000; total "
           "assets 200,000; total liabilities 120,000; equity 80,000; sales 400,000; COGS 240,000; "
           "net income 40,000; accounts receivable 50,000.\n"
           "Required: Compute current ratio, quick ratio, debt ratio, gross margin, net margin, ROA, "
           "ROE, asset turnover, receivables turnover, and days sales outstanding.")

SOLE = ("Data: Cash 10,000; AR 15,000; inventory 20,000; equipment 50,000; accumulated "
        "depreciation 10,000; AP 12,000; bank loan 25,000; drawings 10,000; sales 120,000; "
        "expenses 70,000. No additional capital was contributed.\n"
        "Required: Create an income statement, statement of owner's equity, and balance sheet; "
        "determine beginning capital.")

SOLE2 = ("Data: Cash 5,000; AR 8,000; inventory 12,000; equipment 40,000; accumulated "
         "depreciation 5,000; AP 6,000; bank loan 20,000; drawings 4,000; sales 90,000; "
         "expenses 55,000. No additional capital was contributed.\n"
         "Required: Create an income statement, statement of owner's equity, and balance sheet; "
         "determine beginning capital.")


class MoreBasicProblemsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        attach()

    def test_asset_disposal(self):
        record = statements.solve(DISPOSAL)
        s = record["core"]["scalars"]
        self.assertEqual(money(s["annual_depreciation"]), Decimal("18000"))
        self.assertEqual(money(s["accumulated_depreciation"]), Decimal("54000"))
        self.assertEqual(money(s["book_value_at_disposal"]), Decimal("46000"))
        self.assertEqual(money(s["gain_or_loss_on_disposal"]), Decimal("-11000"))
        self.assertIn("18,000.00", record["statements_only"])
        self.assertIn("11,000.00", record["statements_only"])

    def test_asset_disposal_second_problem(self):
        record = statements.solve(DISPOSAL2)
        s = record["core"]["scalars"]
        self.assertEqual(money(s["annual_depreciation"]), Decimal("18000"))
        self.assertEqual(money(s["accumulated_depreciation"]), Decimal("72000"))
        self.assertEqual(money(s["book_value_at_disposal"]), Decimal("128000"))
        self.assertEqual(money(s["gain_or_loss_on_disposal"]), Decimal("-38000"))

    def test_ratio_computation(self):
        record = statements.solve(RATIOS)
        s = record["core"]["scalars"]
        self.assertEqual(money(s["current_ratio"]), Decimal("2"))
        self.assertEqual(money(s["quick_ratio"]), Decimal("1.2"))
        self.assertEqual(money(s["debt_ratio"]), Decimal("0.6"))
        self.assertEqual(money(s["gross_margin"]), Decimal("0.4"))
        self.assertEqual(money(s["net_margin"]), Decimal("0.1"))
        self.assertEqual(money(s["roa"]), Decimal("0.2"))
        self.assertEqual(money(s["roe"]), Decimal("0.5"))
        self.assertEqual(money(s["asset_turnover"]), Decimal("2"))
        self.assertEqual(money(s["receivables_turnover"]), Decimal("12"))
        self.assertAlmostEqual(float(money(s["days_sales_outstanding"])), 30.4, places=1)

    def test_ratio_computation_second_problem(self):
        record = statements.solve(RATIOS2)
        s = record["core"]["scalars"]
        self.assertEqual(money(s["current_ratio"]), Decimal("2"))
        self.assertEqual(money(s["quick_ratio"]), Decimal("1.25"))
        self.assertEqual(money(s["debt_ratio"]), Decimal("0.6"))
        self.assertAlmostEqual(float(money(s["days_sales_outstanding"])), 45.6, places=1)

    def test_sole_trader(self):
        record = statements.solve(SOLE)
        s = record["core"]["scalars"]
        self.assertEqual(money(s["net_income"]), Decimal("50000"))
        self.assertEqual(money(s["total_assets"]), Decimal("85000"))
        self.assertEqual(money(s["total_liabilities"]), Decimal("37000"))
        self.assertEqual(money(s["ending_capital"]), Decimal("48000"))
        self.assertEqual(money(s["beginning_capital"]), Decimal("8000"))
        self.assertIn("50,000.00", record["statements_only"])
        self.assertIn("8,000.00", record["statements_only"])

    def test_sole_trader_second_problem(self):
        record = statements.solve(SOLE2)
        s = record["core"]["scalars"]
        # net income = 90000 - 55000 = 35000
        self.assertEqual(money(s["net_income"]), Decimal("35000"))
        # assets = 5000+8000+12000+(40000-5000)=60000; liabilities = 6000+20000=26000
        # ending capital = 34000; beginning = 34000 - 35000 + 4000 = 3000
        self.assertEqual(money(s["total_assets"]), Decimal("60000"))
        self.assertEqual(money(s["total_liabilities"]), Decimal("26000"))
        self.assertEqual(money(s["ending_capital"]), Decimal("34000"))
        self.assertEqual(money(s["beginning_capital"]), Decimal("3000"))
