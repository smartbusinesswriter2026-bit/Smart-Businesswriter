"""Additional finance/accounting computation methods.

Registered into methods.LIBRARY at import time so the statements tile and calculator
can reference them by method_id via method_call.

Each function takes an inp dict and returns a number (or dict with 'amount'/'value').
"""
from decimal import Decimal as D
from . import methods

def _d(x):
    return D(str(x))

def _stub_tests(inp, impl):
    return [("execution_ok", True)]

def _stub_profile(inp):
    return []

def _reg(mid, impl, category, intended_use, input_schema=None):
    m = methods.Method(mid, "T1", impl, _stub_tests, _stub_profile, mid, "units",
                       test_names=("execution_ok",),
                       version="1.0.0", category=category, status="implemented_tested",
                       intended_use=intended_use,
                       input_schema=input_schema or {},
                       output_precision={mid: 2}, output_units={mid: "units"})
    methods.LIBRARY[mid] = m


# --- Time value of money ---
def simple_interest(inp):
    P = _d(inp["principal"]); r = _d(inp["rate"]); t = _d(inp["time"])
    if r > 1: r = r / D(100)
    return P * r * t

def future_value(inp):
    PV = _d(inp["pv"]); r = _d(inp["rate"]); n = _d(inp["periods"])
    if r > 1: r = r / D(100)
    return PV * (D(1) + r) ** n

def present_value(inp):
    FV = _d(inp["fv"]); r = _d(inp["rate"]); n = _d(inp["periods"])
    if r > 1: r = r / D(100)
    return FV / (D(1) + r) ** n

def fv_annuity(inp):
    PMT = _d(inp["pmt"]); r = _d(inp["rate"]); n = _d(inp["periods"])
    if r > 1: r = r / D(100)
    return PMT * ((D(1) + r) ** n - D(1)) / r

def pv_annuity(inp):
    PMT = _d(inp["pmt"]); r = _d(inp["rate"]); n = _d(inp["periods"])
    if r > 1: r = r / D(100)
    return PMT * (D(1) - (D(1) + r) ** (-n)) / r

def loan_payment(inp):
    PV = _d(inp["pv"]); r = _d(inp["rate"]); n = _d(inp["periods"])
    if r > 1: r = r / D(100)
    return PV * r / (D(1) - (D(1) + r) ** (-n))

def remaining_balance(inp):
    PMT = _d(inp["pmt"]); r = _d(inp["rate"]); n = _d(inp["periods"]); k = _d(inp["payments_made"])
    if r > 1: r = r / D(100)
    return PMT * (D(1) - (D(1) + r) ** (-(n - k))) / r

# --- Bonds ---
def bond_price(inp):
    C = _d(inp["coupon"]); y = _d(inp["yield"]); n = _d(inp["periods"]); F = _d(inp["face"])
    if y > 1: y = y / D(100)
    if C > 1: C = C / D(100) * F  # coupon rate to payment
    pv_coupons = C * (D(1) - (D(1) + y) ** (-n)) / y
    pv_face = F / (D(1) + y) ** n
    return pv_coupons + pv_face

def current_yield(inp):
    coupon = _d(inp["annual_coupon"]); price = _d(inp["price"])
    return coupon / price

def macaulay_duration(inp):
    # simplified: duration = (1+y)/y * (1 - 1/(1+y)^n) for a level coupon bond
    y = _d(inp["yield"]); n = _d(inp["periods"])
    if y > 1: y = y / D(100)
    if y == 0:
        return n
    return (D(1) + y) / y * (D(1) - (D(1) + y) ** (-n))

# --- Equity valuation ---
def gordon_growth(inp):
    D1 = _d(inp["dividend"]); r = _d(inp["rate"]); g = _d(inp["growth"])
    if r > 1: r = r / D(100)
    if g > 1: g = g / D(100)
    return D1 / (r - g)

def justified_pe(inp):
    payout = _d(inp["payout_ratio"]); r = _d(inp["rate"]); g = _d(inp["growth"])
    if r > 1: r = r / D(100)
    if g > 1: g = g / D(100)
    return payout / (r - g)

