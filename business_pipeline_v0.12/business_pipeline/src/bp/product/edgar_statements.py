"""Best-effort financial-statement research via U.S. SEC EDGAR (no key).

This is the "online research" path for the Portfolio Lab: for a US-listed
company it pulls the latest annual XBRL facts and builds the lines the
statement reader needs.  For a non-US or private company it raises
``EdgarUnavailable`` with a plain-language reason, so the caller can record a
named gap instead of inventing a figure.
"""

import re
from . import marketdata

EDGAR_CONCEPTS = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "net_income": ("NetIncomeLoss",),
    "total_assets": ("Assets",),
    "total_liabilities": ("Liabilities",),
    "equity": ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
    "current_assets": ("AssetsCurrent",),
    "current_liabilities": ("LiabilitiesCurrent",),
    "inventory": ("InventoryNet",),
    "cost_of_goods_sold": ("CostOfGoodsAndServicesSold", "CostOfGoodsSold"),
    "gross_profit": ("GrossProfit",),
    "ebit": ("OperatingIncomeLoss",),
    "retained_earnings": ("RetainedEarningsAccumulatedDeficit",),
    "eps": ("EarningsPerShareDiluted", "EarningsPerShareBasic"),
}


class EdgarUnavailable(Exception):
    """The statement could not be researched; the message is shown to the student."""


def _lines_for(ticker):
    filings = marketdata.sec_filings(ticker, "", 1)
    cik = str(filings.get("cik") or "").strip()
    if not cik:
        raise EdgarUnavailable("SEC EDGAR covers US registrants only; %s is not one." % ticker)
    cik = cik.zfill(10)
    lines = {}
    ends = []
    for key, tags in EDGAR_CONCEPTS.items():
        try:
            value, end, _raw, _final, _tag = marketdata._sec_concept(cik, tags)
        except marketdata.MarketDataError:
            continue
        lines[key] = float(value)
        if end:
            ends.append(end)
    if not lines:
        raise EdgarUnavailable("SEC EDGAR has no XBRL statement facts for " + ticker)
    # market value of equity from a quote, if available (best effort)
    try:
        q = marketdata.equity_quote(ticker)
        if q and q.get("value") and q.get("as_of"):
            # no share count here; leave market_value_equity as a gap
            pass
    except Exception:
        pass
    as_of = max(ends) if ends else ""
    return lines, as_of, cik


def research(ticker):
    """Return (text_lines, as_of, source_url) for a US-listed ticker, or raise."""
    ticker = marketdata._symbol(ticker)
    try:
        lines, as_of, cik = _lines_for(ticker)
    except marketdata.MarketDataError as error:
        raise EdgarUnavailable(str(error))
    # render as the statement reader expects
    out = []
    labels = {
        "revenue": "Revenue",
        "net_income": "Net income",
        "total_assets": "Total assets",
        "total_liabilities": "Total liabilities",
        "equity": "Shareholders equity",
        "current_assets": "Current assets",
        "current_liabilities": "Current liabilities",
        "inventory": "Inventory",
        "cost_of_goods_sold": "Cost of goods sold",
        "gross_profit": "Gross profit",
        "ebit": "EBIT",
        "retained_earnings": "Retained earnings",
        "eps": "Earnings per share",
    }
    for key, label in labels.items():
        if key in lines:
            out.append("%s, %s" % (label, lines[key]))
    text = "\n".join(out)
    url = "https://data.sec.gov/api/xbrl/companyconcept/CIK%s" % cik
    return text, as_of, url, lines
