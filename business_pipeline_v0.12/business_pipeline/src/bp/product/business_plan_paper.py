"""Render the business-plan record as the financial-plan paper.

The narrative sections (company, market, marketing, operations) belong to the Home
chat's business-plan profile.  This paper is the financial plan the tile produces: the
tables the record actually holds, the checks that hold, and every gap named.
"""

from decimal import Decimal, InvalidOperation

from . import business_plan_sections
from . import docx as docx_render


def _n(value, places=2):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    text = "{:,.%df}" % places
    return text.format(number)


def _money(value):
    return _n(value, 2)


def _rows(record):
    statements = record.get("statements") or {}
    revenue_years = record.get("revenue_years") or []
    years = [str(i) for i in range(1, len(revenue_years) + 1)] or ["1", "2", "3"]

    def year_row(label, key):
        values = [statements.get("%s_%s" % (key, y)) for y in years]
        return label + ": " + " | ".join(_money(v) if v is not None else "n/a" for v in values)

    return [
        ("Revenue", year_row("Revenue", "revenue")),
        ("Gross profit", year_row("Gross profit", "gross_profit")),
        ("Operating profit", year_row("Operating profit", "operating_profit")),
        ("Interest", year_row("Interest", "interest")),
        ("Tax", year_row("Tax", "tax")),
        ("Owner withdrawals", year_row("Owner withdrawals", "owner_withdrawals")),
        ("Net income", year_row("Net income", "net_income")),
        ("Cash from operations", year_row("Operating cash", "cash_from_operations")),
        ("Net cash flow", year_row("Net cash", "net_cash_flow")),
        ("Closing cash", year_row("Closing cash", "closing_cash")),
    ]


