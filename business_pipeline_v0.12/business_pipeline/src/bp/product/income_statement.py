"""Multi-step income statement computation engine.

Handles problems where accounts and amounts are given directly (not as transactions
or a trial balance), and the income statement must be computed line by line:

    Net Sales        = Sales Revenue − Sales Returns − Sales Discounts
    Gross Profit     = Net Sales − COGS
    Operating Income = Gross Profit − Operating Expenses
    Income Before Tax= Operating Income ± Non-operating items
    Net Income       = Income Before Tax − Income Tax

Tax rate is read from the problem text (e.g. "25% of pretax income"). Non-operating
items (gains on sale, interest expense) flow below operating income. This is the
multi-step format — single-step would just be all revenues minus all expenses.

Nothing here composes journal entries or posts to the ledger; it computes figures
directly from the declared problem data. Every figure is traceable to its source
line in the instruction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


MONEY = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


#: Detectors for multi-step income statement problems.
INCOME_STATEMENT_DETECTORS = [
    (r"multi.step\s+income\s+statement", "multi_step"),
    (r"income\s+statement\s+components", "multi_step"),
]


def detect_income_statement(text: str) -> bool:
    """Return True if the problem reads as a multi-step income statement computation."""
    low = text.lower()
    for pattern, _ in INCOME_STATEMENT_DETECTORS:
        if re.search(pattern, low):
            return True
    return False


#: Detectors for ratio analysis / balance sheet analysis problems.
RATIO_DETECTORS = [
    (r"current\s+ratio", "ratio"),
    (r"working\s+capital", "ratio"),
    (r"current\s+assets", "ratio"),
    (r"current\s+liabilities", "ratio"),
    (r"liquidity", "ratio"),
    (r"balance\s+sheet\s+analysis", "ratio"),
]


def detect_ratio_analysis(text: str) -> bool:
    """Return True if the problem reads as a ratio analysis / balance sheet analysis."""
    low = text.lower()
    for pattern, _ in RATIO_DETECTORS:
        if re.search(pattern, low):
            return True
    return False


@dataclass
class AccountLine:
    """One parsed line from the problem: account name, raw amount, classification."""
    account: str
    amount: Decimal
    kind: str  # revenue | contra_revenue | cogs | operating_expense |
               # non_operating_revenue | non_operating_expense | tax_rate |
               # current_asset | current_liability | non_current_asset | non_current_liability
    line: str  # presentation line name


@dataclass
class IncomeStatementResult:
    """Computed multi-step income statement."""
    gross_revenue: Decimal
    contra_revenue: Decimal
    net_sales: Decimal
    cogs: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    operating_income: Decimal
    non_operating_revenue: Decimal
    non_operating_expense: Decimal
    income_before_tax: Decimal
    tax_rate: Decimal
    income_tax: Decimal
    net_income: Decimal
    gross_margin_percent: Decimal  # gross profit / net sales
    lines: List[Dict[str, Any]]  # rendered lines for presentation


@dataclass
class BalanceSheetResult:
    """Computed balance sheet analysis (ratio analysis)."""
    current_assets: Decimal
    current_liabilities: Decimal
    working_capital: Decimal
    current_ratio: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    lines: List[Dict[str, Any]]  # rendered lines for presentation


@dataclass
class EPSResult:
    """Computed EPS result."""
    profit_from_continuing_operations: Decimal
    loss_from_discontinued_operations: Decimal
    profit_for_the_year: Decimal
    preference_dividends: Decimal
    numerator_basic: Decimal
    weighted_average_shares: Decimal
    basic_eps: Decimal
    numerator_diluted: Decimal
    diluted_shares: Decimal
    diluted_eps: Decimal
    lines: List[Dict[str, Any]]  # rendered lines for presentation


#: Detectors for multi-step income statement problems.
INCOME_STATEMENT_DETECTORS = [
    (r"multi.step\s+income\s+statement", "multi_step"),
    (r"income\s+statement\s+components", "multi_step"),
]

#: Detectors for ratio analysis / balance sheet analysis problems.
RATIO_DETECTORS = [
    (r"current\s+ratio", "ratio"),
    (r"working\s+capital", "ratio"),
    (r"current\s+assets", "ratio"),
    (r"current\s+liabilities", "ratio"),
    (r"liquidity", "ratio"),
    (r"balance\s+sheet\s+analysis", "ratio"),
]

#: Detectors for "given account balances" problems — a list of accounts with
#: amounts where the task is to compute a statement from them. Fires when
#: the text contains multiple known account names with amounts.
GIVEN_BALANCES_DETECTORS = [
    (r"\brevenue\s+\$?[\d,]", "given_balances"),
    (r"\bcost of (sales|goods sold)\s+\$?[\d,]", "given_balances"),
    (r"\b(distribution|administrative|operating)\s+expenses?\s+\$?[\d,]", "given_balances"),
    (r"\b(interest|depreciation|amortization|impairment)\s+(expense|loss)\s+\$?[\d,]", "given_balances"),
    (r"\b(gain|loss)\s+on\s+sale\s+\$?[\d,]", "given_balances"),
    (r"\b(cash|accounts? receivable|inventory|supplies|equipment|land|building)\s+\$?[\d,]", "given_balances"),
    (r"\b(accounts? payable|notes? payable|loan|borrowings)\s+\$?[\d,]", "given_balances"),
    (r"\b(unearned|deferred)\s+revenue\s+\$?[\d,]", "given_balances"),
    (r"\b(common stock|share capital|retained earnings|dividends)\s+\$?[\d,]", "given_balances"),
]


def detect_owner_equity(text: str) -> bool:
    """A given-balances problem that must derive a missing owner's capital.

    It lists assets, liabilities and income/expense accounts, and either names drawings or
    capital (or says no additional capital was contributed) — the capital account is the plug
    that makes the accounting equation hold.  A problem with no income/expense account and no
    drawings/capital word is a plain balance sheet analysis, not this.
    """
    if not detect_given_balances(text):
        return False
    low = text.lower()
    if not re.search(r"drawings|capital|owner", low):
        return False
    # Need at least one asset and one liability or income/expense account to be a statement problem.
    lines, _ = parse_problem(text) if False else ([], Decimal("0"))
    return True
    """Return True if the problem lists multiple account balances with amounts."""
    low = text.lower()
    matches = 0
    for pattern, _ in GIVEN_BALANCES_DETECTORS:
        if re.search(pattern, low):
            matches += 1
    return matches >= 2  # Need at least 2 account types to be a "given balances" problem


def _money(text: str) -> Optional[Decimal]:
    if text is None:
        return None
    cleaned = text.replace(",", "").replace("$", "").strip()
    cleaned = cleaned.strip("()")
    try:
        d = Decimal(cleaned)
    except Exception:
        return None
    if not d.is_finite():
        return None
    return d


def _extract_tax_rate(text: str) -> Decimal:
    """Extract the tax rate from problem text (e.g. '25% of pretax income')."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s+pre.?tax\s+income", text, re.I)
    if match:
        return Decimal(match.group(1)) / Decimal(100)
    match = re.search(r"tax.*?(\d+(?:\.\d+)?)%", text, re.I)
    if match:
        return Decimal(match.group(1)) / Decimal(100)
    return Decimal("0")


