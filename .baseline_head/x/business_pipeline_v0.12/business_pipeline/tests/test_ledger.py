import sys, os, random, copy, unittest
from decimal import Decimal as D
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "spike"))
from bp import ledger as L

def chart():
    return L.Chart([L.Account("1000", "Cash", "asset", "Cash"), L.Account("1500", "Equipment", "asset", "Equipment"), L.Account("1510", "Accumulated depreciation", "asset", "Equipment", contra=True),
                    L.Account("2000", "Loan", "liability", "Loans"), L.Account("3000", "Owner capital", "equity", "Capital", role="capital"), L.Account("3100", "Retained earnings", "equity", "Retained earnings", role="retained_earnings"),
                    L.Account("3200", "Dividends", "equity", "Dividends", role="dividends"), L.Account("4000", "Sales", "income", "Revenue"), L.Account("5000", "Rent", "expense", "Rent"), L.Account("5100", "Depreciation", "expense", "Depreciation")])
def journal(places=2):
    j = L.Journal(chart(), "2026-01-01", "2026-03-31", "USD"); mk = lambda d, t, ls, o=False: j.post(L.Entry.make(d, t, ls, places, o))
    mk("2026-01-01", "opening", [{"account": "1000", "debit": "5000"}, {"account": "1500", "debit": "3000"}, {"account": "3000", "credit": "7000"}, {"account": "3100", "credit": "1000"}], True)
    mk("2026-01-15", "sale", [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}])
    mk("2026-02-10", "owner pays in", [{"account": "1000", "debit": "500"}, {"account": "3000", "credit": "500"}])
    mk("2026-02-20", "dividend", [{"account": "3200", "debit": "300"}, {"account": "1000", "credit": "300"}])
    mk("2026-03-31", "depreciation", [{"account": "5100", "debit": "100"}, {"account": "1510", "credit": "100"}]); return j
ok = lambda inv: {n: o for n, o, _ in inv}

class Construction(unittest.TestCase):
    def test_unbalanced_and_malformed_entries_cannot_be_built(self):
        M = L.Entry.make
        for lines, exc in (([{"account": "1000", "debit": "1"}, {"account": "4000", "credit": "2"}], L.UnbalancedEntry), ([{"account": "1000", "debit": "1"}], L.UnbalancedEntry),
                           ([{"account": "1000", "debit": "1"}, {"account": "4000", "debit": "1"}], L.UnbalancedEntry), ([{"account": "1000", "debit": "1", "credit": "1"}, {"account": "4000", "credit": "1"}], L.UnbalancedEntry)):
            with self.assertRaises(exc): M("2026-01-01", "x", lines)
    def test_amount_rules(self):
        M = lambda a, p=2: L.Entry.make("2026-01-01", "x", [{"account": "1000", "debit": a}, {"account": "4000", "credit": a}], p)
        for bad in (0.1, True, "0", "-5", "NaN", "Infinity", "10.005", "abc"):
            with self.assertRaises((L.BadAmount, ArithmeticError)): M(bad)
        self.assertEqual(M("10.50").lines[0].amount, D("10.50")); self.assertEqual(M("10", 0).lines[0].amount, D(10))
        with self.assertRaises(L.BadAmount): M("10.5", 0)
    def test_date_format(self):
        with self.assertRaises(L.LedgerError): L.Entry.make("01/02/2026", "x", [{"account": "1000", "debit": "1"}, {"account": "4000", "credit": "1"}])
    def test_chart_rules(self):
        with self.assertRaises(L.ChartError): L.Chart([L.Account("1", "a", "asset", "x"), L.Account("1", "b", "asset", "x")])
        with self.assertRaises(L.ChartError): L.Account("1", "a", "gadget", "x")
        with self.assertRaises(L.ChartError): L.Account("bad code", "a", "asset", "x")
    def test_normal_sides(self):
        a = lambda t, c=False: L.Account("1", "n", t, "l", c).normal
        self.assertEqual([a("asset"), a("expense"), a("liability"), a("equity"), a("income"), a("asset", True), a("income", True)], ["D", "D", "C", "C", "C", "C", "D"])

