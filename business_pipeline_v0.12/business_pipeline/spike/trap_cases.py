"""Neutral trap cases for the Stage 8 ledger-engine spike (manual 9.2 and section 14). Plain data: any arm (custom kernel, Beancount, ...) can run them.
Each case says what should be detected; 'how' differs by arm (rejected at entry, flagged, invariant) and is recorded in the results table."""
CHART = [
    {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash"}, {"code": "1500", "name": "Equipment", "type": "asset", "line": "Equipment"},
    {"code": "1510", "name": "Accumulated depreciation", "type": "asset", "line": "Equipment", "contra": True},
    {"code": "2000", "name": "Loan", "type": "liability", "line": "Loans"}, {"code": "3000", "name": "Owner capital", "type": "equity", "line": "Capital", "role": "capital"},
    {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"}, {"code": "3200", "name": "Dividends", "type": "equity", "line": "Dividends", "role": "dividends"},
    {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"}, {"code": "5000", "name": "Rent", "type": "expense", "line": "Rent"}, {"code": "5100", "name": "Depreciation", "type": "expense", "line": "Depreciation"}]
OPEN = {"date": "2026-01-01", "description": "opening", "opening": True, "lines": [{"account": "1000", "debit": "5000"}, {"account": "1500", "debit": "3000"}, {"account": "3000", "credit": "7000"}, {"account": "3100", "credit": "1000"}]}
def e(date, desc, *lines): return {"date": date, "description": desc, "lines": [dict(account=a, **{k: v}) for a, k, v in lines]}
RENT = lambda m, d: e(f"2026-{m}-{d}", "rent", ("5000", "debit", "500"), ("1000", "credit", "500"))
SALE = e("2026-01-15", "sale", ("1000", "debit", "2000"), ("4000", "credit", "2000"))
PERIOD = ("2026-01-01", "2026-04-30")

CASES = [
 {"id": "clean_baseline", "what": "A correct journal: nothing should be reported", "entries": [OPEN, SALE, RENT("01", "31"), RENT("02", "28"), RENT("03", "31"), RENT("04", "30")], "expect": "nothing"},
 {"id": "unbalanced_entry", "what": "An entry whose debits and credits differ", "entries": [OPEN, e("2026-01-20", "bad", ("1000", "debit", "100"), ("4000", "credit", "90"))], "expect": "rejected_at_entry"},
 {"id": "float_amount", "what": "A binary-float amount", "entries": [OPEN, e("2026-01-20", "float", ("1000", "debit", 0.1), ("4000", "credit", 0.1))], "expect": "rejected_at_entry"},
 {"id": "silent_rounding", "what": "Three decimal places in a two-decimal currency", "entries": [OPEN, e("2026-01-20", "precise", ("1000", "debit", "10.005"), ("4000", "credit", "10.005"))], "expect": "rejected_at_entry"},
 {"id": "unknown_account", "what": "A line posted to an account that does not exist", "entries": [OPEN, e("2026-01-20", "typo", ("1001", "debit", "10"), ("4000", "credit", "10"))], "expect": "rejected_at_entry"},
 {"id": "date_outside_period", "what": "An entry dated after the period end", "entries": [OPEN, e("2026-06-01", "late", ("1000", "debit", "10"), ("4000", "credit", "10"))], "expect": "rejected_at_entry"},
 {"id": "flipped_sign_expense", "what": "Rent credited and cash debited: balanced, but the sign is wrong", "entries": [OPEN, SALE, e("2026-01-31", "rent reversed", ("1000", "debit", "500"), ("5000", "credit", "500"))], "expect": "flag"},
 {"id": "misclassified_contra", "what": "Accumulated depreciation set up as an ordinary asset", "chart_change": {"1510": {"contra": False}}, "entries": [OPEN, e("2026-03-31", "dep", ("5100", "debit", "100"), ("1510", "credit", "100"))], "expect": "flag"},
 {"id": "missing_accrual", "what": "Rent recorded monthly but absent in the last month", "entries": [OPEN, SALE, RENT("01", "31"), RENT("02", "28"), RENT("03", "31"), e("2026-04-30", "sale", ("1000", "debit", "50"), ("4000", "credit", "50"))], "expect": "flag"},
 {"id": "opening_not_prior_closing", "what": "Opening balances differ from the prior period's closing balances", "entries": [OPEN], "prior_closing": {"1000": "5100", "1500": "3000", "3000": "7000", "3100": "1000"}, "expect": "invariant"},
 {"id": "tampered_journal", "what": "An entry edited after posting", "entries": [OPEN, SALE], "tamper": True, "expect": "invariant"},
 {"id": "mid_year_policy_change", "what": "Depreciation method changed mid-year without disclosure", "entries": [OPEN, e("2026-02-28", "dep straight line", ("5100", "debit", "100"), ("1510", "credit", "100")), e("2026-04-30", "dep new method", ("5100", "debit", "250"), ("1510", "credit", "250"))], "expect": "not_detectable_from_data", "note": "Needs a declared policy-change input; no arm can infer it from the journal alone."},
]