def sections(record, narrative=None):
    """The paper's sections as (heading, lines) pairs; no figure is computed here.

    ``narrative`` is the writer's merged output.  When it is absent every section
    is the deterministic text, which is the floor the paper always has.
    """
    written = {heading: lines for heading, lines in (narrative or {}).get("sections") or []}
    out = [(heading, written.get(heading, lines))
           for heading, lines in business_plan_sections.sections(record)]
    startup = record.get("startup") or {}
    sources = record.get("sources") or {}
    revenue = record.get("revenue") or {}
    fixed = record.get("fixed") or {}
    loan = record.get("loan") or {}
    break_even = record.get("break_even") or {}
    payback = record.get("payback") or {}
    statements = record.get("statements") or {}
    gaps = list(record.get("gaps") or [])

    out.append(("Financial summary", [
        "Startup cost: " + _money(startup.get("total")) + ".",
        "Funding: owner equity " + _money(sources.get("equity")) + ", loan "
        + _money(sources.get("loan")) + ", total " + _money(sources.get("total")) + ".",
        "Year 1 revenue: " + _money(revenue.get("total_revenue")) + "; Year 1 net income: "
        + _money(statements.get("net_income_1")) + ".",
        "Monthly fixed cost: " + _money(fixed.get("monthly")) + "; break-even "
        + _n(break_even.get("breakeven_units"), 1) + " units a month.",
    ]))

    market = record.get("market") or {}
    if market:
        lines = []
        for key, value in market.items():
            if str(key).startswith("_"):
                continue
            lines.append(str(key).replace("_", " ").title() + ": " + _n(value, 2))
        out.append(("Market sizing (TAM / SAM / SOM)", lines))

    lines = []
    for key, value in sorted(startup.items()):
        if key.startswith("category_"):
            lines.append(key.replace("category_", "").replace("_", " ").title() + ": " + _money(value))
    lines.append("Total startup cost: " + _money(startup.get("total")))
    out.append(("Startup budget", lines))

    out.append(("Sources and uses", [
        "Owner equity: " + _money(sources.get("equity")),
        "Bank loan: " + _money(sources.get("loan")),
        "Total sources: " + _money(sources.get("total")),
        "Total uses: " + _money(startup.get("total")),
    ]))

    lines = []
    for index in range(1, 13):
        value = revenue.get("revenue_%d" % index)
        if value is None:
            break
        lines.append("Month %d: %s" % (index, _money(value)))
    if lines:
        lines.append("Year 1 total: " + _money(revenue.get("total_revenue")))
        out.append(("Sales forecast", lines))

    out.append(("Operating costs", [
        "Fixed monthly cost: " + _money(fixed.get("monthly")),
        "Payroll on-cost rate: " + _n(fixed.get("payroll_rate"), 4),
    ]))

    dep = record.get("depreciation") or {}
    out.append(("Depreciation", [
        "Straight-line annual charge: " + _money(dep.get("depreciation_1")),
        "Total over the life: " + _money(dep.get("total_depreciation")),
    ]))

    if loan:
        lines = []
        for index in range(1, (len(record.get("revenue_years") or []) or 6) + 1):
            interest = loan.get("interest_%d" % index)
            if interest is None:
                break
            lines.append("Year %d: interest %s, principal %s, closing balance %s" % (
                index, _money(interest), _money(loan.get("principal_%d" % index)),
                _money(loan.get("closing_balance_%d" % index))))
        lines.append("Payment: " + _money(loan.get("payment")))
        out.append(("Loan schedule", lines))

    if statements:
        count = len(record.get("revenue_years") or []) or 3
        header = " | ".join("Year %d" % i for i in range(1, count + 1))
        out.append(("Pro forma (Years 1-%d)" % count, [
            header,
            *[row[1] for row in _rows(record)],
        ]))

    monthly = record.get("monthly") or {}
    if monthly:
        lines = ["Month | Revenue | Net income | Closing cash"]
        for index in range(1, 13):
            if monthly.get("revenue_%d" % index) is None:
                break
            lines.append("%d | %s | %s | %s" % (
                index, _money(monthly.get("revenue_%d" % index)),
                _money(monthly.get("net_income_%d" % index)),
                _money(monthly.get("closing_cash_%d" % index))))
        out.append(("Year 1 monthly", lines))

    if break_even:
        out.append(("Break-even", [
            "Break-even units a month: " + _n(break_even.get("breakeven_units"), 1),
            "Break-even revenue: " + _money(break_even.get("breakeven_revenue")),
            "Contribution per unit: " + _money(break_even.get("contribution_margin")),
        ]))

    returns = record.get("returns") or {}
    return_lines = [
        ("Payback on owner equity: " + _n(payback.get("payback_periods"), 2) + " periods"
         if payback else "Payback: not reached within the three-year horizon."),
    ]
    if returns:
        if returns.get("npv"):
            return_lines.append("Net present value at the declared rate: " + _money(returns["npv"].get("npv")))
        if returns.get("irr"):
            return_lines.append("Internal rate of return: " + _n(returns["irr"].get("irr"), 4))
        if returns.get("discounted_payback"):
            return_lines.append("Discounted payback: "
                                + _n(returns["discounted_payback"].get("discounted_payback"), 2) + " periods")
    out.append(("Returns", return_lines))

    sensitivity = record.get("sensitivity") or {}
    if sensitivity:
        lines = []
        grid = sensitivity.get("price_volume") or {}
        if grid:
            lines.append("Profit grid: rows are the ticket change, columns the volume change.")
            for index in (1, 2, 3):
                lines.append("Price row %d | %s | %s | %s" % (
                    index, _money(grid.get("profit_%d_1" % index)),
                    _money(grid.get("profit_%d_2" % index)),
                    _money(grid.get("profit_%d_3" % index))))
        for row in sensitivity.get("variable_cost") or []:
            lines.append("Variable cost change %s: break-even %s units" % (
                row.get("change"), _n(row.get("breakeven_units"), 1)))
        out.append(("Sensitivity", lines))

    gates = record.get("gates") or []
    out.append(("Checks", [
        ("%s %s — %s" % (gate["code"], "PASS" if gate["ok"] else "FAIL", gate.get("detail") or ""))
        for gate in gates
    ]))

    warnings = record.get("warnings") or []
    if warnings:
        out.append(("Reasonableness warnings", list(warnings)))

    ratios = record.get("ratios") or {}
    if ratios:
        lines = []
        for key, value in ratios.items():
            if str(key).startswith("_") or key == "n_computed":
                continue
            lines.append(str(key).replace("_", " ").title() + ": " + _n(value, 4))
        out.append(("Ratios (Year 1)", lines))

    assumptions = record.get("assumptions") or []
    if assumptions:
        out.append(("Assumptions", [
            "%s: %s (%s; used in %s)" % (row.get("assumption"), row.get("value"),
                                          row.get("basis"), row.get("used_in"))
            for row in assumptions
        ]))

    if gaps:
        out.append(("Gaps", gaps))
    return out


def document(record, narrative=None):
    """The paper as Word bytes."""
    title = "Business plan financials" + (": " + record.get("objective") if record.get("objective") else "")
    pairs = sections(record, narrative)
    return docx_render.render_bytes(title, pairs, mono=True)