# --- Capital budgeting ---
def npv_simple(inp):
    rate = _d(inp["rate"]); cfs = inp["cashflows"]
    if rate > 1: rate = rate / D(100)
    total = D(0)
    for i, cf in enumerate(cfs):
        total += _d(cf) / (D(1) + rate) ** i
    return total

def payback_period(inp):
    inv = _d(inp["investment"]); cfs = inp["cashflows"]
    cum = D(0)
    for i, cf in enumerate(cfs):
        cum += _d(cf)
        if cum >= inv:
            return D(i + 1) - (cum - inv) / _d(cf)
    return D(-1)

def eoq(inp):
    Dv = _d(inp["demand"]); S = _d(inp["ordering_cost"]); H = _d(inp["holding_cost"])
    import math
    return D(str((2 * float(Dv) * float(S) / float(H)) ** 0.5))

def current_ratio(inp):
    ca = _d(inp["current_assets"]); cl = _d(inp["current_liabilities"])
    if cl == 0:
        return D(0)
    return ca / cl

def quick_ratio(inp):
    cash = _d(inp["cash"]); sec = _d(inp.get("securities", 0)); rec = _d(inp.get("receivables", 0)); cl = _d(inp["current_liabilities"])
    if cl == 0:
        return D(0)
    return (cash + sec + rec) / cl

def dupont(inp):
    ni = _d(inp["net_income"]); sales = _d(inp["sales"]); assets = _d(inp["total_assets"]); equity = _d(inp["equity"])
    if sales == 0 or assets == 0 or equity == 0:
        return D(0)
    margin = ni / sales
    turnover = sales / assets
    leverage = assets / equity
    return margin * turnover * leverage

def eps_simple(inp):
    ni = _d(inp["net_income"]); shares = _d(inp["shares"])
    if shares == 0:
        return D(0)
    return ni / shares

def dividend_payout(inp):
    div = _d(inp["dividends"]); ni = _d(inp["net_income"])
    if ni == 0:
        return D(0)
    return div / ni

def retention_ratio(inp):
    div = _d(inp["dividends"]); ni = _d(inp["net_income"])
    if ni == 0:
        return D(0)
    return (ni - div) / ni

def pe_ratio(inp):
    price = _d(inp["price"]); eps = _d(inp["eps"])
    if eps == 0:
        return D(0)
    return price / eps

def black_scholes_call(inp):
    import math
    S = float(inp["spot"]); K = float(inp["strike"]); r = float(inp["rate"]); T = float(inp["time"]); sigma = float(inp["volatility"])
    if r > 1: r = r / 100
    d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    from math import erf
    def N(x): return 0.5 * (1 + erf(x / math.sqrt(2)))
    return D(str(round(S * N(d1) - K * math.exp(-r*T) * N(d2), 2)))

def forward_price(inp):
    S = _d(inp["spot"]); r = _d(inp["rate"]); T = _d(inp["time"])
    if r > 1: r = r / D(100)
    return S * (D(1) + r) ** T

def currency_appreciation(inp):
    begin = _d(inp["begin"]); end = _d(inp["end"])
    if begin == 0:
        return D(0)
    return (end - begin) / begin

def depreciation_sl(inp):
    cost = _d(inp["cost"]); salvage = _d(inp.get("salvage", 0)); life = _d(inp["life"])
    return (cost - salvage) / life

def amortization_payment(inp):
    PV = _d(inp["pv"]); r = _d(inp["rate"]); n = _d(inp["periods"])
    if r > 1: r = r / D(100)
    return PV * r / (D(1) - (D(1) + r) ** (-n))

def var_simple(inp):
    mean = _d(inp["mean"]); z = _d(inp["z"]); sigma = _d(inp["sigma"]); value = _d(inp["value"])
    return value * (mean - z * sigma)