class JournalRules(unittest.TestCase):
    def test_account_and_period_checks(self):
        j = journal()
        with self.assertRaises(L.UnknownAccount): j.post(L.Entry.make("2026-02-01", "x", [{"account": "9999", "debit": "1"}, {"account": "4000", "credit": "1"}]))
        with self.assertRaises(L.OutOfPeriod): j.post(L.Entry.make("2026-04-01", "x", [{"account": "1000", "debit": "1"}, {"account": "4000", "credit": "1"}]))
        with self.assertRaises(L.LedgerError): L.Journal(chart(), "2026-02-01", "2026-01-01", "USD")
    def test_hash_chain_detects_edits_and_reordering(self):
        j = journal(); self.assertTrue(j.verify_chain())
        e = j.entries[1]; j.entries[1] = L.Entry(e.date, "edited", e.lines, e.opening); self.assertFalse(j.verify_chain())
        j2 = journal(); j2.entries[1], j2.entries[2] = j2.entries[2], j2.entries[1]; self.assertFalse(j2.verify_chain())
    def test_export_is_plain_and_deterministic(self):
        t = journal().export_text(); self.assertEqual(t, journal().export_text()); self.assertIn("2026-01-15 sale\n  1000       Dr 2000.00".replace("2000.00", "2000"), t.replace("2000.00", "2000")); self.assertIn("(opening) opening", t)

class Statements(unittest.TestCase):
    def test_hand_checked_example(self):
        st = L.statements(journal()); self.assertEqual((st["net_income"], st["total_assets"], st["total_liabilities"], st["total_equity"]), (D(1900), D(10100), D(0), D(8200)))
        self.assertEqual(st["assets"], {"Cash": D(7200), "Equipment": D(2900)}); self.assertEqual(st["equity"]["Dividends"], D(-300)); self.assertEqual(st["equity_with_current_earnings"], D(10100))
    def test_trial_balance(self):
        tb = L.trial_balance(journal()); self.assertEqual(tb["total_debits"], tb["total_credits"]); self.assertEqual(tb["total_debits"], D(10600))
    def test_clean_journal_passes_every_invariant(self):
        j = journal(); r = L.check_invariants(j, L.statements(j), {"1000": 5000, "1500": 3000, "3000": 7000, "3100": 1000}); self.assertTrue(all(ok(r).values()), r)
        self.assertEqual(set(ok(r)), {"trial_balance_debits_equal_credits", "assets_equal_liabilities_plus_equity", "net_income_agrees_across_routes", "opening_balances_equal_prior_closing", "statement_lines_foot_to_totals", "journal_hash_chain_intact"})

class InvariantsCatchDefects(unittest.TestCase):
    def check(self, mutate):
        j = journal(); st = L.statements(j); mutate(j, st); return ok(L.check_invariants(j, st))
    def test_each_invariant_fails_when_its_target_is_corrupted(self):
        r = self.check(lambda j, st: st.update(total_assets=st["total_assets"] + 1)); self.assertFalse(r["assets_equal_liabilities_plus_equity"])
        r = self.check(lambda j, st: st.update(net_income=st["net_income"] + 1)); self.assertFalse(r["net_income_agrees_across_routes"])
        r = self.check(lambda j, st: st["assets"].update(Cash=st["assets"]["Cash"] + 1)); self.assertFalse(r["statement_lines_foot_to_totals"])
        def corrupt(j, st): object.__setattr__(j.entries[1].lines[0], "amount", D(2001))
        r = self.check(corrupt); self.assertFalse(r["trial_balance_debits_equal_credits"]); self.assertFalse(r["journal_hash_chain_intact"])
    def test_second_route_does_not_depend_on_account_roles(self):
        j = journal(); ch = j.chart
        for code in ("3000", "3100"): a = ch.accounts[code]; ch.accounts[code] = L.Account(a.code, a.name, a.type, a.line, a.contra, "")
        self.assertTrue(all(ok(L.check_invariants(j, L.statements(j))).values()))
    def test_dividends_role_implies_a_debit_normal_contra_equity_account(self):
        a = L.Account("3200", "Dividends", "equity", "Dividends", role="dividends"); self.assertTrue(a.contra); self.assertEqual(a.normal, "D")
    def test_prior_closing_mismatch(self):
        j = journal(); r = ok(L.check_invariants(j, L.statements(j), {"1000": 5001})); self.assertFalse(r["opening_balances_equal_prior_closing"])
    def test_second_route_unavailable_is_stated_not_faked(self):
        j = L.Journal(chart(), "2026-01-01", "2026-03-31", "USD"); j.post(L.Entry.make("2026-01-05", "sale", [{"account": "1000", "debit": "10"}, {"account": "4000", "credit": "10"}]))
        d = {n: det for n, _, det in L.check_invariants(j, L.statements(j))}; self.assertIn("second route is unavailable", d["net_income_agrees_across_routes"])

