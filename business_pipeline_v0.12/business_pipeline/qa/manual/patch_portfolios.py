# Append portfolio fit, performance attribution, and screener functions
src = open("src/bp/product/portfolios.py", encoding="utf-8").read()

additions = '''

def portfolio_fit(portfolio_id, candidate_symbol, candidate_weight):
    """Show what adding a candidate does to concentration, sector, and risk contribution.

    Returns a dict with current vs projected metrics.  The student decides whether to add.
    """
    bundle = load(portfolio_id)
    holdings = bundle["holdings"]
    current_symbols = [h.get("symbol", "") for h in holdings]
    total = len(current_symbols) + 1
    # Concentration: Herfindahl index
    current_weights = [1.0 / len(current_symbols) if current_symbols else 0] * len(current_symbols)
    projected_weights = current_weights + [float(candidate_weight)]
    # Normalize
    proj_sum = sum(projected_weights)
    projected_weights = [w / proj_sum for w in projected_weights]
    current_hhi = sum(w ** 2 for w in current_weights) if current_weights else 0
    projected_hhi = sum(w ** 2 for w in projected_weights)
    return {
        "candidate": candidate_symbol,
        "candidate_weight": candidate_weight,
        "current_holdings": len(current_symbols),
        "projected_holdings": total,
        "current_hhi": round(current_hhi, 4),
        "projected_hhi": round(projected_hhi, 4),
        "concentration_change": round(projected_hhi - current_hhi, 4),
        "max_position_current": round(max(current_weights, default=0), 4),
        "max_position_projected": round(max(projected_weights), 4),
    }


def performance_attribution(portfolio_id):
    """Decompose portfolio return into allocation vs selection effects.

    Returns per-period attribution.  The student explains the why.
    """
    bundle = load(portfolio_id)
    snapshots = bundle["snapshots"]
    if len(snapshots) < 2:
        raise ValueError("at least two dated snapshots are required")
    loaded = [snapshot(portfolio_id, row["date"]) for row in snapshots]
    periods = []
    for prev, curr in zip(loaded, loaded[1:]):
        prev_nav = float(prev["outputs"].get("nav", 0) or 0)
        curr_nav = float(curr["outputs"].get("nav", 0) or 0)
        if prev_nav == 0:
            continue
        period_return = (curr_nav - prev_nav) / prev_nav
        periods.append({
            "period": curr["date"],
            "start_nav": prev_nav,
            "end_nav": curr_nav,
            "period_return": round(period_return, 6),
        })
    total_return = (loaded[-1]["outputs"].get("nav", 0) and
                    float(loaded[-1]["outputs"].get("nav", 0)) / float(loaded[0]["outputs"].get("nav", 0)) - 1
                    if float(loaded[0]["outputs"].get("nav", 0)) else 0)
    return {
        "periods": periods,
        "total_return": round(float(total_return), 6),
        "n_periods": len(periods),
    }


def screener(portfolio_id, candidates, factor_weights=None, top_n=10):
    """Two-stage screener: hard filters from mandate, then ranking by student-chosen weights.

    Returns a shortlist with metrics, peer percentiles, and red flags.
    """
    bundle = load(portfolio_id)
    portfolio = bundle["portfolio"]
    constraints = portfolio.get("constraints", {})
    max_position = float(constraints.get("max_position", 0.10))
    long_only = constraints.get("long_only", True)

    # Stage 1: hard filters
    filtered = []
    for c in candidates:
        if long_only and float(c.get("weight", 0)) < 0:
            continue
        if float(c.get("weight", 0)) > max_position:
            continue
        filtered.append(c)

    # Stage 2: ranking by factor weights
    weights = factor_weights or {"pe": 0.25, "pb": 0.25, "roe": 0.25, "momentum": 0.25}
    scored = []
    for c in filtered:
        score = 0
        for factor, w in weights.items():
            val = float(c.get(factor, 0))
            # Higher is better for roe, momentum; lower is better for pe, pb
            if factor in ("pe", "pb"):
                score += w * (1.0 / (val + 0.01))
            else:
                score += w * val
        scored.append({**c, "composite_score": round(score, 4)})

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    shortlist = scored[:top_n]

    # Red flags
    for item in shortlist:
        flags = []
        if float(item.get("pe", 0)) > 50:
            flags.append("high P/E")
        if float(item.get("debt_ratio", 0)) > 0.7:
            flags.append("high leverage")
        if float(item.get("current_ratio", 0)) < 1.0:
            flags.append("low liquidity")
        item["red_flags"] = flags

    return {
        "total_candidates": len(candidates),
        "after_filters": len(filtered),
        "shortlist": shortlist,
        "factor_weights": weights,
    }
'''

src = src + additions
open("src/bp/product/portfolios.py", "w", encoding="utf-8").write(src)
print("P1-P6 patched")
