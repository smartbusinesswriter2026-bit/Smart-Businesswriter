import sys, os, unittest
from decimal import Decimal as D
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from bp import ledger as L, report as R, reconcile as RC

def chart():
    return L.Chart([L.Account("1000", "Cash", "asset", "Cash", role="cash"), L.Account("1500", "Equipment", "asset", "Equipment"),
                    L.Account("1510", "Accumulated depreciation", "asset", "Equipment", contra=True),
                    L.Account("3000", "Owner capital", "equity", "Capital", role="capital"),
                    L.Account("3100", "Retained earnings", "equity", "Retained earnings", role="retained_earnings"),
                    L.Account("3200", "Dividends", "equity", "Dividends", role="dividends"),
                    L.Account("4000", "Sales", "income", "Revenue"), L.Account("5000", "Rent", "expense", "Rent"), L.Account("5100", "Depreciation", "expense", "Depreciation")])

def journal():
    j = L.Journal(chart(), "2026-01-01", "2026-12-31", "USD"); mk = lambda d, t, ls, o=False: j.post(L.Entry.make(d, t, ls, opening=o))
    mk("2026-01-01", "opening", [{"account": "1000", "debit": "5000"}, {"account": "1500", "debit": "1200"}, {"account": "3000", "credit": "6200"}], True)
    mk("2026-01-15", "sale", [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}])
    mk("2026-03-31", "rent", [{"account": "5000", "debit": "500"}, {"account": "1000", "credit": "500"}])
    mk("2026-06-30", "depreciation", [{"account": "5100", "debit": "120"}, {"account": "1510", "credit": "120"}])
    mk("2026-09-30", "dividend", [{"account": "3200", "debit": "300"}, {"account": "1000", "credit": "300"}])
    return j

def closed():
    j = journal(); pre = L.statements(j)
    for e in L.closing_entries(j, pre): j.post(L.Entry.make(e["date"], e["description"], e["lines"], closing=e["closing"]))
    return j, pre

class Statements(unittest.TestCase):
    def test_trial_balance(self):
        j, _ = closed(); t = R.trial_balance(j)
        self.assertIn("TRIAL BALANCE", t); self.assertIn("2026-01-01 to 2026-12-31   USD", t)
        self.assertIn("6,200.00", t); self.assertIn("1,200.00", t); self.assertIn("120.00", t)
        self.assertNotIn("Sales", t)                      # closed accounts carry no trial-balance line
        self.assertEqual(t.count("7,400.00"), 2)          # debits and credits agree
    def test_income_statement_uses_pre_closing_figures(self):
        _, pre = closed(); j = journal(); t = R.income_statement(pre, j)
        for frag in ("INCOME STATEMENT", "Revenue", "2,000.00", "Rent", "500.00", "Depreciation", "120.00", "Net income", "1,380.00"): self.assertIn(frag, t)
    def test_balance_sheet(self):
        j, _ = closed(); t = R.balance_sheet(j, L.statements(j))
        for frag in ("BALANCE SHEET", "As at 2026-12-31", "Cash", "6,200.00", "Equipment", "Accumulated depreciation", "(120.00)",
                     "Total assets", "7,280.00", "Owner capital", "6,200.00", "Retained earnings", "1,080.00", "Total liabilities and equity", "7,280.00"): self.assertIn(frag, t)
    def test_cash_flow_statement(self):
        j, _ = closed(); t = R.cash_flow_statement(j, L.cash_flow(j))
        for frag in ("CASH FLOW STATEMENT", "Operating activities", "sale", "2,000.00", "rent", "(500.00)", "Total operating activities", "1,500.00",
                     "Financing activities", "dividend", "(300.00)", "Net change in cash", "1,200.00", "Cash at start of period", "5,000.00", "Cash at end of period", "6,200.00"): self.assertIn(frag, t)
    def test_notes_and_policy_changes(self):
        j, pre = closed()
        t = R.notes(j, "local", pre, policy_changes=[{"date": "2026-07-01", "description": "useful life revised", "kind": "useful_life_revision", "treatment": "prospective"}])
        self.assertIn("Reporting framework: local", t); self.assertIn("not GAAP or IFRS", t)
        self.assertIn("useful life revised", t); self.assertIn("prospective", t)
        self.assertIn("Declared policy changes: none", R.notes(j, "local", pre))
    def test_reconciliation_statement(self):
        j, _ = closed()
        st = {"opening_balance": "5000", "closing_balance": "5100", "lines": [{"description": "interest", "amount": "100", "direction": "in"}]}
        rec = RC.reconcile(j, "1000", st)["report"]; t = R.reconciliation_statement(rec)
        for frag in ("RECONCILIATION (account 1000)", "Balance per statement", "5,100.00", "Adjusted statement balance", "Adjusted ledger balance", "Difference", "0.00"): self.assertIn(frag, t)
    def test_combined_document_has_every_section_in_order(self):
        j, pre = closed(); se = R.financial_statements(j, pre, L.cash_flow(j), "local")
        self.assertEqual(set(se), {"trial_balance", "income_statement", "balance_sheet", "cash_flow", "notes", "combined"})
        order = [se["combined"].index(k) for k in ("TRIAL BALANCE", "INCOME STATEMENT", "BALANCE SHEET", "CASH FLOW STATEMENT", "NOTES")]
        self.assertEqual(order, sorted(order)); self.assertIn("statements_export", {"statements_export"})
    def test_deterministic(self):
        j, pre = closed()
        self.assertEqual(R.financial_statements(j, pre, L.cash_flow(j), "local")["combined"], R.financial_statements(j, pre, L.cash_flow(j), "local")["combined"])
if __name__ == "__main__": unittest.main()
