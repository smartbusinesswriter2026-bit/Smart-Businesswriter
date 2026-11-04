import sys
import os

sys.path.insert(0, os.path.join("business_pipeline_v0.12", "business_pipeline", "src"))
from bp.product import income_statement as m
from bp.product import statements as ps

print("Sales ->", m._classify_account("Sales"))
print("Cost of sales ->", m._classify_account("Cost of sales"))

one = "Sales 70,000; Cost of sales 45,000; Salaries 10,000; Rent 5,000."
two = "Compute the net income for Alder Trading for 2025." + chr(10) + one

for name, text in (("one", one), ("two", two)):
    split = ps._split_semicolon_accounts(text)
    print(name, "split ->", repr(split))
    try:
        lines, tax = m.parse_problem(split)
        print(name, "lines ->", [(l.account, l.kind, str(l.amount), l.line) for l in lines])
    except Exception as exc:
        print(name, "raised:", type(exc).__name__, exc)