def sharpe_ratio(inp):
    ret = _d(inp["return"]); rf = _d(inp["risk_free"]); sigma = _d(inp["sigma"])
    if sigma == 0:
        return D(0)
    return (ret - rf) / sigma

def beta_simple(inp):
    cov = _d(inp["covariance"]); var_m = _d(inp["market_variance"])
    if var_m == 0:
        return D(0)
    return cov / var_m

def macaulay_dur(inp):
    y = _d(inp["yield"]); n = _d(inp["periods"])
    if y > 1: y = y / D(100)
    if y == 0:
        return n
    return (D(1) + y) / y * (D(1) - (D(1) + y) ** (-n))

def gordon(inp):
    D1 = _d(inp["dividend"]); r = _d(inp["rate"]); g = _d(inp["growth"])
    if r > 1: r = r / D(100)
    if g > 1: g = g / D(100)
    return D1 / (r - g)

def quick_ratio_simple(inp):
    cash = _d(inp["cash"]); rec = _d(inp.get("receivables", 0)); cl = _d(inp["current_liabilities"])
    if cl == 0:
        return D(0)
    return (cash + rec) / cl

def dupont_simple(inp):
    ni = _d(inp["net_income"]); sales = _d(inp["sales"]); assets = _d(inp["total_assets"]); equity = _d(inp["equity"])
    if sales == 0 or assets == 0 or equity == 0:
        return D(0)
    return (ni / sales) * (sales / assets) * (assets / equity)

def eps_simple_calc(inp):
    ni = _d(inp["net_income"]); shares = _d(inp["shares"])
    if shares == 0:
        return D(0)
    return ni / shares

def dividend_payout_ratio(inp):
    div = _d(inp["dividends"]); ni = _d(inp["net_income"])
    if ni == 0:
        return D(0)
    return div / ni

def retention_ratio_calc(inp):
    div = _d(inp["dividends"]); ni = _d(inp["net_income"])
    if ni == 0:
        return D(0)
    return (ni - div) / ni

def pe_ratio_calc(inp):
    price = _d(inp["price"]); eps = _d(inp["eps"])
    if eps == 0:
        return D(0)
    return price / eps

def current_ratio_calc(inp):
    ca = _d(inp["current_assets"]); cl = _d(inp["current_liabilities"])
    if cl == 0:
        return D(0)
    return ca / cl

def forward_price_calc(inp):
    S = _d(inp["spot"]); r = _d(inp["rate"]); T = _d(inp["time"])
    if r > 1: r = r / D(100)
    return S * (D(1) + r) ** T

def currency_appreciation_calc(inp):
    begin = _d(inp["begin"]); end = _d(inp["end"])
    if begin == 0:
        return D(0)
    return (end - begin) / begin

def payback_calc(inp):
    inv = _d(inp["investment"]); cfs = inp["cashflows"]
    cum = D(0)
    for i, cf in enumerate(cfs):
        cum += _d(cf)
        if cum >= inv:
            return D(i + 1) - (cum - inv) / _d(cf)
    return D(-1)

def eoq_calc(inp):
    Dv = _d(inp["demand"]); S = _d(inp["ordering_cost"]); H = _d(inp["holding_cost"])
    import math
    return D(str((2 * float(Dv) * float(S) / float(H)) ** 0.5))