def _classify_account(account: str) -> Tuple[str, str]:
    """Classify an account name into (kind, line).

    kind: revenue | contra_revenue | cogs | operating_expense |
          non_operating_revenue | non_operating_expense | tax_rate
    line: presentation line name
    """
    a = account.strip().lower()

    # Contra-revenue (subtract from gross sales)
    if re.search(r"sales\s+(returns|allowances)", a) or re.search(r"sales\s+discounts?", a):
        return ("contra_revenue", "Sales Returns & Allowances")

    # Revenue
    if re.search(r"^(sales|turnover|fees earned)$", a):
        return ("revenue", "Sales Revenue")
    if re.search(r"revenue$", a) and not re.search(r"unearned\s+revenue", a):
        return ("revenue", "Sales Revenue")

    # COGS
    if re.search(r"^(purchases?|cost of (sales|goods sold)|cogs)$", a):
        return ("cogs", "Cost of Goods Sold")
    # Inventory components for COGS computation
    if re.search(r"^(beginning inventory|opening inventory|beginning stock)$", a):
        return ("beginning_inventory", "Beginning Inventory")
    if re.search(r"^(purchase returns?|returns? outwards|purchase returns and allowances)$", a):
        return ("purchase_returns", "Purchase Returns")
    if re.search(r"^(freight[- ]?in|carriage inwards?|freight on purchases)$", a):
        return ("freight_in", "Freight-In")
    if re.search(r"^(ending inventory|closing inventory|ending stock)$", a):
        return ("ending_inventory", "Ending Inventory")

    # Operating expenses
    if re.search(r"^(rent|salaries|salary|wages|utilities|insurance|advertising|marketing|depreciation|bad debts?|general expenses|operating expenses|telephone|transport|repairs|stationery|fuel|travel)$", a):
        return ("operating_expense", "Operating Expenses")

    # Non-operating revenue / gains
    if re.search(r"\bgain\s+on\s+sale", a) or re.search(r"\bgain\b", a):
        return ("non_operating_revenue", "Gain on Sale of Equipment")

    # Non-operating expense
    if re.search(r"^(interest (expense|paid)|finance costs?)$", a):
        return ("non_operating_expense", "Interest Expense")

    # Balance sheet: current assets
    if re.search(r"^(cash|bank|cash at bank|bank account)$", a):
        return ("current_asset", "Cash")
    if re.search(r"^(trade receivables?|receivables?|accounts? receivable|sundry debtors|a/?r)$", a):
        return ("current_asset", "Accounts Receivable")
    if re.search(r"^(contract asset)$", a):
        return ("current_asset", "Contract Asset")
    if re.search(r"^(inventor(y|ies)|stock|closing stock)$", a):
        return ("current_asset", "Inventory")
    if re.search(r"^(prepaid\s+expenses?|prepaids?)$", a):
        return ("current_asset", "Prepaid Expenses")
    # Contra-asset (netted against its asset)
    if re.search(r"accumulated depreciation", a):
        return ("contra_asset", "Accumulated depreciation")
    # Balance sheet: non-current assets
    if re.search(r"^(equipment|vehicles?|machinery|furniture|land|buildings?|plant|office equipment|freehold property)$", a) and not re.search(r"accumulated", a):
        return ("non_current_asset", "Property, plant and equipment")
    if re.search(r"^(deferred tax asset)$", a):
        return ("non_current_asset", "Deferred Tax Asset")
    # Balance sheet: current liabilities
    if re.search(r"^(trade payables?|payables?|creditors?|accounts? payable|sundry creditors|a/?p)$", a):
        return ("current_liability", "Accounts Payable")
    if re.search(r"^(contract liability)$", a):
        return ("current_liability", "Contract Liability")
    if re.search(r"^(accrued (expenses?|liabilities?|liability)|accruals?)$", a):
        return ("current_liability", "Accrued Liabilities")
    if re.search(r"^(bank overdraft)$", a):
        return ("current_liability", "Bank Overdraft")
    if re.search(r"^(short.term notes? payable)$", a):
        return ("current_liability", "Short-term Notes Payable")
    if re.search(r"^(warranty provision|warranty liability)$", a):
        return ("current_liability", "Warranty Provision")
    if re.search(r"^(lease liability)$", a):
        return ("current_liability", "Lease Liability (current)")
    # Balance sheet: non-current liabilities
    if re.search(r"^(bank loan|loan|borrowings?|notes? payable)$", a):
        return ("non_current_liability", "Bank loan")
    if re.search(r"^(long.term (debt|notes? payable)|long.term debt|long.term loan)$", a):
        return ("non_current_liability", "Long-term Debt")
    if re.search(r"^(deferred tax liability)$", a):
        return ("non_current_liability", "Deferred Tax Liability")
    if re.search(r"^(lease liability)$", a):
        return ("non_current_liability", "Lease Liability (non-current)")
    # Balance sheet: equity
    if re.search(r"^(drawings?|owner'?s? drawings?|withdrawals?)$", a):
        return ("drawings", "Drawings")
    if re.search(r"^(capital|owner'?s? capital|beginning capital|owner'?s? equity)$", a):
        return ("equity", "Capital")
    if re.search(r"^(common stock|share capital|capital stock|share premium)$", a):
        return ("equity", "Share Capital")
    if re.search(r"^(treasury shares?|treasury stock)$", a):
        return ("equity", "Treasury Shares")
    if re.search(r"^(retained earnings?|accumulated (profit|earnings)|revenue reserve|revaluation reserve|translation reserve)$", a):
        return ("equity", "Retained Earnings")

    # Stated totals: a problem may give "Current assets 50,000" or "Total liabilities 90,000"
    # with no components.  They are recognised so the analysis can use them when the components
    # are absent, and never double-count when both are present.
    if re.search(r"^(total )?current assets?$", a):
        return ("total_current_assets", "Current Assets")
    if re.search(r"^(total )?current liabilities?$", a):
        return ("total_current_liabilities", "Current Liabilities")
    if re.search(r"^(total )?assets$", a):
        return ("total_assets", "Total Assets")
    if re.search(r"^(total )?liabilities$", a):
        return ("total_liabilities", "Total Liabilities")
    if re.search(r"^(total )?(equity|shareholders?'? funds?|capital employed)$", a):
        return ("total_equity", "Total Equity")

    # Tax rate — only if explicitly a tax account
    if re.search(r"\btax\b", a):
        return ("tax_rate", "Income Tax Expense")

    # Generic expense fallback
    if re.search(r"\b(expenses?|costs?)\b", a):
        return ("operating_expense", "Operating Expenses")

    return ("unknown", account)


