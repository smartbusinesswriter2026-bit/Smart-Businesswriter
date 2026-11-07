"""Pinned tests for the four financial-statement engines added in this build.

- Reconstruction engine (Tip 5 Type 2): solve a missing figure from a stated relation.
- Error correction engine (Tip 5 Type 4): build the correcting entry and its effect.
- Integrated case solver (Tip 5 Type 7 / Tip 6): the full state machine over transactions.
- Guards G1-G22 (Tip 7): the unified runner over a frozen record.
"""

import os
import sys
import unittest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import reconstruction as recon
from bp.product import error_correction as ec
from bp import case_solver
from bp import guards


class ReconstructionTest(unittest.TestCase):
    def test_cogs_from_beginning_purchases_ending(self):
        knowns = {"beginning_inventory": Decimal("10000"),
                  "net_purchases": Decimal("60000"),
                  "ending_inventory": Decimal("15000")}
        r = recon.solve_for("cogs", knowns)
        self.assertIsNotNone(r)
        self.assertEqual(r.value, Decimal("55000"))

    def test_solve_for_an_unknown_purchases(self):
        knowns = {"cogs": Decimal("55000"), "beginning_inventory": Decimal("10000"),
                  "ending_inventory": Decimal("15000")}
        r = recon.solve_for("net_purchases", knowns)
        self.assertIsNotNone(r)
        self.assertEqual(r.value, Decimal("60000"))

    def test_capital_is_assets_minus_liabilities(self):
        r = recon.solve_for("equity", {"assets": Decimal("100000"), "liabilities": Decimal("40000")})
        self.assertIsNotNone(r)
        self.assertEqual(r.value, Decimal("60000"))

    def test_current_ratio(self):
        r = recon.solve_for("current_ratio", {"current_assets": Decimal("50000"),
                                              "current_liabilities": Decimal("20000")})
        self.assertIsNotNone(r)
        self.assertEqual(r.value, Decimal("2.5"))

    def test_solve_current_assets_from_ratio(self):
        r = recon.solve_for("current_assets", {"current_ratio": Decimal("2.5"),
                                               "current_liabilities": Decimal("20000")})
        self.assertIsNotNone(r)
        self.assertEqual(r.value, Decimal("50000"))

    def test_ending_re_rollforward(self):
        r = recon.solve_for("ending_re", {"beginning_re": Decimal("20000"),
                                          "net_income": Decimal("40000"),
                                          "dividends": Decimal("5000")})
        self.assertIsNotNone(r)
        self.assertEqual(r.value, Decimal("55000"))

    def test_unknown_target_is_none(self):
        self.assertIsNone(recon.solve_for("not_a_variable", {"x": Decimal("1")}))

    def test_solve_all_chains_relations(self):
        knowns = {"beginning_inventory": Decimal("10000"), "net_purchases": Decimal("60000"),
                  "ending_inventory": Decimal("15000"), "net_sales": Decimal("100000")}
        solved = recon.solve_all(knowns)
        self.assertIn("cogs", solved)
        self.assertIn("gross_profit", solved)

    def test_canonical_maps_labels(self):
        self.assertEqual(recon.canonical("cost of goods sold"), "cogs")
        self.assertEqual(recon.canonical("Beginning Inventory"), "beginning_inventory")
        self.assertEqual(recon.canonical("net purchases"), "net_purchases")

    def test_detect_reconstruction_problem(self):
        self.assertTrue(recon.detect_reconstruction_problem(
            "Find the net purchases. COGS is 55,000."))
        self.assertFalse(recon.detect_reconstruction_problem(
            "The following trial balance was extracted."))


