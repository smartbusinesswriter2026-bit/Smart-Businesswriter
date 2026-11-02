"""Instrument choices for the Portfolio Lab (product layer, standard library only).

A **fixed reference list**, not a recommendation engine. Each row says what a
widely held, long-only listing is, in one neutral line, and links to a source the
student can read. Nothing here carries an expected return, a rating, a rank or a
target price; the page sorts alphabetically and the student decides.

The list exists because a student asked to "pick stocks" needs somewhere to start
that is not a tip: the guide explains how to choose, the list shows what the common
building blocks are, and the example books show compositions - all labelled as
examples, never as advice (B-178).

The catalogue is global and quoted in the portfolio's declared base currency. It is
data, not product behaviour: the portfolio store remains the only writer, and no
price or return is ever derived here.
"""

FORMAT = "bp-instruments/1"
CATALOGUE_VERSION = 1

GUIDANCE = {
    "title": "How to choose what you hold",
    "intro": ("A portfolio is the collection of holdings you declare. The app does not recommend, "
              "rank or forecast an investment: it helps you make a deliberate choice and record why "
              "you made it, so the report can defend the decision. Work through these steps in order."),
    "steps": [
        {"title": "Write the mandate.",
         "text": ("State the objective, the benchmark you will be measured against and the base "
                  "currency before you look at a single name. A mandate you can restate in one "
                  "sentence is a mandate you can defend.")},
        {"title": "Decide the mix before the names.",
         "text": ("A broad index fund is a diversified core; a sector or thematic fund is a "
                  "deliberate tilt; a single company is a firm-specific view; cash is liquidity. "
                  "Write the target share of each before you pick a ticker.")},
        {"title": "Pick from the list, not from a tip.",
         "text": ("The list below is a fixed reference set of large, widely held listings with a "
                  "one-line description and a source link. It is not ranked and it carries no "
                  "expected return. Read what the instrument is, then add it.")},
        {"title": "Check that it fits the book.",
         "text": ("One base currency: a foreign price must be converted before entry, because the "
                  "app does not convert it for you. Keep the declared limits (by default no single "
                  "position above 10% of NAV and at least 5% cash), and remember a holding you "
                  "cannot price is not a holding yet.")},
        {"title": "Read the evidence, then write the reason.",
         "text": ("Open the fundamentals and filings lookup beside the book, then write one line "
                  "per holding: what you expect it to do in this portfolio and what would make you "
                  "remove it. The report prints it under Holdings and rationale; a blank reason is "
                  "a gap, not a neutral choice.")},
        {"title": "Snapshot, then grade the decision.",
         "text": ("Create the dated snapshot, read the checks, export the report, then compare the "
                  "outcome with the reason you wrote. A defensible decision is one you can explain, "
                  "not one that happened to go up.")},
    ],
    "principles": [
        "The app never recommends, ranks or forecasts an investment.",
        "Diversification is a decision you make; the app only reports the concentration you end up with.",
        "A price is a declared value on a date, not the value of the company.",
        "If you cannot write the reason, you are not ready to hold it.",
    ],
    "limits": [
        "No FX conversion: convert a foreign price before entry.",
        "No fees, tax, dividends or corporate actions.",
        "No forecast, target price or rating.",
        "The list is a fixed reference and is not a complete market; a listing is not an endorsement.",
    ],
}