def parse_problem(text: str) -> Tuple[List[AccountLine], Decimal]:
    """Parse a multi-step income statement problem into account lines and tax rate.

    Returns (account_lines, tax_rate).  Raises ValueError if no parseable accounts.
    """
    lines: List[AccountLine] = []
    tax_rate = _extract_tax_rate(text)

    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        found = list(MONEY.finditer(line))
        if not found:
            continue
        last = found[-1]
        amount_str = last.group(0)
        amount = _money(amount_str)
        if amount is None:
            continue
        label = re.sub(r"\b(dr|cr)\.?\b", " ", re.sub(r"\.{2,}", " ", line[:last.start()]), flags=re.I)
        label = re.sub(r"\b(dr|cr)\.?\b", " ", label, flags=re.I)
        label = re.sub(r"[\t$]", " ", label)
        # Skip tax-rate lines (they carry a % figure, not an account balance)
        if re.search(r"\btax\b", label, re.I) and re.search(r"\d+%", label):
            continue
        # Strip parenthetical qualifiers (e.g. "(Jan 1)") before matching
        label = re.sub(r"\s*\(.*", "", label)
        label = re.sub(r"\s+", " ", label).strip(" .,:-|()[]")
        if not label:
            continue
        kind, line_name = _classify_account(label)
        if kind == "unknown" or kind == "tax_rate":
            continue
        lines.append(AccountLine(
            account=label, amount=amount, kind=kind, line=line_name,
        ))

    if not lines:
        raise ValueError("no parseable account lines in the problem text")

    return lines, tax_rate


