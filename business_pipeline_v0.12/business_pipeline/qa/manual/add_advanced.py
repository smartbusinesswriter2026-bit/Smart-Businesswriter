# Additional advanced computations from Advanced_Financial_Statement_Computations.docx
# Appended to finance_methods.py

import os
src = open("src/bp/finance_methods.py", encoding="utf-8").read()

# Check if already has advanced section
if "advanced_" not in src:
    # Append a batch of key advanced computations
    additions = '''

# ---------------------------------------------------------------------------
# Advanced computations (from Advanced_Financial_Statement_Computations.docx)
# ---------------------------------------------------------------------------

def _adv(name, fn):
    """Register an advanced computation method."""
    _reg(name, fn, "advanced")


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
'''
    src = src + additions
    open("src/bp/finance_methods.py", "w", encoding="utf-8").write(src)
    print("appended advanced computations")
else:
    print("already has advanced section")
