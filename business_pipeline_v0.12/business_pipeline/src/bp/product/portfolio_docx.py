"""DOCX rendering for a portfolio snapshot (product layer, formatting only).

Every number and label is read from the stored snapshot produced by the frozen
``portfolio_valuation`` method.  This module formats; it does not compute.
"""

from . import docx


def _fmt(value):
    text = str(value or "")
    try:
        from decimal import Decimal
        number = Decimal(text)
        if number == number.to_integral_value():
            return f"{number:,.0f}"
        return f"{number:,.2f}"
    except Exception:
        return text


def filename(portfolio, snapshot):
    name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(portfolio.get("name", "portfolio")))
    return "%s-%s.docx" % (name.strip("-") or "portfolio", snapshot.get("date", "snapshot"))


def render(portfolio, snapshot):
    """Return the report bytes and its filename."""
    outputs = snapshot.get("outputs") or {}
    positions = snapshot.get("positions") or []
    prices = snapshot.get("prices") or {}
    currency = portfolio.get("base_currency", "")
    title = portfolio.get("name", "Portfolio")
    subtitle = "%s portfolio · snapshot %s · %s" % (portfolio.get("mode", "paper").title(),
                                                    snapshot.get("date", ""), currency)
    sections = [
        {"heading": "Portfolio summary", "paragraphs": [
            "Net asset value: %s %s" % (currency, _fmt(outputs.get("nav"))),
            "Invested value: %s %s" % (currency, _fmt(outputs.get("invested_value"))),
            "Cash: %s %s (%s of NAV)" % (currency, _fmt(outputs.get("cash")),
                                          _pct(outputs.get("cash_pct"))),
            "Largest holding: %s of NAV; top three: %s." % (_pct(outputs.get("top_weight")),
                                                            _pct(outputs.get("top3_concentration"))),
        ]},
        {"heading": "Holdings", "table": {
            "columns": ["Symbol", "Shares", "Price", "Value", "Weight"],
            "rows": [[p.get("symbol", ""), _fmt(p.get("shares")), _fmt(p.get("price")),
                      _fmt(p.get("value")), _pct(p.get("weight"))] for p in positions],
        }},
        {"heading": "Data provenance", "table": {
            "columns": ["Symbol", "Price", "Source", "As of"],
            "rows": [[symbol, _fmt(point.get("price")), point.get("source", ""), point.get("as_of", "")]
                     for symbol, point in sorted(prices.items())],
        }},
        {"heading": "Checks", "bullets": [
            "%s: %s" % (check.get("name", ""), "pass" if check.get("ok") else "fail")
            for check in (snapshot.get("checks") or [])
        ]},
        {"heading": "Assumptions and limits", "bullets": [
            "Prices are the dated values recorded in this snapshot, in one base currency; no FX conversion, fees, tax or dividends are applied.",
            "Weights are value / NAV, so the holding weights plus cash equal one.",
            "A snapshot is a valuation, not a sale price, a forecast or a recommendation.",
            "This report was generated from the stored snapshot and the frozen method result; the figures are not recomputed here.",
        ]},
    ]
    return docx.render_note(title, subtitle, sections), filename(portfolio, snapshot)


def _pct(value):
    try:
        from decimal import Decimal
        return "%.2f%%" % (Decimal(str(value)) * 100)
    except Exception:
        return str(value or "")