def compute_income_statement(lines: List[AccountLine], tax_rate: Decimal) -> IncomeStatementResult:
    """Compute the multi-step income statement from parsed account lines."""
    revenue = Decimal("0")
    contra_revenue = Decimal("0")
    cogs = Decimal("0")
    operating_expenses = Decimal("0")
    non_operating_revenue = Decimal("0")
    non_operating_expense = Decimal("0")
    beginning_inventory = Decimal("0")
    purchases = Decimal("0")
    purchase_returns = Decimal("0")
    freight_in = Decimal("0")
    ending_inventory = Decimal("0")

    # First pass: detect if inventory data is present
    has_inventory_data = any(l.kind in ("beginning_inventory", "purchase_returns",
                                       "freight_in", "ending_inventory") for l in lines)

    for line in lines:
        if line.kind == "revenue":
            revenue += line.amount
        elif line.kind == "contra_revenue":
            contra_revenue += line.amount
        elif line.kind == "cogs":
            if has_inventory_data:
                # "purchases" classified as cogs; treat as purchases component
                purchases += line.amount
            else:
                cogs += line.amount
        elif line.kind == "operating_expense":
            operating_expenses += line.amount
        elif line.kind == "non_operating_revenue":
            non_operating_revenue += line.amount
        elif line.kind == "non_operating_expense":
            non_operating_expense += line.amount
        elif line.kind == "beginning_inventory":
            beginning_inventory += line.amount
        elif line.kind == "purchases":
            purchases += line.amount
        elif line.kind == "purchase_returns":
            purchase_returns += line.amount
        elif line.kind == "freight_in":
            freight_in += line.amount
        elif line.kind == "ending_inventory":
            ending_inventory += line.amount

    # If inventory data is present, compute COGS from it
    if has_inventory_data:
        cogs = beginning_inventory + purchases - purchase_returns + freight_in - ending_inventory

    net_sales = revenue - contra_revenue
    gross_profit = net_sales - cogs
    operating_income = gross_profit - operating_expenses
    income_before_tax = operating_income + non_operating_revenue - non_operating_expense
    income_tax = income_before_tax * tax_rate if income_before_tax > 0 else Decimal("0")
    net_income = income_before_tax - income_tax

    # Build rendered lines
    rendered: List[Dict[str, Any]] = []

    # Revenue section
    rendered.append({"label": "Sales Revenue", "kind": "revenue", "amount": revenue, "indent": 0})
    if contra_revenue > 0:
        rendered.append({"label": "Less: Sales Returns & Allowances", "kind": "contra_revenue",
                        "amount": contra_revenue, "indent": 1})
    rendered.append({"label": "Net Sales", "kind": "subtotal", "amount": net_sales, "indent": 0})

    # COGS
    rendered.append({"label": "Less: Cost of Goods Sold", "kind": "cogs", "amount": cogs, "indent": 1})
    rendered.append({"label": "Gross Profit", "kind": "subtotal", "amount": gross_profit, "indent": 0})

    # Operating expenses
    rendered.append({"label": "Less: Operating Expenses", "kind": "heading", "amount": Decimal("0"), "indent": 0})
    for line in lines:
        if line.kind == "operating_expense":
            rendered.append({"label": "  " + line.account.title(), "kind": "operating_expense",
                           "amount": line.amount, "indent": 1})
    rendered.append({"label": "Total Operating Expenses", "kind": "subtotal",
                    "amount": operating_expenses, "indent": 1})
    rendered.append({"label": "Operating Income", "kind": "subtotal",
                    "amount": operating_income, "indent": 0})

    # Non-operating items
    if non_operating_revenue > 0:
        rendered.append({"label": "Add: Gain on Sale of Equipment", "kind": "non_operating_revenue",
                        "amount": non_operating_revenue, "indent": 1})
    if non_operating_expense > 0:
        rendered.append({"label": "Less: Interest Expense", "kind": "non_operating_expense",
                        "amount": non_operating_expense, "indent": 1})
    rendered.append({"label": "Income Before Income Tax", "kind": "subtotal",
                    "amount": income_before_tax, "indent": 0})
    rendered.append({"label": "Less: Income Tax Expense", "kind": "tax",
                    "amount": income_tax, "indent": 1})
    rendered.append({"label": "Net Income", "kind": "total", "amount": net_income, "indent": 0})

    return IncomeStatementResult(
        gross_revenue=revenue,
        contra_revenue=contra_revenue,
        net_sales=net_sales,
        cogs=cogs,
        gross_profit=gross_profit,
        operating_expenses=operating_expenses,
        operating_income=operating_income,
        non_operating_revenue=non_operating_revenue,
        non_operating_expense=non_operating_expense,
        income_before_tax=income_before_tax,
        tax_rate=tax_rate,
        income_tax=income_tax,
        net_income=net_income,
        gross_margin_percent=(gross_profit / net_sales * 100) if net_sales else Decimal("0"),
        lines=rendered,
    )


