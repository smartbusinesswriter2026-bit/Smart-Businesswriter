"""Domain invariants for tile computations.

A case checks that the method returns the numbers the case recorded.  This module
checks that those numbers are **internally consistent**: the accounting equation
balances, a ratio equals the division it is named after, the DuPont identity holds,
a break-even quantity follows from fixed cost and contribution, the weights of a
WACC sum to one, and so on.  An invariant is derived from the method's own
definition and the declared inputs, never from a new assumption.

The checks are deliberately tolerant (`rel_tol=1e-6`): the frozen methods carry
Decimal values at different precisions, and a trailing-digit difference is not a
defect.  A missing input or output key skips the invariant; a wrong relationship
fails it.
"""

import math


def _num(value):
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _input(inputs, name):
    return _num((inputs or {}).get(name))


def _value(result, name):
    return _num((result or {}).get(name))


def _close(left, right, rel=1e-6, absolute=1e-9):
    if left is None or right is None:
        return True
    return math.isclose(left, right, rel_tol=rel, abs_tol=absolute)


def _require(problems, condition, message):
    if not condition:
        # The prefix lets the case runner tell a case whose *own figures* are
        # inconsistent (an invalid fixture) from a method that returned a wrong
        # figure (a pipeline defect).
        problems.append("invalid input: " + message)


def _need(*values):
    return all(value is not None for value in values)


def _ratio_analysis(inputs, result, problems):
    assets, liabilities, equity = _input(inputs, "total_assets"), _input(inputs, "total_liabilities"), _input(inputs, "equity")
    if _need(assets, liabilities, equity):
        _require(problems, _close(assets, liabilities + equity),
                 "the accounting equation does not balance: assets %s != liabilities %s + equity %s"
                 % (assets, liabilities, equity))
    current_assets, current_liabilities = _input(inputs, "current_assets"), _input(inputs, "current_liabilities")
    inventory, cash = _input(inputs, "inventory"), _input(inputs, "cash")
    if _need(current_assets, current_liabilities) and current_liabilities:
        _require(problems, _close(_value(result, "current_ratio"), current_assets / current_liabilities),
                 "current_ratio does not equal current assets / current liabilities")
        if inventory is not None:
            _require(problems, _close(_value(result, "quick_ratio"), (current_assets - inventory) / current_liabilities),
                     "quick_ratio does not equal (current assets - inventory) / current liabilities")
        if cash is not None:
            _require(problems, _close(_value(result, "cash_ratio"), cash / current_liabilities),
                     "cash_ratio does not equal cash / current liabilities")
    revenue, cost = _input(inputs, "revenue"), _input(inputs, "cost_of_sales")
    net_income = _input(inputs, "net_income")
    if _need(revenue, cost) and revenue:
        _require(problems, _close(_value(result, "gross_margin"), (revenue - cost) / revenue),
                 "gross_margin does not equal (revenue - cost of sales) / revenue")
    if _need(net_income, revenue) and revenue:
        _require(problems, _close(_value(result, "net_margin"), net_income / revenue),
                 "net_margin does not equal net income / revenue")
    if _need(net_income, assets) and assets:
        _require(problems, _close(_value(result, "return_on_assets"), net_income / assets),
                 "return_on_assets does not equal net income / total assets")
    if _need(net_income, equity) and equity:
        _require(problems, _close(_value(result, "return_on_equity"), net_income / equity),
                 "return_on_equity does not equal net income / equity")
    if _need(assets, equity) and equity:
        _require(problems, _close(_value(result, "equity_multiplier"), assets / equity),
                 "equity_multiplier does not equal total assets / equity")
    if _need(liabilities, equity) and equity:
        _require(problems, _close(_value(result, "debt_to_equity"), liabilities / equity),
                 "debt_to_equity does not equal total liabilities / equity")
    if _need(revenue, assets) and assets:
        _require(problems, _close(_value(result, "asset_turnover"), revenue / assets),
                 "asset_turnover does not equal revenue / total assets")


def _dupont(inputs, result, problems):
    margin, turnover, multiplier = _value(result, "net_margin"), _value(result, "asset_turnover"), _value(result, "equity_multiplier")
    if _need(margin, turnover, multiplier):
        expected = margin * turnover * multiplier
        _require(problems, _close(_value(result, "roe_three_step"), expected),
                 "the DuPont identity does not hold: net margin x asset turnover x equity multiplier != ROE")
        _require(problems, _close(_value(result, "return_on_equity"), expected),
                 "return_on_equity does not equal the three-step DuPont product")
        _require(problems, _close(_value(result, "return_on_assets"), margin * turnover),
                 "return_on_assets does not equal net margin x asset turnover")
    if _need(multiplier) and multiplier:
        _require(problems, _close(_value(result, "equity_to_assets"), 1.0 / multiplier),
                 "equity_to_assets does not equal 1 / equity multiplier")


