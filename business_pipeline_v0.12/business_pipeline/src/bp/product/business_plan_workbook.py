"""The business-plan record as an Excel workbook.

One sheet per table the record holds, built with the product's own xlsx writer so the
workbook is a real package, not a CSV in disguise.  No figure is recomputed here.
"""

from decimal import Decimal, InvalidOperation

from . import spreadsheets


def _number(value):
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return value


def _sheet(name, rows, widths=None):
    return (name, [[cell for cell in row] for row in rows],
            {"widths": widths} if widths else {})


def sheets(record, include_checks=True):
    out = []
    startup = record.get("startup") or {}
    sources = record.get("sources") or {}
    revenue = record.get("revenue") or {}
    monthly = record.get("monthly") or {}
    statements = record.get("statements") or {}
    loan = record.get("loan") or {}
    break_even = record.get("break_even") or {}
    payback = record.get("payback") or {}

    out.append(_sheet("Summary", [
        ["Business plan financials", record.get("objective") or ""],
        ["Startup cost", _number(startup.get("total"))],
        ["Owner equity", _number(sources.get("equity"))],
        ["Bank loan", _number(sources.get("loan"))],
        ["Total funding", _number(sources.get("total"))],
        ["Year 1 revenue", _number(revenue.get("total_revenue"))],
        ["Year 1 net income", _number(statements.get("net_income_1"))],
        ["Break-even units a month", _number(break_even.get("breakeven_units"))],
        ["Payback (periods)", _number(payback.get("payback_periods")) if payback else "not reached"],
    ], [34, 18]))

    rows = [["Category", "Amount"]]
    for key in sorted(startup):
        if key.startswith("category_"):
            rows.append([key.replace("category_", "").replace("_", " ").title(), _number(startup[key])])
    rows.append(["Total", _number(startup.get("total"))])
    out.append(_sheet("Startup budget", rows, [34, 18]))

    out.append(_sheet("Sources and uses", [
        ["Source", "Amount"], ["Owner equity", _number(sources.get("equity"))],
        ["Bank loan", _number(sources.get("loan"))], ["Total sources", _number(sources.get("total"))],
        ["", ""], ["Uses", _number(startup.get("total"))],
    ], [34, 18]))

    if monthly:
        rows = [["Month", "Revenue", "Gross profit", "Net income", "Closing cash"]]
        for index in range(1, 13):
            rows.append([index, _number(monthly.get("revenue_%d" % index)),
                         _number(monthly.get("gross_profit_%d" % index)),
                         _number(monthly.get("net_income_%d" % index)),
                         _number(monthly.get("closing_cash_%d" % index))])
        out.append(_sheet("Year 1 monthly", rows, [8, 14, 14, 14, 14]))

    if statements:
        pairs = [("Revenue", "revenue"), ("Gross profit", "gross_profit"),
                 ("Operating profit", "operating_profit"), ("Interest", "interest"),
                 ("Tax", "tax"), ("Owner withdrawals", "owner_withdrawals"),
                 ("Net income", "net_income"),
                 ("Operating cash", "cash_from_operations"), ("Net cash flow", "net_cash_flow"),
                 ("Closing cash", "closing_cash")]
        count = len(record.get("revenue_years") or []) or 3
        rows = [["Line"] + ["Year %d" % index for index in range(1, count + 1)]]
        for label, key in pairs:
            rows.append([label] + [_number(statements.get("%s_%d" % (key, y)))
                                   for y in range(1, count + 1)])
        out.append(_sheet("Pro forma", rows, [22] + [16] * count))

    if loan:
        rows = [["Year", "Interest", "Principal", "Closing balance"]]
        for index in range(1, (len(record.get("revenue_years") or []) or 6) + 1):
            if loan.get("interest_%d" % index) is None:
                break
            rows.append([index, _number(loan.get("interest_%d" % index)),
                         _number(loan.get("principal_%d" % index)),
                         _number(loan.get("closing_balance_%d" % index))])
        out.append(_sheet("Loan schedule", rows, [8, 16, 16, 18]))

    if break_even:
        out.append(_sheet("Break-even", [
            ["Break-even units a month", _number(break_even.get("breakeven_units"))],
            ["Break-even revenue", _number(break_even.get("breakeven_revenue"))],
            ["Contribution per unit", _number(break_even.get("contribution_margin"))],
        ], [30, 18]))

    sensitivity = record.get("sensitivity") or {}
    if sensitivity:
        rows = [["Ticket change \\ Volume change", "-10%", "base", "+10%"]]
        grid = sensitivity.get("price_volume") or {}
        for index in (1, 2, 3):
            rows.append(["row %d" % index] + [_number(grid.get("profit_%d_%d" % (index, column)))
                                              for column in (1, 2, 3)])
        rows.append([])
        rows.append(["Variable cost change", "Break-even units"])
        for row in sensitivity.get("variable_cost") or []:
            rows.append([row.get("change"), _number(row.get("breakeven_units"))])
        out.append(_sheet("Sensitivity", rows, [30, 16, 16, 16]))

    market = record.get("market") or {}
    if market:
        rows = [["Market measure", "Value"]]
        for key, value in market.items():
            if str(key).startswith("_"):
                continue
            rows.append([str(key).replace("_", " ").title(), _number(value)])
        out.append(_sheet("Market sizing", rows, [30, 18]))

    ratios = record.get("ratios") or {}
    if ratios:
        rows = [["Ratio", "Value"]]
        for key, value in ratios.items():
            if str(key).startswith("_") or key == "n_computed":
                continue
            rows.append([str(key).replace("_", " ").title(), _number(value)])
        out.append(_sheet("Ratios", rows, [30, 16]))

    returns = record.get("returns") or {}
    if returns:
        rows = [["Measure", "Value"]]
        if returns.get("npv"):
            rows.append(["Net present value", _number(returns["npv"].get("npv"))])
        if returns.get("irr"):
            rows.append(["Internal rate of return", _number(returns["irr"].get("irr"))])
        if returns.get("discounted_payback"):
            rows.append(["Discounted payback (periods)",
                         _number(returns["discounted_payback"].get("discounted_payback"))])
        out.append(_sheet("Returns", rows, [30, 18]))

    if include_checks:
        rows = [["Check", "Result", "Detail"]]
        for gate in record.get("gates") or []:
            rows.append([gate.get("code"), "PASS" if gate.get("ok") else "FAIL", gate.get("detail") or ""])
        for warning in record.get("warnings") or []:
            rows.append(["warning", "WARN", warning])
        out.append(_sheet("Checks", rows, [8, 10, 60]))
    return out


def workbook(record, include_checks=True):
    """The workbook as .xlsx bytes."""
    return spreadsheets.write_xlsx(sheets(record, include_checks=include_checks))
