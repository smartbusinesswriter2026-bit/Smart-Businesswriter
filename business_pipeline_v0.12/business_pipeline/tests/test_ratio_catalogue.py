"""The ratio catalogue: the cash-flow and quality ratios the registry now defines.

The statement ratio engine used to hold only liquidity, profitability, solvency and efficiency
ratios; a student asking for the operating cash flow ratio or the accruals ratio was told the
registry did not define it.  The catalogue now defines four cash-flow ratios and the accruals
ratio, and the static gap list no longer names the ones that are computed.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import accounts, methods  # noqa: E402


class RatioCatalogueTest(unittest.TestCase):
    def test_the_cash_flow_and_accruals_ratios_are_computed(self):
        figures = {
            "operating_cash_flow": "25000", "capital_expenditure": "8000",
            "revenue": "100000", "current_liabilities": "10000",
            "total_liabilities": "50000", "net_income": "20000", "total_assets": "120000",
        }
        pack = methods.LIBRARY["ratio_analysis"].impl(figures)
        rows = {row["ratio"] for row in (pack.get("_appendix") or {}).get("ratios") or []}
        for name in ("operating_cash_flow_ratio", "cash_flow_margin", "cash_flow_to_debt",
                     "free_cash_flow_margin", "accruals_ratio"):
            self.assertIn(name, rows, name)

    def test_the_gap_list_no_longer_names_a_computed_ratio(self):
        names = {gap["ratio"] for gap in accounts.RATIO_GAPS}
        self.assertNotIn("operating_cash_flow_ratio", names)
        self.assertNotIn("accruals_ratio", names)
        self.assertNotIn("market_to_book", names)
        self.assertNotIn("altman_z_score", names)
        self.assertIn("piotroski_f_score", names)
        self.assertIn("beneish_m_score", names)

    def test_the_market_and_altman_ratios_are_computed(self):
        figures = {
            "share_price": "20", "shares_outstanding": "1000", "dividends_declared": "2000",
            "net_income": "5000", "equity": "20000",
            "working_capital": "8000", "total_assets": "50000",
            "retained_earnings": "12000", "ebit": "7000", "market_value_equity": "20000",
            "total_liabilities": "30000", "sales": "60000",
        }
        pack = methods.LIBRARY["ratio_analysis"].impl(figures)
        rows = {row["ratio"] for row in (pack.get("_appendix") or {}).get("ratios") or []}
        for name in ("earnings_per_share", "book_value_per_share", "price_earnings",
                     "market_to_book", "dividend_payout", "dividend_yield", "altman_z_score"):
            self.assertIn(name, rows, name)

    def test_a_missing_cash_flow_is_named_not_guessed(self):
        figures = {"revenue": "100000", "current_liabilities": "10000",
                   "net_income": "20000", "total_assets": "120000"}
        pack = methods.LIBRARY["ratio_analysis"].impl(figures)
        missing = {row["ratio"] for row in (pack.get("_appendix") or {}).get("not_computed") or []}
        self.assertIn("cash_flow_margin", missing)


if __name__ == "__main__":
    unittest.main()
