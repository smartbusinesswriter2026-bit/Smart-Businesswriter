"""Tests for the RRA back-test harness."""
import unittest

from tests.relevance_base import RelevanceTestCase  # noqa: E402

from bp.product.relevance import backtest as rbacktest  # noqa: E402
from bp.product.relevance import s0_scope as _scope  # noqa: E402


class BacktestRegistryTest(RelevanceTestCase):
    def test_the_registry_is_present_and_complete(self):
        backtest = _scope.load_backtest()
        self.assertIsNotNone(backtest)
        self.assertGreaterEqual(len(backtest["seeded_gaps"]), 10)
        self.assertGreaterEqual(len(backtest["seeded_present"]), 5)
        self.assertIn("thresholds", backtest)


class BacktestEvaluationTest(RelevanceTestCase):
    def test_an_empty_run_flags_nothing(self):
        result = rbacktest.evaluate(produced_gaps=[])
        self.assertEqual(result["false_flag_count"], 0)
        self.assertEqual(result["recall"], 0.0)
        self.assertFalse(result["passed"])

    def test_the_recall_is_counted(self):
        gaps = [{"title": "Balanced Scorecard"},
                {"title": "OKR (Objectives and Key Results)"}]
        result = rbacktest.evaluate(produced_gaps=gaps)
        titles = [f["title"] for f in result["found"]]
        self.assertIn("Balanced Scorecard", titles)
        self.assertIn("OKR", titles)

    def test_a_present_item_that_is_flagged_is_a_false_flag(self):
        gaps = [{"title": "PESTEL"}, {"title": "SWOT"}]
        result = rbacktest.evaluate(produced_gaps=gaps)
        self.assertGreaterEqual(result["false_flag_count"], 1)
        self.assertFalse(result["passed"])

    def test_a_parked_item_recognised_as_parked_is_a_correct_identification(self):
        coverage = [{"taxonomy_item": "Factor analysis", "status": "parked"},
                    {"taxonomy_item": "Cluster analysis / k-means", "status": "parked"}]
        result = rbacktest.evaluate(produced_gaps=[], coverage_rows=coverage)
        titles = [f["title"] for f in result["found"]]
        self.assertIn("Factor analysis", titles)
        self.assertIn("Cluster analysis", titles)
        self.assertEqual(result["found_count"], 2)
        self.assertEqual(result["false_flag_count"], 0)
        # Two of twelve is far short of the threshold.
        self.assertFalse(result["passed"])

    def test_a_present_item_verified_as_missing_is_a_false_flag(self):
        coverage = [{"taxonomy_item": "PESTEL analysis", "status": "missing"}]
        result = rbacktest.evaluate(produced_gaps=[], coverage_rows=coverage)
        self.assertGreaterEqual(result["false_flag_count"], 1)

    def test_the_normalisation_ignores_punctuation_and_case(self):
        self.assertEqual(rbacktest._norm("McKinsey 7-S"), rbacktest._norm("mckinsey7s"))

    def test_the_alias_forms_drop_the_parenthetical(self):
        forms = rbacktest._alias_forms("Balanced Scorecard (BSC)")
        self.assertIn(rbacktest._norm("Balanced Scorecard"), forms)


if __name__ == "__main__":
    unittest.main()