#: The instrument list. `quote_supported` says whether the optional free quote
#: source is likely to answer for this listing; a manual price always works.
CATALOGUE = [
    {"id": "voo", "symbol": "VOO", "name": "Vanguard S&P 500 ETF", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Tracks the S&P 500: about 500 large US companies in one fund.",
     "teaching_note": ("One fund holds hundreds of companies, so a single company's result moves "
                       "it only a little. A common diversified core."),
     "source_url": "https://investor.vanguard.com/investment-products/etfs/profile/voo"},
    {"id": "vti", "symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Tracks the total US stock market, from the largest to the smallest listed company.",
     "teaching_note": "Broader than a large-cap index: it reaches smaller companies as well.",
     "source_url": "https://investor.vanguard.com/investment-products/etfs/profile/vti"},
    {"id": "vxus", "symbol": "VXUS", "name": "Vanguard Total International Stock ETF",
     "exchange": "NASDAQ", "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds listed companies outside the United States in one fund.",
     "teaching_note": ("Adds countries and currencies a US-only fund misses; the fund's own price "
                       "is quoted in the base currency."),
     "source_url": "https://investor.vanguard.com/investment-products/etfs/profile/vxus"},
    {"id": "vt", "symbol": "VT", "name": "Vanguard Total World Stock ETF", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "A single global fund covering US and non-US listed companies.",
     "teaching_note": "Global diversification in one line, instead of several regional funds.",
     "source_url": "https://investor.vanguard.com/investment-products/etfs/profile/vt"},
    {"id": "qqq", "symbol": "QQQ", "name": "Invesco QQQ Trust", "exchange": "NASDAQ",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Tracks the Nasdaq-100: the largest non-financial companies listed on Nasdaq.",
     "teaching_note": ("Concentrated in large growth companies, so it behaves differently from a "
                       "broad market fund."),
     "source_url": "https://www.invesco.com/qqq-etf/en/home.html"},
    {"id": "iwm", "symbol": "IWM", "name": "iShares Russell 2000 ETF", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Tracks 2,000 smaller US companies.",
     "teaching_note": "Smaller companies can move more than large ones in the same market.",
     "source_url": "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf"},
    {"id": "xle", "symbol": "XLE", "name": "Energy Select Sector SPDR Fund", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds energy-sector companies: oil, gas and energy equipment and services.",
     "teaching_note": ("A sector fund is a deliberate tilt: its result follows one industry, not "
                       "the whole market."),
     "source_url": "https://www.ssga.com/us/en/intermediary/etfs/the-energy-select-sector-spdr-fund-xle"},
    {"id": "xlk", "symbol": "XLK", "name": "Technology Select Sector SPDR Fund",
     "exchange": "NYSE Arca", "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds technology-sector companies.",
     "teaching_note": "A sector tilt means a large share of the book can depend on one industry.",
     "source_url": "https://www.ssga.com/us/en/intermediary/etfs/the-technology-select-sector-spdr-fund-xlk"},
    {"id": "xlv", "symbol": "XLV", "name": "Health Care Select Sector SPDR Fund",
     "exchange": "NYSE Arca", "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds health-care-sector companies: pharmaceuticals, providers and equipment.",
     "teaching_note": "A defensive sector in many market conditions, but still one industry.",
     "source_url": "https://www.ssga.com/us/en/intermediary/etfs/the-health-care-select-sector-spdr-fund-xlv"},
    {"id": "xlf", "symbol": "XLF", "name": "Financial Select Sector SPDR Fund",
     "exchange": "NYSE Arca", "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds banks, insurers and other financial companies.",
     "teaching_note": "A sector whose results are sensitive to interest rates and credit conditions.",
     "source_url": "https://www.ssga.com/us/en/intermediary/etfs/the-financial-select-sector-spdr-fund-xlf"},
    {"id": "vnq", "symbol": "VNQ", "name": "Vanguard Real Estate ETF", "exchange": "NYSE Arca",
     "currency": "USD", "asset_class": "etf", "quote_supported": True,
     "description": "Holds real-estate investment trusts and related companies.",
     "teaching_note": "Property-linked cash flows and values move for their own reasons.",
     "source_url": "https://investor.vanguard.com/investment-products/etfs/profile/vnq"},
    {"id": "aapl", "symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Consumer electronics, software and services.",
     "teaching_note": "One company: a firm-specific view, not a diversified holding.",
     "source_url": "https://investor.apple.com/"},
    {"id": "msft", "symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Software, cloud computing and hardware.",
     "teaching_note": "One company: its own results drive the holding, not the market average.",
     "source_url": "https://www.microsoft.com/en-us/investor"},
    {"id": "nvda", "symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Graphics processors and accelerated computing.",
     "teaching_note": "A single company whose price has moved sharply; concentration risk shows here.",
     "source_url": "https://investor.nvidia.com/"},
    {"id": "ko", "symbol": "KO", "name": "The Coca-Cola Company", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Beverages, sold in most countries in the world.",
     "teaching_note": "A single, mature company: lower volatility than a small growth company is not diversification.",
     "source_url": "https://investors.coca-colacompany.com/"},
    {"id": "pg", "symbol": "PG", "name": "Procter & Gamble Company", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Household and personal-care products.",
     "teaching_note": "Demand tends to be steady, but this is still one company and one share of the book.",
     "source_url": "https://www.pginvestor.com/"},
    {"id": "jnj", "symbol": "JNJ", "name": "Johnson & Johnson", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Pharmaceuticals, medical devices and consumer health products.",
     "teaching_note": "One company across several health-care segments; not a substitute for a sector fund.",
     "source_url": "https://www.investor.jnj.com/"},
    {"id": "jpm", "symbol": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Banking, payments and asset management.",
     "teaching_note": "A bank's results depend on interest rates, credit and the economy.",
     "source_url": "https://www.jpmorganchase.com/ir"},
    {"id": "xom", "symbol": "XOM", "name": "Exxon Mobil Corporation", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Oil and gas exploration, production and refining.",
     "teaching_note": "Earnings follow energy prices; one commodity cycle can dominate the result.",
     "source_url": "https://investor.exxonmobil.com/"},
    {"id": "wmt", "symbol": "WMT", "name": "Walmart Inc.", "exchange": "NYSE",
     "currency": "USD", "asset_class": "equity", "quote_supported": True,
     "description": "Retail stores and e-commerce, mostly in the United States.",
     "teaching_note": "Retail margins are thin; the reason to hold it must say why it fits the mandate.",
     "source_url": "https://stock.walmart.com/"},
]

