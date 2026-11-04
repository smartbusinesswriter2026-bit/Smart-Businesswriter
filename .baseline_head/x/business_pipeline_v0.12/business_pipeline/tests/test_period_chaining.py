"""Chaining two periods: the closing balances become the next opening, and nothing resets.

A single-period engagement can be wrong in ways a second period exposes. The revaluation reserve, the
accumulated depreciation, retained earnings after dividends, and the receivables all have to survive the
boundary. If any of them silently restarts, every statement still balances - which is why this needs its own
test rather than an inference from period one.

The chain is built the way a student would build it: period two's `prior_closing` is period one's
`closing_balances`, and its opening entry is period one's `opening_lines_next`. Both are produced by the
engine, so this tests the handover the engine actually offers.
"""

import copy
import os
import sys
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp import accounts as accounts_mod   # noqa: E402


def chart():
    return [
        {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash", "section": "current"},
        {"code": "1100", "name": "Receivables", "type": "asset", "line": "Receivables", "section": "current"},
        {"code": "1200", "name": "Equipment", "type": "asset", "line": "Equipment", "section": "non_current"},
        {"code": "1210", "name": "Accum. dep.", "type": "asset", "line": "Accum. dep.", "section": "non_current", "contra": True},
        {"code": "3000", "name": "Capital", "type": "equity", "line": "Capital", "role": "capital"},
        {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"},
        {"code": "3200", "name": "Dividends", "type": "equity", "line": "Dividends", "role": "dividends"},
        {"code": "3300", "name": "Revaluation reserve", "type": "equity", "line": "Revaluation reserve", "role": "oci_reserve"},
        {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"},
        {"code": "4200", "name": "Revaluation gain", "type": "oci", "line": "Revaluation gain"},
        {"code": "5000", "name": "Rent", "type": "expense", "line": "Rent"},
        {"code": "5100", "name": "Depreciation", "type": "expense", "line": "Depreciation"},
        {"code": "5400", "name": "Revaluation loss", "type": "expense", "line": "Revaluation loss"},
    ]


def period_one():
    return {
        "period": {"start": "2026-01-01", "end": "2026-03-31"},
        "currency": "USD", "framework": "IFRS", "places": 2,
        "chart": chart(),
        "prior_closing": {"1000": "10000", "3000": "10000"},
        "opening": [{"description": "opening", "lines": [
            {"account": "1000", "debit": "10000"}, {"account": "3000", "credit": "10000"}]}],
        "entries": [
            {"date": "2026-01-10", "description": "buy equipment",
             "lines": [{"account": "1200", "debit": "6000"}, {"account": "1000", "credit": "6000"}]},
            {"date": "2026-01-20", "description": "credit sale",
             "lines": [{"account": "1100", "debit": "5000"}, {"account": "4000", "credit": "5000"}]},
            {"date": "2026-02-28", "description": "rent paid",
             "lines": [{"account": "5000", "debit": "1000"}, {"account": "1000", "credit": "1000"}]},
            {"date": "2026-03-20", "description": "dividend declared",
             "lines": [{"account": "3200", "debit": "300"}, {"account": "1000", "credit": "300"}]},
        ],
        "schedules": [
            {"kind": "depreciation", "cost": "6000", "residual": "3000", "life": 3, "places": 2,
             "start": "2026-01", "dep_account": "5100", "accum_account": "1210"},
            {"kind": "revaluation", "date": "2026-03-31", "revalued_amount": "3600",
             "method": "proportionate", "places": 2, "asset_account": "1200", "accum_account": "1210",
             "oci_account": "4200", "loss_account": "5400"},
        ],
    }


def period_two(opening_lines, prior_closing):
    return {
        "period": {"start": "2026-04-01", "end": "2026-06-30"},
        "currency": "USD", "framework": "IFRS", "places": 2,
        "chart": chart(),
        "prior_closing": prior_closing,
        "opening": [{"description": "opening", "lines": opening_lines}],
        "entries": [
            {"date": "2026-05-05", "description": "cash sale",
             "lines": [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}]},
            {"date": "2026-05-31", "description": "rent paid",
             "lines": [{"account": "5000", "debit": "500"}, {"account": "1000", "credit": "500"}]},
        ],
        "schedules": [
            # depreciation continues on the REVALUED carrying amount, declared by the owner:
            # gross 7,200 with 3,600 accumulated leaves 3,600, of which 1,800 is the new residual
            {"kind": "depreciation", "cost": "3600", "residual": "1800", "life": 3, "places": 2,
             "start": "2026-04", "dep_account": "5100", "accum_account": "1210"},
        ],
    }


class Chaining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.one = accounts_mod.build(period_one())
        cls.ex_one = cls.one["_appendix"]
        cls.two = accounts_mod.build(period_two(cls.ex_one["opening_lines_next"], cls.ex_one["closing_balances"]))
        cls.ex_two = cls.two["_appendix"]

    def test_period_one_is_clean(self):
        failed = [n for n, ok, _ in self.one["_checks"] if not ok]
        self.assertEqual(failed, [])

    def test_period_two_is_clean(self):
        failed = [n for n, ok, _ in self.two["_checks"] if not ok]
        self.assertEqual(failed, [])

    def test_the_opening_passes_the_prior_closing_check(self):
        detail = {n: (ok, d) for n, ok, d in self.two["_checks"]}["opening_balances_equal_prior_closing"]
        self.assertTrue(detail[0], detail[1])

    def test_every_balance_carries_forward(self):
        for code, closed in self.ex_one["closing_balances"].items():
            if D(closed) == 0:
                continue        # a nil balance is simply not carried, so the key may be absent
            opened = self.ex_two["closing_balances"]
            self.assertIn(code, opened, "%s vanished across the boundary" % code)

    def test_the_revaluation_reserve_does_not_reset(self):
        one = D([g for g in self.ex_one["ledgers"] if g["code"] == "3300"][0]["closing_balance"])
        two = D([g for g in self.ex_two["ledgers"] if g["code"] == "3300"][0]["closing_balance"])
        self.assertEqual(one, D("600"))
        self.assertEqual(two, D("600"), "the reserve must carry forward unchanged")

    def test_retained_earnings_rolls_forward_with_the_new_profit(self):
        re_two = D([g for g in self.ex_two["ledgers"] if g["code"] == "3100"][0]["closing_balance"])
        re_one = D([g for g in self.ex_one["ledgers"] if g["code"] == "3100"][0]["closing_balance"])
        self.assertEqual(re_one, D("700"))
        self.assertEqual(re_two, D("400"), "700 carried in, less the 300 loss of period two")

    def test_the_equity_statement_opens_at_period_ones_closing(self):
        rows = {r["code"]: r for r in self.ex_two["equity_statement"]["accounts"]}
        for code, closing in (("3100", "700"), ("3300", "600"), ("3000", "10000")):
            self.assertEqual(D(rows[code]["opening"]), D(closing),
                             "%s must open at period one's closing balance" % code)

    def test_total_equity_moves_only_by_the_second_profit(self):
        e1 = D(self.ex_one["equity_statement"]["total_closing"])
        e2 = D(self.ex_two["equity_statement"]["total_closing"])
        self.assertEqual(e1, D("11300"))
        self.assertEqual(e2 - e1, D(self.two["net_income"]), "equity moved only by the period's result")

    def test_both_balance_sheets_balance(self):
        for name, ex in (("period one", self.ex_one), ("period two", self.ex_two)):
            st = ex["statements"]
            self.assertEqual(D(st["total_assets"]),
                             D(st["total_liabilities"]) + D(st["equity_with_current_earnings"]), name)

    def test_the_asset_is_depreciated_to_its_new_residual(self):
        lg = {g["code"]: g for g in self.ex_two["ledgers"]}
        self.assertEqual(D(lg["1200"]["closing_balance"]), D("7200"))
        self.assertEqual(D(lg["1210"]["closing_balance"]), D("5400"), "3,600 carried in plus 1,800 charged")
        self.assertEqual(D(lg["1200"]["closing_balance"]) - D(lg["1210"]["closing_balance"]), D("1800"))


class ItRefusesToChainBadly(unittest.TestCase):
    def test_a_wrong_prior_closing_fails_the_opening_check(self):
        """`build` reports the check rather than raising; the pipeline is what blocks on a failure."""
        one = accounts_mod.build(period_one())["_appendix"]
        bad = dict(one["closing_balances"])
        bad["1000"] = str(D(bad["1000"]) + 1)
        out = accounts_mod.build(period_two(one["opening_lines_next"], bad))
        checks = {n: (ok, d) for n, ok, d in out["_checks"]}
        self.assertFalse(checks["opening_balances_equal_prior_closing"][0],
                         "a tampered prior closing must not pass the opening check")


if __name__ == "__main__":
    unittest.main()
