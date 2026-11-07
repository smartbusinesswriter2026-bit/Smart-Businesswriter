# Append P3 methods to finance_methods.py
src = open("src/bp/finance_methods.py", encoding="utf-8").read()

additions = '''

# ---------------------------------------------------------------------------
# Portfolio selection methods (P3)
# ---------------------------------------------------------------------------

def multi_year_cagr(inputs):
    """Compound Annual Growth Rate over N years."""
    start = _d(inputs, "start_value")
    end = _d(inputs, "end_value")
    years = _d(inputs, "years")
    if start == 0 or years == 0:
        return {"cagr": None}
    cagr = (end / start) ** (1 / years) - 1
    return {"cagr": cagr}


def piotroski_f_score(inputs):
    """Piotroski F-score: 9 binary criteria for financial strength."""
    score = 0
    # Profitability
    if _d(inputs, "net_income") > 0:
        score += 1
    if _d(inputs, "operating_cash_flow") > 0:
        score += 1
    if _d(inputs, "roa_current") > _d(inputs, "roa_prior"):
        score += 1
    if _d(inputs, "operating_cash_flow") > _d(inputs, "net_income"):
        score += 1
    # Leverage/liquidity
    if _d(inputs, "leverage_current") < _d(inputs, "leverage_prior"):
        score += 1
    if _d(inputs, "current_ratio_current") > _d(inputs, "current_ratio_prior"):
        score += 1
    if not _d(inputs, "shares_diluted"):
        score += 1
    # Operating efficiency
    if _d(inputs, "gross_margin_current") > _d(inputs, "gross_margin_prior"):
        score += 1
    if _d(inputs, "asset_turnover_current") > _d(inputs, "asset_turnover_prior"):
        score += 1
    return {"piotroski_f_score": score}


def dcf_with_sensitivity(inputs):
    """Discounted Cash Flow with sensitivity grid."""
    fcf = _d(inputs, "free_cash_flow")
    growth = _d(inputs, "growth_rate")
    discount = _d(inputs, "discount_rate")
    terminal_growth = _d(inputs, "terminal_growth_rate")
    years = int(_d(inputs, "projection_years"))
    shares = _d(inputs, "shares_outstanding")

    pv_fcfs = Decimal(0)
    for t in range(1, years + 1):
        cf = fcf * (1 + growth) ** t
        pv_fcfs += cf / (1 + discount) ** t

    terminal_cf = fcf * (1 + growth) ** years * (1 + terminal_growth)
    terminal_value = terminal_cf / (discount - terminal_growth) if discount > terminal_growth else Decimal(0)
    pv_terminal = terminal_value / (1 + discount) ** years

    enterprise_value = pv_fcfs + pv_terminal
    # Sensitivity grid
    grid = {}
    for g in [growth - Decimal("0.02"), growth, growth + Decimal("0.02")]:
        for d in [discount - Decimal("0.02"), discount, discount + Decimal("0.02")]:
            pv = Decimal(0)
            for t in range(1, years + 1):
                cf = fcf * (1 + g) ** t
                pv += cf / (1 + d) ** t
            tcf = fcf * (1 + g) ** years * (1 + terminal_growth)
            tv = tcf / (d - terminal_growth) if d > terminal_growth else Decimal(0)
            pv += tv / (1 + d) ** years
            grid[f"g={g:.2%}_d={d:.2%}"] = pv

    return {"enterprise_value": enterprise_value, "pv_fcfs": pv_fcfs,
            "pv_terminal": pv_terminal, "sensitivity_grid": grid,
            "value_per_share": enterprise_value / shares if shares else None}


def peer_relative_multiples(inputs):
    """Compare a company's multiples to peer medians."""
    company_pe = _d(inputs, "company_pe")
    peer_pe_median = _d(inputs, "peer_pe_median")
    company_ev_ebitda = _d(inputs, "company_ev_ebitda")
    peer_ev_ebitda_median = _d(inputs, "peer_ev_ebitda_median")
    company_pb = _d(inputs, "company_pb")
    peer_pb_median = _d(inputs, "peer_pb_median")

    return {
        "pe_premium_discount": _safe_div(company_pe - peer_pe_median, peer_pe_median) if peer_pe_median else None,
        "ev_ebitda_premium_discount": _safe_div(company_ev_ebitda - peer_ev_ebitda_median, peer_ev_ebitda_median) if peer_ev_ebitda_median else None,
        "pb_premium_discount": _safe_div(company_pb - peer_pb_median, peer_pb_median) if peer_pb_median else None,
    }


def multi_year_cagr(inputs):
    """Compound Annual Growth Rate over N years."""
    start = _d(inputs, "start_value")
    end = _d(inputs, "end_value")
    years = _d(inputs, "years")
    if start == 0 or years == 0:
        return {"cagr": None}
    cagr = (end / start) ** (1 / years) - 1
    return {"cagr": cagr}


# Register advanced portfolio methods
for _name, _fn in [
    ("multi_year_cagr", multi_year_cagr),
    ("piotroski_f_score", piotroski_f_score),
    ("dcf_with_sensitivity", dcf_with_sensitivity),
    ("peer_relative_multiples", peer_relative_multiples),
]:
    _reg(_name, _fn, "portfolio", "portfolio selection computation")
'''

src = src + additions
open("src/bp/finance_methods.py", "w", encoding="utf-8").write(src)
print("appended portfolio methods")
