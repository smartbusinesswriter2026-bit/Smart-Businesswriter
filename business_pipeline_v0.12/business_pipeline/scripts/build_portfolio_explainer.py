"""Build the Portfolio Lab explainer (a note-style Word document).

    PYTHONPATH=src python scripts/build_portfolio_explainer.py

The explainer is written for students and instructors. Every figure it quotes is
from the generated sample fund (`scripts/build_portfolio_sample.py`), and the
sample's prices are simulated.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bp.product import docx  # noqa: E402

SECTIONS = [
    {"heading": "What this is", "paragraphs": [
        "The Portfolio Lab is a local workbench for two related jobs: valuing a paper portfolio on one date, "
        "and running a semester mock fund with a weekly journal. It takes the holdings and prices you declare, "
        "stores each valuation as a dated snapshot, computes the figures in the frozen method library, and "
        "exports a Word report you can submit.",
        "It is not a broker, a price predictor or a stock picker. It does not fetch a price unless you press "
        "the fetch button, and it never turns a missing number into a plausible one.",
    ]},
    {"heading": "Paper mode in five steps", "bullets": [
        "Create a portfolio: give it a name, a base currency and, if you use one, a benchmark.",
        "Add holdings: symbol, shares, an optional cost basis and a one-line rationale.",
        "Enter prices for one date: type them, paste a table, or choose a CSV/TSV file. The optional fetch button can fill them from a configured source; you still check each one.",
        "Create the snapshot: the frozen method computes NAV, invested value, cash, each weight and the concentration measures, then runs its checks.",
        "Export the report: summary, holdings and rationale, provenance, checks and limits.",
    ]},
    {"heading": "Fund mode: the weekly rhythm", "paragraphs": [
        "A mock fund adds a journal and a return. Each week you create a snapshot, then record the period's "
        "external flow and, if you use one, the benchmark level. A note in your own words says what changed and "
        "why. The report chains the periods into a time-weighted return.",
    ], "bullets": [
        "The flow is treated as occurring at the start of its period, so a contribution is not counted as performance.",
        "The time-weighted return chains (1 + period return) across the declared periods; a benchmark is chained the same way.",
        "A benchmark is reported only when every period declares both levels. A partial benchmark is a named gap, not a filled number.",
        "The journal is your record of decisions. It is not generated, scored or rewritten by the app.",
    ]},
    {"heading": "Reading the numbers", "bullets": [
        "NAV: the market value of the holdings plus cash. It is a valuation, not a sale price.",
        "Invested value: the holdings alone, before cash.",
        "Weight: a holding's value divided by NAV. The holding weights plus the cash share equal one.",
        "Top three: the three largest weights added together. HHI is a second concentration measure; higher means more concentrated.",
        "Time-weighted return: the return of the portfolio, with contributions and withdrawals kept out of the performance.",
        "Active return: the portfolio's time-weighted return minus the benchmark's chained return.",
    ]},
    {"heading": "What the checks mean", "paragraphs": [
        "The report says \"All 12 checks passed\" rather than printing internal names. The checks confirm the "
        "arithmetic and the weights, not the prices. A failed check blocks the result; it is named, never hidden.",
    ], "bullets": [
        "A second calculation route agrees with the first.",
        "NAV equals the holdings' value plus cash.",
        "The holding weights plus cash sum to one.",
        "Doubling every price doubles the invested value.",
        "One more unit of cash raises NAV by one.",
        "The concentration measures stay between zero and one.",
        "The return chains every period; a no-flow period equals the NAV ratio.",
        "The average period sits between the best and the worst.",
        "The benchmark chains the same way; the final NAV is the last period's end.",
    ]},
    {"heading": "Where the prices come from", "paragraphs": [
        "Manual entry, paste and CSV import are the default. The fetch button is optional and never runs on its "
        "own. It tries Alpha Vantage first, then Massive, then a declared QVeris capability; each provider has an "
        "internal ceiling. A provider without its key, or at its limit, is skipped and the next is tried. The "
        "provider that answered, and its real trading day, are recorded in the snapshot.",
    ], "bullets": [
        "No key is exposed to the page; the server reads it from its environment or a gitignored local file.",
        "A fetched price still needs your check; the app records the source and the as-of date.",
        "One base currency only: there is no FX conversion, so a foreign quote must be converted before entry.",
        "When every provider is exhausted, the fetch says so and points to manual entry; the snapshot stays blocked until every holding has a price.",
    ]},
    {"heading": "A worked example", "paragraphs": [
        "The sample fund holds AAPL, MSFT and VOO, with a USD 500 contribution in the second week and the S&P 500 "
        "as a declared benchmark. Its prices are simulated for the illustration.",
    ], "table": {
        "columns": ["Period ends", "Start NAV", "End NAV", "Flow", "Period return", "Benchmark"],
        "rows": [
            ["2026-10-16", "15,510", "15,700", "500", "-1.94%", "1.00%"],
            ["2026-10-23", "15,700", "16,030", "0", "2.10%", "0.99%"],
        ],
    }},
    {"heading": "The report a professor can grade", "table": {
        "columns": ["Section", "What it answers"],
        "rows": [
            ["Objective and mandate", "What were you asked to do, in your own words?"],
            ["Portfolio summary", "What is the book worth, and how much is cash?"],
            ["Holdings and rationale", "What do you own, and why?"],
            ["Performance", "What did it return, net of flows, against the benchmark?"],
            ["Journal of decisions", "What changed each week, and why?"],
            ["Data provenance", "Where did each price come from, and on what date?"],
            ["Checks", "What was verified, in plain language?"],
            ["Assumptions and limits", "What does the report not claim?"],
        ],
    }},
    {"heading": "For instructors", "bullets": [
        "The artifacts are dated and immutable: a snapshot for a date cannot be rewritten after it is saved.",
        "The journal is student-authored; the app records it, it does not generate it.",
        "The export gate refuses an incomplete report, so a missing price or an unrecorded benchmark is visible before submission.",
        "A rubric can map directly onto the report sections: objective, holdings and rationale, data provenance, performance, decisions, limits.",
        "The same frozen methods run on the student's own numbers, so the arithmetic is auditable rather than a black box.",
    ]},
    {"heading": "What it does not do", "bullets": [
        "No FX conversion, fees, tax, dividends or corporate actions.",
        "No shorting, margin or derivatives; the book is long-only equities, ETFs and cash.",
        "No forecast, target price or recommendation.",
        "No automatic trading or broker connection; this is a simulation, not real money.",
        "No silent filling: a gap is named and blocks the result.",
    ]},
    {"heading": "A one-page checklist", "bullets": [
        "Name the objective and the benchmark before you buy.",
        "Record one rationale per holding, in your own words.",
        "Enter a price for every holding on the snapshot date.",
        "Create the snapshot and read the checks; do not submit a failed one.",
        "For a fund, record the flow and the benchmark level each week.",
        "Write the journal entry the same day; memory is not a source.",
        "Export the report and read the limits before you submit it.",
    ]},
]


def build():
    data = docx.render_note("Portfolio Lab: from holdings to a report you can defend",
                            "A short explainer for students and instructors \u00b7 build 1.43",
                            SECTIONS)
    target = ROOT / "samples" / "portfolio-lab-explainer.docx"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


if __name__ == "__main__":
    target = build()
    print("wrote %s (%d bytes)" % (target, target.stat().st_size))
