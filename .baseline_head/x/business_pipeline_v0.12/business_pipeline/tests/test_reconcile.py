import sys, os, random, unittest
from decimal import Decimal as D
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from bp import ledger as L, reconcile as R

def chart():
    return L.Chart([L.Account("1000", "Cash", "asset", "Cash", role="cash"), L.Account("3000", "Owner capital", "equity", "Capital", role="capital"),
                    L.Account("3100", "Retained earnings", "equity", "Retained earnings", role="retained_earnings"),
                    L.Account("4000", "Sales", "income", "Revenue"), L.Account("5000", "Rent", "expense", "Rent")])

def journal(with_transit=True):
    j = L.Journal(chart(), "2026-01-01", "2026-03-31", "USD"); mk = lambda d, t, ls, o=False: j.post(L.Entry.make(d, t, ls, opening=o))
    mk("2026-01-01", "opening", [{"account": "1000", "debit": "5000"}, {"account": "3000", "credit": "5000"}], True)
    mk("2026-01-15", "sale", [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}])
    mk("2026-02-28", "rent", [{"account": "5000", "debit": "500"}, {"account": "1000", "credit": "500"}])
    if with_transit: mk("2026-03-31", "deposit in transit", [{"account": "1000", "debit": "150"}, {"account": "4000", "credit": "150"}])
    return j

STATEMENT = {"opening_balance": "5000", "closing_balance": "6475", "lines": [
    {"date": "2026-01-15", "description": "sale deposit", "amount": "2000", "direction": "in"},
    {"date": "2026-02-28", "description": "rent cheque", "amount": "500", "direction": "out"},
    {"date": "2026-03-31", "description": "bank charge", "amount": "25", "direction": "out"}]}

class HandChecked(unittest.TestCase):
    def test_adjustments_tie(self):
        r = R.reconcile(journal(), "1000", STATEMENT); rp = r["report"]
        self.assertEqual((rp["ledger_balance"], rp["statement_closing"], rp["receipts_in_transit"], rp["unrecorded_payments"]), (D(6650), D(6475), D(150), D(25)))
        self.assertEqual((rp["adjusted_statement"], rp["adjusted_ledger"], rp["difference"]), (D(6625), D(6625), D(0)))
        self.assertTrue(all(ok for _, ok, _ in r["checks"]), r["checks"]); self.assertEqual(r["flags"], [])
        self.assertEqual([b["description"] for b in rp["books_only"]], ["deposit in transit"])
        self.assertEqual([s["description"] for s in rp["statement_only"]], ["bank charge"]); self.assertEqual(len(rp["matched"]), 2)
    def test_unrecorded_receipts_direction(self):
        j = journal(with_transit=False)                                    # book: 5000 + 2000 - 500 = 6500
        st = {"opening_balance": "5000", "closing_balance": "5100", "lines": [{"description": "interest", "amount": "100", "direction": "in"}]}
        r = R.reconcile(j, "1000", st)
        self.assertEqual(r["report"]["unrecorded_receipts"], D(100)); self.assertEqual(r["report"]["difference"], D(0))
        self.assertTrue(all(ok for _, ok, _ in r["checks"]), r["checks"])
    def test_opening_mismatch_fails_and_leaves_a_difference(self):
        # internally consistent statement (closing = opening + lines) whose opening disagrees with the book by 1
        r = R.reconcile(journal(), "1000", {**STATEMENT, "opening_balance": "4999", "closing_balance": "6474"}); checks = {n: (ok, d) for n, ok, d in r["checks"]}
        self.assertFalse(checks["opening_balances_agree"][0]); self.assertTrue(checks["statement_internally_consistent"][0])
        self.assertEqual(r["report"]["difference"], D(-1))
    def test_inconsistent_statement_fails(self):
        r = R.reconcile(journal(), "1000", {**STATEMENT, "closing_balance": "6476"}); checks = {n: (ok, d) for n, ok, d in r["checks"]}
        self.assertFalse(checks["statement_internally_consistent"][0]); self.assertTrue(checks["opening_balances_agree"][0])

