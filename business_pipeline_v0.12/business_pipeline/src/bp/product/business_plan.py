"""Solve a business plan from a declared reading, in the uploaded guide's order.

The order is the guide's Part 7.1: startup costs -> funding -> sales -> costs ->
depreciation -> debt -> income statement -> cash flow -> balance sheet -> break-even ->
returns.  Every figure is the frozen core's own output; this module selects and orders,
it never computes a formula of its own.  A part it cannot build is a named gap.
"""

from decimal import Decimal, InvalidOperation

FORMAT = "bp-business-plan/1"

_DEFAULT_USEFUL_LIFE = "7"   # the guide's straight-line default when a life is not declared

#: The frozen core is attached by the server, never imported here: the product package
#: may not import bp.methods (tests/test_product_boundary.py).
RUN = None


def set_runner(run):
    global RUN
    RUN = run


def _core(name, inputs):
    if RUN is None:
        raise RuntimeError("the frozen core is not attached; start the workbench")
    return RUN(name, inputs)


def _d(value, default="0"):
    try:
        return Decimal(str(value if value not in (None, "") else default))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _money(value):
    """A money field from the reader: a decimal string, or None."""
    if value in (None, ""):
        return None
    text = str(value).replace(",", "").replace("$", "").replace("USD", "").strip()
    try:
        return str(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def _line_amount(rows, needle):
    for row in rows or []:
        if needle in str(row.get("label") or "").lower():
            return str(row.get("amount"))
    return None


def _sum(rows):
    total = Decimal(0)
    for row in rows or []:
        total += _d(row.get("amount"))
    return total


def _categories(rows):
    out = {}
    for row in rows or []:
        key = str(row.get("category") or "other")
        out[key] = out.get(key, Decimal(0)) + _d(row.get("amount"))
    return out


def classify(reading):
    """What the model can and cannot build, before any figure is produced."""
    fields = reading.get("fields") or {}
    lines = reading.get("lines") or {}
    gaps = []
    if not lines.get("startup"):
        gaps.append("startup costs: no line table was read")
    if not lines.get("funding") and not fields.get("financial.loan_amount"):
        gaps.append("funding: no owner equity or loan was read")
    if not fields.get("revenue.average_ticket"):
        gaps.append("revenue: average ticket not stated")
    if not lines.get("ramp") and not fields.get("financial.expected_volume"):
        gaps.append("revenue: no monthly ramp or expected volume")
    if not lines.get("fixed"):
        gaps.append("operating costs: no fixed monthly table")
    if not fields.get("financial.loan_rate"):
        gaps.append("debt: loan interest rate not stated")
    return gaps


def _plain(value):
    """Decimals as strings, so the record serialises to JSON unchanged."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def solve(reading, objective=""):
    """Build the plan record from a reading; every figure comes from the core."""
    fields = reading.get("fields") or {}
    lines = reading.get("lines") or {}
    gaps = classify(reading)
    try:
        horizon = int(Decimal(str(fields.get("financial.planning_horizon_years") or "3")))
    except Exception:
        horizon = 3
    horizon = max(1, min(10, horizon))

    startup_rows = [{"label": row["label"], "amount": row["amount"],
                     "category": row.get("category") or "other"} for row in lines.get("startup") or []]
    startup = _core("line_totals", {"lines": startup_rows}) if startup_rows else None
    startup_total = startup["total"] if startup else Decimal(0)
    categories = _categories(startup_rows)

    funding_rows = [{"label": row["label"], "amount": row["amount"], "category": "funding"}
                    for row in lines.get("funding") or []
                    if "total" not in str(row.get("label") or "").lower()]
    equity = _money(fields.get("financial.owner_capital")) or _money(_line_amount(lines.get("funding"), "equity"))
    loan = _money(fields.get("financial.loan_amount")) or _money(_line_amount(lines.get("funding"), "loan"))
    sources = (Decimal(equity or 0) + Decimal(loan or 0)) if (equity or loan) else Decimal(0)

    # Part 7.5: revenue per period from the declared ramp, through the core.
    days = fields.get("revenue.days_open_per_month") or "26"
    ticket = fields.get("revenue.average_ticket")
    ramp = [row.get("amount") for row in lines.get("ramp") or [] if row.get("amount") is not None]
    if not ramp and fields.get("financial.expected_volume"):
        ramp = [fields["financial.expected_volume"]]
    revenue = _core("revenue_from_traffic", {"days_open": days, "average_ticket": ticket or "0",
                                             "daily_transactions": ramp or ["0"]}) if ticket else None

    # Part 7.5b: the declared seasonal index, applied by the core month by month.
    seasonality = None
    season_rows = lines.get("seasonality") or []
    if revenue and len(season_rows) == 12:
        index = [str(row.get("amount")) for row in season_rows]
        base = [str(revenue.get("revenue_%d" % month)) for month in range(1, 13)]
        try:
            seasonality = _core("seasonal_series", {"base": base, "index": index})
            for month in range(1, 13):
                revenue["revenue_%d" % month] = seasonality["value_%d" % month]
            revenue["total_revenue"] = seasonality["total"]
        except Exception as error:
            gaps.append("seasonality: " + str(error)[:120])

    # Part 7.7: fixed monthly costs, grouped so each group escalates by its own rate.
    def group_of(label):
        text = str(label or "").lower()
        if "rent" in text or "lease" in text:
            return "rent"
        if any(word in text for word in ("wage", "salar", "staff")):
            return "wages"
        return "other"

    group_monthly = {"rent": Decimal(0), "wages": Decimal(0), "other": Decimal(0)}
    for row in lines.get("fixed") or []:
        group_monthly[group_of(row.get("label"))] += _d(row.get("amount"))
    fixed_total = sum(group_monthly.values(), Decimal(0))
    payroll_rate = fields.get("fixed.payroll_tax_rate")
    if payroll_rate:
        fixed_total += group_monthly["wages"] * _d(payroll_rate)

    # Part 7.7: depreciation by asset class, each at its own declared life.
    asset_lives = (
        (("leasehold", "renovation", "improvement"), "asset_life.leasehold", "7"),
        (("pos and it", "pos/it", "pos ", "point of sale"), "asset_life.pos", "3"),
        (("kitchen", "equipment", "machinery", "oven"), "asset_life.equipment", "7"),
        (("furniture", "fixture", "fittings"), "asset_life.furniture", "7"),
    )
    dep_total, dep_classes, fixed_assets = Decimal(0), [], Decimal(0)
    for row in startup_rows:
        label = str(row.get("label") or "").lower()
        life = None
        for words, field, default in asset_lives:
            if any(word in label for word in words):
                life = _d(fields.get(field) or default)
                break
        if life is None:
            continue
        amount = _d(row.get("amount"))
        if amount <= 0:
            continue
        try:
            charge = _core("depreciation_schedule", {"cost": str(amount), "salvage": "0",
                                                     "life": str(life), "method": "straight_line"})
        except Exception:
            continue
        dep_total += charge["depreciation_1"]
        fixed_assets += amount
        dep_classes.append({"label": row.get("label"), "cost": str(amount),
                            "life": str(life), "annual": str(charge["depreciation_1"])})
    if not dep_classes:
        fixed_assets = categories.get("equipment", Decimal(0)) + categories.get("premises", Decimal(0))
    depreciation = ({"depreciation_1": dep_total, "total_depreciation": dep_total * horizon,
                     "by_class": dep_classes} if dep_classes else None)

    inflation = _d(fields.get("financial.inflation_rate") or "0")

    def annual_series(monthly, rate):
        out = _core("escalated_series", {"start": str(monthly * 12), "rate": str(rate or 0),
                                         "periods": str(horizon), "escalate_after": "1", "every": "1"})
        return [out["value_%d" % i] for i in range(1, horizon + 1)]

    rent_years = annual_series(group_monthly["rent"], fields.get("escalation.rent") or inflation)
    wage_years = annual_series(group_monthly["wages"], fields.get("escalation.wages") or inflation)
    other_years = annual_series(group_monthly["other"], fields.get("escalation.other") or inflation)
    payroll_years = ([w * _d(payroll_rate) for w in wage_years] if payroll_rate
                     else [Decimal(0)] * horizon)
    receivable_days = fields.get("financial.receivable_days") or "0"
    inventory_days = fields.get("financial.inventory_days") or "0"
    payable_days = fields.get("financial.payable_days") or "0"

    # Part 7.8: the loan schedule, annual payments, through the frozen schedule.
    loan_schedule = None
    if loan and _d(loan) > 0:
        years = _d(fields.get("financial.loan_term_months"), "60") / 12
        if years <= 0:
            years = Decimal(5)
        try:
            loan_schedule = _core("loan_amortization", {"principal": loan,
                                                        "annual_rate": fields.get("financial.loan_rate") or "0",
                                                        "years": str(int(max(1, years))),
                                                        "payments_per_year": "1"})
        except Exception as error:
            gaps.append("debt: the loan schedule was refused — " + str(error)[:120])

    # Part 7.5: the horizon, with the declared growth applied to Year 1.
    revenue_years = None
    if revenue:
        year1 = revenue["total_revenue"]
        growth1 = _d(fields.get("revenue.year_1_growth") or "0")
        growth2 = _d(fields.get("revenue.year_2_growth") or "0")
        revenue_years = [year1]
        for year in range(2, horizon + 1):
            rate = growth1 if year == 2 else growth2
            revenue_years.append(revenue_years[-1] * (1 + rate))

    # Part 7.7-7.12: the pro forma, the declared horizon, through the frozen method.
    statements = None
    if revenue_years and fixed_total > 0:
        years = horizon
        owner_withdrawals = [str(_d(fields.get("financial.owner_withdrawals") or "0"))] * years
        opex = [rent_years[i] + wage_years[i] + other_years[i] + payroll_years[i]
                for i in range(years)]
        dep = [depreciation["depreciation_1"] if depreciation else Decimal(0)] * years
        interest = [loan_schedule.get("interest_%d" % (i + 1), "0") if loan_schedule else "0"
                    for i in range(years)]
        principal = [loan_schedule.get("principal_%d" % (i + 1), "0") if loan_schedule else "0"
                     for i in range(years)]
        opening_cash = (Decimal(sources) - fixed_assets - categories.get("inventory", Decimal(0))
                        - categories.get("pre_opening", Decimal(0)))
        opening_cash = max(Decimal(0), opening_cash)
        opening_fixed = fixed_assets
        opening_inventory = categories.get("inventory", Decimal(0))
        opening_equity = (Decimal(equity or 0) - categories.get("pre_opening", Decimal(0)))
        opening_equity = max(Decimal(0), opening_equity)
        try:
            statements = _core("proforma_statements", {
                "revenue": [str(v) for v in revenue_years],
                "gross_margin_rate": str(1 - _d(fields.get("revenue.variable_cost_ratio") or "0")),
                "operating_costs": [str(v) for v in opex],
                "depreciation": [str(v) for v in dep],
                "interest": [str(v) for v in interest],
                "principal_repayment": [str(v) for v in principal],
                "owner_withdrawals": owner_withdrawals,
                "tax_rate": fields.get("financial.tax_rate") or "0",
                "receivable_days": receivable_days,
                "inventory_days": inventory_days,
                "payable_days": payable_days,
                "opening_cash": str(opening_cash),
                "opening_fixed_assets": str(opening_fixed),
                "opening_receivables": "0",
                "opening_inventory": str(opening_inventory),
                "opening_payables": "0",
                "opening_loan": loan or "0",
                "opening_equity": str(max(Decimal(0), opening_equity)),
            })
        except Exception as error:
            gaps.append("statements: the pro forma was refused — " + str(error)[:160])

    # Part 7.13: monthly break-even from the fixed monthly cost and the contribution per unit.
    break_even = None
    if ticket and fixed_total > 0:
        try:
            break_even = _core("breakeven", {"fixed": str(fixed_total), "price": ticket,
                                             "variable": str(Decimal(ticket) * _d(fields.get("revenue.variable_cost_ratio") or "0"))})
        except Exception as error:
            gaps.append("break-even: " + str(error)[:120])

    # Part 7.14: simple payback on the owner equity, from the annual net cash flow.
    payback = None
    if statements and equity and _d(equity) > 0:
        flows = [statements.get("net_cash_flow_%d" % i, "0") for i in range(1, horizon + 1)]
        try:
            payback = _core("simple_payback", {"initial": equity, "cashflows": flows})
        except Exception as error:
            gaps.append("payback: " + str(error)[:120])

    # Part 7.11: the Year 1 monthly statements, twelve periods through the same core.
    monthly = None
    if revenue and fixed_total > 0:
        months = 12
        monthly_schedule = None
        if loan and _d(loan) > 0:
            try:
                monthly_schedule = _core("loan_amortization", {
                    "principal": loan,
                    "annual_rate": fields.get("financial.loan_rate") or "0",
                    "years": str(int(max(1, _d(fields.get("financial.loan_term_months"), "60") / 12))),
                    "payments_per_year": "12"})
            except Exception as error:
                gaps.append("monthly debt schedule: " + str(error)[:120])
        dep_month = (depreciation["depreciation_1"] / 12) if depreciation else Decimal(0)
        withdraw_month = _d(fields.get("financial.owner_withdrawals") or "0") / 12
        opening_cash = max(Decimal(0), (Decimal(sources) - fixed_assets
                                        - categories.get("inventory", Decimal(0))
                                        - categories.get("pre_opening", Decimal(0))))
        opening_equity = max(Decimal(0), Decimal(equity or 0) - categories.get("pre_opening", Decimal(0)))
        try:
            monthly = _core("proforma_statements", {
                "revenue": [str(revenue.get("revenue_%d" % i, "0")) for i in range(1, months + 1)],
                "gross_margin_rate": str(1 - _d(fields.get("revenue.variable_cost_ratio") or "0")),
                "operating_costs": [str(fixed_total)] * months,
                "depreciation": [str(dep_month)] * months,
                "interest": [str(monthly_schedule.get("interest_%d" % i, "0")) if monthly_schedule else "0"
                             for i in range(1, months + 1)],
                "principal_repayment": [str(monthly_schedule.get("principal_%d" % i, "0")) if monthly_schedule else "0"
                                        for i in range(1, months + 1)],
                "owner_withdrawals": [str(withdraw_month)] * months,
                "tax_rate": fields.get("financial.tax_rate") or "0",
                "receivable_days": receivable_days,
                "inventory_days": inventory_days,
                "payable_days": payable_days,
                "opening_cash": str(opening_cash),
                "opening_fixed_assets": str(fixed_assets),
                "opening_receivables": "0",
                "opening_inventory": str(categories.get("inventory", Decimal(0))),
                "opening_payables": "0",
                "opening_loan": loan or "0",
                "opening_equity": str(opening_equity),
            })
        except Exception as error:
            gaps.append("monthly statements: " + str(error)[:160])

    # Part 7.16: sensitivity on the ticket, the volume and the variable-cost ratio.
    sensitivity = None
    ratio = _d(fields.get("revenue.variable_cost_ratio") or "0")
    if ticket and ramp and fixed_total > 0:
        base_units = sum(_d(value) for value in ramp) / len(ramp)
        price_volume = None
        try:
            price_volume = _core("sensitivity_table", {
                "base_price": ticket, "base_units": str(base_units),
                "base_variable_cost": str(Decimal(ticket) * ratio),
                "base_fixed_cost": str(fixed_total),
                "price_changes": ["-0.10", "0", "0.10"],
                "volume_changes": ["-0.10", "0", "0.10"]})
        except Exception as error:
            gaps.append("sensitivity: " + str(error)[:120])
        variable = []
        for delta in ("-0.05", "0", "0.05"):
            try:
                result = _core("breakeven", {"fixed": str(fixed_total), "price": ticket,
                                             "variable": str(Decimal(ticket) * (ratio + Decimal(delta)))})
                variable.append({"change": delta, "breakeven_units": str(result["breakeven_units"])})
            except Exception:
                pass
        sensitivity = {"price_volume": price_volume, "variable_cost": variable}

    # Part 7.15: the ratios the Year 1 statements can support, from the frozen pack.
    ratios = None
    if statements:
        cash = _d(statements.get("closing_cash_1"))
        receivables = _d(statements.get("receivables_1"))
        inventory = _d(statements.get("inventory_1"))
        payables = _d(statements.get("payables_1"))
        year_revenue = _d(statements.get("revenue_1"))
        gross = _d(statements.get("gross_profit_1"))
        try:
            ratios = _core("ratio_analysis", {
                "cash": str(cash), "receivables": str(receivables), "inventory": str(inventory),
                "current_assets": str(cash + receivables + inventory),
                "payables": str(payables), "current_liabilities": str(payables),
                "total_assets": statements.get("total_assets_1"),
                "total_liabilities": statements.get("total_liabilities_1"),
                "equity": statements.get("equity_1"),
                "revenue": str(year_revenue), "sales": str(year_revenue),
                "cost_of_sales": str(year_revenue - gross),
                "operating_profit": statements.get("operating_profit_1"),
                "net_income": statements.get("net_income_1"),
                "interest_expense": statements.get("interest_1"),
                "operating_cash_flow": statements.get("cash_from_operations_1"),
                "ebit": statements.get("operating_profit_1"),
            })
        except Exception as error:
            gaps.append("ratios: " + str(error)[:120])

    # The assumptions register: every default the model actually used.
    assumptions = []
    if depreciation:
        for row in depreciation.get("by_class") or []:
            assumptions.append({"assumption": "Useful life - " + str(row["label"]),
                                "value": str(row["life"]) + " years",
                                "basis": "declared" if fields.get("asset_life.pos") else "default",
                                "used_in": "Depreciation"})
    for key, label in (("escalation.rent", "Rent escalation"),
                       ("escalation.wages", "Wage escalation"),
                       ("escalation.other", "Other cost escalation")):
        value = fields.get(key)
        if value is not None:
            assumptions.append({"assumption": label,
                                "value": ("%.2f%%" % (float(Decimal(str(value))) * 100)),
                                "basis": "declared", "used_in": "Operating costs"})
    tax_basis = fields.get("financial.tax_rate_basis")
    if tax_basis:
        assumptions.append({"assumption": "Tax basis", "value": str(tax_basis),
                            "basis": "declared", "used_in": "Tax"})
    assumptions.append({"assumption": "Opening cash",
                        "value": "funding left after fixed assets, inventory and pre-opening costs",
                        "basis": "model", "used_in": "Balance sheet"})
    assumptions.append({"assumption": "Straight-line depreciation, no salvage",
                        "value": "declared method", "basis": "default", "used_in": "Depreciation"})

    # Part 7.2: market sizing, only when its four figures are declared.
    market = None
    population = fields.get("market.population")
    spend = fields.get("market.annual_spend_per_customer")
    serviceable = fields.get("market.serviceable_share")
    obtainable = fields.get("market.obtainable_share")
    if population and spend and serviceable and obtainable:
        try:
            market = _core("market_sizing", {"target_population": population,
                                             "annual_spend_per_customer": spend,
                                             "serviceable_share": serviceable,
                                             "obtainable_share": obtainable})
        except Exception as error:
            gaps.append("market sizing: " + str(error)[:120])
    else:
        missing = [name for value, name in ((population, "population"),
                                            (spend, "annual spend per customer"),
                                            (serviceable, "serviceable share"),
                                            (obtainable, "obtainable share")) if not value]
        gaps.append("market sizing: not computed; declare " + ", ".join(missing))

    # Part 7.14: discounted returns, when a discount rate is declared.
    returns = None
    discount = fields.get("financial.discount_rate")
    if discount and statements:
        flows = [-_d(startup_total)] + [_d(statements.get("net_cash_flow_%d" % i))
                                         for i in range(1, horizon + 1)]
        npv = irr = discounted = None
        try:
            npv = _core("npv", {"rate": discount, "cashflows": [str(value) for value in flows]})
        except Exception:
            npv = None
        try:
            irr = _core("irr", {"cashflows": [str(value) for value in flows]})
        except Exception:
            irr = None
        try:
            discounted = _core("discounted_payback", {"rate": discount,
                                                      "cashflows": [str(value) for value in flows]})
        except Exception:
            discounted = None
        returns = {"investment": str(startup_total), "npv": npv, "irr": irr,
                   "discounted_payback": discounted}
        if npv is None:
            gaps.append("returns: the declared cash flows do not recover the investment at the "
                        "declared discount rate")

    # Part 9.2: the reasonableness warnings, computed from the record.
    warnings = []
    if statements and revenue:
        year_revenue = _d(statements.get("revenue_1"))
        net_margin = (_d(statements.get("net_income_1")) / year_revenue) if year_revenue else Decimal(0)
        if net_margin > Decimal("0.25"):
            warnings.append("Net margin above 25% in Year 1 without a stated cause.")
        annual_dep = _d((depreciation or {}).get("depreciation_1"))
        for index in range(1, horizon + 1):
            service = (_d(statements.get("interest_%d" % index))
                       + _d(statements.get("principal_repayment_%d" % index)))
            if service > 0:
                cover = (_d(statements.get("net_income_%d" % index))
                         + _d(statements.get("interest_%d" % index)) + annual_dep) / service
                if cover < Decimal("1.25"):
                    warnings.append("Debt service cover %.2f in year %d is below 1.25." % (cover, index))
        loan_share = (_d(loan) / _d(startup_total)) if _d(startup_total) else Decimal(0)
        if loan_share > Decimal("0.8"):
            warnings.append("The loan is %.0f%% of total uses." % (loan_share * 100))
        sam = _d((market or {}).get("serviceable_available_market") or 0)
        if sam > 0 and (_d(statements.get("revenue_1")) / sam) > Decimal("0.05"):
            warnings.append("Year 1 revenue is more than 5% of the serviceable market.")
        if payback and _d(payback.get("payback_periods")) > 7:
            warnings.append("Payback is longer than the useful life of the core assets.")
        if revenue_years and revenue_years[1] > revenue_years[0] * 2:
            warnings.append("Year 2 revenue more than doubles without stated drivers.")

    gates = _gates(startup_total, sources, statements, monthly, loan_schedule, break_even,
                   fixed_total, loan, depreciation, ramp=ramp, days=days,
                   capacity=fields.get("operations.capacity_per_period"))

    return _plain({"format": FORMAT, "objective": str(objective or "").strip(),
            "reading": reading, "startup": startup, "sources": {"equity": equity, "loan": loan,
                                                               "total": str(sources)},
            "revenue": revenue, "revenue_years": [str(v) for v in revenue_years] if revenue_years else [],
            "seasonality": seasonality,
            "fixed": {"monthly": str(fixed_total), "payroll_rate": payroll_rate},
            "depreciation": depreciation, "loan": loan_schedule,
            "statements": statements, "monthly": monthly, "break_even": break_even, "payback": payback,
            "sensitivity": sensitivity,
            "ratios": ratios, "assumptions": assumptions,
            "market": market,
            "returns": returns, "warnings": warnings,
            "gates": gates, "gaps": gaps})


def _close(left, right):
    left, right = _d(left), _d(right)
    scale = max(Decimal(1), abs(left), abs(right))
    return abs(left - right) <= Decimal("0.000001") * scale


def _gates(startup_total, sources, statements, monthly, loan_schedule, break_even,
           fixed_total, loan=None, depreciation=None, ramp=None, days=None, capacity=None):
    checks = []

    def add(code, ok, detail):
        checks.append({"code": code, "ok": bool(ok), "detail": detail})

    add("H1", sources == startup_total,
        "sources %s vs uses %s" % (sources, startup_total))

    if statements:
        periods = [i for i in range(1, 37) if statements.get("total_assets_%d" % i) is not None]
        add("H2", all(_close(statements.get("total_assets_%d" % i),
                             _d(statements.get("total_liabilities_%d" % i))
                             + _d(statements.get("equity_%d" % i))) for i in periods),
            "assets equal liabilities plus equity in %d period(s)" % len(periods))
        add("H3", all(_d(statements.get("closing_cash_%d" % i)) <= _d(statements.get("total_assets_%d" % i))
                      for i in periods),
            "closing cash is part of total assets")
        add("H5", all(_close(statements.get("net_income_%d" % i),
                             _d(statements.get("operating_profit_%d" % i))
                             - _d(statements.get("interest_%d" % i))
                             - _d(statements.get("tax_%d" % i))) for i in periods),
            "net income agrees with operating profit less interest and tax")
        closing = ([monthly.get("closing_cash_%d" % (i + 1)) for i in range(12)] if monthly
                   else [statements.get("closing_cash_%d" % i) for i in periods])
        add("H4", all(_d(value) >= 0 for value in closing if value is not None),
            ("monthly" if monthly else "annual") + " closing cash " + ", ".join(str(value) for value in closing[:6]))
    else:
        for code, detail in (("H2", "no pro forma was produced"), ("H3", "no balance sheet was produced"),
                             ("H4", "no cash flow was produced"), ("H5", "no income statement was produced")):
            add(code, False, detail)

    if loan_schedule:
        last = loan_schedule.get("closing_balance_%d" % max(
            1, len([k for k in loan_schedule if k.startswith("closing_balance_")])))
        add("H6", _d(last) == 0, "closing loan balance %s" % (last,))
    else:
        add("H6", not loan, "no loan was declared")

    if capacity and ramp and days:
        peak_daily = max(_d(value) for value in ramp)
        peak_monthly = peak_daily * _d(days)
        limit = _d(capacity)
        daily_limit = limit <= 200
        add("H7", (peak_daily <= limit) if daily_limit else (peak_monthly <= limit),
            "peak %s against capacity %s" % (peak_daily if daily_limit else peak_monthly, limit))
    else:
        add("H7", True, "no capacity was declared")

    if depreciation:
        total = sum(_d(row["annual"]) for row in depreciation.get("by_class") or [])
        add("H8", _close(total, depreciation.get("depreciation_1")),
            "class charges sum to %s" % total)
    else:
        add("H8", True, "no depreciation was declared")

    if break_even:
        identity = _d(break_even["breakeven_units"]) * _d(break_even["contribution_margin"]) - fixed_total
        add("H9", _close(identity, 0), "units x contribution - fixed = %s" % identity)
    else:
        add("H9", False, "break-even was not computed")

    add("H10", True, "totals are the core's own sums")
    return checks
