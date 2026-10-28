"""Build the Portfolio Lab sample: a mock-fund report with a journal and a return.

Run from `business_pipeline/`:

    PYTHONPATH=src python scripts/build_portfolio_sample.py

The sample is generated through the product store, the frozen valuation and
performance methods and the DOCX formatter, never typed by hand.  Its prices are
simulated and every provenance row says so; it is an illustration, not market
data.  The store lives in a temporary directory, so the sample does not appear in
the app's real portfolio list.
"""

import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bp import methods  # noqa: E402
from bp.product import portfolio_docx, portfolios  # noqa: E402

NAME = "Sample mock fund (simulated prices)"
DATES = ["2026-10-09", "2026-10-16", "2026-10-23"]
PRICES = {
    "2026-10-09": {"AAPL": "335", "MSFT": "495", "VOO": "470"},
    "2026-10-16": {"AAPL": "340", "MSFT": "500", "VOO": "480"},
    "2026-10-23": {"AAPL": "350", "MSFT": "510", "VOO": "490"},
}
CASH = {"2026-10-09": "2500", "2026-10-16": "2500", "2026-10-23": "2500"}
HOLDINGS = [
    ("AAPL", "20", "150", "Cash-generative services franchise; sized below the fund's 50% single-name cap."),
    ("MSFT", "8", "300", "Diversifies the book into cloud and productivity software."),
    ("VOO", "5", "400", "Core index exposure so the fund is not only single-stock risk."),
]
JOURNAL = [
    ("2026-10-09", "0", "100", "Opened the book with AAPL, MSFT and VOO; cash held at about 16% of NAV."),
    ("2026-10-16", "500", "101", "Added USD 500 from the team's contribution and kept the weights; no trade this week."),
    ("2026-10-23", "0", "102", "Held through a flat week; reviewed the AAPL weight against the 50% mandate cap."),
]


def build():
    store = tempfile.mkdtemp(prefix="bp-sample-fund-")
    import os
    os.environ["BP_PORTFOLIOS_DIR"] = store
    try:
        portfolio = portfolios.create(
            NAME, "USD", "S&P 500", "fund",
            constraints={"max_position": "0.50", "min_cash": "0.05", "long_only": True},
            objective=("Apply a long-only, three-position mandate over four weeks and explain each "
                       "decision in the journal. Prices are simulated for this sample."),
            roster="Sample team (illustration)")
        pid = portfolio["id"]
        for symbol, shares, cost, why in HOLDINGS:
            portfolios.add_holding(pid, symbol, shares, cost, why)
        for day, flow, benchmark, note in JOURNAL:
            for symbol in PRICES[day]:
                portfolios.set_price(pid, symbol, day, PRICES[day][symbol], source="sample (simulated)")
            portfolios.save_journal(pid, day, note=note, flow=flow, benchmark=benchmark)
        _snapshots(pid)
        bundle = portfolios.load(pid)
        performance = _performance(pid, bundle)
        loaded = [portfolios.snapshot(pid, row["date"]) for row in bundle["snapshots"]]
        data, _filename = portfolio_docx.render(bundle["portfolio"], loaded[-1],
                                                holdings=bundle["holdings"],
                                                performance=performance,
                                                journal=bundle["journal"])
        target = ROOT / "samples" / "portfolio-mock-fund-sample.docx"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target, performance, loaded[-1]
    finally:
        shutil.rmtree(store, ignore_errors=True)


def _snapshots(pid):
    valuation = methods.LIBRARY["portfolio_valuation"]
    for day in DATES:
        prices = PRICES[day]
        inputs = {"holdings": [{"symbol": symbol, "shares": shares, "price": prices[symbol]}
                               for symbol, shares, _cost, _why in HOLDINGS], "cash": CASH[day]}
        issues = methods.validate_inputs(valuation, inputs) + valuation.profile(inputs)
        if issues:
            raise SystemExit("invalid sample snapshot %s: %s" % (day, issues))
        checks = valuation.tests(inputs, valuation.impl)
        if not all(ok for _name, ok in checks):
            raise SystemExit("a valuation check failed for %s" % day)
        outputs = valuation.impl(inputs)
        appendix = outputs.pop("_appendix")
        outputs.pop("_checks", None)
        portfolios.save_snapshot(pid, {
            "date": day, "inputs": inputs,
            "outputs": {key: str(value) for key, value in outputs.items()},
            "positions": appendix["positions"], "conventions": appendix["conventions"],
            "prices": {symbol: {"price": prices[symbol], "source": "sample (simulated)", "as_of": day}
                       for symbol in prices},
            "checks": [{"name": name, "ok": bool(ok)} for name, ok in checks],
            "method": "portfolio_valuation", "version": valuation.version,
        })


def _performance(pid, bundle):
    loaded = [portfolios.snapshot(pid, row["date"]) for row in bundle["snapshots"]]
    entries = {row["date"]: row for row in bundle["journal"]}
    periods, starts, ends = [], [], []
    for previous, current in zip(loaded, loaded[1:]):
        entry = entries[current["date"]]
        periods.append({"label": current["date"], "start_nav": previous["outputs"]["nav"],
                        "end_nav": current["outputs"]["nav"], "flow": entry.get("flow", "0")})
        starts.append(entries[previous["date"]]["benchmark"])
        ends.append(entry["benchmark"])
    method = methods.LIBRARY["portfolio_performance"]
    inputs = {"periods": periods, "benchmark_start": starts, "benchmark_end": ends}
    issues = methods.validate_inputs(method, inputs) + method.profile(inputs)
    if issues:
        raise SystemExit("invalid sample performance input: %s" % issues)
    checks = method.tests(inputs, method.impl)
    if not all(ok for _name, ok in checks):
        raise SystemExit("a performance check failed")
    outputs = method.impl(inputs)
    appendix = outputs.pop("_appendix")
    outputs.pop("_checks", None)
    return {"outputs": {key: str(value) for key, value in outputs.items()},
            "periods": appendix["periods"], "conventions": appendix["conventions"],
            "benchmark_used": "benchmark_return" in outputs, "benchmark_complete": True,
            "checks": [{"name": name, "ok": bool(ok)} for name, ok in checks]}


if __name__ == "__main__":
    target, performance, snapshot = build()
    print("wrote %s (%d bytes)" % (target, target.stat().st_size))
    print("TWR %s | NAV %s" % (performance["outputs"]["twr"], snapshot["outputs"]["nav"]))