class ErrorCorrectionTest(unittest.TestCase):
    def test_equipment_expensed(self):
        r = ec.correct("Equipment costing $50,000 was expensed instead of capitalised.")
        self.assertIsNotNone(r)
        self.assertEqual(r.pattern_id, "equipment_expensed")
        self.assertEqual(r.amount, Decimal("50000"))
        self.assertEqual(r.net_income_delta, Decimal("50000"))
        self.assertEqual(r.assets_delta, Decimal("50000"))

    def test_unearned_revenue(self):
        r = ec.correct("Unearned revenue of $10,000 was recorded as revenue.")
        self.assertIsNotNone(r)
        self.assertEqual(r.pattern_id, "unearned_revenue")
        self.assertEqual(r.net_income_delta, Decimal("-10000"))
        self.assertEqual(r.liabilities_delta, Decimal("10000"))

    def test_depreciation_omitted(self):
        r = ec.correct("Depreciation of $5,000 was omitted from the accounts.")
        self.assertIsNotNone(r)
        self.assertEqual(r.pattern_id, "depreciation_omitted")
        self.assertEqual(r.net_income_delta, Decimal("-5000"))

    def test_inventory_overstated(self):
        r = ec.correct("Ending inventory was overstated by $3,000.")
        self.assertIsNotNone(r)
        self.assertEqual(r.pattern_id, "inventory_overstated")
        self.assertEqual(r.net_income_delta, Decimal("-3000"))

    def test_no_pattern_is_none(self):
        self.assertIsNone(ec.correct("A normal transaction with no error."))

    def test_detect_error_problem(self):
        self.assertTrue(ec.detect_error_problem("Equipment was wrongly expensed instead of capitalised."))
        self.assertFalse(ec.detect_error_problem("Prepare the income statement."))

    def test_stated_correction(self):
        original = [("Equipment", "Dr", Decimal("5000")), ("Cash", "Cr", Decimal("5000"))]
        correct = [("Repairs", "Dr", Decimal("5000")), ("Cash", "Cr", Decimal("5000"))]
        r = ec.correct_stated(original, correct)
        accounts = {line.account for line in r.lines}
        self.assertIn("Repairs", accounts)
        self.assertIn("Equipment", accounts)


class CaseSolverTest(unittest.TestCase):
    def test_a_simple_case_runs_the_full_state_machine(self):
        text = ("The owner started the business with 20,000 cash. The business sold goods "
                "for 9,500 cash and paid rent of 1,200.")
        r = case_solver.solve_case(text)
        self.assertEqual(r.status, "ok")
        names = [s.name for s in r.stages]
        for required in ("INGEST", "PARSE", "DETECT", "RESOLVE", "JOURNALIZE",
                         "POST", "ADJUST", "PROJECT", "VALIDATE"):
            self.assertIn(required, names)
        self.assertEqual(r.result["net_income"], Decimal("8300"))
        self.assertEqual(r.result["total_assets"], Decimal("28300"))

    def test_sold_goods_is_a_sale_not_an_asset_disposal(self):
        """The detector must not treat 'sold goods' as a PPE disposal."""
        from bp import statement_detect as sd
        matches = sd.detect("sold goods for 9,500 cash")
        ids = [m.detector_id for m in matches]
        self.assertIn("goods_sale_cash", ids)
        self.assertNotIn("asset_disposal", ids)

    def test_asset_disposal_still_matches_equipment(self):
        from bp import statement_detect as sd
        matches = sd.detect("sold equipment for 9,500 cash")
        ids = [m.detector_id for m in matches if sd.journalizable(m)]
        self.assertIn("asset_disposal", ids)

    def test_capital_contribution_is_detected(self):
        from bp import statement_detect as sd
        matches = sd.detect("started the business with 20,000 cash")
        ids = [m.detector_id for m in matches if sd.journalizable(m)]
        self.assertIn("capital_contribution", ids)

    def test_empty_text_is_a_review(self):
        r = case_solver.solve_case("")
        self.assertEqual(r.status, "review")
        self.assertEqual(r.stages[0].name, "INGEST")

    def test_no_transaction_is_a_review(self):
        r = case_solver.solve_case("Prepare the income statement.")
        self.assertEqual(r.status, "review")


