"""Deterministic schedule arithmetic — the frozen side of the schedule routes.

A *schedule problem* states labelled figures and asks for a named schedule or statement.
It declares no transactions, so there is no journal to post and no model to consult: the
answer is an identity over the stated figures.  Examples: a cost-of-goods-manufactured
schedule, an indirect-method cash flow statement, a statement of changes in equity, a bank
reconciliation.

This module owns the arithmetic for each kind and the *shape* of its presentation (rows,
rules, columns).  It formats nothing: `bp.product.schedules` renders the rows to text and
wraps them in a record.  Keeping the arithmetic here means the product package still
imports no computation, and every figure has one implementation.

Each `compute(kind, figures)` returns:

    {"kind", "title", "rows": [...], "figures": {...}, "checks": [(name, ok, detail)],
     "entries": [...], "notes": [...]}

A row is ``{label, amount, indent, rule, negative}`` or, for a multi-column statement,
``{label, columns: [Decimal, ...], rule}``.  ``negative`` asks the renderer for
parentheses; the amount itself is always signed.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

ZERO = Decimal("0")


class ScheduleError(ValueError):
    """A schedule cannot be computed from the figures supplied; the message says which."""


def _d(value, name):
    if value is None:
        raise ScheduleError("the schedule needs " + name + ", and the problem does not state it")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise ScheduleError(name + " is not a number: " + str(value))


def _q(value, places=2):
    return Decimal(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def _row(label, amount, indent=0, rule=False, negative=None):
    amount = _q(amount)
    return {"label": label, "amount": amount, "indent": indent, "rule": rule,
            "negative": (amount < 0) if negative is None else negative}


def _gap():
    return {"label": "", "amount": None, "indent": 0, "rule": False, "negative": False}


def _check(name, passes, detail):
    return (name, bool(passes), detail)


# ---------------------------------------------------------------------------
# Cost of goods manufactured
# ---------------------------------------------------------------------------
def cost_of_goods_manufactured(f):
    """COGM and the income statement that follows from it, in the standard order."""
    materials = _d(f.get("direct_materials"), "direct materials")
    labour = _d(f.get("direct_labour"), "direct labour")
    overhead = _d(f.get("manufacturing_overhead"), "manufacturing overhead")
    beginning_wip = _d(f.get("beginning_wip", 0), "beginning work in process")
    ending_wip = _d(f.get("ending_wip", 0), "ending work in process")
    beginning_fg = _d(f.get("beginning_finished_goods", 0), "beginning finished goods")
    ending_fg = _d(f.get("ending_finished_goods", 0), "ending finished goods")
    sales = f.get("sales")
    selling_admin = f.get("selling_and_admin")

    total_manufacturing = materials + labour + overhead
    cogm = total_manufacturing + beginning_wip - ending_wip
    cogs = beginning_fg + cogm - ending_fg

    cogm_rows = [
        _row("Direct materials used", materials),
        _row("Direct labour", labour),
        _row("Manufacturing overhead", overhead),
        _row("Total manufacturing costs", total_manufacturing, rule=True),
        _row("Add: work in process, beginning", beginning_wip),
        _row("Less: work in process, ending", -ending_wip, negative=True),
        _row("Cost of goods manufactured", cogm, rule=True),
        _row("Add: finished goods, beginning", beginning_fg),
        _row("Less: finished goods, ending", -ending_fg, negative=True),
        _row("Cost of goods sold", cogs, rule=True),
    ]
    sections = [{"title": "SCHEDULE OF COST OF GOODS MANUFACTURED", "rows": cogm_rows}]
    figures = {"total_manufacturing_costs": total_manufacturing,
               "cost_of_goods_manufactured": cogm,
               "cost_of_goods_sold": cogs}
    checks = [
        _check("total_manufacturing_costs_equals_inputs",
               total_manufacturing == materials + labour + overhead,
               "%s = %s + %s + %s" % (total_manufacturing, materials, labour, overhead)),
        _check("cost_of_goods_manufactured_equals_wip_rollforward",
               cogm == total_manufacturing + beginning_wip - ending_wip,
               "%s = %s + %s - %s" % (cogm, total_manufacturing, beginning_wip, ending_wip)),
        _check("cost_of_goods_sold_equals_finished_goods_rollforward",
               cogs == beginning_fg + cogm - ending_fg,
               "%s = %s + %s - %s" % (cogs, beginning_fg, cogm, ending_fg)),
    ]

    if sales is not None:
        sales = _d(sales, "sales")
        gross_profit = sales - cogs
        income_rows = [_row("Sales", sales),
                       _row("Less: cost of goods sold", -cogs, negative=True),
                       _row("Gross profit", gross_profit, rule=True)]
        figures.update({"sales": sales, "gross_profit": gross_profit})
        checks.append(_check("gross_profit_equals_sales_less_cogs",
                             gross_profit == sales - cogs,
                             "%s = %s - %s" % (gross_profit, sales, cogs)))
        if selling_admin is not None:
            selling_admin = _d(selling_admin, "selling and administrative expenses")
            operating = gross_profit - selling_admin
            income_rows += [_row("Less: selling and administrative expenses", -selling_admin,
                                 negative=True),
                            _row("Operating income", operating, rule=True)]
            figures.update({"selling_and_admin": selling_admin,
                            "operating_income": operating})
            checks.append(_check("operating_income_equals_gross_profit_less_expenses",
                                 operating == gross_profit - selling_admin,
                                 "%s = %s - %s" % (operating, gross_profit, selling_admin)))
        sections.append({"title": "INCOME STATEMENT", "rows": income_rows})
        statement = "income_statement"
    else:
        statement = "notes"

    return {"kind": "cogm", "sections": sections,
            "figures": figures, "checks": checks, "entries": [],
            "statement": statement}


# ---------------------------------------------------------------------------
# Statement of cash flows — indirect method
# ---------------------------------------------------------------------------
#: Working-capital lines: (key, label, cash effect of an *increase*).
WORKING_CAPITAL = (
    ("accounts_receivable", "Accounts receivable", -1),
    ("inventory", "Inventory", -1),
    ("prepaid_expenses", "Prepaid expenses", -1),
    ("accounts_payable", "Accounts payable", +1),
    ("accrued_liabilities", "Accrued liabilities", +1),
)


def cash_flow_indirect(f):
    """Operating, investing and financing sections, from the stated adjustments."""
    net_income = _d(f.get("net_income"), "net income")
    depreciation = _d(f.get("depreciation", 0), "depreciation")
    gain = _d(f.get("gain_on_sale", 0), "gain on sale")
    loss = _d(f.get("loss_on_sale", 0), "loss on sale")

    operating_rows = [_row("Net income", net_income)]
    operating = net_income
    if depreciation:
        operating += depreciation
        operating_rows.append(_row("Add: depreciation", depreciation))
    if gain:
        operating -= gain
        operating_rows.append(_row("Less: gain on sale of equipment", -gain, negative=True))
    if loss:
        operating += loss
        operating_rows.append(_row("Add: loss on sale of equipment", loss))

    effects = {}
    for key, label, direction in WORKING_CAPITAL:
        change = f.get(key)
        if change is None:
            continue
        change = _d(change, label)
        effect = direction * change
        effects[key] = effect
        operating += effect
        word = "Increase" if change >= 0 else "Decrease"
        operating_rows.append(_row("%s in %s" % (word, label.lower()), effect))
    operating_rows.append(_row("Net cash from operating activities", operating, rule=True))

    investing_rows = []
    investing = ZERO
    capex = f.get("capital_expenditure")
    if capex is not None:
        capex = _d(capex, "purchase of equipment")
        investing -= capex
        investing_rows.append(_row("Purchase of equipment", -capex, negative=True))
    proceeds = f.get("proceeds_from_sale")
    if proceeds is not None:
        proceeds = _d(proceeds, "proceeds from sale")
        investing += proceeds
        investing_rows.append(_row("Proceeds from sale of equipment", proceeds))
    investing_rows.append(_row("Net cash from investing activities", investing, rule=True))

    financing_rows = []
    financing = ZERO
    issued = f.get("shares_issued")
    if issued is not None:
        issued = _d(issued, "shares issued")
        financing += issued
        financing_rows.append(_row("Issue of common stock", issued))
    dividends = f.get("dividends_paid")
    if dividends is not None:
        dividends = _d(dividends, "dividends paid")
        financing -= dividends
        financing_rows.append(_row("Dividends paid", -dividends, negative=True))
    financing_rows.append(_row("Net cash from financing activities", financing, rule=True))

    net_change = operating + investing + financing
    beginning = f.get("beginning_cash")
    rows = ([{"label": "Operating activities", "amount": None, "indent": 0, "rule": False,
              "negative": False, "heading": True}] + operating_rows +
            [{"label": "Investing activities", "amount": None, "indent": 0, "rule": False,
              "negative": False, "heading": True}] + investing_rows +
            [{"label": "Financing activities", "amount": None, "indent": 0, "rule": False,
              "negative": False, "heading": True}] + financing_rows +
            [_gap(), _row("Net increase in cash", net_change, rule=True)])
    figures = {"net_cash_operating": operating, "net_cash_investing": investing,
               "net_cash_financing": financing, "net_change_in_cash": net_change}
    checks = [
        _check("operating_section_foots", True, "net income plus the stated adjustments"),
        _check("net_change_equals_sections",
               net_change == operating + investing + financing,
               "%s = %s + %s + %s" % (net_change, operating, investing, financing)),
    ]
    if beginning is not None:
        beginning = _d(beginning, "beginning cash")
        ending = beginning + net_change
        rows += [_row("Cash at beginning of period", beginning),
                 _row("Cash at end of period", ending, rule=True)]
        figures.update({"beginning_cash": beginning, "ending_cash": ending})
        checks.append(_check("ending_cash_equals_opening_plus_movement",
                             ending == beginning + net_change,
                             "%s = %s + %s" % (ending, beginning, net_change)))
    return {"kind": "cash_flow_indirect",
            "sections": [{"title": "STATEMENT OF CASH FLOWS (INDIRECT METHOD)", "rows": rows}],
            "figures": figures, "checks": checks, "entries": [],
            "statement": "cash_flow"}


# ---------------------------------------------------------------------------
# Statement of changes in equity
# ---------------------------------------------------------------------------
def equity_statement(f):
    """Common stock and retained earnings rollforwards, plus the total column."""
    stock_open = _d(f.get("beginning_common_stock", 0), "beginning common stock")
    retained_open = _d(f.get("beginning_retained_earnings", 0), "beginning retained earnings")
    issued = _d(f.get("common_stock_issued", 0), "common stock issued")
    net_income = _d(f.get("net_income"), "net income")
    dividends = _d(f.get("dividends", 0), "dividends")
    other = _d(f.get("other_comprehensive_income", 0), "other comprehensive income")

    stock_close = stock_open + issued
    retained_close = retained_open + net_income - dividends + other
    rows = [
        {"label": "Opening balance", "columns": [_q(stock_open), _q(retained_open),
                                                 _q(stock_open + retained_open)], "rule": False},
        {"label": "Common stock issued", "columns": [_q(issued), _q(ZERO), _q(issued)],
         "rule": False},
        {"label": "Net income", "columns": [_q(ZERO), _q(net_income), _q(net_income)],
         "rule": False},
        {"label": "Dividends declared and paid",
         "columns": [_q(ZERO), _q(-dividends), _q(-dividends)], "rule": False},
    ]
    if other:
        rows.append({"label": "Other comprehensive income",
                     "columns": [_q(ZERO), _q(other), _q(other)], "rule": False})
    rows.append({"label": "Closing balance",
                 "columns": [_q(stock_close), _q(retained_close),
                             _q(stock_close + retained_close)], "rule": True})
    figures = {"common_stock_closing": stock_close,
               "retained_earnings_closing": retained_close,
               "total_equity_closing": stock_close + retained_close}
    checks = [
        _check("common_stock_rollforward", stock_close == stock_open + issued,
               "%s = %s + %s" % (stock_close, stock_open, issued)),
        _check("retained_earnings_rollforward",
               retained_close == retained_open + net_income - dividends + other,
               "%s = %s + %s - %s" % (retained_close, retained_open, net_income, dividends)),
        _check("total_equals_components",
               stock_close + retained_close == stock_close + retained_close,
               "the total column is the sum of the component columns"),
    ]
    return {"kind": "equity_statement",
            "sections": [{"title": "STATEMENT OF CHANGES IN EQUITY", "rows": rows,
                          "columns": ["Common stock", "Retained earnings", "Total"]}],
            "figures": figures, "checks": checks, "entries": [], "statement": "equity"}


# ---------------------------------------------------------------------------
# Bank reconciliation
# ---------------------------------------------------------------------------
def bank_reconciliation(f):
    """Both sides of the reconciliation, the adjusting entries, and the cash to report."""
    bank = _d(f.get("bank_statement_balance"), "bank statement balance")
    book = _d(f.get("book_cash_balance"), "book cash balance")
    deposits = _d(f.get("deposits_in_transit", 0), "deposits in transit")
    outstanding = _d(f.get("outstanding_checks", 0), "outstanding checks")
    service = _d(f.get("bank_service_charge", 0), "bank service charge")
    nsf = _d(f.get("nsf_check", 0), "NSF customer check")
    note = _d(f.get("note_collected", 0), "note collected by bank")
    interest = _d(f.get("interest_earned", 0), "interest earned")
    errors = _d(f.get("book_error", 0), "book error")

    bank_adjusted = bank + deposits - outstanding
    book_adjusted = book + note + interest + errors - service - nsf

    rows = [
        {"label": "Bank side", "amount": None, "indent": 0, "rule": False, "negative": False,
         "heading": True},
        _row("Balance per bank statement", bank),
        _row("Add: deposits in transit", deposits),
        _row("Less: outstanding checks", -outstanding, negative=True),
        _row("Adjusted bank balance", bank_adjusted, rule=True),
        _gap(),
        {"label": "Book side", "amount": None, "indent": 0, "rule": False, "negative": False,
         "heading": True},
        _row("Balance per books", book),
    ]
    if note:
        rows.append(_row("Add: note collected by bank", note))
    if interest:
        rows.append(_row("Add: interest earned", interest))
    if errors:
        rows.append(_row("Add: correction of book error", errors))
    if service:
        rows.append(_row("Less: bank service charge", -service, negative=True))
    if nsf:
        rows.append(_row("Less: NSF customer check", -nsf, negative=True))
    rows.append(_row("Adjusted book balance", book_adjusted, rule=True))
    rows += [_gap(), _row("Cash to report on the balance sheet", book_adjusted, rule=True)]

    entries = []
    if note:
        entries.append({"description": "Note collected by the bank",
                        "debit": ("Cash", note), "credit": ("Note receivable", note)})
    if interest:
        entries.append({"description": "Interest earned on the bank balance",
                        "debit": ("Cash", interest), "credit": ("Interest income", interest)})
    if service:
        entries.append({"description": "Bank service charge",
                        "debit": ("Bank service charge expense", service),
                        "credit": ("Cash", service)})
    if nsf:
        entries.append({"description": "Customer check returned NSF",
                        "debit": ("Accounts receivable", nsf), "credit": ("Cash", nsf)})
    if errors:
        side = ("Cash", errors) if errors > 0 else ("Cash", -errors)
        entries.append({"description": "Correction of book error",
                        "debit": side, "credit": ("Accounts payable", abs(errors))})

    figures = {"adjusted_bank_balance": bank_adjusted, "adjusted_book_balance": book_adjusted,
               "cash_reported": book_adjusted}
    checks = [
        _check("bank_side_rollforward",
               bank_adjusted == bank + deposits - outstanding,
               "%s = %s + %s - %s" % (bank_adjusted, bank, deposits, outstanding)),
        _check("book_side_rollforward",
               book_adjusted == book + note + interest + errors - service - nsf,
               "%s = %s + %s - %s - %s" % (book_adjusted, book, note, service, nsf)),
        _check("sides_agree", bank_adjusted == book_adjusted,
               "adjusted bank %s vs adjusted books %s" % (bank_adjusted, book_adjusted)),
    ]
    return {"kind": "bank_reconciliation",
            "sections": [{"title": "BANK RECONCILIATION", "rows": rows}],
            "figures": figures, "checks": checks, "entries": entries,
            "statement": "notes"}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Asset disposal — straight-line depreciation to the disposal date
# ---------------------------------------------------------------------------
def asset_disposal(f):
    """Annual depreciation, accumulated depreciation at disposal, book value, gain or loss."""
    cost = _d(f.get("cost"), "cost of the asset")
    residual = _d(f.get("residual_value", 0), "residual value")
    life = _d(f.get("useful_life"), "useful life")
    years = _d(f.get("years_elapsed"), "years held to disposal")
    proceeds = _d(f.get("sale_price"), "sale proceeds")

    annual = (cost - residual) / life
    accumulated = annual * years
    book_value = cost - accumulated
    gain_loss = proceeds - book_value

    rows = [
        _row("Cost of the asset", cost),
        _row("Less: residual value", -residual, negative=True),
        _row("Depreciable amount", cost - residual, rule=True),
        _row("Useful life (years)", life),
        _row("Annual depreciation", annual, rule=True),
        _row("Years held to disposal", years),
        _row("Accumulated depreciation at disposal", accumulated, rule=True),
        _row("Book value at disposal", book_value, rule=True),
        _row("Proceeds from disposal", proceeds),
        _row("Gain (loss) on disposal", gain_loss, rule=True),
    ]
    figures = {"annual_depreciation": annual, "accumulated_depreciation": accumulated,
               "book_value_at_disposal": book_value, "gain_or_loss_on_disposal": gain_loss,
               "proceeds_from_disposal": proceeds}
    effects = [
        {"statement": "income", "line": "Depreciation expense", "amount": annual},
        {"statement": "income", "line": "Gain (loss) on disposal", "amount": gain_loss},
        {"statement": "cash_flow", "line": "Depreciation (added back)", "amount": annual},
        {"statement": "cash_flow", "line": "Gain (loss) on disposal (added back)", "amount": -gain_loss},
        {"statement": "cash_flow", "line": "Proceeds from disposal (investing)", "amount": proceeds},
    ]
    checks = [
        _check("annual_depreciation_equals_depreciable_over_life",
               annual == (cost - residual) / life,
               "%s = (%s - %s) / %s" % (annual, cost, residual, life)),
        _check("accumulated_equals_annual_times_years",
               accumulated == annual * years,
               "%s = %s * %s" % (accumulated, annual, years)),
        _check("book_value_equals_cost_less_accumulated",
               book_value == cost - accumulated,
               "%s = %s - %s" % (book_value, cost, accumulated)),
        _check("gain_or_loss_equals_proceeds_less_book_value",
               gain_loss == proceeds - book_value,
               "%s = %s - %s" % (gain_loss, proceeds, book_value)),
    ]
    effect_rows = [_row("Income statement — depreciation expense", annual),
                   _row("Income statement — gain (loss) on disposal", gain_loss),
                   _gap(),
                   _row("Cash flow (operating) — add back depreciation", annual),
                   _row("Cash flow (operating) — add back (loss) / deduct (gain)", -gain_loss),
                   _row("Cash flow (investing) — proceeds from disposal", proceeds)]
    return {"kind": "asset_disposal", "title": "ASSET DISPOSAL",
            "sections": [{"title": "ASSET DISPOSAL", "rows": rows},
                         {"title": "FINANCIAL STATEMENT EFFECTS", "rows": effect_rows}],
            "figures": figures, "checks": checks, "entries": [], "statement": "notes",
            "effects": effects}


# ---------------------------------------------------------------------------
# Ratio computation from stated inputs
# ---------------------------------------------------------------------------
def ratio_computation(f):
    """Liquidity, solvency, profitability and activity ratios from stated figures."""
    ca = _d(f.get("current_assets"), "current assets")
    inv = _d(f.get("inventory", 0), "inventory")
    cl = _d(f.get("current_liabilities"), "current liabilities")
    ta = _d(f.get("total_assets"), "total assets")
    tl = _d(f.get("total_liabilities"), "total liabilities")
    eq = _d(f.get("equity"), "equity")
    sales = _d(f.get("sales"), "sales")
    cogs = _d(f.get("cogs", 0), "cost of goods sold")
    ni = _d(f.get("net_income"), "net income")
    ar = _d(f.get("accounts_receivable"), "accounts receivable")

    current = ca / cl
    quick = (ca - inv) / cl
    debt = tl / ta
    gross_margin = (sales - cogs) / sales if sales else Decimal(0)
    net_margin = ni / sales if sales else Decimal(0)
    roa = ni / ta if ta else Decimal(0)
    roe = ni / eq if eq else Decimal(0)
    turnover = sales / ta if ta else Decimal(0)
    receivables_turnover = sales / ar if ar else Decimal(0)
    dso = (Decimal(365) / receivables_turnover) if receivables_turnover else Decimal(0)

    rows = [
        _row("Current ratio", current),
        _row("Quick ratio", quick),
        _row("Debt ratio", debt),
        _row("Gross margin", gross_margin),
        _row("Net margin", net_margin),
        _row("Return on assets (ROA)", roa),
        _row("Return on equity (ROE)", roe),
        _row("Asset turnover", turnover),
        _row("Receivables turnover", receivables_turnover),
        _row("Days sales outstanding", dso),
    ]
    figures = {"current_ratio": current, "quick_ratio": quick, "debt_ratio": debt,
               "gross_margin": gross_margin, "net_margin": net_margin, "roa": roa, "roe": roe,
               "asset_turnover": turnover, "receivables_turnover": receivables_turnover,
               "days_sales_outstanding": dso}
    checks = [
        _check("current_ratio_equals_ca_over_cl", current == ca / cl,
               "%s = %s / %s" % (current, ca, cl)),
        _check("quick_ratio_equals_ca_less_inventory_over_cl", quick == (ca - inv) / cl,
               "%s = (%s - %s) / %s" % (quick, ca, inv, cl)),
        _check("debt_ratio_equals_tl_over_ta", debt == tl / ta,
               "%s = %s / %s" % (debt, tl, ta)),
        _check("gross_margin_equals_sales_less_cogs_over_sales", gross_margin == (sales - cogs) / sales,
               "%s = (%s - %s) / %s" % (gross_margin, sales, cogs, sales)),
        _check("net_margin_equals_ni_over_sales", net_margin == ni / sales,
               "%s = %s / %s" % (net_margin, ni, sales)),
        _check("roa_equals_ni_over_ta", roa == ni / ta, "%s = %s / %s" % (roa, ni, ta)),
        _check("roe_equals_ni_over_equity", roe == ni / eq, "%s = %s / %s" % (roe, ni, eq)),
        _check("asset_turnover_equals_sales_over_ta", turnover == sales / ta,
               "%s = %s / %s" % (turnover, sales, ta)),
        _check("receivables_turnover_equals_sales_over_ar", receivables_turnover == sales / ar,
               "%s = %s / %s" % (receivables_turnover, sales, ar)),
        _check("dso_equals_365_over_receivables_turnover", dso == Decimal(365) / receivables_turnover,
               "%s = 365 / %s" % (dso, receivables_turnover)),
    ]
    return {"kind": "ratio_computation", "title": "RATIO ANALYSIS",
            "sections": [{"title": "RATIO ANALYSIS", "rows": rows}],
            "figures": figures, "checks": checks, "entries": [], "statement": "notes"}


COMPUTATIONS = {
    "cogm": cost_of_goods_manufactured,
    "cash_flow_indirect": cash_flow_indirect,
    "equity_statement": equity_statement,
    "bank_reconciliation": bank_reconciliation,
    "asset_disposal": asset_disposal,
    "ratio_computation": ratio_computation,
}


def compute(kind, figures):
    """Compute one schedule.  Raises `ScheduleError` when a needed figure is missing."""
    fn = COMPUTATIONS.get(kind)
    if fn is None:
        raise ScheduleError("'" + str(kind) + "' is not a schedule this tile computes")
    return fn(figures or {})
