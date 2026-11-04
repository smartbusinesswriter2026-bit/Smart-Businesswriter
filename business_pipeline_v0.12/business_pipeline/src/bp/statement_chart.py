"""The one chart of accounts the statements tile reads with.

There were two charts, and they were not the same chart.  The model path was handed
`statement_plan.DEFAULT_CHART` - sixteen accounts with a single catch-all
`6000 Operating expenses` - while the deterministic detector path carried its own, with
Salaries, Rent and Utilities on separate lines.  So the model could not post rent to a rent
account (there was none to post to), and the deterministic path posted to five account
codes that its own chart did not contain, which failed the build with a message that named
the ledger rather than the gap.

So the chart lives here, once, and carries:

* every account code a detector template posts to (`bp.statement_detect.TEMPLATES`);
* every account the plan layer's adjustments need;
* **distinct lines for the expenses that used to collide** - Salaries, Rent, Utilities,
  Insurance, Advertising, Depreciation, Bad debts, Interest and the rest are separate
  accounts, not one "Operating expenses";
* the same line names the tile's own reader places (`bp.product.statements.RULES`), and
  the same codes, so the model path and the deterministic path print one statement.

The codes are the conventional ones the detector templates already use, so a template and
its chart always agree.  `bp.statement_detect` owns the *reading*; this module owns the
*vocabulary* it reads into.
"""

#: The chart.  Each account is the dictionary `statement_plan.account` produces, so it
#: can be handed straight to `statement_plan.validate_chart` and to the ledger.
CHART = [
    # --- assets -----------------------------------------------------------
    {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "section": "current", "role": "cash"},
    {"code": "1100", "name": "Trade receivables", "type": "asset", "line": "Trade receivables", "section": "current"},
    {"code": "1150", "name": "Accrued revenue", "type": "asset", "line": "Accrued revenue", "section": "current"},
    {"code": "1200", "name": "Inventory", "type": "asset", "line": "Inventory", "section": "current"},
    {"code": "1300", "name": "Prepayments", "type": "asset", "line": "Prepayments", "section": "current"},
    {"code": "1310", "name": "Allowance for doubtful accounts", "type": "asset",
     "line": "Trade receivables", "section": "current", "contra": True},
    {"code": "1350", "name": "Supplies", "type": "asset", "line": "Supplies", "section": "current"},
    {"code": "1500", "name": "Property, plant and equipment", "type": "asset",
     "line": "Property, plant and equipment", "section": "non_current"},
    {"code": "1700", "name": "Accumulated depreciation", "type": "asset",
     "line": "Property, plant and equipment", "section": "non_current", "contra": True},
    # --- liabilities ------------------------------------------------------
    {"code": "2000", "name": "Trade payables", "type": "liability", "line": "Trade payables", "section": "current"},
    {"code": "2100", "name": "Borrowings", "type": "liability", "line": "Borrowings", "section": "non_current"},
    {"code": "2200", "name": "Tax payable", "type": "liability", "line": "Accruals", "section": "current"},
    {"code": "2300", "name": "Accrued expenses", "type": "liability", "line": "Accruals", "section": "current"},
    {"code": "2400", "name": "Unearned revenue", "type": "liability", "line": "Unearned revenue", "section": "current"},
    {"code": "2500", "name": "Warranty provision", "type": "liability", "line": "Accruals", "section": "current"},
    # --- equity -----------------------------------------------------------
    {"code": "3000", "name": "Capital", "type": "equity", "line": "Capital", "section": "", "role": "capital"},
    {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings",
     "section": "", "role": "retained_earnings"},
    {"code": "3200", "name": "Dividends", "type": "equity", "line": "Dividends", "section": "",
     "role": "dividends", "contra": True},
    # --- income -----------------------------------------------------------
    {"code": "4000", "name": "Revenue", "type": "income", "line": "Revenue", "section": ""},
    {"code": "4050", "name": "Other income", "type": "income", "line": "Other income", "section": ""},
    {"code": "4100", "name": "Sales returns", "type": "income", "line": "Sales returns", "section": "", "contra": True},
    {"code": "4200", "name": "Sales discounts", "type": "income", "line": "Sales discounts", "section": "", "contra": True},
    # --- expenses ---------------------------------------------------------
    {"code": "5000", "name": "Cost of sales", "type": "expense", "line": "Cost of sales", "section": ""},
    {"code": "5100", "name": "Operating expenses", "type": "expense", "line": "Operating expenses", "section": ""},
    {"code": "5200", "name": "Finance costs", "type": "expense", "line": "Finance costs", "section": ""},
    {"code": "5300", "name": "Other expenses", "type": "expense", "line": "Other expenses", "section": ""},
    {"code": "6010", "name": "Telephone expense", "type": "expense", "line": "Telephone expense", "section": ""},
    {"code": "6020", "name": "Transport expense", "type": "expense", "line": "Transport expense", "section": ""},
    {"code": "6030", "name": "Repairs expense", "type": "expense", "line": "Repairs expense", "section": ""},
    {"code": "6040", "name": "Stationery expense", "type": "expense", "line": "Stationery expense", "section": ""},
    {"code": "6050", "name": "Fuel expense", "type": "expense", "line": "Fuel expense", "section": ""},
    {"code": "6060", "name": "Travel expense", "type": "expense", "line": "Travel expense", "section": ""},
    {"code": "6100", "name": "Salaries expense", "type": "expense", "line": "Salaries expense", "section": ""},
    {"code": "6200", "name": "Rent expense", "type": "expense", "line": "Rent expense", "section": ""},
    {"code": "6250", "name": "Utilities expense", "type": "expense", "line": "Utilities expense", "section": ""},
    {"code": "6300", "name": "Insurance expense", "type": "expense", "line": "Insurance expense", "section": ""},
    {"code": "6350", "name": "Advertising expense", "type": "expense", "line": "Advertising expense", "section": ""},
    {"code": "6400", "name": "Depreciation", "type": "expense", "line": "Depreciation", "section": ""},
    {"code": "6500", "name": "Bad debts", "type": "expense", "line": "Bad debts", "section": ""},
    {"code": "6600", "name": "General expenses", "type": "expense", "line": "General expenses", "section": ""},
    #: The detector layer posts accruals, bad debts and straight-line depreciation to this
    #: one code, so the line says so rather than pretending to be a single expense.
    {"code": "6700", "name": "Accruals, provisions and depreciation", "type": "expense",
     "line": "Accruals, provisions and depreciation", "section": ""},
    {"code": "6800", "name": "Warranty expense", "type": "expense", "line": "Warranty expense", "section": ""},
    {"code": "6900", "name": "Freight out", "type": "expense", "line": "Freight out", "section": ""},
    {"code": "7100", "name": "Interest expense", "type": "expense", "line": "Interest expense", "section": ""},
    {"code": "8000", "name": "Tax", "type": "expense", "line": "Tax", "section": ""},
]


def codes():
    """Every account code the chart carries."""
    return {account["code"] for account in CHART}
