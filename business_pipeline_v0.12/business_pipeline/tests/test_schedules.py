import sys, os, unittest
from decimal import Decimal as D
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from bp import schedules as S
from bp import ledger as L

DEP = {"cost": "1200", "residual": "0", "life": 12, "start": "2026-01", "dep_account": "5100", "accum_account": "1510"}
AM = {"principal": "1000", "rate": "0.12", "periods_per_year": 12, "term": 12, "start": "2026-01", "cash_account": "1000", "loan_account": "2000", "interest_account": "2100"}
ACC = {"amount": "500.00", "periods": 3, "start": "2026-01", "expense_account": "5000", "accrual_account": "2300"}

class Depreciation(unittest.TestCase):
    def test_hand_checked_schedule(self):
        es = S.depreciation(DEP)
        self.assertEqual(len(es), 12); self.assertEqual(es[0]["date"], "2026-01-31"); self.assertEqual(es[-1]["date"], "2026-12-31")
        self.assertEqual(es[0]["lines"], [{"account": "5100", "debit": "100.00"}, {"account": "1510", "credit": "100.00"}])
        self.assertTrue(all(e["lines"][0]["debit"] == e["lines"][1]["credit"] for e in es))
    def test_final_period_absorbs_the_remainder(self):
        es = S.depreciation({**DEP, "cost": "100", "residual": "0", "life": 3})
        amts = [D(e["lines"][0]["debit"]) for e in es]
        self.assertEqual([str(a) for a in amts], ["33.33", "33.33", "33.34"]); self.assertEqual(sum(amts, D(0)), D(100))
    def test_residual_is_kept(self):
        es = S.depreciation({**DEP, "cost": "1200", "residual": "240", "life": 12})
        self.assertEqual(sum((D(e["lines"][0]["debit"]) for e in es), D(0)), D(960))
    def test_validation(self):
        for bad, frag in (({**DEP, "cost": "0"}, "positive"), ({**DEP, "cost": 100.0}, "binary float"), ({**DEP, "residual": "1200"}, "between zero"), ({**DEP, "residual": "-1"}, "between zero"),
                          ({**DEP, "life": 0}, "at least one"), ({**DEP, "start": "01/2026"}, "YYYY-MM"), ({**DEP, "dep_account": "bad code"}, "valid account"), ({**DEP, "cost": "10.005"}, "never rounds silently")):
            with self.assertRaises(S.ScheduleError) as c: S.depreciation(bad)
            self.assertIn(frag, str(c.exception))
    def test_posts_into_the_ledger_and_passes_invariants(self):
        ch = L.Chart([L.Account("1500", "Equipment", "asset", "Equipment"), L.Account("1510", "Accumulated depreciation", "asset", "Equipment", contra=True),
                      L.Account("3000", "Owner capital", "equity", "Capital", role="capital"), L.Account("4000", "Sales", "income", "Revenue"), L.Account("5100", "Depreciation", "expense", "Depreciation")])
        j = L.Journal(ch, "2026-01-01", "2026-12-31", "USD")
        j.post(L.Entry.make("2026-01-01", "opening", [{"account": "1500", "debit": "1200"}, {"account": "3000", "credit": "1200"}], opening=True))
        for e in S.depreciation(DEP): j.post(L.Entry.make(e["date"], e["description"], e["lines"]))
        r = L.check_invariants(j, L.statements(j)); self.assertTrue(all(ok for _, ok, _ in r), r)
        st = L.statements(j); self.assertEqual(st["expenses"]["Depreciation"], D(1200)); self.assertEqual(st["total_assets"], D(0))