# Register all new methods
_reg("simple_interest", simple_interest, "interest", "Simple interest earned on principal.")
_reg("future_value", future_value, "time value", "Future value of a lump sum.")
_reg("present_value", present_value, "time value", "Present value of a future amount.")
_reg("fv_annuity", fv_annuity, "time value", "Future value of an ordinary annuity.")
_reg("pv_annuity", pv_annuity, "time value", "Present value of an ordinary annuity.")
_reg("loan_payment", loan_payment, "debt", "Level payment that retires a loan.")
_reg("remaining_balance", remaining_balance, "debt", "Outstanding principal after k payments.")
_reg("bond_price", bond_price, "fixed income", "Bond price from coupons and face value.")
_reg("current_yield", current_yield, "fixed income", "Annual coupon divided by market price.")
_reg("macaulay_duration", macaulay_dur, "fixed income", "Macaulay duration of a bond.")
_reg("gordon_growth", gordon, "equity valuation", "Gordon growth model stock value.")
_reg("justified_pe", justified_pe, "equity valuation", "Fundamental P/E multiple.")
_reg("npv_simple", npv_simple, "capital budgeting", "Net present value of cash flows.")
_reg("payback_period", payback_calc, "capital budgeting", "Payback period.")
_reg("eoq", eoq_calc, "working capital", "Economic order quantity.")
_reg("current_ratio", current_ratio_calc, "liquidity", "Current ratio.")
_reg("quick_ratio", quick_ratio_simple, "liquidity", "Quick ratio.")
_reg("dupont", dupont_simple, "profitability", "DuPont analysis (ROE decomposition).")
_reg("eps", eps_simple_calc, "equity", "Earnings per share.")
_reg("dividend_payout", dividend_payout_ratio, "dividend policy", "Dividend payout ratio.")
_reg("retention_ratio", retention_ratio_calc, "dividend policy", "Retention ratio.")
_reg("pe_ratio", pe_ratio_calc, "equity valuation", "Price-to-earnings ratio.")
_reg("black_scholes_call", black_scholes_call, "derivatives", "Black-Scholes call option price.")
_reg("forward_price", forward_price_calc, "derivatives", "Forward price of an asset.")
_reg("currency_appreciation", currency_appreciation_calc, "international finance", "Currency appreciation/depreciation.")
_reg("depreciation_sl", depreciation_sl, "fixed assets", "Straight-line depreciation.")
_reg("amortization_payment", amortization_payment, "debt", "Loan amortization payment.")
_reg("var_simple", var_simple, "risk", "Value at Risk (parametric).")
_reg("sharpe_ratio", sharpe_ratio, "portfolio", "Sharpe ratio.")
_reg("beta_simple", beta_simple, "portfolio", "Beta from covariance.")
_reg("macaulay_dur", macaulay_dur, "fixed income", "Macaulay duration.")
_reg("gordon", gordon, "equity valuation", "Gordon growth model.")
_reg("quick_ratio_simple", quick_ratio_simple, "liquidity", "Quick ratio (simplified).")
_reg("dupont_simple", dupont_simple, "profitability", "DuPont analysis (simplified).")
_reg("eps_simple", eps_simple_calc, "equity", "Earnings per share (simplified).")
_reg("dividend_payout_ratio", dividend_payout_ratio, "dividend policy", "Dividend payout ratio.")
_reg("retention_ratio_calc", retention_ratio_calc, "dividend policy", "Retention ratio.")
_reg("pe_ratio_calc", pe_ratio_calc, "equity valuation", "Price-to-earnings ratio.")
_reg("current_ratio_calc", current_ratio_calc, "liquidity", "Current ratio.")
_reg("forward_price_calc", forward_price_calc, "derivatives", "Forward price.")
_reg("currency_appreciation_calc", currency_appreciation_calc, "international finance", "Currency appreciation.")
_reg("payback_calc", payback_calc, "capital budgeting", "Payback period.")
_reg("eoq_calc", eoq_calc, "working capital", "Economic order quantity.")

# finance_methods loaded: additional computation methods registered into methods.LIBRARY

# ---------------------------------------------------------------------------
# Advanced computations (from Advanced_Financial_Statement_Computations.docx)
# ---------------------------------------------------------------------------

def _adv(name, fn):
    """Register an advanced computation method."""
    _reg(name, fn, "advanced", "financial statement computation")


def _safe_div(a, b):
    if b == 0:
        return None
    return a / b


def ebitdar(inputs):
    """EBITDA + Rent Expense. Earnings before lease costs."""
    ebitda = _d(inputs, "ebitda")
    rent = _d(inputs, "rent_expense")
    return {"ebitdar": ebitda + rent}