def render_income_statement(result: IncomeStatementResult, period: str, currency: str = "USD") -> str:
    """Render the multi-step income statement as text."""
    out = ["INCOME STATEMENT", f"For the Year Ended {period}", f"   {currency}", ""]

    # Revenue section
    out.append(f"Sales Revenue                                             {result.gross_revenue:>12,.2f}")
    if result.contra_revenue > 0:
        out.append(f"  Less: Sales Returns & Allowances                          {result.contra_revenue:>12,.2f}")
    out.append(f"Net Sales                                                 {result.net_sales:>12,.2f}")
    out.append("")

    # COGS
    out.append(f"Less: Cost of Goods Sold                                    {result.cogs:>12,.2f}")
    out.append(f"Gross Profit                                              {result.gross_profit:>12,.2f}")
    out.append(f"Gross Margin %                                            {result.gross_margin_percent:>12.2f}%")
    out.append("")

    # Operating expenses
    out.append("Less: Operating Expenses")
    for line in result.lines:
        if line["kind"] == "operating_expense":
            out.append(f"    {line['label'].strip():<55}{line['amount']:>12,.2f}")
    out.append(f"    Total Operating Expenses                                {result.operating_expenses:>12,.2f}")
    out.append(f"Operating Income                                          {result.operating_income:>12,.2f}")
    out.append("")

    # Non-operating
    if result.non_operating_revenue > 0:
        out.append(f"Add: Gain on Sale of Equipment                              {result.non_operating_revenue:>12,.2f}")
    if result.non_operating_expense > 0:
        out.append(f"Less: Interest Expense                                      {result.non_operating_expense:>12,.2f}")
    out.append(f"Income Before Income Tax                                  {result.income_before_tax:>12,.2f}")
    out.append(f"Less: Income Tax Expense ({result.tax_rate * 100:.0f}%)                      {result.income_tax:>12,.2f}")
    out.append(f"Net Income                                                  {result.net_income:>12,.2f}")

    out.append(f"Net Income                                                  {result.net_income:>12,.2f}")

    return "\n".join(out)


def compute_balance_sheet_analysis(lines: List[AccountLine]) -> BalanceSheetResult:
    """Compute balance sheet analysis from parsed account lines.

    Computes current assets, current liabilities, working capital, and current ratio.
    """
    current_assets = Decimal("0")
    current_liabilities = Decimal("0")
    non_current_assets = Decimal("0")
    non_current_liabilities = Decimal("0")
    stated_current_assets = None
    stated_current_liabilities = None
    stated_total_assets = None
    stated_total_liabilities = None

    for line in lines:
        if line.kind == "current_asset":
            current_assets += line.amount
        elif line.kind == "current_liability":
            current_liabilities += line.amount
        elif line.kind == "non_current_asset":
            non_current_assets += line.amount
        elif line.kind == "non_current_liability":
            non_current_liabilities += line.amount
        elif line.kind == "total_current_assets":
            stated_current_assets = line.amount
        elif line.kind == "total_current_liabilities":
            stated_current_liabilities = line.amount
        elif line.kind == "total_assets":
            stated_total_assets = line.amount
        elif line.kind == "total_liabilities":
            stated_total_liabilities = line.amount

    # A stated total is used only when its components are absent; when both are present the
    # components are the detail and are kept, so nothing is counted twice.
    if current_assets == 0 and stated_current_assets is not None:
        current_assets = stated_current_assets
    if current_liabilities == 0 and stated_current_liabilities is not None:
        current_liabilities = stated_current_liabilities
    if non_current_assets == 0 and stated_total_assets is not None:
        non_current_assets = max(Decimal("0"), stated_total_assets - current_assets)
    if non_current_liabilities == 0 and stated_total_liabilities is not None:
        non_current_liabilities = max(Decimal("0"), stated_total_liabilities - current_liabilities)

    total_assets = current_assets + non_current_assets
    total_liabilities = current_liabilities + non_current_liabilities
    total_equity = total_assets - total_liabilities
    working_capital = current_assets - current_liabilities
    current_ratio = current_assets / current_liabilities if current_liabilities > 0 else Decimal("0")

    # Build rendered lines
    rendered: List[Dict[str, Any]] = []

    rendered.append({"label": "Current Assets", "kind": "heading", "amount": Decimal("0"), "indent": 0})
    for line in lines:
        if line.kind == "current_asset":
            rendered.append({"label": "  " + line.account.title(), "kind": "current_asset",
                            "amount": line.amount, "indent": 1})
    rendered.append({"label": "Total Current Assets", "kind": "subtotal",
                    "amount": current_assets, "indent": 0})

    rendered.append({"label": "Non-Current Assets", "kind": "heading", "amount": Decimal("0"), "indent": 0})
    for line in lines:
        if line.kind == "non_current_asset":
            rendered.append({"label": "  " + line.account.title(), "kind": "non_current_asset",
                            "amount": line.amount, "indent": 1})
    rendered.append({"label": "Total Non-Current Assets", "kind": "subtotal",
                    "amount": non_current_assets, "indent": 1})
    rendered.append({"label": "Total Assets", "kind": "subtotal",
                    "amount": total_assets, "indent": 0})

    rendered.append({"label": "Current Liabilities", "kind": "heading", "amount": Decimal("0"), "indent": 0})
    for line in lines:
        if line.kind == "current_liability":
            rendered.append({"label": "  " + line.account.title(), "kind": "current_liability",
                            "amount": line.amount, "indent": 1})
    rendered.append({"label": "Total Current Liabilities", "kind": "subtotal",
                    "amount": current_liabilities, "indent": 1})

    rendered.append({"label": "Non-Current Liabilities", "kind": "heading", "amount": Decimal("0"), "indent": 0})
    for line in lines:
        if line.kind == "non_current_liability":
            rendered.append({"label": "  " + line.account.title(), "kind": "non_current_liability",
                            "amount": line.amount, "indent": 1})
    rendered.append({"label": "Total Non-Current Liabilities", "kind": "subtotal",
                    "amount": non_current_liabilities, "indent": 1})
    rendered.append({"label": "Total Liabilities", "kind": "subtotal",
                    "amount": total_liabilities, "indent": 0})

    rendered.append({"label": "Total Equity", "kind": "subtotal",
                    "amount": total_equity, "indent": 0})
    rendered.append({"label": "Total Liabilities and Equity", "kind": "total",
                    "amount": total_liabilities + total_equity, "indent": 0})

    rendered.append({"label": "", "kind": "spacer", "amount": Decimal("0"), "indent": 0})
    rendered.append({"label": "Working Capital (Current Assets − Current Liabilities)",
                    "kind": "ratio_line", "amount": working_capital, "indent": 0})
    rendered.append({"label": "Current Ratio (Current Assets ÷ Current Liabilities)",
                    "kind": "ratio_line", "amount": current_ratio, "indent": 0})

    return BalanceSheetResult(
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        working_capital=working_capital,
        current_ratio=current_ratio,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        lines=rendered,
    )


