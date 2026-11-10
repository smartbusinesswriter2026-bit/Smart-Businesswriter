"""The business plan's narrative sections, written from the declared data.

The uploaded guide's Part 6 says what each section must contain.  This module writes the
sections the record can support — facts, figures and the checks that failed — and names
what the case does not state, rather than filling it with generic prose.  It never prints
the guide's instructions into the paper.
"""

from decimal import Decimal, InvalidOperation


def _d(value, default="0"):
    try:
        return Decimal(str(value if value not in (None, "") else default))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _money(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    return "{:,.2f}".format(number)


def _pct(value):
    try:
        return "{:.1f}%".format(float(Decimal(str(value))) * 100)
    except (InvalidOperation, ValueError):
        return str(value)


def _f(record, key):
    return (record.get("reading") or {}).get("fields", {}).get(key)


def _lines(record, name):
    return (record.get("reading") or {}).get("lines", {}).get(name) or []


def _gate(record, code):
    for gate in record.get("gates") or []:
        if gate.get("code") == code:
            return gate
    return {}


def sections(record):
    """The eleven narrative sections, as (heading, lines)."""
    startup = record.get("startup") or {}
    sources = record.get("sources") or {}
    revenue = record.get("revenue") or {}
    statements = record.get("statements") or {}
    break_even = record.get("break_even") or {}
    market = record.get("market") or {}
    fixed = record.get("fixed") or {}
    out = []

    name = _f(record, "business.name")
    kind = _f(record, "business.type")
    stage = _f(record, "business.stage")
    place = _f(record, "business.location")

    def first_sentence():
        parts = []
        if name:
            parts.append(name)
        if kind:
            parts.append("a %s business" % kind)
        if stage:
            parts.append("at the %s stage" % stage)
        if place:
            parts.append("in %s" % place)
        return (" ".join(parts) + ".") if parts else "The case does not name the business."

    out.append(("Executive Summary", [
        first_sentence(),
        "It needs %s in startup funding: %s of owner equity and %s of debt." % (
            _money(sources.get("total")), _money(sources.get("equity")), _money(sources.get("loan"))),
        "Year 1 revenue is planned at %s and net income at %s; monthly break-even is %s units." % (
            _money(revenue.get("total_revenue")), _money(statements.get("net_income_1")),
            _money(break_even.get("breakeven_units"))),
        "What the case does not state: the customer problem, the team and the milestones. "
        "They are named as gaps below rather than invented.",
    ]))

    legal = _f(record, "business.legal_structure")
    out.append(("Company Description", [
        first_sentence(),
        ("Legal structure: " + legal + ".") if legal else
        "Legal structure: not stated; the form of organisation is a decision the owner has not made in the case.",
        "Ownership: not stated beyond the %s of owner equity." % _money(sources.get("equity")),
    ]))

    market_lines = []
    for key, label in (("market.population", "Potential customers"),
                       ("market.annual_spend_per_customer", "Average annual spend per customer"),
                       ("market.serviceable_share", "Serviceable share"),
                       ("market.obtainable_share", "Obtainable share")):
        value = _f(record, key)
        if value:
            market_lines.append("%s: %s" % (label, _pct(value) if "share" in key else _money(value)))
    if market:
        for key, value in market.items():
            if not str(key).startswith("_"):
                market_lines.append("%s: %s" % (str(key).replace("_", " ").title(), _money(value)))
    else:
        market_lines.append("Market size (TAM/SAM/SOM) is not computed: annual spend per customer, "
                            "serviceable share and obtainable share are not all stated.")
    competitors = None
    for row in _lines(record, "startup"):
        if "competitor" in str(row.get("label", "")).lower():
            competitors = row
    out.append(("Market Analysis", market_lines or ["No market data was stated."]))

    ticket = _f(record, "revenue.average_ticket")
    ratio = _f(record, "revenue.variable_cost_ratio")
    product_lines = []
    if ticket:
        product_lines.append("Average selling price: %s per transaction." % _money(ticket))
    if ratio:
        product_lines.append("Variable cost: %s of revenue; contribution %s." % (
            _pct(ratio), _pct(str(1 - _d(ratio)))))
    if not product_lines:
        product_lines.append("The case does not state the product lines, their prices or their unit costs.")
    out.append(("Products and Services", product_lines))

    marketing = next((row for row in _lines(record, "fixed")
                      if "market" in str(row.get("label", "")).lower()), None)
    out.append(("Marketing and Sales Plan", [
        ("Monthly marketing spend: %s." % _money(marketing.get("amount"))) if marketing else
        "Monthly marketing spend: not stated as its own line.",
        "Channels, messages and conversion assumptions are not stated in the case; "
        "they are a gap, not a claim.",
    ]))

    operations = []
    days = _f(record, "revenue.days_open_per_month")
    if days:
        operations.append("Trading days: %s a month." % _money(days))
    capacity = _f(record, "operations.capacity_per_period")
    if capacity:
        operations.append("Declared capacity: %s." % _money(capacity))
    if fixed.get("monthly"):
        operations.append("Monthly fixed operating cost: %s." % _money(fixed.get("monthly")))
    if not operations:
        operations.append("The case does not state the operating pattern.")
    out.append(("Operations Plan", operations))

    out.append(("Management and Organisation", [
        "The case names no owners, roles or experience, so no management claim is made here.",
        "Owner equity is %s." % _money(sources.get("equity")),
    ]))

    financial = [
        "Startup cost: %s. Sources: %s, of which %s is debt." % (
            _money(startup.get("total")), _money(sources.get("total")), _money(sources.get("loan"))),
        "Year 1 revenue %s; net income %s; closing cash %s." % (
            _money(statements.get("revenue_1")), _money(statements.get("net_income_1")),
            _money(statements.get("closing_cash_1"))),
        "Break-even %s units a month at %s revenue." % (
            _money(break_even.get("breakeven_units")), _money(break_even.get("breakeven_revenue"))),
    ]
    payback = record.get("payback") or {}
    financial.append("Payback on owner equity: %s periods." % _money(payback.get("payback_periods"))
                     if payback else "Payback on owner equity is not reached within the horizon.")
    out.append(("Financial Plan", financial))

    risks = []
    cash = _gate(record, "H4")
    if cash and not cash.get("ok"):
        risks.append("Cash: the closing balance turns negative — " + str(cash.get("detail")))
    funding = _gate(record, "H1")
    if funding and not funding.get("ok"):
        risks.append("Funding: the declared sources do not equal the declared uses — " + str(funding.get("detail")))
    if break_even and revenue:
        peak = max(_d(revenue.get("revenue_%d" % i)) for i in range(1, 13)
                   if revenue.get("revenue_%d" % i) is not None) if any(
            revenue.get("revenue_%d" % i) is not None for i in range(1, 13)) else Decimal(0)
        if break_even.get("breakeven_revenue") and peak and _d(break_even["breakeven_revenue"]) > peak:
            risks.append("Demand: break-even revenue is %s a month against a planned peak of %s." % (
                _money(break_even["breakeven_revenue"]), _money(peak)))
    if not risks:
        risks.append("No check failed; the three largest risks remain demand below the ramp, "
                     "cost escalation and debt service.")
    out.append(("Risk Analysis and Mitigation", risks))

    out.append(("Implementation Timeline and Milestones", [
        "The case does not state opening dates or milestones, so none are invented.",
    ]))
    out.append(("Appendices", [
        "The workbook carries the tables: startup budget, sources and uses, monthly and annual "
        "statements, loan schedule, break-even, sensitivity, ratios and the checks.",
    ]))
    return out
