"""One engagement that uses every accounting feature at once.

Each increment was proven in isolation. This test exists because features interact: a revaluation changes
the carrying amount, a disposal clears accumulated depreciation, deferrals release over the same periods as
depreciation, an allowance moves against receivables, and a reversal removes revenue that was already
closed. Any of those can break an invariant that passed alone.

What is asserted is not a set of hard-coded totals (those belong to the individual tests) but the
**invariants that must hold whatever the numbers are**:

- every pipeline check passes;
- the balance sheet balances;
- both cash-flow routes agree;
- every T-account foots: opening + movements = closing, with debits and credits equal to the trial balance;
- every journal entry balances;
- the statement of changes in equity ties to the balance sheet;
- other comprehensive income is where it belongs.

If a future feature breaks one of these, this test says so before a student sees a number.
"""

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


def the_engagement():
    return {
        "period": {"start": "2026-01-01", "end": "2026-03-31"},
        "currency": "USD",
        "framework": "IFRS",
        "places": 2,
        "chart": [
            {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash", "section": "current"},
            {"code": "1100", "name": "Trade receivables", "type": "asset", "line": "Receivables", "section": "current"},
            {"code": "1200", "name": "Equipment A", "type": "asset", "line": "Equipment A", "section": "non_current"},
            {"code": "1210", "name": "Accum. dep. A", "type": "asset", "line": "Accum. dep. A", "section": "non_current", "contra": True},
            {"code": "1300", "name": "Prepaid rent", "type": "asset", "line": "Prepayments", "section": "current"},
            {"code": "1400", "name": "Equipment B", "type": "asset", "line": "Equipment B", "section": "non_current"},
            {"code": "1410", "name": "Accum. dep. B", "type": "asset", "line": "Accum. dep. B", "section": "non_current", "contra": True},
            {"code": "1500", "name": "Allowance for doubtful debts", "type": "asset", "line": "Allowance", "section": "current", "contra": True},
            {"code": "2100", "name": "Payables", "type": "liability", "line": "Payables", "section": "current"},
            {"code": "2200", "name": "Deferred income", "type": "liability", "line": "Deferred income", "section": "current"},
            {"code": "3000", "name": "Owner capital", "type": "equity", "line": "Capital", "role": "capital"},
            {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"},
            {"code": "3200", "name": "Dividends", "type": "equity", "line": "Dividends", "role": "dividends"},
            {"code": "3300", "name": "Revaluation reserve", "type": "equity", "line": "Revaluation reserve", "role": "oci_reserve"},
            {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"},
            {"code": "4100", "name": "Gain on disposal", "type": "income", "line": "Gain on disposal"},
            {"code": "4200", "name": "Revaluation gain", "type": "oci", "line": "Revaluation gain"},
            {"code": "5000", "name": "Rent expense", "type": "expense", "line": "Rent"},
            {"code": "5100", "name": "Depreciation expense", "type": "expense", "line": "Depreciation"},
            {"code": "5200", "name": "Bad debt expense", "type": "expense", "line": "Bad debts"},
            {"code": "5300", "name": "Loss on disposal", "type": "expense", "line": "Loss on disposal"},
            {"code": "5400", "name": "Revaluation loss", "type": "expense", "line": "Revaluation loss"},
        ],
        "prior_closing": {"1000": "20000", "3000": "20000"},
        "opening": [{"description": "opening balances",
                     "lines": [{"account": "1000", "debit": "20000"}, {"account": "3000", "credit": "20000"}]}],
        "entries": [
            {"date": "2026-01-05", "description": "buy equipment A",
             "lines": [{"account": "1200", "debit": "9000"}, {"account": "1000", "credit": "9000"}]},
            {"date": "2026-01-06", "description": "buy equipment B",
             "lines": [{"account": "1400", "debit": "4000"}, {"account": "1000", "credit": "4000"}]},
            {"date": "2026-01-15", "description": "credit sale", "ref": "sale-1",
             "lines": [{"account": "1100", "debit": "8000"}, {"account": "4000", "credit": "8000"}]},
            {"date": "2026-02-05", "description": "reverse the credit sale", "reverses": "sale-1"},
            {"date": "2026-02-10", "description": "second credit sale",
             "lines": [{"account": "1100", "debit": "3000"}, {"account": "4000", "credit": "3000"}]},
            {"date": "2026-03-20", "description": "dividend declared",
             "lines": [{"account": "3200", "debit": "500"}, {"account": "1000", "credit": "500"}]},
        ],
        "schedules": [
            {"kind": "prepayment", "total": "900", "periods": 3, "places": 2, "start": "2026-01",
             "date": "2026-01-03", "prepaid_account": "1300", "expense_account": "5000", "cash_account": "1000"},
            {"kind": "deferred_income", "total": "600", "periods": 3, "places": 2, "start": "2026-01",
             "date": "2026-01-10", "cash_account": "1000", "deferred_account": "2200", "revenue_account": "4000"},
            {"kind": "depreciation", "cost": "9000", "residual": "3000", "life": 3, "places": 2,
             "start": "2026-01", "dep_account": "5100", "accum_account": "1210"},
            {"kind": "bad_debt", "date": "2026-02-28", "charge": "300", "places": 2,
             "receivable_account": "1100", "allowance_account": "1500", "expense_account": "5200"},
            {"kind": "bad_debt", "date": "2026-03-10", "charge": "0", "write_off": "200", "places": 2,
             "receivable_account": "1100", "allowance_account": "1500", "expense_account": "5200"},
            {"kind": "disposal", "date": "2026-03-15", "cost": "4000", "accumulated": "0", "proceeds": "3500",
             "places": 2, "asset_account": "1400", "accum_account": "1410",
             "proceeds_account": "1000", "gain_account": "4100", "loss_account": "5300"},
            {"kind": "revaluation", "date": "2026-03-31", "revalued_amount": "4000", "method": "proportionate",
             "places": 2, "asset_account": "1200", "accum_account": "1210",
             "oci_account": "4200", "loss_account": "5400"},
        ],
        "policy_changes": [],
    }


class TheWholePipelineHolds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = accounts_mod.build(the_engagement())
        cls.ex = cls.out["_appendix"]

    def test_every_check_passes(self):
        failed = [(n, d) for n, ok, d in self.out["_checks"] if not ok]
        self.assertEqual(failed, [], "pipeline checks failed: %r" % (failed,))
        self.assertEqual(len(self.out["_checks"]), 11, "the eleven frozen checks must all run")

    def test_the_balance_sheet_balances(self):
        st = self.ex["statements"]
        self.assertEqual(D(st["total_assets"]), D(st["total_liabilities"]) + D(st["equity_with_current_earnings"]))

    def test_both_cash_flow_routes_agree(self):
        cf = self.ex["cash_flow"]
        self.assertEqual(D(cf["net_direct"]), D(cf["net_indirect"]))
        self.assertEqual(D(cf["operating"]) + D(cf["investing"]) + D(cf["financing"]), D(cf["net_direct"]))

    def test_every_t_account_rolls_forward(self):
        for lg in self.ex["ledgers"]:
            opening = D(lg["opening_balance"])
            moved = sum((D(r["debit"]) - D(r["credit"]) if lg["normal"] == "D"
                         else D(r["credit"]) - D(r["debit"])) for r in lg["movements"])
            self.assertEqual(opening + moved, D(lg["closing_balance"]),
                             "%s does not roll forward" % lg["code"])

    def test_every_journal_entry_balances(self):
        for row in self.ex["journal"]:
            self.assertEqual(D(row["debits"]), D(row["credits"]),
                             "entry '%s' does not balance" % row["description"])

    def test_the_equity_statement_ties_to_the_balance_sheet(self):
        eq = self.ex["equity_statement"]
        st = self.ex["statements"]
        self.assertEqual(D(eq["total_closing"]), D(st["equity_with_current_earnings"]))

    def test_other_comprehensive_income_is_present_and_separate(self):
        ci = self.ex["comprehensive_income"]
        self.assertGreater(D(ci["total_oci"]), D(0), "the revaluation surplus must appear in OCI")
        self.assertEqual(D(ci["total_comprehensive_income"]),
                         D(ci["profit_for_period"]) + D(ci["total_oci"]))
        lg = {g["code"]: g for g in self.ex["ledgers"]}
        self.assertEqual(D(lg["3300"]["closing_balance"]), D(ci["total_oci"]))
        self.assertEqual(D(lg["4200"]["closing_balance"]), D(0), "the OCI account closes to the reserve")

    def test_the_deferrals_and_the_allowance_clear(self):
        lg = {g["code"]: g for g in self.ex["ledgers"]}
        self.assertEqual(D(lg["1300"]["closing_balance"]), D(0), "prepayment must release fully")
        self.assertEqual(D(lg["2200"]["closing_balance"]), D(0), "deferred income must be recognised fully")
        self.assertEqual(D(lg["1400"]["closing_balance"]), D(0), "equipment B was disposed of")
        self.assertEqual(D(lg["1500"]["closing_balance"]), D("100"), "300 charged less 200 written off")


class ItIsDeterministic(unittest.TestCase):
    def test_the_same_specification_produces_identical_output(self):
        a = accounts_mod.build(the_engagement())["_appendix"]
        b = accounts_mod.build(the_engagement())["_appendix"]
        for key in ("journal_export", "statements_export", "equity_statement_export", "export"):
            self.assertEqual(a[key], b[key], "%s is not deterministic" % key)
        self.assertEqual(a["ledgers"], b["ledgers"])
        self.assertEqual(a["checks"], b["checks"])

    def test_rebuilding_changes_nothing(self):
        a = accounts_mod.build(the_engagement())
        b = accounts_mod.build(the_engagement())
        self.assertEqual(a["_appendix"]["journal_export"], b["_appendix"]["journal_export"])
        self.assertEqual(a["net_income"], b["net_income"])


if __name__ == "__main__":
    unittest.main()
