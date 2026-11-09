"""Best-effort SEC EDGAR statement research for the Portfolio Lab."""

import os
import sys
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))

from bp.product import edgar_statements, marketdata  # noqa: E402


class ResearchTest(unittest.TestCase):
    def test_research_returns_lines_and_ratios_for_a_us_ticker(self):
        fake_concept = {
            "revenue": (1000.0, "2024-12-31", b"", "https://data.sec.gov/x", "Revenues"),
        }
        # stub _sec_concept to return a value for every requested tag
        def fake_sec_concept(cik, tags):
            mapping = {
                "RevenueFromContractWithCustomerExcludingAssessedTax": 1000.0,
                "Revenues": 1000.0,
                "SalesRevenueNet": 1000.0,
                "NetIncomeLoss": 120.0,
                "Assets": 800.0,
                "Liabilities": 320.0,
                "StockholdersEquity": 480.0,
                "AssetsCurrent": 300.0,
                "LiabilitiesCurrent": 150.0,
                "InventoryNet": 50.0,
                "CostOfGoodsAndServicesSold": 400.0,
                "CostOfGoodsSold": 400.0,
                "GrossProfit": 600.0,
                "OperatingIncomeLoss": 180.0,
                "RetainedEarningsAccumulatedDeficit": 200.0,
                "EarningsPerShareDiluted": 2.4,
                "EarningsPerShareBasic": 2.4,
            }
            for tag in tags:
                if tag in mapping:
                    return (mapping[tag], "2024-12-31", b"", "https://data.sec.gov/x", tag)
            raise marketdata.MarketDataError("no concept")

        with mock.patch.object(marketdata, "sec_filings",
                               return_value={"cik": "12345", "company": "Test Co"}):
            with mock.patch.object(marketdata, "_sec_concept", side_effect=fake_sec_concept):
                text, as_of, url, lines = edgar_statements.research("AAPL")
        self.assertIn("Revenue, 1000", text.replace("  ", " "))
        self.assertEqual(as_of, "2024-12-31")
        self.assertIn("revenue", lines)

    def test_non_us_ticker_raises_unavailable(self):
        with mock.patch.object(marketdata, "sec_filings",
                               return_value={"cik": "", "company": ""}):
            with self.assertRaises(edgar_statements.EdgarUnavailable):
                edgar_statements.research("SAP")

    def test_no_facts_raises_unavailable(self):
        with mock.patch.object(marketdata, "sec_filings",
                               return_value={"cik": "999", "company": "X"}):
            with mock.patch.object(marketdata, "_sec_concept",
                                   side_effect=marketdata.MarketDataError("none")):
                with self.assertRaises(edgar_statements.EdgarUnavailable):
                    edgar_statements.research("ZZZZ")


if __name__ == "__main__":
    unittest.main()