def render_balance_sheet_analysis(result: BalanceSheetResult, period: str, currency: str = "USD") -> str:
    """Render the balance sheet analysis as text."""
    out = ["BALANCE SHEET ANALYSIS", f"As of {period}", f"   {currency}", ""]

    out.append("Current Assets")
    for line in result.lines:
        if line["kind"] == "current_asset":
            out.append(f"  {line['label'].strip():<55}{line['amount']:>12,.2f}")
    out.append(f"  Total Current Assets                                {result.current_assets:>12,.2f}")
    out.append("")

    out.append("Non-Current Assets")
    for line in result.lines:
        if line["kind"] == "non_current_asset":
            out.append(f"  {line['label'].strip():<55}{line['amount']:>12,.2f}")
    out.append(f"  Total Non-Current Assets                            {result.total_assets - result.current_assets:>12,.2f}")
    out.append(f"  Total Assets                                        {result.total_assets:>12,.2f}")
    out.append("")

    out.append("Current Liabilities")
    for line in result.lines:
        if line["kind"] == "current_liability":
            out.append(f"  {line['label'].strip():<55}{line['amount']:>12,.2f}")
    out.append(f"  Total Current Liabilities                           {result.current_liabilities:>12,.2f}")
    out.append("")

    out.append("Non-Current Liabilities")
    for line in result.lines:
        if line["kind"] == "non_current_liability":
            out.append(f"  {line['label'].strip():<55}{line['amount']:>12,.2f}")
    out.append(f"  Total Non-Current Liabilities                       {result.total_liabilities - result.current_liabilities:>12,.2f}")
    out.append(f"  Total Liabilities                                   {result.total_liabilities:>12,.2f}")
    out.append("")

    out.append(f"Total Equity                                          {result.total_equity:>12,.2f}")
    out.append(f"Total Liabilities and Equity                          {result.total_liabilities + result.total_equity:>12,.2f}")
    out.append("")

    out.append(f"Working Capital                                       {result.working_capital:>12,.2f}")
    out.append(f"Current Ratio                                         {result.current_ratio:>12,.2f}")

    return "\n".join(out)


# ============================================================================
# EPS computation
# ============================================================================

#: Detectors for earnings-per-share problems.
EPS_DETECTORS = [
    (r"\bearnings per share\b", "eps"),
    (r"\bbasic earnings per share\b", "eps"),
    (r"\bdiluted earnings per share\b", "eps"),
    (r"\bEPS\b", "eps"),
    (r"\bbonus issue\b", "eps"),
    (r"\bshare options?\b", "eps"),
    (r"\bconvertible bonds?\b", "eps"),
    (r"\bpreference dividends?\b", "eps"),
    (r"\bprofit from continuing operations\b", "eps"),
    (r"\bloss from discontinued operations\b", "eps"),
]


def detect_given_balances(text: str) -> bool:
    """Return True if the problem lists multiple account balances with amounts."""
    low = text.lower()
    matches = 0
    for pattern, _ in GIVEN_BALANCES_DETECTORS:
        if re.search(pattern, low):
            matches += 1
    return matches >= 2  # Need at least 2 account types to be a "given balances" problem


def detect_eps(text: str) -> bool:
    """Return True if the problem reads as an earnings-per-share computation."""
    low = text.lower()
    for pattern, _ in EPS_DETECTORS:
        if re.search(pattern, low, re.I):
            return True
    return False


