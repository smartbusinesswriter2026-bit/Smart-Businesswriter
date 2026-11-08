"""Piotroski F-score from two statement records (prior and current).

The single-record ratio pack cannot compute the nine criteria (they compare two periods), so a
dedicated two-record consumer builds the nine inputs from the two frozen bundles and calls the
frozen `piotroski_f_score`.  This test uses synthetic records so it proves the consumer, not the
solver.
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


def record(figures, period, record_id):
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
                "balance_sheet_groups": {"groups": {"equity": {}}},
            },
        },
        "warnings": [],
    }


PRIOR = record({
    "net_income": "5000", "total_assets": "50000", "total_liabilities": "30000",
    "current_assets": "20000", "current_liabilities": "10000",
    "revenue": "60000", "cost_of_sales": "40000", "operating_cash_flow": "6000",
}, {"start": "2025-01-01", "end": "2025-12-31"}, "aaaaaaaaaaa1")

CURRENT = record({
    "net_income": "8000", "total_assets": "55000", "total_liabilities": "31000",
    "current_assets": "24000", "current_liabilities": "11000",
    "revenue": "70000", "cost_of_sales": "45000", "operating_cash_flow": "9000",
}, {"start": "2026-01-01", "end": "2026-12-31"}, "bbbbbbbbbbb2")


class PiotroskiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        statements.reset_core()
        statements.attach_core(
            piotroski=lambda inputs: methods.LIBRARY["piotroski_f_score"].impl(inputs))

    @classmethod
    def tearDownClass(cls):
        statements.reset_core()

    def test_the_score_is_eight_for_this_pair(self):
        pack = statements.piotroski([PRIOR, CURRENT], {"shares_diluted": "1000"})
        self.assertEqual(pack["format"], statements.PIOTROSKI_FORMAT)
        self.assertEqual(pack["result"]["piotroski_f_score"], "8")
        self.assertEqual(pack["periods"], ["2025", "2026"])

    def test_a_missing_figure_is_named(self):
        broken = copy.deepcopy(CURRENT)
        broken["core"]["appendix"]["ratio_figures"].pop("current_liabilities", None)
        with self.assertRaises(statements.StatementError) as caught:
            statements.piotroski([PRIOR, broken], {"shares_diluted": "1000"})
        self.assertIn("current_ratio_current", str(caught.exception))

    def test_the_route_returns_the_score(self):
        previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = tempfile.mkdtemp(prefix="piotroski-")
        try:
            prior = statements.save(copy.deepcopy(PRIOR))
            current = statements.save(copy.deepcopy(CURRENT))
            status, payload = statements.handle(
                "POST", ["piotroski"],
                {"records": [prior["id"], current["id"]], "extra": {"shares_diluted": "1000"}})
            self.assertEqual(status, 200)
            self.assertEqual(payload["result"]["piotroski_f_score"], "8")
        finally:
            if previous is None:
                os.environ.pop("BP_CASES_DIR", None)
            else:
                os.environ["BP_CASES_DIR"] = previous


if __name__ == "__main__":
    unittest.main()
