"""Portfolio valuation method: NAV, weights, concentration and refusals."""

import os
import sys
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp.methods import DataError  # noqa: E402

INPUT = {
    "holdings": [
        {"symbol": "AAPL", "shares": "10", "price": "200"},
        {"symbol": "MSFT", "shares": "5", "price": "400"},
    ],
    "cash": "1000",
}


class PortfolioValuationTest(unittest.TestCase):
    def setUp(self):
        self.method = methods.LIBRARY["portfolio_valuation"]

    def test_nav_weights_and_concentration(self):
        out = self.method.impl(INPUT)
        self.assertEqual(out["nav"], D(5000))
        self.assertEqual(out["invested_value"], D(4000))
        self.assertEqual(out["cash"], D(1000))
        self.assertEqual(out["cash_pct"], D("0.2"))
        self.assertEqual(out["n_holdings"], D(2))
        self.assertEqual(out["value_AAPL"], D(2000))
        self.assertEqual(out["weight_AAPL"], D("0.4"))
        self.assertEqual(out["top_weight"], D("0.4"))
        self.assertEqual(out["top3_concentration"], D("0.8"))

    def test_every_declared_check_passes(self):
        results = self.method.tests(INPUT, self.method.impl)
        self.assertEqual([name for name, _ in results], list(self.method.test_names))
        self.assertTrue(all(ok for _, ok in results), results)

    def test_the_snapshot_is_linear_in_prices_and_cash(self):
        base = self.method.impl(INPUT)
        doubled = self.method.impl({**INPUT, "holdings": [
            {**row, "price": str(D(row["price"]) * 2)} for row in INPUT["holdings"]]})
        self.assertEqual(doubled["invested_value"], base["invested_value"] * 2)
        self.assertEqual(doubled["nav"], base["invested_value"] * 2 + base["cash"])
        richer = self.method.impl({**INPUT, "cash": "1001"})
        self.assertEqual(richer["nav"], base["nav"] + 1)

    def test_a_zero_cash_portfolio_still_has_full_holding_weights(self):
        out = self.method.impl({**INPUT, "cash": "0"})
        self.assertEqual(out["cash_pct"], D(0))
        self.assertEqual(out["weight_AAPL"] + out["weight_MSFT"], D(1))

    def test_bad_holdings_are_refused(self):
        for change in (
            {"holdings": []},
            {"holdings": [{"symbol": "AAPL", "shares": "0", "price": "200"}]},
            {"holdings": [{"symbol": "AAPL", "shares": "1", "price": "0"}]},
            {"holdings": [{"symbol": "AAPL", "shares": "1", "price": "1"},
                          {"symbol": "aapl", "shares": "1", "price": "1"}]},
            {"cash": "-1"},
        ):
            with self.assertRaises(DataError):
                self.method.impl({**INPUT, **change})

    def test_schema_and_profile_accept_the_student_input(self):
        self.assertEqual(methods.validate_inputs(self.method, INPUT), [])
        self.assertEqual(self.method.profile(INPUT), [])


if __name__ == "__main__":
    unittest.main()
