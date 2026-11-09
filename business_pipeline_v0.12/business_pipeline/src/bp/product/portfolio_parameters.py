"""Stock-selection parameters for the Portfolio Lab (classroom criteria).

This module is data and definitions only.  It never recommends, never ranks and
never invents a value.  Each parameter carries its classroom name, a one-line
definition, the formula and whether the Portfolio Lab can source it or the
student must type it from their own source.  A missing value stays a named gap.
"""

FORMAT = "bp-portfolio-parameters/1"


def _param(pid, label, sets, definition, formula, unit, source, screener_field=None):
    return {
        "id": pid,
        "label": label,
        "sets": list(sets),
        "definition": definition,
        "formula": formula,
        "unit": unit,
        "source": source,
        "screener_field": screener_field,
    }


_PARAMETERS = [
    # ---- finance ratios (investments course) ----
    _param("pe_ratio", "Price-to-earnings (P/E)", ["finance", "both"],
           "How much investors pay per dollar of earnings. Lower is cheaper relative to earnings, "
           "but a low P/E can mean distress rather than value.",
           "share price / earnings per share", "x (multiple)", "sourced", "pe_ratio"),
    _param("pb_ratio", "Price-to-book (P/B)", ["finance", "both"],
           "Price relative to accounting book value. Below 1 means the market prices the firm below "
           "its net assets; useful for asset-heavy firms.",
           "share price / book value per share", "x (multiple)", "manual"),
    _param("dividend_yield", "Dividend yield", ["finance", "both"],
           "Cash returned to shareholders as a share of the price. Higher is more income, but a very "
           "high yield can signal a price that has already fallen.",
           "annual dividend per share / share price", "percent", "manual"),
    _param("roe", "Return on equity (ROE)", ["finance", "accounting", "both"],
           "How much profit the firm earns on the shareholders' money. Higher is better, but check it "
           "is not driven only by debt.",
           "net income / shareholders' equity", "percent", "sourced", "roe"),
    _param("roa", "Return on assets (ROA)", ["finance", "accounting", "both"],
           "How efficiently the firm uses its assets to earn profit. Higher is better and is less "
           "distorted by leverage than ROE.",
           "net income / total assets", "percent", "manual"),
    _param("eps_growth", "EPS growth", ["finance", "both"],
           "Growth in earnings per share. Positive and steady growth supports a higher valuation.",
           "(EPS this period - EPS last period) / EPS last period", "percent", "manual"),
    _param("beta", "Beta", ["finance", "both"],
           "How much the stock moves with the market. Above 1 means more volatile than the market; "
           "below 1 means less.",
           "covariance(stock, market) / variance(market)", "x", "manual"),
    _param("sharpe", "Sharpe ratio", ["finance", "both"],
           "Excess return per unit of risk taken. Higher is better, but it needs a return history to "
           "compute.",
           "(mean return - risk-free rate) / standard deviation of returns", "x", "sourced",
           "sharpe"),
    _param("one_day_return", "One-day return", ["finance", "both"],
           "The latest daily price change. A snapshot of recent movement, not a forecast.",
           "(today's price - yesterday's price) / yesterday's price", "percent", "sourced",
           "one_day_return"),
    _param("mean_return", "Mean return", ["finance", "both"],
           "Average period return over the recorded history. Needs at least three recorded returns.",
           "sum of period returns / number of periods", "percent", "sourced", "mean_return"),
    _param("market_cap", "Market capitalisation", ["finance", "both"],
           "The market value of the firm: price times shares outstanding. A size measure, not a "
           "quality measure.",
           "share price x shares outstanding", "currency", "sourced", "market_cap"),
    # ---- accounting ratios ----
    _param("gross_margin", "Gross profit margin", ["accounting", "both"],
           "Share of revenue left after the cost of goods sold. Higher means stronger pricing or lower "
           "direct costs.",
           "gross profit / revenue", "percent", "manual"),
    _param("net_margin", "Net profit margin", ["accounting", "both"],
           "Share of revenue that becomes net income. Higher is better and less easily distorted.",
           "net income / revenue", "percent", "manual"),
    _param("current_ratio", "Current ratio", ["accounting", "both"],
           "Short-term liquidity: can current assets cover current liabilities? Above 1 is generally "
           "safe; far above 1 may mean idle assets.",
           "current assets / current liabilities", "x", "manual"),
    _param("quick_ratio", "Quick ratio", ["accounting", "both"],
           "A stricter liquidity test that excludes inventory. Above 1 means the firm can pay short-term "
           "debts without selling stock.",
           "(current assets - inventory) / current liabilities", "x", "manual"),
    _param("debt_to_equity", "Debt-to-equity", ["accounting", "both"],
           "How much of the firm is financed by debt. Higher means more leverage and more risk.",
           "total liabilities / shareholders' equity", "x", "manual"),
    _param("asset_turnover", "Asset turnover", ["accounting", "both"],
           "How much revenue each dollar of assets generates. Higher means more efficient use of assets.",
           "revenue / total assets", "x", "manual"),
    _param("inventory_turnover", "Inventory turnover", ["accounting", "both"],
           "How often inventory is sold and replaced. Higher is usually better, but too high may mean "
           "stock-outs.",
           "cost of goods sold / average inventory", "x", "manual"),
    # ---- composite scores ----
    _param("altman_z", "Altman Z-score", ["composite", "both"],
           "A bankruptcy-prediction score built from five financial ratios. Above 2.99 is generally "
           "safe, below 1.81 is distress. A classroom tool, not a guarantee.",
           "1.2(WC/TA) + 1.4(RE/TA) + 3.3(EBIT/TA) + 0.6(MVE/TL) + 1.0(S/TA)", "x", "manual"),
    _param("piotroski_f", "Piotroski F-score", ["composite", "both"],
           "Nine binary accounting tests summed (0-9). Higher means stronger financial health and "
           "improving fundamentals.",
           "sum of nine pass/fail accounting tests", "0-9", "manual"),
    _param("dupont_roe", "DuPont ROE", ["composite", "both"],
           "Breaks ROE into profitability, efficiency and leverage, so you can see why ROE moved.",
           "net margin x asset turnover x equity multiplier", "percent", "manual"),
    _param("graham_number", "Graham number", ["composite", "both"],
           "Benjamin Graham's estimate of a stock's fair value from earnings and book value. A value "
           "screen, not a buy signal.",
           "sqrt(22.5 x EPS x book value per share)", "currency", "manual"),
]

_SETS = [
    {"id": "finance", "label": "Finance ratios",
     "description": "The standard investments-course set: valuation, profitability, risk and size."},
    {"id": "accounting", "label": "Accounting ratios",
     "description": "Profitability, liquidity, solvency and efficiency ratios from financial statements."},
    {"id": "both", "label": "Both (finance + accounting)",
     "description": "The combined set, grouped by class."},
    {"id": "composite", "label": "Composite scores",
     "description": "Single-number screens taught in class: Altman Z, Piotroski F, DuPont, Graham number."},
]


def catalogue():
    return {"format": FORMAT, "sets": [dict(s) for s in _SETS],
            "parameters": [dict(p) for p in _PARAMETERS]}


def parameters_for(set_id):
    if set_id == "both":
        wanted = {"finance", "accounting", "both", "composite"}
    else:
        wanted = {set_id, "both"}
    return [dict(p) for p in _PARAMETERS if wanted & set(p["sets"])]


def get(pid):
    for p in _PARAMETERS:
        if p["id"] == pid:
            return dict(p)
    return None
