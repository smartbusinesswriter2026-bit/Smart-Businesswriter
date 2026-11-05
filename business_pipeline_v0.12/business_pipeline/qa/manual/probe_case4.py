import sys
sys.path.insert(0, "src")
from bp.product import statements as S

ADJ = ("Data — unadjusted trial balance: Cash 10,000 Dr; AR 20,000 Dr; Supplies 3,000 Dr; "
       "Equipment 40,000 Dr; Accumulated depreciation 8,000 Cr; AP 12,000 Cr; Unearned revenue 5,000 Cr; "
       "Common stock 30,000 Cr; Retained earnings 6,000 Cr; Service revenue 45,000 Cr; "
       "Salaries expense 28,000 Dr; Rent expense 5,000 Dr.\n"
       "Adjustments: Supplies on hand 1,000; depreciation 4,000; unearned revenue earned 3,000; "
       "accrued salaries 2,000.\n"
       "Required: Journalize adjustments and create adjusted income statement and balance sheet.")

EQ = ("Data: Beginning common stock 100,000; beginning retained earnings 40,000; common stock issued 30,000; "
      "net income 25,000; dividends declared/paid 10,000; no other comprehensive income.\n"
      "Required: Create a statement of changes in equity.")

text = S._split_semicolon_accounts(ADJ)
print("---- after split ----")
print(text[:1200])
print("---- classify ----")
try:
    print(S.classify(text))
except Exception as e:
    print("ERR", e)
print("---- parse_rows ----")
rows, skipped = S.parse_rows(text)
for r in rows:
    print("  ROW", r["label"], "=", r["written"], "side", r["side"])
for s in skipped:
    print("  SKIP", s[:80])
print("---- preflight ----")
try:
    S.preflight(text)
    print("ok")
except Exception as e:
    print("ERR", type(e).__name__, e)
print("---- EQ detect ----")
for n, fn in (("is", S.detect_income_statement), ("gb", S.detect_given_balances),
              ("ratio", S.detect_ratio_analysis), ("eps", S.detect_eps)):
    print(" ", n, bool(fn(EQ)))
rows, skipped = S.parse_rows(S._split_semicolon_accounts(EQ))
print("  rows:", [(r["label"], r["written"], r["placed"]["placement"]["line"]) for r in rows])
print("  skipped:", skipped)