def parse_eps_problem(text: str) -> Tuple[List[AccountLine], Decimal]:
    """Parse an EPS problem into account lines and tax rate.

    EPS problems have specific language like:
      "profit from continuing operations 1,000"
      "loss from discontinued operations 200"
      "preference dividends 50"
      "ordinary shares opening 1,000"
      "bonus issue 1-for-5 during the year"
      "share options 100 with exercise price 5 and average market price 10"
      "convertible bonds 500 at 6%, convertible into 100 ordinary shares"
      "tax rate 25%"

    Each figure is extracted with a targeted regex so no figure is guessed.
    Returns (account_lines, tax_rate).
    """
    lines: List[AccountLine] = []
    tax_rate = _extract_tax_rate(text)

    # Profit from continuing operations
    m = re.search(r"profit from continuing operations\s+([\d,]+(?:\.\d+)?)", text, re.I)
    if m:
        lines.append(AccountLine(
            account="Profit from continuing operations",
            amount=_money(m.group(1)), kind="revenue", line="Sales Revenue",
        ))

    # Loss from discontinued operations
    m = re.search(r"loss from discontinued operations\s+([\d,]+(?:\.\d+)?)", text, re.I)
    if m:
        lines.append(AccountLine(
            account="Loss from discontinued operations",
            amount=_money(m.group(1)), kind="contra_revenue",
            line="Loss from Discontinued Operations",
        ))

    # Preference dividends
    m = re.search(r"preference dividends?\s+([\d,]+(?:\.\d+)?)", text, re.I)
    if m:
        lines.append(AccountLine(
            account="Preference dividends",
            amount=_money(m.group(1)), kind="contra_revenue",
            line="Preference dividends",
        ))

    # Ordinary shares opening
    m = re.search(r"ordinary shares opening\s+([\d,]+(?:\.\d+)?)", text, re.I)
    if m:
        lines.append(AccountLine(
            account="Ordinary shares opening",
            amount=_money(m.group(1)), kind="equity", line="Share Capital",
        ))

    # Bonus issue ratio: "bonus issue 1-for-5" means 1 new share for every 5 held
    m = re.search(r"bonus issue\s+(\d+)\s*-?\s*for\s*-?\s*(\d+)", text, re.I)
    if m:
        lines.append(AccountLine(
            account="Bonus issue ratio",
            amount=Decimal(m.group(1)) / Decimal(m.group(2)),
            kind="equity", line="Bonus Issue Ratio",
        ))

    # Share options: "share options 100 with exercise price $5 and average market price $10"
    m = re.search(
        r"share options?\s+(\d+)\s+with exercise price\s+\$?([\d,]+(?:\.\d+)?)\s+and average market price\s+\$?([\d,]+(?:\.\d+)?)",
        text, re.I)
    if m:
        lines.append(AccountLine(
            account="Share options count",
            amount=_money(m.group(1)), kind="operating_expense",
            line="Share options count",
        ))
        lines.append(AccountLine(
            account="Share options exercise price",
            amount=_money(m.group(2)), kind="operating_expense",
            line="Share options exercise price",
        ))
        lines.append(AccountLine(
            account="Share options market price",
            amount=_money(m.group(3)), kind="operating_expense",
            line="Share options market price",
        ))

    # Convertible bonds: "convertible bonds 500 at 6%, convertible into 100 ordinary shares"
    m = re.search(
        r"convertible bonds?\s+([\d,]+(?:\.\d+)?)\s+at\s+([\d,]+(?:\.\d+)?)%\s*,?\s*convertible into\s+(\d+)\s+ordinary shares",
        text, re.I)
    if m:
        lines.append(AccountLine(
            account="Convertible bonds face value",
            amount=_money(m.group(1)), kind="non_current_liability",
            line="Convertible bonds face value",
        ))
        lines.append(AccountLine(
            account="Convertible bonds rate",
            amount=_money(m.group(2)), kind="non_current_liability",
            line="Convertible bonds rate",
        ))
        lines.append(AccountLine(
            account="Convertible bonds shares",
            amount=_money(m.group(3)), kind="equity",
            line="Convertible bonds shares",
        ))

    if not lines:
        raise ValueError("no parseable account lines in the problem text")

    return lines, tax_rate


