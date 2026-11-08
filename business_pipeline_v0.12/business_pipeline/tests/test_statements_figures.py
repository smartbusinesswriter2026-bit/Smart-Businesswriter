"""The statement record as a shared input, and the library's accounting-group tag.

Two things are proved here:

1. `statements.figures(record)` turns a solved record into a stable bundle (the named figures
   plus the structured groups) that ratio, DuPont, trend, working-capital, pro-forma and tax
   tiles can consume without a student re-typing anything.  The route
   `GET /api/cases/statements/{id}/figures` returns the same bundle.
2. `statement_library.record_problem(group, ...)` tags a problem with its accounting shelf, and
   `gap_report()` reports `by_group` and can be filtered to one group, so a calculator's
   failures are counted beside the statements tile's.
"""

import os
import sys
import tempfile
import unittest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp import statement_plan  # noqa: E402
from bp.product import statements, statement_library  # noqa: E402

TB = ("The following trial balance was extracted at 31 December 2026.\n"
      "Cash 7,000\nTrade receivables 3,000\nInventory 1,500\nEquipment 10,000\n"
      "Accumulated depreciation 2,000\nTrade payables 2,500\nCapital 13,000\n"
      "Sales 9,000\nPurchases 4,000\nRent 1,000")

TB2 = ("The following trial balance was extracted at 31 December 2025.\n"
       "Cash 8,000\nTrade receivables 2,500\nInventory 1,200\nEquipment 10,000\n"
       "Accumulated depreciation 1,500\nTrade payables 2,000\nCapital 13,000\n"
       "Sales 11,700\nPurchases 5,000\nRent 1,500")


def attach():
    statements.attach_core(
        solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
        diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
            {"journal": None, "trial_balance": rows, "places": places}),
        ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
        dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
        working_capital=lambda inputs: methods.LIBRARY["working_capital"].impl(inputs),
        working_capital_cycle=lambda inputs: methods.LIBRARY["working_capital_cycle"].impl(inputs),
        trend=lambda inputs: methods.LIBRARY["trend_analysis"].impl(inputs),
        tax_reconciliation=lambda inputs: methods.LIBRARY["tax_reconciliation"].impl(inputs),
        build=lambda plan: statement_plan.build(plan))


class FiguresBundleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._old_cases = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = tempfile.mkdtemp(prefix="bp-statements-fig-")
        attach()
        cls.record = statements.save(statements.solve(TB, currency="USD"))
        cls.record2 = statements.save(statements.solve(TB2, currency="USD"))

    @classmethod
    def tearDownClass(cls):
        statements.reset_core()
        if cls._old_cases is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = cls._old_cases

    def test_the_bundle_carries_the_named_figures(self):
        bundle = statements.figures(self.record)
        self.assertEqual(bundle["format"], statements.FIGURES_FORMAT)
        self.assertEqual(bundle["source"]["record"], self.record.get("id"))
        for name in ("revenue", "net_income", "current_assets", "current_liabilities",
                     "inventory", "receivables", "payables", "total_assets",
                     "total_liabilities", "equity"):
            self.assertIn(name, bundle["figures"], name)

    def test_the_bundle_carries_the_structured_groups(self):
        bundle = statements.figures(self.record)
        self.assertIn("income_groups", bundle)
        self.assertIn("balance_sheet_groups", bundle)
        self.assertIn("equity", bundle)
        self.assertIn("cash_flow", bundle)
        self.assertIsInstance(bundle["gaps"], list)

    def test_a_refused_record_has_no_bundle(self):
        with self.assertRaises(statements.StatementError):
            statements.figures({"format": statements.FORMAT, "solved": False,
                                "refusal": "debits 5000, credits 4500"})

    def test_the_route_returns_the_same_bundle(self):
        status, payload = statements.handle("GET", [self.record.get("id"), "figures"])
        self.assertEqual(status, 200)
        self.assertEqual(payload["format"], statements.FIGURES_FORMAT)
        self.assertEqual(payload["figures"], statements.figures(self.record)["figures"])

    def test_the_ratios_consumer_computes_from_the_bundle(self):
        pack = statements.ratios(self.record)
        self.assertEqual(pack["format"], statements.RATIOS_FORMAT)
        self.assertTrue(pack["computed"], "the ratio pack computed nothing")
        names = {row.get("ratio") for row in pack["computed"]}
        self.assertIn("current_ratio", names)
        for row in pack["named_unsupported"]:
            self.assertIsNotNone(row.get("reason"))

    def test_the_ratios_route_returns_the_pack(self):
        status, payload = statements.handle("GET", [self.record.get("id"), "ratios"])
        self.assertEqual(status, 200)
        self.assertEqual(payload["format"], statements.RATIOS_FORMAT)
        self.assertEqual(payload["computed"], statements.ratios(self.record)["computed"])

    def test_the_bundle_carries_a_derived_map(self):
        bundle = statements.figures(self.record)
        self.assertIn("derived", bundle)
        self.assertIsInstance(bundle["derived"], dict)

    def test_dupont_runs_from_the_bundle(self):
        pack = statements.dupont(self.record)
        self.assertEqual(pack["format"], statements.DUPONT_FORMAT)
        self.assertIn("return_on_equity", pack["result"])
        self.assertIn("roe_three_step", pack["result"])
        self.assertFalse(pack["five_step"])
        self.assertTrue(pack["not_run"])

    def test_the_dupont_route_returns_the_pack(self):
        status, payload = statements.handle("GET", [self.record.get("id"), "dupont"])
        self.assertEqual(status, 200)
        self.assertEqual(payload["format"], statements.DUPONT_FORMAT)
        self.assertEqual(payload["result"], statements.dupont(self.record)["result"])

    def test_working_capital_names_the_declared_inputs(self):
        with self.assertRaises(statements.StatementError) as caught:
            statements.working_capital(self.record)
        self.assertIn("annual_demand", str(caught.exception))

    def test_working_capital_runs_with_the_declared_terms(self):
        extra = {"annual_demand": "1000", "order_cost": "50", "holding_cost_per_unit": "2",
                 "discount_percent": "0.02", "credit_terms_days": "30", "discount_days": "10"}
        pack = statements.working_capital(self.record, extra=extra)
        self.assertEqual(pack["format"], statements.WORKING_CAPITAL_FORMAT)
        self.assertIn("cash_conversion_cycle", pack["result"])
        self.assertIn("dso", pack["result"])

    def test_the_working_capital_route_accepts_the_terms(self):
        extra = {"annual_demand": "1000", "order_cost": "50", "holding_cost_per_unit": "2",
                 "discount_percent": "0.02", "credit_terms_days": "30", "discount_days": "10"}
        status, payload = statements.handle("POST", [self.record.get("id"), "working-capital"],
                                            {"extra": extra})
        self.assertEqual(status, 200)
        self.assertEqual(payload["format"], statements.WORKING_CAPITAL_FORMAT)

    def test_the_cycle_runs_from_the_bundle_alone(self):
        pack = statements.cycle(self.record)
        self.assertEqual(pack["format"], statements.CYCLE_FORMAT)
        self.assertIn("cash_conversion_cycle", pack["result"])
        self.assertIn("dso", pack["result"])

    def test_the_cycle_route_returns_the_pack(self):
        status, payload = statements.handle("GET", [self.record.get("id"), "cycle"])
        self.assertEqual(status, 200)
        self.assertEqual(payload["format"], statements.CYCLE_FORMAT)
        self.assertEqual(payload["result"], statements.cycle(self.record)["result"])

    def test_the_trend_needs_two_records(self):
        with self.assertRaises(statements.StatementError):
            statements.trend([self.record])

    def test_the_trend_runs_on_two_periods(self):
        pack = statements.trend([self.record, self.record2])
        self.assertEqual(pack["format"], statements.TREND_FORMAT)
        self.assertEqual(pack["periods"], ["2025", "2026"])
        self.assertIn("revenue_cagr", pack["result"])
        self.assertIn("net_margin_latest", pack["result"])

    def test_the_trend_route_returns_the_pack(self):
        status, payload = statements.handle(
            "POST", ["trend"], {"records": [self.record.get("id"), self.record2.get("id")]})
        self.assertEqual(status, 200)
        self.assertEqual(payload["format"], statements.TREND_FORMAT)
        self.assertEqual(payload["result"], statements.trend([self.record, self.record2])["result"])

    def test_the_tax_note_reconciles_the_record(self):
        bundle = statements.figures(self.record)
        net = Decimal(bundle["figures"]["net_income"])
        note = statements.tax_note(self.record, {"tax_rate": "0.25", "non_deductible": "1000"})
        self.assertEqual(note["format"], statements.TAX_FORMAT)
        self.assertEqual(Decimal(note["result"]["taxable_income"]), net + Decimal("1000"))
        self.assertIn("current_tax", note["result"])

    def test_the_tax_route_returns_the_note(self):
        status, payload = statements.handle("POST", [self.record.get("id"), "tax"],
                                            {"extra": {"tax_rate": "0.25"}})
        self.assertEqual(status, 200)
        self.assertEqual(payload["format"], statements.TAX_FORMAT)


class GroupTagTest(unittest.TestCase):
    def setUp(self):
        self._old = statement_library._STORE_DIR
        statement_library._STORE_DIR = tempfile.mkdtemp(prefix="slib_test_")

    def tearDown(self):
        statement_library._STORE_DIR = self._old

    def test_a_group_tag_is_counted_and_filterable(self):
        statement_library.record_problem("Cost and variance analysis", "standard cost problem",
                                         solved=False, refusal="unfavourable material price variance")
        statement_library.record_problem("Working capital and financing", "cash cycle problem",
                                         solved=True)
        report = statement_library.gap_report()
        self.assertEqual(report["by_group"].get("Cost and variance analysis"), 1)
        self.assertEqual(report["by_group"].get("Working capital and financing"), 1)
        only_cost = statement_library.gap_report(group="Cost and variance analysis")
        self.assertEqual(only_cost["total"], 1)
        self.assertEqual(only_cost["by_group"].get("Cost and variance analysis"), 1)

    def test_a_calculator_records_under_its_shelf(self):
        group = statement_library.record_calculator(
            "standard_cost_variances", "standard cost problem", solved=True)
        self.assertEqual(group, "Cost and variance analysis")
        self.assertEqual(statement_library.gap_report()["by_group"].get(group), 1)

    def test_a_non_accounting_method_is_not_recorded(self):
        before = statement_library.gap_report()["total"]
        group = statement_library.record_calculator("npv", "project appraisal", solved=True)
        self.assertIsNone(group)
        self.assertEqual(statement_library.gap_report()["total"], before)


if __name__ == "__main__":
    unittest.main()
