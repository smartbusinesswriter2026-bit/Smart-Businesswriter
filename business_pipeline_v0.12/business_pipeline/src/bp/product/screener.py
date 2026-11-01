"""Deterministic screening of a student-supplied candidate list (product layer).

The screener does not invent a universe and does not decide an investment.  The
student names the symbols they are weighing; the screener fetches a current
quote for each (through the market-data layer, Alpha Vantage or Massive), adds
whatever recorded-history statistics exist for that symbol, applies the
student's declared filters and sort, and returns a ranked shortlist with the
source, date and gaps for every row.  A value the app cannot source is a named
gap, never a guess.

All arithmetic is a simple return or a sample statistic over recorded prices;
the frozen evaluators remain the only place a portfolio or risk number is
produced.  This module never imports the frozen core.
"""

from decimal import Decimal, InvalidOperation

from . import instruments
from . import marketdata

FORMAT = "bp-screener/1"

#: A screen is bounded so one request cannot fan out into an unbounded fetch.
MAX_SYMBOLS = 25


class ScreenerError(Exception):
    """The screen request cannot be answered."""


def _dec(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def _statistics(returns):
    values = [v for v in (_dec(r) for r in returns) if v is not None]
    count = len(values)
    if count == 0:
        return {"n_returns": 0}
    mean = sum(values, Decimal(0)) / count
    stats = {"n_returns": count, "mean_return": str(mean)}
    if count >= 2:
        variance = sum(((v - mean) ** 2 for v in values), Decimal(0)) / (count - 1)
        sd = variance.sqrt() if variance >= 0 else Decimal(0)
        stats["sd"] = str(sd)
        stats["sharpe"] = str(mean / sd) if sd > 0 else None
    return stats


def _cumulative(returns):
    growth = Decimal(1)
    seen = False
    for r in returns:
        value = _dec(r)
        if value is None:
            continue
        growth *= (1 + value)
        seen = True
    return str(growth - 1) if seen else None


def _row(symbol, quote, tracked):
    row = {"symbol": symbol, "provider": quote.get("provider") or "alphavantage",
           "as_of": quote.get("as_of"), "source": quote.get("source"),
           "source_url": quote.get("source_url"), "response_sha256": quote.get("response_sha256"),
           "gaps": []}
    price = _dec(quote.get("value"))
    row["price"] = str(price) if price is not None else None
    previous = _dec(quote.get("previous_close"))
    if price is not None and previous and previous > 0:
        row["one_day_return"] = str((price - previous) / previous)
    else:
        row["one_day_return"] = None
        row["gaps"].append("the change needs a previous close, which this quote did not carry")
    if tracked:
        returns = instruments.returns_series(tracked)
        row.update(_statistics(returns))
        row["cumulative_return"] = _cumulative(returns)
        if row.get("n_returns", 0) < 3:
            row["gaps"].append("mean, volatility and Sharpe need at least three recorded returns")
    else:
        row["n_returns"] = 0
        row["gaps"].append("no recorded price history yet; record snapshots to get mean, volatility and momentum")
    row["gaps"].append("P/E, P/B, market cap and dividend yield are not available: fundamentals are not wired")
    return row


def _metric(row, name):
    if name not in row or row[name] is None:
        return None
    return _dec(row[name])


def _apply_filters(rows, filters):
    if not isinstance(filters, list):
        return rows
    kept = []
    for row in rows:
        ok = "error" not in row
        for rule in filters:
            if not isinstance(rule, dict):
                continue
            value = _metric(row, rule.get("metric"))
            if value is None:
                ok = False
                break
            minimum, maximum = _dec(rule.get("min")), _dec(rule.get("max"))
            if minimum is not None and value < minimum:
                ok = False
                break
            if maximum is not None and value > maximum:
                ok = False
                break
        if ok:
            kept.append(row)
    return kept


def _apply_sort(rows, sort_by, order):
    descending = str(order or "desc").lower() != "asc"
    if not sort_by:
        return sorted(rows, key=lambda r: r.get("symbol") or "")
    def key(row):
        if "error" in row:
            return (1, Decimal(0), row.get("symbol") or "")
        value = _metric(row, sort_by)
        if value is None:
            return (1, Decimal(0), row.get("symbol") or "")
        return (0, -value if descending else value, row.get("symbol") or "")
    return sorted(rows, key=key)


def screen(symbols, criteria=None, provider="alphavantage", fetch=None):
    """Fetch a quote per candidate symbol and return a ranked, sourced shortlist."""
    if not isinstance(symbols, (list, tuple)) or not symbols:
        raise ScreenerError("supply a list of candidate symbols")
    if len(symbols) > MAX_SYMBOLS:
        raise ScreenerError("at most %d symbols can be screened at once" % MAX_SYMBOLS)
    fetcher = fetch or instruments._quote_fetcher(provider)
    tracked = instruments.by_symbol()
    rows = []
    for raw in symbols:
        symbol = str(raw or "").strip().upper()
        if not symbol:
            continue
        try:
            quote = fetcher(symbol)
        except marketdata.MarketDataError as error:
            rows.append({"symbol": symbol, "error": str(error), "gaps": [str(error)]})
            continue
        rows.append(_row(symbol, quote, tracked.get(symbol)))
    criteria = criteria if isinstance(criteria, dict) else {}
    rows = _apply_filters(rows, criteria.get("filters"))
    rows = _apply_sort(rows, criteria.get("sort"), criteria.get("order"))
    return {"format": FORMAT, "provider": (provider or "alphavantage"), "criteria": criteria,
            "count": len(rows), "rows": rows,
            "note": "A ranked shortlist of sourced values, not an investment recommendation; "
                    "a missing metric is a named gap, never a guess."}