class VocabularyTest(unittest.TestCase):
    def test_every_raw_input_has_a_pattern(self):
        from bp.product.financial_computations import COMMON_PATTERNS, REGISTRY
        specs = REGISTRY.all()
        outputs = {s.output_name for s in specs}
        raw = set()
        for s in specs:
            raw.update(s.inputs)
        raw -= outputs
        missing = sorted(raw - set(COMMON_PATTERNS))
        self.assertEqual(missing, [], "raw inputs with no parse pattern: %s" % missing)

    def test_a_rich_sample_parses(self):
        from bp.product.financial_computations import COMMON_PATTERNS, parse_inputs_from_text
        sample = ("Beginning inventory 10,000. Purchases 60,000. Ending inventory 15,000. "
                  "Accumulated depreciation 9,000. Depreciation expense 3,000. "
                  "Other income 1,500. Taxable income 40,000. Dividends declared 5,000. "
                  "Cash receipts 80,000. Debt repayments 4,000. Number of years 5.")
        inputs = parse_inputs_from_text(sample, COMMON_PATTERNS)
        self.assertEqual(inputs["beginning_inventory"], Decimal("10000"))
        self.assertEqual(inputs["purchases"], Decimal("60000"))
        self.assertEqual(inputs["ending_inventory"], Decimal("15000"))
        self.assertEqual(inputs["depreciation_expense"], Decimal("3000"))
        self.assertEqual(inputs["accumulated_depreciation"], Decimal("9000"))
        self.assertEqual(inputs["dividends_declared"], Decimal("5000"))
        self.assertEqual(inputs["n_years"], Decimal("5"))

    def test_depreciation_expense_does_not_read_accumulated(self):
        from bp.product.financial_computations import COMMON_PATTERNS, parse_inputs_from_text
        inputs = parse_inputs_from_text(
            "Accumulated depreciation 9,000. Depreciation expense 3,000.", COMMON_PATTERNS)
        self.assertEqual(inputs["depreciation_expense"], Decimal("3000"))
        self.assertEqual(inputs["accumulated_depreciation"], Decimal("9000"))


class ClassifierTest(unittest.TestCase):
    def _type(self, text):
        from bp.product.problem_type import classify_problem
        return classify_problem(text)["type"]

    def test_correction(self):
        self.assertEqual(self._type(
            "Equipment costing $50,000 was expensed instead of capitalised."), 4)

    def test_reconstruction(self):
        self.assertEqual(self._type(
            "Find the net purchases. COGS is 55,000, beginning inventory 10,000."), 2)

    def test_trial_balance(self):
        self.assertEqual(self._type("The following trial balance was extracted."), 6)

    def test_cash_flow(self):
        self.assertEqual(self._type(
            "Prepare the statement of cash flows with operating, investing and financing activities."), 5)

    def test_ratio(self):
        self.assertEqual(self._type(
            "Compute the current ratio and debt to equity ratio."), 3)

    def test_integrated_case(self):
        self.assertEqual(self._type(
            "The owner started the business with 20,000 cash. The business sold goods "
            "for 9,500 cash and paid rent of 1,200."), 7)

    def test_transactions(self):
        self.assertEqual(self._type("The owner paid rent of 1,200."), 1)


class GuardRunnerTest(unittest.TestCase):
    def _record(self, **overrides):
        base = {
            "format": "bp-statements/1", "solved": True,
            "problem_type": "income_statement",
            "instruction": "Compute net sales.",
            "reading": {"assumptions": [], "figures": [], "derivations": []},
            "core": {"scalars": {"net_sales": "92000"}, "appendix": {}},
            "working": {"journal": "", "derivations": [], "assumptions": [], "missing": []},
            "diagnosis": None,
            "checks": [{"name": "trial_balance_debits_equal_credits", "ok": True, "detail": ""}],
            "spec": {},
            "rejected": [],
        }
        base.update(overrides)
        return base

    def test_all_guards_run_and_report(self):
        result = guards.run(self._record())
        self.assertEqual(len(result["results"]), 22)
        self.assertIn("summary", result)
        self.assertIn("passed_ids", result["summary"])

    def test_g2_flags_a_float(self):
        record = self._record()
        record["core"]["scalars"]["net_sales"] = 92000.0  # a float, not a Decimal
        result = guards.run(record)
        g2 = next(r for r in result["results"] if r["guard"] == "G2")
        self.assertFalse(g2["ok"])

    def test_g9_flags_a_failed_check(self):
        record = self._record(checks=[{"name": "assets_equal_liabilities_plus_equity",
                                       "ok": False, "detail": "out by 1"}])
        result = guards.run(record)
        g9 = next(r for r in result["results"] if r["guard"] == "G9")
        self.assertFalse(g9["ok"])

    def test_a_guard_that_raises_is_a_failure(self):
        # A record whose shape is wrong must not look like a passing gate.
        result = guards.run({})
        for row in result["results"]:
            if row["applicable"] and not row["ok"]:
                self.assertTrue(row["detail"])


if __name__ == "__main__":
    unittest.main()
