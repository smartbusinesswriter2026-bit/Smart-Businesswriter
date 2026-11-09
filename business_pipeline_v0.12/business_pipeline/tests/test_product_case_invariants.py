"""Domain invariants: the numbers a case records must also agree with each other."""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import case_invariants, case_runner  # noqa: E402

RATIO_INPUTS = {
    "total_assets": "12000", "total_liabilities": "7000", "equity": "5000",
    "current_assets": "5000", "current_liabilities": "2000",
    "inventory": "1200", "cash": "800", "revenue": "20000",
    "cost_of_sales": "12000", "net_income": "1800",
}
RATIO_RESULT = {
    "current_ratio": "2.5", "quick_ratio": "1.9", "cash_ratio": "0.4",
    "gross_margin": "0.4", "net_margin": "0.09", "return_on_assets": "0.15",
    "return_on_equity": "0.36", "debt_to_equity": "1.4", "equity_multiplier": "2.4",
    "asset_turnover": "1.6666666666666666666666666666666666666666666666667",
}


class CaseInvariantTest(unittest.TestCase):
    def test_the_ratio_identities_hold_and_a_wrong_ratio_is_caught(self):
        self.assertEqual(case_invariants.check("ratio_analysis", RATIO_INPUTS, RATIO_RESULT), [])
        broken = dict(RATIO_RESULT, current_ratio="9.9")
        problems = case_invariants.check("ratio_analysis", RATIO_INPUTS, broken)
        self.assertTrue(any("current_ratio" in problem for problem in problems))

    def test_a_broken_balance_sheet_is_caught(self):
        broken = dict(RATIO_INPUTS, equity="4000")
        problems = case_invariants.check("ratio_analysis", broken, RATIO_RESULT)
        self.assertTrue(any("accounting equation" in problem for problem in problems))
        self.assertTrue(case_runner._input_only(problems),
                        "the case's own figures are invalid input, not a pipeline defect")

    def test_the_dupont_identity_is_caught_when_it_breaks(self):
        result = {"net_margin": "0.09",
                  "asset_turnover": "1.6666666666666666666666666666666666666666666666667",
                  "equity_multiplier": "2.4", "roe_three_step": "9",
                  "return_on_equity": "9", "return_on_assets": "0.15",
                  "equity_to_assets": "0.41666666666666666666666666666666666666666666666667"}
        problems = case_invariants.check("dupont_analysis", {}, result)
        self.assertTrue(any("DuPont" in problem for problem in problems))

    def test_wacc_weights_must_sum_to_one(self):
        result = {"wacc": "0.106", "weight_equity": "0.8", "weight_debt": "0.3",
                  "cost_of_equity": "0.12", "cost_of_debt_after_tax": "0.05"}
        problems = case_invariants.check("wacc", {}, result)
        self.assertTrue(any("weights do not sum to one" in problem for problem in problems))

    def test_break_even_units_must_follow_from_fixed_cost_and_contribution(self):
        result = {"breakeven_units": "999", "contribution_margin": "10",
                  "contribution_margin_ratio": "0.5", "breakeven_revenue": "2000"}
        problems = case_invariants.check("breakeven", {"fixed": "1000", "price": "20", "variable": "10"}, result)
        self.assertTrue(any("breakeven_units" in problem for problem in problems))

    def test_the_hdi_must_be_the_geometric_mean(self):
        result = {"hdi": "0.9", "life_index": "0.7", "education_index": "0.6", "income_index": "0.5"}
        problems = case_invariants.check("hdi", {}, result)
        self.assertTrue(any("geometric mean" in problem for problem in problems))

    def test_cap_table_shares_must_sum_to_one(self):
        result = {"founder_pct": "0.5", "investor_pct": "0.2", "pool_pct_actual": "0.1"}
        problems = case_invariants.check("cap_table_round", {}, result)
        self.assertTrue(any("sum to one" in problem for problem in problems))

    def test_queue_utilisation_must_be_arrival_over_service(self):
        result = {"arrival_rate": "18", "service_rate": "24", "utilisation": "0.9",
                  "average_in_queue": "2.25", "average_in_system": "3.0",
                  "probability_empty": "0.25"}
        problems = case_invariants.check("queue_analysis", {}, result)
        self.assertTrue(any("utilisation" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