def _breakeven(inputs, result, problems):
    fixed, price, variable = _input(inputs, "fixed"), _input(inputs, "price"), _input(inputs, "variable")
    contribution = _value(result, "contribution_margin")
    if _need(price, variable):
        _require(problems, _close(contribution, price - variable),
                 "contribution_margin does not equal price - variable cost")
    if _need(fixed, contribution) and contribution:
        _require(problems, _close(_value(result, "breakeven_units"), fixed / contribution),
                 "breakeven_units does not equal fixed cost / contribution margin")
        if _need(price):
            _require(problems, _close(_value(result, "breakeven_revenue"), (fixed / contribution) * price),
                     "breakeven_revenue does not equal break-even units x price")
    if _need(contribution, price) and price:
        _require(problems, _close(_value(result, "contribution_margin_ratio"), contribution / price),
                 "contribution_margin_ratio does not equal contribution margin / price")


def _multi_breakeven(inputs, result, problems):
    fixed = _value(result, "fixed_costs")
    total = _value(result, "breakeven_total_units")
    weighted = _value(result, "weighted_contribution")
    if _need(fixed, total, weighted) and total:
        _require(problems, _close(fixed / total, weighted),
                 "weighted_contribution does not equal fixed costs / break-even total units")
    units = [_num(value) for name, value in (result or {}).items()
             if str(name).startswith("units_") and _num(value) is not None]
    if units and _need(total):
        _require(problems, _close(sum(units), total),
                 "the units by product do not sum to the break-even total units")


def _loan(inputs, result, problems):
    payment, periods = _value(result, "payment"), _value(result, "n_payments")
    principal = _value(result, "principal")
    if _need(payment, periods):
        _require(problems, _close(_value(result, "total_paid"), payment * periods),
                 "total_paid does not equal payment x number of payments")
    if _need(_value(result, "total_paid"), principal):
        _require(problems, _close(_value(result, "total_interest"), _value(result, "total_paid") - principal),
                 "total_interest does not equal total paid - principal")
    rate, first_interest = _value(result, "periodic_rate"), _value(result, "first_interest")
    if _need(principal, rate):
        _require(problems, _close(first_interest, principal * rate),
                 "first_interest does not equal principal x periodic rate")
    if _need(payment, first_interest):
        _require(problems, _close(_value(result, "first_principal"), payment - first_interest),
                 "first_principal does not equal payment - first interest")


def _npv(inputs, result, problems):
    cashflows = (inputs or {}).get("cashflows")
    rate = _input(inputs, "rate")
    if not isinstance(cashflows, list) or rate is None:
        return
    numbers = [_num(value) for value in cashflows]
    if any(value is None for value in numbers):
        return
    expected = sum(value / ((1.0 + rate) ** index) for index, value in enumerate(numbers))
    actual = _value(result, "npv")
    if actual is None:
        actual = _value(result, "value")
    if actual is None:
        # the bare Decimal is recorded under the method's output key
        actual = _num(next(iter((result or {}).values()), None)) if isinstance(result, dict) else None
    _require(problems, _close(actual, expected),
             "NPV does not equal the discounted sum of the declared cash flows")


def _irr(inputs, result, problems):
    _require(problems, _close(_value(result, "npv_at_irr"), 0.0, absolute=1e-6),
             "the NPV at the reported IRR is not zero")
    roots = _value(result, "n_roots")
    if roots is not None:
        _require(problems, roots >= 1, "the IRR reports no root")


def _wacc(inputs, result, problems):
    we, wd = _value(result, "weight_equity"), _value(result, "weight_debt")
    ke, kd = _value(result, "cost_of_equity"), _value(result, "cost_of_debt_after_tax")
    if _need(we, wd):
        _require(problems, _close(we + wd, 1.0),
                 "the equity and debt weights do not sum to one")
    if _need(we, wd, ke, kd):
        _require(problems, _close(_value(result, "wacc"), we * ke + wd * kd),
                 "WACC does not equal the weighted cost of equity and after-tax debt")


def _dcf(inputs, result, problems):
    explicit, terminal = _value(result, "pv_explicit"), _value(result, "pv_terminal")
    enterprise = _value(result, "enterprise_value")
    if _need(explicit, terminal):
        _require(problems, _close(enterprise, explicit + terminal),
                 "enterprise_value does not equal PV explicit + PV terminal")
    if _need(terminal, enterprise) and enterprise:
        _require(problems, _close(_value(result, "terminal_share"), terminal / enterprise),
                 "terminal_share does not equal PV terminal / enterprise value")


def _proforma(inputs, result, problems):
    revenues = [_num(value) for name, value in (result or {}).items()
                if str(name).startswith("revenue_") and _num(value) is not None]
    incomes = [_num(value) for name, value in (result or {}).items()
               if str(name).startswith("net_income_") and _num(value) is not None]
    if revenues and _need(_value(result, "total_revenue")):
        _require(problems, _close(sum(revenues), _value(result, "total_revenue")),
                 "the period revenues do not sum to total revenue")
    if incomes and _need(_value(result, "total_net_income")):
        _require(problems, _close(sum(incomes), _value(result, "total_net_income")),
                 "the period net incomes do not sum to total net income")


