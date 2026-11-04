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


#: Detectors for multi-step income statement problems.
INCOME_STATEMENT_DETECTORS = [
    (r"multi.step\s+income\s+statement", "multi_step"),
    (r"income\s+statement\s+components", "multi_step"),
    (r"net\s+sales", "multi_step"),
    (r"gross\s+profit", "multi_step"),
    (r"operating\s+income", "multi_step"),
    (r"income\s+before\s+tax", "multi_step"),
    (r"cost\s+of\s+goods\s+sold", "multi_step"),
    (r"sales\s+returns", "multi_step"),
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


def detect_income_statement(text: str) -> bool:
    """Return True if the problem reads as a multi-step income statement computation."""
    low = text.lower()
    for pattern, _ in INCOME_STATEMENT_DETECTORS:
        if re.search(pattern, low):
            return True
    return False


def detect_ratio_analysis(text: str) -> bool:
    """Return True if the problem reads as a ratio analysis / balance sheet analysis."""
    low = text.lower()
    for pattern, _ in RATIO_DETECTORS:
        if re.search(pattern, low):
            return True
    return False


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

    # Revenue (must end in "revenue" or be exactly "sales"/"turnover")
    if re.search(r"revenue$", a) or re.search(r"^(sales|turnover)$", a):
        return ("revenue", "Sales Revenue")

    # COGS
    if re.search(r"^(purchases?|cost of (sales|goods sold)|cogs)$", a):
        return ("cogs", "Cost of Goods Sold")

    # Operating expenses
    if re.search(r"^(rent|salaries|salary|wages|utilities|insurance|advertising|marketing|depreciation|bad debts?|general expenses|operating expenses|telephone|transport|repairs|stationery|fuel|travel)$", a):
        return ("operating_expense", "Operating Expenses")

    # Non-operating revenue / gains
    if re.search(r"\bgain\s+on\s+sale", a) or re.search(r"\bgain\b", a):
        return ("non_operating_revenue", "Gain on Sale of Equipment")

    # Non-operating expense
    if re.search(r"^(interest (expense|paid)|finance costs?)$", a):
        return ("non_operating_expense", "Interest Expense")

    # Tax rate — only if explicitly a tax account
    if re.search(r"\btax\b", a):
        return ("tax_rate", "Income Tax Expense")

    # Balance sheet classification
    if re.search(r"^(cash|bank|cash at bank|bank account)$", a):
        return ("current_asset", "Cash")
    if re.search(r"^(trade receivables?|receivables?|accounts? receivable|sundry debtors)$", a):
        return ("current_asset", "Accounts Receivable")
    if re.search(r"^(inventor(y|ies)|stock|closing stock)$", a):
        return ("current_asset", "Inventory")
    if re.search(r"^(prepaid\s+expenses?|prepaids?)$", a):
        return ("current_asset", "Prepaid Expenses")
    if re.search(r"^(equipment|vehicles?|machinery|furniture|land|buildings?|plant)$", a) and not re.search(r"accumulated", a):
        return ("non_current_asset", "Equipment (net)")
    if re.search(r"^(trade payables?|payables?|creditors?|accounts? payable|sundry creditors)$", a):
        return ("current_liability", "Accounts Payable")
    if re.search(r"^(notes payable|short.term notes? payable)$", a):
        return ("current_liability", "Short-term Notes Payable")
    if re.search(r"^(accrued (expenses?|liabilities?|liability)|accruals?)$", a):
        return ("current_liability", "Accrued Liabilities")
    if re.search(r"^(long.term (debt|notes? payable)|long.term debt|long.term loan)$", a):
        return ("non_current_liability", "Long-term Debt")

    # Generic expense fallback
    if re.search(r"\b(expense|cost)\b", a):
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

    for line in lines:
        if line.kind == "revenue":
            revenue += line.amount
        elif line.kind == "contra_revenue":
            contra_revenue += line.amount
        elif line.kind == "cogs":
            cogs += line.amount
        elif line.kind == "operating_expense":
            operating_expenses += line.amount
        elif line.kind == "non_operating_revenue":
            non_operating_revenue += line.amount
        elif line.kind == "non_operating_expense":
            non_operating_expense += line.amount

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

    for line in lines:
        if line.kind == "current_asset":
            current_assets += line.amount
        elif line.kind == "current_liability":
            current_liabilities += line.amount
        elif line.kind == "non_current_asset":
            non_current_assets += line.amount
        elif line.kind == "non_current_liability":
            non_current_liabilities += line.amount

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