class Flags(unittest.TestCase):
    def kinds(self, j): return sorted((f["kind"], f["account"]) for f in L.flags(j))
    def test_clean_journal_has_no_flags(self): self.assertEqual(L.flags(journal()), [])
    def test_flipped_expense_and_misclassified_contra(self):
        j = journal(); j.post(L.Entry.make("2026-03-15", "rent refund", [{"account": "1000", "debit": "700"}, {"account": "5000", "credit": "700"}])); self.assertIn(("abnormal_balance", "5000"), self.kinds(j))
        ch = chart(); ch.accounts["1510"] = L.Account("1510", "Accumulated depreciation", "asset", "Equipment"); j2 = L.Journal(ch, "2026-01-01", "2026-03-31", "USD")
        j2.post(L.Entry.make("2026-03-31", "dep", [{"account": "5100", "debit": "100"}, {"account": "1510", "credit": "100"}])); k = self.kinds(j2)
        self.assertIn(("possible_misclassified_contra", "1510"), k); self.assertIn(("abnormal_balance", "1510"), k)
    def test_missing_accrual_needs_a_pattern(self):
        j = L.Journal(chart(), "2026-01-01", "2026-04-30", "USD"); rent = lambda d: j.post(L.Entry.make(d, "rent", [{"account": "5000", "debit": "500"}, {"account": "1000", "credit": "500"}]))
        for d in ("2026-01-31", "2026-02-28", "2026-03-31"): rent(d)
        j.post(L.Entry.make("2026-04-30", "sale", [{"account": "1000", "debit": "5"}, {"account": "4000", "credit": "5"}])); self.assertIn(("possible_missing_accrual", "5000"), self.kinds(j))
        j2 = L.Journal(chart(), "2026-01-01", "2026-04-30", "USD")
        for d in ("2026-01-31", "2026-04-30"): j2.post(L.Entry.make(d, "rent", [{"account": "5000", "debit": "500"}, {"account": "1000", "credit": "500"}]))
        self.assertNotIn("possible_missing_accrual", [k for k, _ in self.kinds(j2)])

class Fuzz(unittest.TestCase):
    def test_random_balanced_journals_always_satisfy_the_invariants(self):
        rng = random.Random(7); codes = list(chart().accounts)
        for n in range(300):
            ch = chart(); j = L.Journal(ch, "2026-01-01", "2026-12-31", "USD")
            j.post(L.Entry.make("2026-01-01", "opening", [{"account": "1000", "debit": "10000"}, {"account": "1500", "debit": "4000"}, {"account": "3000", "credit": "12000"}, {"account": "3100", "credit": "2000"}], opening=True))
            for k in range(rng.randint(1, 12)):
                dr = rng.sample(codes, rng.randint(1, 3)); cr = rng.sample([c for c in codes if c not in dr], rng.randint(1, 3))
                amts = [D(rng.randint(1, 5000)) / 100 for _ in dr]; total = sum(amts, D(0)); parts = [round(total / len(cr), 2)] * (len(cr) - 1); parts.append(total - sum(parts, D(0)))
                if min(parts) <= 0: continue
                lines = [{"account": a, "debit": str(x)} for a, x in zip(dr, amts)] + [{"account": a, "credit": str(x)} for a, x in zip(cr, parts)]
                j.post(L.Entry.make(f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}", f"e{k}", lines))
            r = L.check_invariants(j, L.statements(j)); self.assertTrue(all(o for _, o, _ in r), (n, [x for x in r if not x[1]]))

class Framework(unittest.TestCase):
    def test_framework_is_required_with_no_default(self):
        for f in ("IFRS", "US_GAAP", "local"): self.assertEqual(L.require_framework(f), f)
        for bad in (None, "", "GAAP", "ifrs"):
            with self.assertRaises(L.LedgerError): L.require_framework(bad)

class Spike(unittest.TestCase):
    def test_custom_arm_results_match_expectations(self):
        from run_custom_arm import run_all
        for cid, exp, got, _ in run_all():
            self.assertEqual(got, "nothing" if exp == "not_detectable_from_data" else exp, cid)
if __name__ == "__main__": unittest.main()