class Traps(unittest.TestCase):
    def test_ambiguous_amount_is_flagged_not_guessed(self):
        j = journal(with_transit=False)                                    # book: 5000 + 2000 - 500 = 6500
        st = {"opening_balance": "5000", "closing_balance": "8500", "lines": [
            {"description": "sale a", "amount": "2000", "direction": "in"}, {"description": "sale b", "amount": "2000", "direction": "in"},
            {"description": "rent", "amount": "500", "direction": "out"}]}                                   # one 2000 is unrecorded
        r = R.reconcile(j, "1000", st)
        self.assertIn("ambiguous_match", [f["kind"] for f in r["flags"]]); self.assertTrue(all(ok for _, ok, _ in r["checks"]))
        self.assertEqual(r["report"]["unrecorded_receipts"], D(2000)); self.assertEqual(r["report"]["difference"], D(0))
    def test_statement_line_outside_the_period_is_flagged(self):
        st = {**STATEMENT, "lines": STATEMENT["lines"] + [{"date": "2027-01-05", "description": "late", "amount": "10", "direction": "in"}]}
        st["closing_balance"] = "6485"
        r = R.reconcile(journal(), "1000", st); self.assertIn("statement_line_outside_period", [f["kind"] for f in r["flags"]])
    def test_statement_validation(self):
        for bad, frag in (({}, "opening_balance"), ({"opening_balance": "1", "closing_balance": "1", "lines": [{"amount": "1", "direction": "up"}]}, "direction"),
                          ({"opening_balance": "1", "closing_balance": "1", "lines": [{"amount": "-1", "direction": "in"}]}, "positive"),
                          ({"opening_balance": "1", "closing_balance": "1", "lines": [{"amount": 1.5, "direction": "in"}]}, "binary float")):
            errs = R.validate_statement(bad); self.assertTrue(any(frag in e for e in errs), (bad, errs))
        with self.assertRaises(R.ReconcileError): R.reconcile(journal(), "1000", {"opening_balance": "1"})

class Fuzz(unittest.TestCase):
    def test_random_books_and_statements_always_partition_and_tie(self):
        rng = random.Random(5)
        for n in range(200):
            j = L.Journal(chart(), "2026-01-01", "2026-12-31", "USD")
            j.post(L.Entry.make("2026-01-01", "opening", [{"account": "1000", "debit": "1000"}, {"account": "3000", "credit": "1000"}], opening=True))
            moves = []
            for k in range(rng.randint(1, 8)):
                amt = D(rng.randint(1, 5000)) / 100; date = f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
                if rng.random() < 0.5:
                    j.post(L.Entry.make(date, f"in{k}", [{"account": "1000", "debit": str(amt)}, {"account": "4000", "credit": str(amt)}])); moves.append((amt, "in"))
                else:
                    j.post(L.Entry.make(date, f"out{k}", [{"account": "5000", "debit": str(amt)}, {"account": "1000", "credit": str(amt)}])); moves.append((amt, "out"))
            stmt_moves = [m for m in moves if rng.random() < 0.7] + [(D(rng.randint(1, 5000)) / 100, rng.choice(("in", "out"))) for _ in range(rng.randint(0, 3))]
            so = D(1000); sc = so + sum((amt if d == "in" else -amt for amt, d in stmt_moves), D(0))
            st = {"opening_balance": str(so), "closing_balance": str(sc), "lines": [{"date": "2026-06-01", "description": f"m{i}", "amount": str(amt), "direction": d} for i, (amt, d) in enumerate(stmt_moves)]}
            r = R.reconcile(j, "1000", st); rp = r["report"]
            self.assertTrue(all(ok for _, ok, _ in r["checks"]), (n, r["checks"]))
            self.assertEqual(rp["difference"], D(0))
            self.assertEqual(len(rp["matched"]) + len(rp["books_only"]), len(moves)); self.assertEqual(len(rp["matched"]) + len(rp["statement_only"]), len(stmt_moves))
if __name__ == "__main__": unittest.main()
