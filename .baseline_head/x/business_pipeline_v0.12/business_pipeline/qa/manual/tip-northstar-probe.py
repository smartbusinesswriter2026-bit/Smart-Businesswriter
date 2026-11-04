"""Reproduction: the owner's tip-2 reference example, run through the pipeline's own core.

What this proves
----------------
The owner's second tip ships a complete worked engagement ("Northstar") with known answers:
depreciation 12,000; insurance expense 5,500 (prepaid 500); rent expense 11,000 (prepaid 1,000);
COGS 60,000; pre-tax income 56,100; tax 14,025; **net income 42,075**; and, from the memo behind
it, **total assets 164,100** and **operating cash flow 59,600**.

This script feeds that same engagement to `bp.accounts.build` -- the frozen core's declarative
management-accounts engine -- in the shape the core expects, and prints what the core computes.
The point is not that the numbers agree; the point is *how much of the tip the pipeline already
is*, measured rather than argued.

Two of the tip's adjustments are DECLARED here, because the pipeline has no engine for them:

  * the periodic-inventory COGS closing entry (no inventory engine in `src/bp/schedules.py`);
  * the income tax accrual (taxation is deferred by B-052).

Everything else -- depreciation, both prepayments, the closing, the retained-earnings
rollforward, the two cash-flow routes and all eleven checks -- is computed by the core.

Run from the repository root:

    python qa/manual/tip-northstar-probe.py

Nothing in the repository is modified by this script.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import accounts  # noqa: E402


def acct(code, name, type_, line, section="", role="", activity="", contra=False):
    """One chart account, in the core's own vocabulary (ledger.Account)."""
    return {"code": code, "name": name, "type": type_, "line": line, "section": section,
            "role": role, "activity": activity, "contra": contra}


CHART = [
    acct("1000", "Cash", "asset", "Cash", "current", "cash", "operating"),
    acct("1100", "Trade receivables", "asset", "Trade receivables", "current", "", "operating"),
    acct("1200", "Inventory", "asset", "Inventory", "current", "", "operating"),
    acct("1300", "Prepaid insurance", "asset", "Prepayments", "current", "", "operating"),
    acct("1400", "Prepaid rent", "asset", "Prepayments", "current", "", "operating"),
    acct("1600", "Equipment", "asset", "Property, plant and equipment", "non_current", "", "investing"),
    acct("1700", "Accumulated depreciation", "asset", "Property, plant and equipment",
         "non_current", "", "investing", contra=True),
    acct("2000", "Trade payables", "liability", "Trade payables", "current", "", "operating"),
    acct("2100", "Bank loan", "liability", "Borrowings", "non_current", "", "financing"),
    acct("2200", "Income tax payable", "liability", "Accruals", "current", "", "operating"),
    acct("2300", "Accrued salaries", "liability", "Accruals", "current", "", "operating"),
    acct("3000", "Share capital", "equity", "Capital", "", "capital", "financing"),
    acct("3100", "Retained earnings", "equity", "Retained earnings", "", "retained_earnings"),
    acct("4000", "Sales revenue", "income", "Revenue", "", "", "operating"),
    acct("5000", "Cost of sales", "expense", "Cost of sales", "", "", "operating"),
    acct("6100", "Salaries and wages", "expense", "Operating expenses", "", "", "operating"),
    acct("6200", "Utilities", "expense", "Operating expenses", "", "", "operating"),
    acct("6300", "Office expenses", "expense", "Operating expenses", "", "", "operating"),
    acct("6400", "Rent expense", "expense", "Operating expenses", "", "", "operating"),
    acct("6500", "Insurance expense", "expense", "Operating expenses", "", "", "operating"),
    acct("6600", "Other operating expenses", "expense", "Operating expenses", "", "", "operating"),
    acct("6700", "Depreciation expense", "expense", "Operating expenses", "", "", "operating"),
    acct("7100", "Interest expense", "expense", "Finance costs", "", "", "operating"),
    acct("8000", "Income tax expense", "expense", "Other expenses", "", "", "operating"),
]


def je(date, desc, lines):
    return {"date": date, "description": desc, "lines": lines}


def d(code, amount):
    return {"account": code, "debit": str(amount)}


def c(code, amount):
    return {"account": code, "credit": str(amount)}