def compute_eps_problem(lines: List[AccountLine], tax_rate: Decimal) -> EPSResult:
    """Compute basic and diluted EPS from parsed account lines."""
    profit_from_continuing_operations = Decimal("0")
    loss_from_discontinued_operations = Decimal("0")
    preference_dividends = Decimal("0")
    ordinary_shares_opening = Decimal("0")
    bonus_ratio = Decimal("0")
    options_count = Decimal("0")
    options_exercise_price = Decimal("0")
    options_market_price = Decimal("0")
    convertible_face = Decimal("0")
    convertible_rate = Decimal("0")
    convertible_shares = Decimal("0")

    for line in lines:
        a = line.account.lower()
        if "profit from continuing operations" in a and line.kind == "revenue":
            profit_from_continuing_operations = line.amount
        elif "loss from discontinued operations" in a and line.kind == "contra_revenue":
            loss_from_discontinued_operations = line.amount
        elif "preference dividends" in a:
            preference_dividends = line.amount
        elif "ordinary shares opening" in a:
            ordinary_shares_opening = line.amount
        elif "bonus issue ratio" in a:
            bonus_ratio = line.amount
        elif "share options count" in a:
            options_count = line.amount
        elif "share options exercise price" in a:
            options_exercise_price = line.amount
        elif "share options market price" in a:
            options_market_price = line.amount
        elif "convertible bonds face value" in a:
            convertible_face = line.amount
        elif "convertible bonds rate" in a:
            convertible_rate = line.amount
        elif "convertible bonds shares" in a:
            convertible_shares = line.amount

    # Basic EPS = (Profit for the year − Preference dividends) / Weighted average shares
    profit_for_the_year = profit_from_continuing_operations - loss_from_discontinued_operations
    numerator_basic = profit_for_the_year - preference_dividends
    weighted_average_shares = ordinary_shares_opening * (Decimal("1") + bonus_ratio)
    basic_eps = (numerator_basic / weighted_average_shares
                 if weighted_average_shares > 0 else Decimal("0"))

    # Diluted EPS
    numerator_diluted = numerator_basic
    diluted_shares = weighted_average_shares

    # Share options: incremental shares (treasury stock method)
    if options_count > 0 and options_market_price > options_exercise_price:
        proceeds = options_count * options_exercise_price
        shares_bought_back = proceeds / options_market_price
        incremental_shares = options_count - shares_bought_back
        diluted_shares += incremental_shares

    # Convertible bonds: interest saved net of tax, added to numerator
    if convertible_face > 0 and convertible_rate > 0:
        interest_expense = convertible_face * convertible_rate / Decimal(100)
        interest_after_tax = interest_expense * (Decimal("1") - tax_rate)
        numerator_diluted += interest_after_tax
        diluted_shares += convertible_shares

    diluted_eps = (numerator_diluted / diluted_shares
                   if diluted_shares > 0 else Decimal("0"))

    rendered = [
        {"label": "Profit from continuing operations", "kind": "revenue",
         "amount": profit_from_continuing_operations, "indent": 0},
        {"label": "Less: Loss from discontinued operations", "kind": "contra_revenue",
         "amount": loss_from_discontinued_operations, "indent": 1},
        {"label": "Profit for the year", "kind": "subtotal",
         "amount": profit_for_the_year, "indent": 0},
        {"label": "Less: Preference dividends", "kind": "contra_revenue",
         "amount": preference_dividends, "indent": 1},
        {"label": "Profit attributable to ordinary shareholders", "kind": "subtotal",
         "amount": numerator_basic, "indent": 0},
        {"label": "Weighted average number of ordinary shares", "kind": "line",
         "amount": weighted_average_shares, "indent": 0},
        {"label": "Basic earnings per share", "kind": "total",
         "amount": basic_eps, "indent": 0},
    ]

    return EPSResult(
        profit_from_continuing_operations=profit_from_continuing_operations,
        loss_from_discontinued_operations=loss_from_discontinued_operations,
        profit_for_the_year=profit_for_the_year,
        preference_dividends=preference_dividends,
        numerator_basic=numerator_basic,
        weighted_average_shares=weighted_average_shares,
        basic_eps=basic_eps,
        numerator_diluted=numerator_diluted,
        diluted_shares=diluted_shares,
        diluted_eps=diluted_eps,
        lines=rendered,
    )


def render_eps_problem(result: EPSResult, period: str, currency: str = "USD") -> str:
    """Render the EPS computation as text."""
    out = ["EARNINGS PER SHARE", f"For the Year Ended {period}", f"   {currency}", ""]
    out.append(f"Profit from continuing operations                         {result.profit_from_continuing_operations:>12,.2f}")
    out.append(f"  Less: Loss from discontinued operations                     {result.loss_from_discontinued_operations:>12,.2f}")
    out.append(f"Profit for the year                                         {result.profit_for_the_year:>12,.2f}")
    out.append(f"  Less: Preference dividends                                  {result.preference_dividends:>12,.2f}")
    out.append(f"Profit attributable to ordinary shareholders                {result.numerator_basic:>12,.2f}")
    out.append(f"Weighted average number of ordinary shares                    {result.weighted_average_shares:>12,.2f}")
    out.append(f"Basic earnings per share                                    {result.basic_eps:>12,.2f}")
    out.append("")
    out.append(f"Diluted earnings per share:")
    out.append(f"  Profit attributable to ordinary shareholders                {result.numerator_basic:>12,.2f}")
    interest_added = result.numerator_diluted - result.numerator_basic
    out.append(f"  Add: Interest on convertible bonds (net of tax)             {interest_added:>12,.2f}")
    out.append(f"  Adjusted profit attributable to ordinary shareholders       {result.numerator_diluted:>12,.2f}")
    out.append(f"  Weighted average number of ordinary shares (diluted)        {result.diluted_shares:>12,.2f}")
    out.append(f"Diluted earnings per share                                    {result.diluted_eps:>12,.2f}")
    return "\n".join(out)