#: Composition examples, never advice. Every row is editable before it is saved.
SAMPLE_BOOKS = [
    {"id": "core", "label": "Diversified core",
     "intent": ("A broad-market core with an international sleeve and a small firm-specific "
                "position: the shape a first paper usually starts from."),
     "holdings": [{"symbol": "VOO", "shares": "20", "cost_basis": "0"},
                  {"symbol": "VTI", "shares": "10", "cost_basis": "0"},
                  {"symbol": "VXUS", "shares": "15", "cost_basis": "0"},
                  {"symbol": "AAPL", "shares": "5", "cost_basis": "0"}],
     "cash": "5000",
     "note": ("Example only, not advice: four positions is a starting point, not a rule. Load it, "
              "then replace, resize or remove every row with your own decision.")},
    {"id": "balanced", "label": "Balanced with a cash buffer",
     "intent": ("A core fund plus two sector tilts and a steady single name, held with a larger "
                "cash balance to show how cash changes the concentration arithmetic."),
     "holdings": [{"symbol": "VOO", "shares": "10", "cost_basis": "0"},
                  {"symbol": "XLV", "shares": "5", "cost_basis": "0"},
                  {"symbol": "XLK", "shares": "5", "cost_basis": "0"},
                  {"symbol": "KO", "shares": "20", "cost_basis": "0"}],
     "cash": "8000",
     "note": ("Example only, not advice: sector funds are tilts and add industry risk. Replace them "
              "if your mandate does not call for a tilt.")},
    {"id": "concentrated", "label": "Concentrated growth view",
     "intent": ("A deliberately concentrated book: one growth fund, one technology tilt and two "
                "large single names. It exists to show what a high-concentration result looks like."),
     "holdings": [{"symbol": "QQQ", "shares": "10", "cost_basis": "0"},
                  {"symbol": "XLK", "shares": "8", "cost_basis": "0"},
                  {"symbol": "NVDA", "shares": "3", "cost_basis": "0"},
                  {"symbol": "MSFT", "shares": "2", "cost_basis": "0"}],
     "cash": "1000",
     "note": ("Example only, not advice: this book is concentrated and will breach the default "
              "10% position limit. It is here so you can see why the limits exist.")},
]


def guidance():
    return GUIDANCE


def catalogue():
    return [dict(row) for row in CATALOGUE]


def sample_books():
    return [dict(row) for row in SAMPLE_BOOKS]


def find(symbol):
    wanted = str(symbol or "").strip().upper()
    for row in CATALOGUE:
        if row["symbol"] == wanted:
            return dict(row)
    return None


def bundle():
    """Everything the page needs to render the chooser and the guide, in one payload."""
    return {"format": FORMAT, "catalogue_version": CATALOGUE_VERSION,
            "guidance": guidance(), "instruments": catalogue(),
            "sample_books": sample_books(),
            "note": ("A fixed reference list of widely held long-only listings. Not ranked, not "
                     "advice and not a forecast; every price is a declared figure the student enters.")}
