"""Reproduce the student guide's miniature engagement through the real ledger kernel.

Guide Â§1: owner invests 50,000 cash; buys 20,000 of stock on credit; sells goods for
15,000 that cost 9,000.  Expected: trial balance 85,000 a side; assets 76,000;
liabilities 20,000 + equity 50,000 + profit 6,000 = 76,000.

Usage:  PYTHONPATH=src python qa/probe_guide_miniature.py
"""
import json
import sys
from decimal import Decimal

sys.path.insert(0, "src")

from bp import accounts  # noqa: E402

SPEC = {
    "period": {"start": "2026-01-01", "end": "2026-01-31"},
    "currency": "USD",
    "framework": "local",
    "places": 2,
    "chart": [
        {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash"},
        {"code": "1100", "name": "Inventory", "type": "asset", "line": "Inventory"},
        {"code": "2000", "name": "Trade payables", "type": "liability", "line": "Payables"},
        {"code": "3000", "name": "Owner capital", "type": "equity", "line": "Capital",
         "role": "capital"},
        {"code": "3100", "name": "Retained earnings", "type": "equity",
         "line": "Retained earnings", "role": "retained_earnings"},
        {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"},
        {"code": "5000", "name": "Cost of sales", "type": "expense", "line": "Cost of sales"},
    ],
    "prior_closing": {},
    "opening": [],
    "entries": [
        {"date": "2026-01-02", "description": "owner investment",
         "lines": [{"account": "1000", "debit": "50000"}, {"account": "3000", "credit": "50000"}]},
        {"date": "2026-01-03", "description": "stock on credit",
         "lines": [{"account": "1100", "debit": "20000"}, {"account": "2000", "credit": "20000"}]},
        {"date": "2026-01-04", "description": "cash sale",
         "lines": [{"account": "1000", "debit": "15000"}, {"account": "4000", "credit": "15000"}]},
        {"date": "2026-01-04", "description": "cost of the goods sold",
         "lines": [{"account": "5000", "debit": "9000"}, {"account": "1100", "credit": "9000"}]},
    ],
    "schedules": [],
    "policy_changes": [],
}


def main():
    try:
        out = accounts.build(SPEC)
    except Exception as error:
        print("REFUSED: %s: %s" % (type(error).__name__, error))
        return
    appendix = out["_appendix"]
    print("checks:", [(name, ok) for name, ok, _ in out["_checks"]])
    statements = appendix["statements"]
    for key in sorted(statements):
        print("   %-34s %s" % (key, statements[key]))
    print("net income:", out.get("net_income"))
    trial = appendix.get("trial_balance") or {}
    print("trial balance totals:", json.dumps(
        {key: trial[key] for key in trial if "total" in key.lower()}, default=str))
    print("assets == L + E:",
          Decimal(str(statements["total_assets"])),
          Decimal(str(statements["total_liabilities"])) +
          Decimal(str(statements["equity_with_current_earnings"])))


if __name__ == "__main__":
    main()