ENTRIES = [
    je("2025-01-01", "Share issuance", [d("1000", 50000), c("3000", 50000)]),
    je("2025-01-02", "Bank loan", [d("1000", 40000), c("2100", 40000)]),
    je("2025-01-03", "Equipment purchase", [d("1600", 60000), c("1000", 60000)]),
    je("2025-01-04", "Inventory purchased on credit", [d("1200", 70000), c("2000", 70000)]),
    je("2025-12-31", "Cash sales", [d("1000", 120000), c("4000", 120000)]),
    je("2025-12-31", "Credit sales", [d("1100", 80000), c("4000", 80000)]),
    je("2025-12-31", "Receivables collected", [d("1000", 65000), c("1100", 65000)]),
    je("2025-12-31", "Payables paid", [d("2000", 55000), c("1000", 55000)]),
    je("2025-12-31", "Salaries paid", [d("6100", 35000), c("1000", 35000)]),
    je("2025-12-31", "Utilities paid", [d("6200", 8000), c("1000", 8000)]),
    je("2025-12-31", "Office expenses paid", [d("6300", 5000), c("1000", 5000)]),
    je("2025-12-31", "Other operating expenses paid", [d("6600", 2000), c("1000", 2000)]),
    je("2025-12-31", "Interest paid", [d("7100", 2400), c("1000", 2400)]),
    je("2025-12-31", "Accrued salaries", [d("6100", 3000), c("2300", 3000)]),
    # DECLARED, not computed: the pipeline has no periodic-inventory COGS engine.
    je("2025-12-31", "Close inventory to cost of sales (declared)",
       [d("5000", 60000), c("1200", 60000)]),
    # DECLARED, not computed: taxation is deferred by B-052.
    je("2025-12-31", "Income tax accrual (declared)", [d("8000", 14025), c("2200", 14025)]),
]

SCHEDULES = [
    {"kind": "depreciation", "method": "straight_line", "cost": "60000", "residual": "0",
     "life": 60, "start": "2025-01", "dep_account": "6700", "accum_account": "1700",
     "description": "depreciation"},
    {"kind": "prepayment", "total": "6000", "periods": 12, "start": "2025-02", "date": "2025-01-10",
     "prepaid_account": "1300", "expense_account": "6500", "cash_account": "1000",
     "description": "prepaid insurance"},
    {"kind": "prepayment", "total": "12000", "periods": 12, "start": "2025-02", "date": "2025-01-15",
     "prepaid_account": "1400", "expense_account": "6400", "cash_account": "1000",
     "description": "prepaid rent"},
]

SPEC = {
    "period": {"start": "2025-01-01", "end": "2025-12-31"},
    "currency": "USD",
    "framework": "US_GAAP",
    "places": 2,
    "chart": CHART,
    "prior_closing": {},
    "opening": [],
    "entries": ENTRIES,
    "schedules": SCHEDULES,
}

TIP = {
    "depreciation": "12000.00",
    "insurance expense": "5500.00 (prepaid 500.00)",
    "rent expense": "11000.00 (prepaid 1000.00)",
    "COGS": "60000",
    "pre-tax income": "56100.00",
    "income tax": "14025.00",
    "net income": "42075.00",
    "total assets": "164100 (memo)",
    "operating cash flow": "59600 (memo)",
}


def main():
    errs = accounts.validate_spec(SPEC)
    print("validate_spec errors:", errs or "none")
    if errs:
        return 1

    out = accounts.build(SPEC)
    appendix = out["_appendix"]
    cash = appendix["cash_flow"]

    print("\n--- what the tip's own example says vs what the core computes ---")
    computed = {
        "depreciation": appendix["statements"].get("expenses", {}).get("Operating expenses"),
        "net income": out["net_income"],
        "total assets": out["total_assets"],
        "operating cash flow": cash["operating"],
    }
    for label, want in TIP.items():
        print(f"  {label:22} tip: {want:26} core: {computed.get(label, '(see below)')}")

    print("\n--- scalars from the core ---")
    for key in ("net_income", "total_assets", "total_liabilities", "total_equity",
                "retained_earnings_closing", "cash_net", "checks_passed", "checks_total",
                "checks_na", "n_entries", "n_flags"):
        print(f"  {key:26} {out[key]}")

    print("\n--- cash flow, two routes ---")
    for key in ("operating", "investing", "financing", "net_direct", "net_indirect"):
        print(f"  {key:26} {cash[key]}")

    print("\n--- checks ---")
    for name, ok, detail in out["_checks"]:
        print(f"  [{'ok ' if ok else 'FAIL'}] {name}: {detail}")

    print("\n--- flags (declared, never silently applied) ---")
    for flag in appendix["flags"]:
        print("  ", flag)

    print("\n--- balance sheet groups ---")
    groups = appendix["balance_sheet_groups"]
    for group, rows in groups.get("groups", {}).items():
        print("  ", group, rows)
    print("   classified:", groups.get("classified"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
