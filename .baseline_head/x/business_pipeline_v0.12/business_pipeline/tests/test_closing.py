import sys, os, unittest
from decimal import Decimal as D
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from bp import ledger as L

def chart():
    return L.Chart([L.Account("1000", "Cash", "asset", "Cash"), L.Account("1500", "Equipment", "asset", "Equipment"), L.Account("1510", "Accumulated depreciation", "asset", "Equipment", contra=True),
                    L.Account("2000", "Loan", "liability", "Loans"), L.Account("3000", "Owner capital", "equity", "Capital", role="capital"), L.Account("3100", "Retained earnings", "equity", "Retained earnings", role="retained_earnings"),
                    L.Account("3200", "Dividends", "equity", "Dividends", role="dividends"), L.Account("4000", "Sales", "income", "Revenue"), L.Account("5000", "Rent", "expense", "Rent"), L.Account("5100", "Depreciation", "expense", "Depreciation")])

def journal():
    j = L.Journal(chart(), "2026-01-01", "2026-12-31", "USD"); mk = lambda d, t, ls, o=False: j.post(L.Entry.make(d, t, ls, opening=o))
    mk("2026-01-01", "opening", [{"account": "1000", "debit": "5000"}, {"account": "1500", "debit": "3000"}, {"account": "3000", "credit": "7000"}, {"account": "3100", "credit": "1000"}], True)
    mk("2026-01-15", "sale", [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}])
    mk("2026-03-31", "rent", [{"account": "5000", "debit": "500"}, {"account": "1000", "credit": "500"}])
    mk("2026-03-31", "dividend", [{"account": "3200", "debit": "300"}, {"account": "1000", "credit": "300"}])
    mk("2026-06-30", "depreciation", [{"account": "5100", "debit": "100"}, {"account": "1510", "credit": "100"}])
    mk("2026-08-01", "loan received", [{"account": "1000", "debit": "1000"}, {"account": "2000", "credit": "1000"}])
    return j

