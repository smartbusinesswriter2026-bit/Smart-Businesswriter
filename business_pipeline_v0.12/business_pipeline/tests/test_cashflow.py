import sys, os, random, unittest
from decimal import Decimal as D
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from bp import ledger as L

def chart(with_second_cash=False):
    accs = [L.Account("1000", "Cash", "asset", "Cash", role="cash"), L.Account("1100", "Receivables", "asset", "Receivables", activity="operating"),
            L.Account("1500", "Equipment", "asset", "Equipment"), L.Account("1510", "Accumulated depreciation", "asset", "Equipment", contra=True),
            L.Account("2000", "Loan", "liability", "Loans"), L.Account("2300", "Accrued expenses", "liability", "Accruals", activity="operating"),
            L.Account("3000", "Owner capital", "equity", "Capital", role="capital"), L.Account("3100", "Retained earnings", "equity", "Retained earnings", role="retained_earnings"),
            L.Account("3200", "Dividends", "equity", "Dividends", role="dividends"), L.Account("4000", "Sales", "income", "Revenue"), L.Account("5000", "Rent", "expense", "Rent"), L.Account("5100", "Depreciation", "expense", "Depreciation")]
    if with_second_cash: accs.append(L.Account("1010", "Petty cash", "asset", "Cash", role="cash"))
    return L.Chart(accs)

def journal(ch=None):
    j = L.Journal(ch or chart(), "2026-01-01", "2026-12-31", "USD"); mk = lambda d, t, ls, o=False: j.post(L.Entry.make(d, t, ls, opening=o))
    mk("2026-01-01", "opening", [{"account": "1000", "debit": "5000"}, {"account": "3000", "credit": "5000"}], True)
    mk("2026-01-15", "cash sale", [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}])
    mk("2026-02-01", "equipment purchase", [{"account": "1500", "debit": "500"}, {"account": "1000", "credit": "500"}])
    mk("2026-02-15", "loan received", [{"account": "1000", "debit": "1000"}, {"account": "2000", "credit": "1000"}])
    mk("2026-03-31", "rent", [{"account": "5000", "debit": "500"}, {"account": "1000", "credit": "500"}])
    mk("2026-03-31", "dividend", [{"account": "3200", "debit": "300"}, {"account": "1000", "credit": "300"}])
    mk("2026-06-30", "depreciation", [{"account": "5100", "debit": "100"}, {"account": "1510", "credit": "100"}])
    mk("2026-09-30", "credit sale", [{"account": "1100", "debit": "150"}, {"account": "4000", "credit": "150"}])
    mk("2026-10-31", "rent accrual", [{"account": "5000", "debit": "200"}, {"account": "2300", "credit": "200"}])
    return j

