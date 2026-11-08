"""The Beneish M-score from two statement records.

The eight indices compare two periods, so the single-record ratio pack cannot compute them.
This consumer derives each index from the two frozen bundles and calls the frozen
`beneish_m_score` for the formula itself.
"""

import copy
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp.product import statements  # noqa: E402


def record(figures, period, record_id, totals, expenses):
    return {
        "format": statements.FORMAT,
        "solved": True,
        "id": record_id,
        "instruction_hash": "hash-" + record_id,
        "problem_type": "trial_balance",
        "core": {
            "scalars": {},
            "appendix": {
                "ratio_figures": figures,
                "cash_flow": {"operating": figures["operating_cash_flow"],
                              "investing": "0", "financing": "0"},
                "engagement": {"period": period, "currency": "USD"},
                "balance_sheet_groups": {"totals": totals, "groups": {"equity": {}}},
                "income_groups": {"expenses": expenses},
            },
        },
        "warnings": [],
    }


PRIOR = record(
    {"receivables": "10000", "revenue": "100000", "cost_of_sales": "60000",
     "current_assets": "30000", "total_assets": "100000", "current_liabilities": "20000",
     "net_income": "10000", "operating_cash_flow": "12000"},
    {"start": "2025-01-01", "end": "2025-12-31"}, "aaaaaaaaaaa1",
    {"non_current_assets": "40000", "non_current_liabilities": "10000", "current_liabilities": "20000"},
    {"Cost of sales": "60000", "Depreciation": "5000", "Salaries": "15000"},
)

CURRENT = record(
    {"receivables": "15000", "revenue": "120000", "cost_of_sales": "70000",
     "current_assets": "35000", "total_assets": "120000", "current_liabilities": "25000",
     "net_income": "12000", "operating_cash_flow": "10000"},
    {"start": "2026-01-01", "end": "2026-12-31"}, "bbbbbbbbbbb2",
    {"non_current_assets": "45000", "non_current_liabilities": "15000", "current_liabilities": "25000"},
    {"Cost of sales": "70000", "Depreciation": "6000", "Salaries": "18000"},
)


class BeneishTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        statements.reset_core()
        statements.attach_core(
            beneish=lambda inputs: methods.LIBRARY["beneish_m_score"].impl(inputs))

    @classmethod
    def tearDownClass(cls):
        statements.reset_core()

    def test_the_eight_indices_are_derived(self):
        pack = statements.beneish([PRIOR, CURRENT])
        self.assertEqual(pack["format"], statements.BENEISH_FORMAT)
        for key in ("dsri", "gmi", "aqi", "sgi", "depi", "sgai", "lvgi", "tata"):
            self.assertIn(key, pack["indices"], key)
        self.assertIn("beneish_m_score", pack["result"])
        self.assertEqual(pack["periods"], ["2025", "2026"])

    def test_the_score_is_the_two_period_value(self):
        pack = statements.beneish([PRIOR, CURRENT])
        score = float(pack["result"]["beneish_m_score"])
        self.assertAlmostEqual(score, -2.0126, places=3)

    def test_a_missing_figure_is_named(self):
        broken = copy.deepcopy(CURRENT)
        broken["core"]["appendix"]["ratio_figures"].pop("receivables", None)
        with self.assertRaises(statements.StatementError) as caught:
            statements.beneish([PRIOR, broken])
        self.assertIn("dsri", str(caught.exception))

    def test_the_route_returns_the_score(self):
        previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = tempfile.mkdtemp(prefix="beneish-")
        try:
            prior = statements.save(copy.deepcopy(PRIOR))
            current = statements.save(copy.deepcopy(CURRENT))
            status, payload = statements.handle(
                "POST", ["beneish"], {"records": [prior["id"], current["id"]]})
            self.assertEqual(status, 200)
            self.assertIn("beneish_m_score", payload["result"])
        finally:
            if previous is None:
                os.environ.pop("BP_CASES_DIR", None)
            else:
                os.environ["BP_CASES_DIR"] = previous


if __name__ == "__main__":
    unittest.main()