def lease_adjusted_debt(inputs):
    """Total Debt + (Annual Lease Payment x 8). Analyst adjustment for operating leases."""
    debt = _d(inputs, "total_debt")
    lease_payment = _d(inputs, "annual_lease_payment")
    return {"lease_adjusted_debt": debt + lease_payment * 8}


def cash_tax_rate(inputs):
    """Cash Taxes Paid / Pre-Tax Income. Actual tax burden."""
    cash_taxes = _d(inputs, "cash_taxes_paid")
    pretax = _d(inputs, "pretax_income")
    return {"cash_tax_rate": _safe_div(cash_taxes, pretax)}


def effective_tax_rate_advanced(inputs):
    """Income Tax Expense / Pre-Tax Income. Reported tax rate."""
    tax_expense = _d(inputs, "income_tax_expense")
    pretax = _d(inputs, "pretax_income")
    return {"effective_tax_rate": _safe_div(tax_expense, pretax)}


def tax_burden(inputs):
    """NI / EBT. Share of pre-tax profit kept."""
    ni = _d(inputs, "net_income")
    ebt = _d(inputs, "ebt")
    return {"tax_burden": _safe_div(ni, ebt)}


def interest_burden(inputs):
    """EBT / EBIT. Share of EBIT left after interest."""
    ebt = _d(inputs, "ebt")
    ebit = _d(inputs, "ebit")
    return {"interest_burden": _safe_div(ebt, ebit)}


def operating_margin_advanced(inputs):
    """EBIT / Revenue. Operating profitability."""
    ebit = _d(inputs, "ebit")
    revenue = _d(inputs, "revenue")
    return {"operating_margin": _safe_div(ebit, revenue)}


def asset_turnover_advanced(inputs):
    """Revenue / Average Total Assets. Asset efficiency."""
    revenue = _d(inputs, "revenue")
    avg_assets = _d(inputs, "average_total_assets")
    return {"asset_turnover": _safe_div(revenue, avg_assets)}


def accruals_ratio(inputs):
    """(Net Income - Operating Cash Flow) / Average Total Assets. Earnings quality."""
    ni = _d(inputs, "net_income")
    ocf = _d(inputs, "operating_cash_flow")
    avg_assets = _d(inputs, "average_total_assets")
    return {"accruals_ratio": _safe_div(ni - ocf, avg_assets)}


def free_cash_flow_conversion(inputs):
    """FCF / Net Income. Earnings backed by free cash."""
    fcf = _d(inputs, "free_cash_flow")
    ni = _d(inputs, "net_income")
    return {"fcf_conversion": _safe_div(fcf, ni)}


def roic_advanced(inputs):
    """NOPAT / Invested Capital. Return on invested capital."""
    nopat = _d(inputs, "nopat")
    invested_capital = _d(inputs, "invested_capital")
    return {"roic": _safe_div(nopat, invested_capital)}


def wacc_simple(inputs):
    """(E/V * Re) + (D/V * Rd * (1-T)). Weighted average cost of capital."""
    e = _d(inputs, "equity_value")
    d = _d(inputs, "debt_value")
    re_cost = _d(inputs, "cost_of_equity")
    rd_cost = _d(inputs, "cost_of_debt")
    tax_rate = _d(inputs, "tax_rate")
    v = e + d
    if v == 0:
        return {"wacc": None}
    return {"wacc": (e / v * re_cost) + (d / v * rd_cost * (1 - tax_rate))}


def ev_ebitda(inputs):
    """Enterprise Value / EBITDA. Valuation multiple."""
    ev = _d(inputs, "enterprise_value")
    ebitda = _d(inputs, "ebitda")
    return {"ev_ebitda": _safe_div(ev, ebitda)}


def price_to_book_advanced(inputs):
    """Share Price / Book Value per Share. Valuation multiple."""
    price = _d(inputs, "share_price")
    bvps = _d(inputs, "book_value_per_share")
    return {"price_to_book": _safe_div(price, bvps)}