class TwoRoutes(unittest.TestCase):
    def test_hand_checked_split_and_agreement(self):
        cf = L.cash_flow(journal())
        self.assertEqual((cf["operating"], cf["investing"], cf["financing"]), (D(1500), D(-500), D(700)))
        self.assertEqual((cf["net_direct"], cf["net_indirect"]), (D(1700), D(1700)))
        self.assertTrue(all(ok for _, ok, _ in cf["checks"]), cf["checks"]); self.assertEqual(cf["flags"], [])
    def test_non_cash_entries_do_not_move_the_routes(self):
        cf = L.cash_flow(journal())
        base = (cf["net_direct"], cf["net_indirect"])
        j = journal(); j.post(L.Entry.make("2026-11-30", "depreciation", [{"account": "5100", "debit": "50"}, {"account": "1510", "credit": "50"}]))
        cf2 = L.cash_flow(j); self.assertEqual((cf2["net_direct"], cf2["net_indirect"]), base); self.assertTrue(all(ok for _, ok, _ in cf2["checks"]))
    def test_collecting_a_receivable_and_paying_an_accrual_are_operating(self):
        j = journal(); j.post(L.Entry.make("2026-12-15", "collection", [{"account": "1000", "debit": "150"}, {"account": "1100", "credit": "150"}]))
        j.post(L.Entry.make("2026-12-20", "settle accrual", [{"account": "2300", "debit": "200"}, {"account": "1000", "credit": "200"}]))
        cf = L.cash_flow(j); self.assertEqual((cf["operating"], cf["net_direct"]), (D(1450), D(1650))); self.assertTrue(all(ok for _, ok, _ in cf["checks"])); self.assertEqual(cf["flags"], [])
    def test_untagged_liability_defaults_to_financing(self):
        j = journal(); j.post(L.Entry.make("2026-12-20", "loan repayment", [{"account": "2000", "debit": "400"}, {"account": "1000", "credit": "400"}]))
        cf = L.cash_flow(j); self.assertEqual(cf["financing"], D(300)); self.assertTrue(all(ok for _, ok, _ in cf["checks"]))
    def test_corrupted_net_income_breaks_the_agreement(self):
        j = journal(); st = L.statements(j); st["net_income"] += 1
        cf = L.cash_flow(j, st); self.assertFalse(cf["checks"][0][1]); self.assertIn("direct", cf["checks"][0][2])
    def test_opening_entries_are_excluded(self):
        j = L.Journal(chart(), "2026-01-01", "2026-12-31", "USD")
        j.post(L.Entry.make("2026-01-01", "opening", [{"account": "1000", "debit": "99999"}, {"account": "3000", "credit": "99999"}], opening=True))
        cf = L.cash_flow(j); self.assertEqual((cf["net_direct"], cf["operating"]), (D(0), D(0))); self.assertTrue(all(ok for _, ok, _ in cf["checks"]))

class ClassificationFlags(unittest.TestCase):
    def test_mixed_counterparts_are_flagged_and_classified_operating_first(self):
        j = journal(); j.post(L.Entry.make("2026-12-15", "mixed sale", [{"account": "1000", "debit": "80"}, {"account": "1500", "debit": "20"}, {"account": "4000", "credit": "100"}]))
        cf = L.cash_flow(j)
        self.assertEqual(cf["operating"], D(1580)); self.assertEqual([f["kind"] for f in cf["flags"]], ["mixed_classification"]); self.assertTrue(all(ok for _, ok, _ in cf["checks"]))
    def test_cash_to_cash_transfer_is_flagged_without_totals(self):
        j2 = journal(chart(True)); j2.post(L.Entry.make("2026-12-15", "transfer", [{"account": "1010", "debit": "50"}, {"account": "1000", "credit": "50"}]))
        cf2 = L.cash_flow(j2)
        self.assertEqual(cf2["net_direct"], D(1700)); self.assertIn("cash_to_cash_transfer", [f["kind"] for f in cf2["flags"]]); self.assertTrue(all(ok for _, ok, _ in cf2["checks"]))
    def test_invalid_activity_tag_is_rejected(self):
        with self.assertRaises(L.ChartError): L.Account("1", "x", "asset", "l", activity="operational")

class Fuzz(unittest.TestCase):
    def test_random_journals_always_satisfy_the_two_route_agreement(self):
        rng = random.Random(11); codes = list(chart().accounts)
        for n in range(300):
            j = L.Journal(chart(), "2026-01-01", "2026-12-31", "USD")
            j.post(L.Entry.make("2026-01-01", "opening", [{"account": "1000", "debit": "10000"}, {"account": "3000", "credit": "10000"}], opening=True))
            for k in range(rng.randint(1, 10)):
                dr = rng.sample(codes, rng.randint(1, 3)); cr = rng.sample([c for c in codes if c not in dr], rng.randint(1, 3))
                amts = [D(rng.randint(1, 5000)) / 100 for _ in dr]; total = sum(amts, D(0)); parts = [round(total / len(cr), 2)] * (len(cr) - 1); parts.append(total - sum(parts, D(0)))
                if min(parts) <= 0: continue
                lines = [{"account": a, "debit": str(x)} for a, x in zip(dr, amts)] + [{"account": a, "credit": str(x)} for a, x in zip(cr, parts)]
                j.post(L.Entry.make(f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}", f"e{k}", lines))
            cf = L.cash_flow(j); self.assertTrue(all(ok for _, ok, _ in cf["checks"]), (n, cf["checks"], cf["flags"]))
if __name__ == "__main__": unittest.main()