class Amortization(unittest.TestCase):
    def test_hand_checked_schedule(self):
        es = S.amortization(AM)
        self.assertEqual(len(es), 12); self.assertEqual(es[0]["date"], "2026-01-31")
        e0 = es[0]["lines"]; self.assertEqual([e0[0]["debit"], e0[1]["debit"], e0[2]["credit"]], ["10.00", "78.85", "88.85"])
        prins = [D(e["lines"][1]["debit"]) for e in es]; ints = [D(e["lines"][0]["debit"]) for e in es]; pays = [D(e["lines"][2]["credit"]) for e in es]
        self.assertEqual(sum(prins, D(0)), D(1000)); self.assertEqual(sum(ints, D(0)) + sum(prins, D(0)), sum(pays, D(0)))
        self.assertLess(pays[-1], pays[0])
    def test_interest_matches_the_running_balance_exactly(self):
        es = S.amortization(AM); bal = D(1000); r = D("0.12") / 12
        for e in es:
            i, pr, pay = (D(e["lines"][0]["debit"]), D(e["lines"][1]["debit"]), D(e["lines"][2]["credit"]))
            self.assertEqual(i + pr, pay); self.assertEqual(i, (bal * r).quantize(D("0.01"))); bal -= pr
        self.assertEqual(bal, 0)
    def test_fixed_payment_and_zero_rate(self):
        es = S.amortization({**AM, "payment": "100.00"})
        self.assertEqual(sum((D(e["lines"][1]["debit"]) for e in es), D(0)), D(1000))
        es2 = S.amortization({**AM, "rate": "0"})
        self.assertEqual(sum((D(e["lines"][0]["debit"]) for e in es2), D(0)), D(0)); self.assertEqual(sum((D(e["lines"][2]["credit"]) for e in es2), D(0)), D(1000))
    def test_validation(self):
        for bad, frag in (({**AM, "payment": "5"}, "does not cover"), ({**AM, "rate": "1.5"}, "between zero"), ({**AM, "principal": "-100"}, "positive"), ({**AM, "term": 0}, "at least one"),
                          ({**AM, "principal": "10.005"}, "never rounds silently"), ({**AM, "loan_account": "nope!"}, "valid account")):
            with self.assertRaises(S.ScheduleError) as c: S.amortization(bad)
            self.assertIn(frag, str(c.exception))
    def test_posts_into_the_ledger_and_passes_invariants(self):
        ch = L.Chart([L.Account("1000", "Cash", "asset", "Cash"), L.Account("2000", "Loan", "liability", "Loans"), L.Account("2100", "Interest expense", "expense", "Interest"),
                      L.Account("3000", "Owner capital", "equity", "Capital", role="capital")])
        j = L.Journal(ch, "2026-01-01", "2026-12-31", "USD")
        j.post(L.Entry.make("2026-01-01", "opening", [{"account": "1000", "debit": "1000"}, {"account": "2000", "credit": "1000"}], opening=True))
        for e in S.amortization(AM): j.post(L.Entry.make(e["date"], e["description"], e["lines"]))
        r = L.check_invariants(j, L.statements(j)); self.assertTrue(all(ok for _, ok, _ in r), r)
        st = L.statements(j); self.assertEqual(st["liabilities"]["Loans"], D(0)); self.assertEqual(st["net_income"], -sum((D(e["lines"][0]["debit"]) for e in S.amortization(AM)), D(0)))

class Accrual(unittest.TestCase):
    def test_hand_checked(self):
        es = S.accrual(ACC); self.assertEqual(len(es), 3); self.assertEqual([e["date"] for e in es], ["2026-01-31", "2026-02-28", "2026-03-31"])
        self.assertTrue(all(e["lines"][0]["debit"] == "500.00" and e["lines"][1]["credit"] == "500.00" for e in es))
    def test_validation(self):
        for bad, frag in (({**ACC, "amount": "0"}, "positive"), ({**ACC, "periods": 0}, "at least one"), ({**ACC, "amount": 0.5}, "binary float"), ({**ACC, "accrual_account": "x y"}, "valid account")):
            with self.assertRaises(S.ScheduleError) as c: S.accrual(bad)
            self.assertIn(frag, str(c.exception))
    def test_posts_into_the_ledger_and_passes_invariants(self):
        ch = L.Chart([L.Account("1000", "Cash", "asset", "Cash"), L.Account("2300", "Accrued expenses", "liability", "Accruals"), L.Account("5000", "Rent", "expense", "Rent"),
                      L.Account("3000", "Owner capital", "equity", "Capital", role="capital")])
        j = L.Journal(ch, "2026-01-01", "2026-03-31", "USD")
        j.post(L.Entry.make("2026-01-01", "opening", [{"account": "1000", "debit": "1500"}, {"account": "3000", "credit": "1500"}], opening=True))
        for e in S.accrual(ACC): j.post(L.Entry.make(e["date"], e["description"], e["lines"]))
        r = L.check_invariants(j, L.statements(j)); self.assertTrue(all(ok for _, ok, _ in r), r)
        self.assertEqual(L.statements(j)["liabilities"]["Accruals"], D(1500))
if __name__ == "__main__": unittest.main()