class Closing(unittest.TestCase):
    def test_closing_zeroes_income_expense_and_rolls_forward(self):
        j = journal(); pre = L.statements(j); es = L.closing_entries(j, pre)
        self.assertEqual(len(es), 3)   # income, expense, dividends
        for e in es: j.post(L.Entry.make(e["date"], e["description"], e["lines"], closing=e["closing"]))
        post = L.statements(j)
        self.assertEqual((post["income"], post["expenses"]), ({}, {})); self.assertEqual(post["net_income"], D(0))
        self.assertEqual(L.closing_balances(j)["3100"], D(2100))     # 1000 + 2000 - 600 - 300
        r = L.retained_earnings_rollforward(j, pre); self.assertTrue(all(ok for _, ok, _ in r), r)
    def test_direct_retained_earnings_posting_is_included(self):
        j = journal(); pre = L.statements(j); j.post(L.Entry.make("2026-11-30", "prior period adjustment", [{"account": "3100", "debit": "50"}, {"account": "1000", "credit": "50"}]))
        for e in L.closing_entries(j, pre): j.post(L.Entry.make(e["date"], e["description"], e["lines"], closing=e["closing"]))
        self.assertEqual(L.closing_balances(j)["3100"], D(2050)); self.assertTrue(all(ok for _, ok, _ in L.retained_earnings_rollforward(j, pre)))
    def test_rollforward_detects_tampering(self):
        j = journal(); pre = L.statements(j)
        for e in L.closing_entries(j, pre): j.post(L.Entry.make(e["date"], e["description"], e["lines"], closing=e["closing"]))
        object.__setattr__(j.entries[-2].lines[0], "amount", D(599))     # tamper the retained-earnings line of the expense closing entry
        r = L.retained_earnings_rollforward(j, pre); self.assertFalse(r[0][1]); self.assertFalse(j.verify_chain())
        # tampering the dividends closing line leaves retained earnings alone but is caught by the zero-balance check
        j3 = journal()
        for e in L.closing_entries(j3, pre): j3.post(L.Entry.make(e["date"], e["description"], e["lines"], closing=e["closing"]))
        object.__setattr__(j3.entries[-1].lines[-1], "amount", D(599)); self.assertFalse(L.retained_earnings_rollforward(j3, pre)[1][1])
        j2 = journal()
        for e in L.closing_entries(j2, pre): j2.post(L.Entry.make(e["date"], e["description"], e["lines"], closing=e["closing"]))
        pre_bad = {**pre, "net_income": pre["net_income"] + 1}; self.assertFalse(L.retained_earnings_rollforward(j2, pre_bad)[0][1])
    def test_abnormal_balance_blocks_closing(self):
        j = journal(); j.post(L.Entry.make("2026-12-20", "rent refund", [{"account": "1000", "debit": "700"}, {"account": "5000", "credit": "700"}]))
        with self.assertRaises(L.LedgerError) as c: L.closing_entries(j)
        self.assertIn("abnormal balance", str(c.exception))
    def test_closing_needs_a_retained_earnings_account(self):
        ch = L.Chart([L.Account("1000", "Cash", "asset", "Cash"), L.Account("4000", "Sales", "income", "Revenue"), L.Account("3000", "Owner capital", "equity", "Capital", role="capital")])
        j = L.Journal(ch, "2026-01-01", "2026-12-31", "USD"); j.post(L.Entry.make("2026-01-15", "sale", [{"account": "1000", "debit": "10"}, {"account": "4000", "credit": "10"}]))
        with self.assertRaises(L.LedgerError) as c: L.closing_entries(j)
        self.assertIn("retained earnings", str(c.exception))
    def test_no_activity_closes_without_entries(self):
        j = L.Journal(chart(), "2026-01-01", "2026-12-31", "USD"); j.post(L.Entry.make("2026-01-01", "opening", [{"account": "1000", "debit": "500"}, {"account": "3000", "credit": "500"}], opening=True))
        self.assertEqual(L.closing_entries(j), []); self.assertTrue(all(ok for _, ok, _ in L.retained_earnings_rollforward(j)))

class MultiPeriod(unittest.TestCase):
    def test_next_period_opens_from_prior_closing(self):
        j1 = journal(); pre = L.statements(j1)
        for e in L.closing_entries(j1, pre): j1.post(L.Entry.make(e["date"], e["description"], e["lines"], closing=e["closing"]))
        prior = L.closing_balances(j1); self.assertEqual(prior["1000"], D(7200)); self.assertEqual(prior["1510"], D(100)); self.assertEqual(prior["3100"], D(2100))
        j2 = L.Journal(chart(), "2027-01-01", "2027-12-31", "USD")
        j2.post(L.Entry.make("2027-01-01", "opening", L.opening_lines(j1), opening=True))
        j2.post(L.Entry.make("2027-02-15", "sale", [{"account": "1000", "debit": "800"}, {"account": "4000", "credit": "800"}]))
        st2 = L.statements(j2)
        inv = L.check_invariants(j2, st2, prior); self.assertTrue(all(ok for _, ok, _ in inv), inv)
        self.assertEqual(st2["net_income"], D(800)); self.assertEqual(st2["assets"]["Cash"], D(8000))
    def test_opening_mismatch_is_detected(self):
        j1 = journal(); pre = L.statements(j1)
        for e in L.closing_entries(j1, pre): j1.post(L.Entry.make(e["date"], e["description"], e["lines"], closing=e["closing"]))
        j2 = L.Journal(chart(), "2027-01-01", "2027-12-31", "USD")
        j2.post(L.Entry.make("2027-01-01", "opening", [{"account": "1000", "debit": "6101"}, {"account": "3000", "credit": "6101"}], opening=True))
        inv = {n: ok for n, ok, _ in L.check_invariants(j2, L.statements(j2), L.closing_balances(j1))}
        self.assertFalse(inv["opening_balances_equal_prior_closing"])
if __name__ == "__main__": unittest.main()