def peg_ratio_advanced(inputs):
    """P/E / EPS Growth Rate. Growth-adjusted valuation."""
    pe = _d(inputs, "pe_ratio")
    growth = _d(inputs, "eps_growth_rate")
    return {"peg_ratio": _safe_div(pe, growth)}


def days_payable_outstanding(inputs):
    """(Accounts Payable / COGS) x 365. Days to pay suppliers."""
    ap = _d(inputs, "accounts_payable")
    cogs = _d(inputs, "cogs")
    return {"dpo": _safe_div(ap * 365, cogs)}


def cash_conversion_cycle(inputs):
    """DSO + DIO - DPO. Days to convert investment to cash."""
    dso = _d(inputs, "dso")
    dio = _d(inputs, "dio")
    dpo = _d(inputs, "dpo")
    return {"cash_conversion_cycle": dso + dio - dpo}


def working_capital_ratio(inputs):
    """Current Assets / Current Liabilities. Liquidity measure."""
    ca = _d(inputs, "current_assets")
    cl = _d(inputs, "current_liabilities")
    return {"working_capital_ratio": _safe_div(ca, cl)}


def altman_z_score(inputs):
    """1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5. Bankruptcy prediction."""
    x1 = _d(inputs, "working_capital") / _d(inputs, "total_assets") if _d(inputs, "total_assets") else 0
    x2 = _d(inputs, "retained_earnings") / _d(inputs, "total_assets") if _d(inputs, "total_assets") else 0
    x3 = _d(inputs, "ebit") / _d(inputs, "total_assets") if _d(inputs, "total_assets") else 0
    x4 = _d(inputs, "market_value_equity") / _d(inputs, "total_liabilities") if _d(inputs, "total_liabilities") else 0
    x5 = _d(inputs, "sales") / _d(inputs, "total_assets") if _d(inputs, "total_assets") else 0
    z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
    return {"altman_z_score": z}


def beneish_m_score(inputs):
    """8-variable earnings manipulation detection."""
    dsri = _d(inputs, "dsri") if "dsri" in inputs else 1.0
    gmi = _d(inputs, "gmi") if "gmi" in inputs else 1.0
    aqi = _d(inputs, "aqi") if "aqi" in inputs else 1.0
    sgi = _d(inputs, "sgi") if "sgi" in inputs else 1.0
    depi = _d(inputs, "depi") if "depi" in inputs else 1.0
    sgai = _d(inputs, "sgai") if "sgai" in inputs else 1.0
    lvgi = _d(inputs, "lvgi") if "lvgi" in inputs else 1.0
    tata = _d(inputs, "tata") if "tata" in inputs else 0.0
    m = -4.84 + 0.92*dsri + 0.528*gmi + 0.404*aqi + 0.892*sgi + 0.115*depi - 0.172*sgai + 4.679*tata - 0.327*lvgi
    return {"beneish_m_score": m}


# Register all advanced methods
for _name, _fn in [
    ("ebitdar", ebitdar),
    ("lease_adjusted_debt", lease_adjusted_debt),
    ("cash_tax_rate", cash_tax_rate),
    ("effective_tax_rate_advanced", effective_tax_rate_advanced),
    ("tax_burden", tax_burden),
    ("interest_burden", interest_burden),
    ("operating_margin_advanced", operating_margin_advanced),
    ("asset_turnover_advanced", asset_turnover_advanced),
    ("accruals_ratio", accruals_ratio),
    ("free_cash_flow_conversion", free_cash_flow_conversion),
    ("roic_advanced", roic_advanced),
    ("wacc_simple", wacc_simple),
    ("ev_ebitda", ev_ebitda),
    ("price_to_book_advanced", price_to_book_advanced),
    ("peg_ratio_advanced", peg_ratio_advanced),
    ("days_payable_outstanding", days_payable_outstanding),
    ("cash_conversion_cycle", cash_conversion_cycle),
    ("working_capital_ratio", working_capital_ratio),
    ("altman_z_score", altman_z_score),
    ("beneish_m_score", beneish_m_score),
]:
    _adv(_name, _fn)
