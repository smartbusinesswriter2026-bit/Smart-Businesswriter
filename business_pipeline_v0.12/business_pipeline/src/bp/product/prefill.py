"""Prefill frozen calculator inputs from recorded instrument prices (product layer).

Builds the exact input objects the frozen `portfolio_analysis`, `risk_metrics`
and `capm` methods expect, from recorded snapshots, so a student can confirm and
run them through the normal create-then-confirm path.  It never runs the method,
recomputes a result or bypasses confirmation, and every missing input is a named
gap rather than an assumed value.  The only arithmetic is a simple return over
two recorded prices.  This module never imports the frozen core.
"""

from decimal import Decimal, InvalidOperation

from . import instruments

FORMAT = "bp-prefill/1"


class PrefillError(Exception):
    """The prefill request cannot be answered."""


def _price_map(document):
    out = {}
    for snapshot in document.get("snapshots", []):
        try:
            price = Decimal(str(snapshot["price"]))
        except (KeyError, InvalidOperation, TypeError):
            continue
        if price > 0:
            out[str(snapshot.get("as_of"))] = price
    return out


def _returns(prices):
    return [str((current - previous) / previous) for previous, current in zip(prices, prices[1:])]


def _aligned(documents):
    """The shared as-of dates across the given documents, oldest first, plus each series."""
    maps = [_price_map(document) for document in documents]
    common = set(maps[0])
    for mapping in maps[1:]:
        common &= set(mapping)
    dates = sorted(common)
    return dates, [[mapping[date] for date in dates] for mapping in maps]


def risk_inputs(document, confidence=None, portfolio_value=None, horizon_days=None, stress_return=None):
    """Build `risk_metrics` inputs from an instrument's recorded returns."""
    returns = instruments.returns_series(document)
    inputs = {"returns": returns}
    for name, value in (("confidence", confidence), ("portfolio_value", portfolio_value),
                        ("horizon_days", horizon_days), ("stress_return", stress_return)):
        if value not in (None, ""):
            inputs[name] = str(value)
    gaps = []
    if not returns:
        gaps.append("record at least two price snapshots before a return exists")
    elif len(returns) < 3:
        gaps.append("risk_metrics is meaningful with more returns; only %d recorded so far" % len(returns))
    return {"format": FORMAT, "target": "risk", "method": "risk_metrics", "symbol": document.get("symbol"),
            "inputs": inputs, "ready": bool(returns), "gaps": gaps}


def portfolio_inputs(document_a, document_b, market=None, weight_a="0.5", risk_free_rate=None):
    """Build `portfolio_analysis` inputs from two tracked instruments (+ optional benchmark)."""
    documents = [document_a, document_b] + ([market] if market else [])
    dates, series = _aligned(documents)
    gaps = []
    if len(dates) < 4:
        gaps.append("portfolio_analysis needs at least three returns, so at least four shared "
                    "snapshot dates; %d shared so far" % len(dates))
    returns_a = _returns(series[0]) if dates else []
    returns_b = _returns(series[1]) if dates else []
    inputs = {"returns_a": returns_a, "returns_b": returns_b,
              "weight_a": str(weight_a if weight_a not in (None, "") else "0.5")}
    if market:
        inputs["returns_market"] = _returns(series[2])
    else:
        gaps.append("returns_market is required: track a benchmark symbol and pass its id as market")
    if risk_free_rate not in (None, ""):
        inputs["risk_free_rate"] = str(risk_free_rate)
    else:
        gaps.append("risk_free_rate is required: declare it, or read the Treasury yield first")
    ready = (len(returns_a) >= 3 and len(returns_a) == len(returns_b)
             and "returns_market" in inputs and "risk_free_rate" in inputs)
    return {"format": FORMAT, "target": "portfolio", "method": "portfolio_analysis",
            "symbols": [document_a.get("symbol"), document_b.get("symbol"),
                        market.get("symbol") if market else None],
            "common_dates": dates, "inputs": inputs, "ready": ready, "gaps": gaps}


def capm_inputs(document_asset, market=None, risk_free_rate=None, market_return=None, beta=None):
    """Build `capm` inputs from a tracked asset (and benchmark) with declared rates."""
    gaps = []
    inputs = {}
    if beta not in (None, ""):
        inputs["beta"] = str(beta)
    else:
        documents = [document_asset] + ([market] if market else [])
        dates, series = _aligned(documents)
        if market and len(dates) >= 4:
            inputs["returns_asset"] = _returns(series[0])
            inputs["returns_market"] = _returns(series[1])
        else:
            gaps.append("declare beta, or track the asset and a benchmark with at least four shared dates")
    if risk_free_rate not in (None, ""):
        inputs["risk_free_rate"] = str(risk_free_rate)
    else:
        gaps.append("risk_free_rate is required (declare it, or read the Treasury yield first)")
    if market_return not in (None, ""):
        inputs["market_return"] = str(market_return)
    else:
        gaps.append("market_return must be declared; the system does not assume a market premium")
    ready = ("risk_free_rate" in inputs and "market_return" in inputs
             and ("beta" in inputs or "returns_asset" in inputs))
    return {"format": FORMAT, "target": "capm", "method": "capm",
            "symbol": document_asset.get("symbol"), "inputs": inputs, "ready": ready, "gaps": gaps}