def _sales_projection(inputs, result, problems):
    price = _value(result, "price")
    unit_cost = _value(result, "unit_variable_cost")
    fixed = _value(result, "fixed_cost_per_period")
    if not _need(price, unit_cost, fixed):
        return
    for index in range(1, 13):
        units, revenue, profit = (_value(result, "units_%d" % index),
                                  _value(result, "revenue_%d" % index),
                                  _value(result, "profit_%d" % index))
        if not _need(units, revenue, profit):
            continue
        _require(problems, _close(revenue, units * price),
                 "revenue_%d does not equal units x price" % index)
        _require(problems, _close(profit, revenue - units * unit_cost - fixed),
                 "profit_%d does not equal revenue - variable cost - fixed cost" % index)


def _gini(inputs, result, problems):
    gini = _value(result, "gini")
    if gini is not None:
        _require(problems, 0.0 <= gini <= 1.0, "the Gini coefficient is outside [0, 1]")
    poorest, richest = _value(result, "poorest_share"), _value(result, "richest_share")
    if _need(poorest, richest):
        _require(problems, poorest <= richest, "the poorest share exceeds the richest share")


def _hdi(inputs, result, problems):
    hdi = _value(result, "hdi")
    if hdi is not None:
        _require(problems, 0.0 <= hdi <= 1.0, "the HDI is outside [0, 1]")
    life, education, income = (_value(result, "life_index"), _value(result, "education_index"),
                               _value(result, "income_index"))
    if _need(life, education, income) and _need(hdi):
        _require(problems, _close(hdi, (life * education * income) ** (1.0 / 3.0)),
                 "the HDI is not the geometric mean of its three indices")


def _market_sizing(inputs, result, problems):
    tam, sam, som = (_value(result, "total_addressable_market"),
                     _value(result, "serviceable_available_market"),
                     _value(result, "serviceable_obtainable_market"))
    if _need(tam, sam):
        _require(problems, tam >= sam, "TAM is smaller than SAM")
    if _need(sam, som):
        _require(problems, sam >= som, "SAM is smaller than SOM")
    if _need(tam, som) and tam:
        _require(problems, _close(_value(result, "share_of_tam_obtained"), som / tam),
                 "share_of_tam_obtained does not equal SOM / TAM")


def _cap_table(inputs, result, problems):
    founder, investor, pool = (_value(result, "founder_pct"), _value(result, "investor_pct"),
                               _value(result, "pool_pct_actual"))
    if _need(founder, investor, pool):
        _require(problems, _close(founder + investor + pool, 1.0),
                 "the founder, investor and option-pool shares do not sum to one")


def _inventory(inputs, result, problems):
    daily_demand = _value(result, "annual_demand")
    days = _value(result, "days_per_year")
    lead = _value(result, "lead_time_days")
    safety = _value(result, "safety_stock")
    if _need(daily_demand, days, lead, safety) and days:
        _require(problems, _close(_value(result, "reorder_point"), (daily_demand / days) * lead + safety),
                 "reorder_point does not equal daily demand x lead time + safety stock")
    ordering, holding = _value(result, "annual_ordering_cost"), _value(result, "annual_holding_cost")
    if _need(ordering, holding):
        _require(problems, _close(_value(result, "total_annual_cost"), ordering + holding),
                 "total annual cost does not equal ordering + holding cost")


def _queue(inputs, result, problems):
    arrival, service = _value(result, "arrival_rate"), _value(result, "service_rate")
    utilisation = _value(result, "utilisation")
    if _need(arrival, service) and service:
        _require(problems, _close(utilisation, arrival / service),
                 "utilisation does not equal arrival rate / service rate")
    in_queue, in_system = _value(result, "average_in_queue"), _value(result, "average_in_system")
    if _need(in_queue, utilisation):
        _require(problems, _close(in_system, in_queue + utilisation),
                 "average_in_system does not equal average_in_queue + utilisation")
    empty = _value(result, "probability_empty")
    if _need(empty, utilisation):
        _require(problems, _close(empty, 1.0 - utilisation),
                 "probability_empty does not equal 1 - utilisation")


INVARIANTS = {
    "ratio_analysis": _ratio_analysis,
    "dupont_analysis": _dupont,
    "breakeven": _breakeven,
    "multi_product_breakeven": _multi_breakeven,
    "loan_amortization": _loan,
    "npv": _npv,
    "irr": _irr,
    "wacc": _wacc,
    "dcf_valuation": _dcf,
    "proforma_statements": _proforma,
    "sales_projection": _sales_projection,
    "gini_coefficient": _gini,
    "hdi": _hdi,
    "market_sizing": _market_sizing,
    "cap_table_round": _cap_table,
    "inventory_policy": _inventory,
    "queue_analysis": _queue,
}


def check(method_id, inputs, result):
    """Every invariant this method has, as a list of failure messages."""
    function = INVARIANTS.get(str(method_id or ""))
    if function is None:
        return []
    problems = []
    function(inputs, result, problems)
    return problems
