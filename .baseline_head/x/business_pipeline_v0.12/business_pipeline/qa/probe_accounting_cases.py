"""Check the accounting behaviours the acceptance suite will assert.

Read-only: prints what the frozen methods return for a handful of declared cases, so
the test writer asserts measured behaviour rather than an assumption.

Usage:  PYTHONPATH=src python qa/probe_accounting_cases.py
"""
import sys
from decimal import Decimal

sys.path.insert(0, "src")

from bp import methods  # noqa: E402

L = methods.LIBRARY


def show(title, method_id, inputs, keys=None):
    print("=" * 70)
    print(title)
    try:
        out = L[method_id].impl(inputs)
    except Exception as error:
        print("   REFUSED: %s: %s" % (type(error).__name__, error))
        return
    for key, value in out.items():
        if str(key).startswith("_"):
            continue
        if keys and key not in keys:
            continue
        print("   %-34s %s" % (key, value))


show("multi_product_breakeven (preset)", "multi_product_breakeven", {
    "fixed_costs": "6000",
    "products": [{"name": "coffee", "price": "5", "variable": "2", "mix_units": "3"},
                 {"name": "cake", "price": "6", "variable": "3", "mix_units": "1"}]})

show("working_capital (guide answer key: D=8000, S=250, H=20)", "working_capital", {
    "revenue": "200000", "cost_of_sales": "120000", "inventory": "20000",
    "receivables": "25000", "payables": "15000", "annual_demand": "8000",
    "order_cost": "250", "holding_cost_per_unit": "20", "discount_percent": "0",
    "credit_terms_days": "30", "discount_days": "10"},
    keys=["dso", "dio", "dpo", "cash_conversion_cycle", "eoq", "n_orders_per_year"])

show("loan at zero rate", "loan_amortization", {
    "principal": "1200", "annual_rate": "0", "years": "1", "payments_per_year": "12"},
    keys=["payment", "n_payments", "total_interest"])

show("loan at 9% for 5 years monthly", "loan_amortization", {
    "principal": "200000", "annual_rate": "0.09", "years": "5", "payments_per_year": "12"},
    keys=["payment", "n_payments", "total_interest", "first_interest", "first_principal"])

show("trend_analysis with a NEGATIVE first net income", "trend_analysis", {
    "years": ["2022", "2023", "2024"],
    "revenue": ["100", "120", "150"],
    "cost_of_sales": ["60", "70", "85"],
    "operating_expenses": ["20", "25", "30"],
    "net_income": ["-10", "5", "20"]})

show("trend_analysis with ZERO revenue in the base year", "trend_analysis", {
    "years": ["2022", "2023", "2024"],
    "revenue": ["0", "120", "150"],
    "cost_of_sales": ["0", "70", "85"],
    "operating_expenses": ["0", "25", "30"],
    "net_income": ["0", "5", "20"]},
    keys=["n_periods", "revenue_cagr", "revenue_growth_latest"])

show("sales_variances (guide example 5)", "sales_variances", {
    "products": [{"name": "X", "budget_units": "100", "budget_price": "10",
                  "actual_units": "120", "actual_price": "11"},
                 {"name": "Y", "budget_units": "100", "budget_price": "20",
                  "actual_units": "80", "actual_price": "18"}]})

show("breakeven with price == variable", "breakeven", {
    "fixed": "1000", "price": "10", "variable": "10"})

print()
print("eoq check:", Decimal("8000") * 0, "guide: sqrt(2*8000*250/20) =",
      (Decimal(2) * Decimal(8000) * Decimal(250) / Decimal(20)).sqrt())
