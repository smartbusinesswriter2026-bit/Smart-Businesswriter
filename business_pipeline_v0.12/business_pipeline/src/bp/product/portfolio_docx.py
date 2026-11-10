"""DOCX rendering for a portfolio snapshot and, in fund mode, its journal.

Every number and label is read from the stored snapshot, the frozen performance
result and the student's own journal.  This module formats; it computes nothing
and invents nothing.  A missing section is named as a gap, never filled.
"""

from . import docx


def _fmt(value):
    text = str(value if value is not None else "")
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


def render(portfolio, snapshot, holdings=(), performance=None, journal=(), portfolio_id=None):
    """Return the report bytes and its filename."""
    outputs = snapshot.get("outputs") or {}
    positions = snapshot.get("positions") or []
    prices = snapshot.get("prices") or {}
    currency = portfolio.get("base_currency", "")
    title = portfolio.get("name", "Portfolio")
    mode = str(portfolio.get("mode", "paper")).title()
    subtitle = "%s portfolio · snapshot %s · %s" % (mode, snapshot.get("date", ""), currency)
    rationale = {str(row.get("symbol", "")).upper(): str(row.get("rationale", "") or "")
                 for row in holdings}
    sections = [
        {"heading": "Objective and mandate", "paragraphs": _objective_lines(portfolio)},
        {"heading": "Portfolio summary", "paragraphs": [
            "Net asset value: %s %s" % (currency, _fmt(outputs.get("nav"))),
            "Invested value: %s %s" % (currency, _fmt(outputs.get("invested_value"))),
            "Cash: %s %s (%s of NAV)" % (currency, _fmt(outputs.get("cash")),
                                          _pct(outputs.get("cash_pct"))),
            "Largest holding: %s of NAV; top three: %s." % (_pct(outputs.get("top_weight")),
                                                            _pct(outputs.get("top3_concentration"))),
        ]},
        {"heading": "Holdings and rationale", "table": {
            "columns": ["Symbol", "Shares", "Price", "Value", "Weight", "Rationale"],
            "rows": [[p.get("symbol", ""), _fmt(p.get("shares")), _fmt(p.get("price")),
                      _fmt(p.get("value")), _pct(p.get("weight")),
                      rationale.get(str(p.get("symbol", "")).upper(), "") or "(not recorded)"]
                     for p in positions],
        }},
    ]
    selection = portfolio.get("selection")
    if isinstance(selection, dict) and selection.get("rows"):
        params = selection.get("parameters") or []
        param_labels = params
        # resolve labels from the parameter catalog when available
        try:
            from . import portfolio_parameters as _pp
            labels = []
            for pid in params:
                p = _pp.get(pid)
                labels.append(p["label"] if p else pid)
            if labels:
                param_labels = labels
        except Exception:
            pass
        set_name = str(selection.get("set") or "").strip() or "not recorded"
        rows = selection.get("rows") or []
        thresholds = selection.get("thresholds") or {}
        columns = ["Symbol"] + param_labels
        if any(isinstance(r.get("score"), str) for r in rows):
            columns = columns + ["Score"]
        columns = columns + ["Reason"]
        table_rows = []
        for row in rows:
            vals = row.get("values") or {}
            tr = [row.get("symbol", "")] + [str(vals.get(pid, "") or "not sourced") for pid in params]
            if any(isinstance(r.get("score"), str) for r in rows):
                tr = tr + [str(row.get("score") or "")]
            tr = tr + [row.get("reason") or "(not recorded)"]
            table_rows.append(tr)
        paras = [
            "Parameter set: %s." % set_name,
            "Criteria used: %s." % (", ".join(param_labels) if param_labels else "none recorded"),
            "Shortlisted: %d holding(s)." % len(rows),
        ]
        if thresholds:
            paras.append("Thresholds declared: %s." % ", ".join(
                "%s >= %s" % (k, v) for k, v in thresholds.items() if v not in (None, "")))
        paras.append("Each value below is what the screener showed or what the student typed; a missing value "
                     "is a named gap, not an estimate.")
        sections.append({"heading": "Selection criteria and shortlist", "paragraphs": paras,
                        "table": {"columns": columns, "rows": table_rows}})
    else:
        sections.append({"heading": "Selection criteria and shortlist", "paragraphs": [
            "No selection record was stored for this book. This is a named gap, not an omission.",
        ]})
    commentary = portfolio.get("commentary") or {}
    if str(commentary.get("status")) == "confirmed" and str(commentary.get("text") or "").strip():
        sections.append({"heading": "Commentary", "paragraphs": [
            str(commentary.get("text") or "").strip(),
            "This commentary is the student's own reading of the figures above. It adds no "
            "figure, source or recommendation.",
        ]})
    else:
        sections.append({"heading": "Commentary", "paragraphs": [
            "No commentary was confirmed for this book. This is a named gap, not an omission.",
        ]})
    if performance:
        sections.append(_performance_section(performance, currency))
    elif str(portfolio.get("mode")) == "fund":
        sections.append({"heading": "Performance", "paragraphs": [
            "Not computed: a return needs at least two dated snapshots and their journal entries.",
            "This is a named gap, not a zero return."]})
    if journal:
        sections.append({"heading": "Journal of decisions", "table": {
            "columns": ["Date", "Flow", "Benchmark", "Note"],
            "rows": [[entry.get("date", ""), _fmt(entry.get("flow", "0")),
                      entry.get("benchmark", "") or "", entry.get("note", "") or ""]
                     for entry in sorted(journal, key=lambda row: str(row.get("date", "")))],
        }})
    sections.extend([
        {"heading": "Data provenance", "table": {
            "columns": ["Symbol", "Price", "Source", "As of"],
            "rows": [[symbol, _fmt(point.get("price")), point.get("source", ""), point.get("as_of", "")]
                     for symbol, point in sorted(prices.items())],
        }},
    ])
    evidence = snapshot.get("evidence") or []
    if evidence:
        sections.append({"heading": "Price evidence", "table": {
            "columns": ["File", "SHA-256", "Captured at", "Size"],
            "rows": [[str(item.get("filename", "")),
                      str(item.get("sha256", ""))[:12] + "...",
                      str(item.get("captured_at", "")),
                      _fmt(item.get("size_bytes", 0))]
                     for item in evidence],
        }})
        sections.append({"heading": "Price evidence note", "paragraphs": [
            "Evidence files are stored with the portfolio. Each file's SHA-256 was recorded "
            "at snapshot time; a changed file no longer matches and is detectable.",
        ]})
    else:
        sections.append({"heading": "Price evidence", "paragraphs": [
            "No evidence was attached to this snapshot. This is a named gap, not an omission.",
        ]})
    sections.extend([
        {"heading": "Checks", "bullets": _check_lines(snapshot, performance)},
        {"heading": "Assumptions and limits", "bullets": _limit_lines(performance)},
    ])
    images = []
    if portfolio_id:
        try:
            from . import portfolios as _portfolios
            base = _portfolios.portfolios_dir() / str(portfolio_id)
            for item in (snapshot.get("evidence") or []):
                if not str(item.get("mime", "")).startswith("image/"):
                    continue
                rel = item.get("relative_path") or ("evidence/%s/%s" % (snapshot.get("date"), item.get("filename")))
                path = base / str(rel)
                try:
                    images.append((str(item.get("filename")), path.read_bytes()))
                except OSError:
                    pass
        except Exception:
            images = []
    return docx.render_note(title, subtitle, sections, images=images), filename(portfolio, snapshot)


def _objective_lines(portfolio):
    objective = str(portfolio.get("objective", "") or "").strip()
    roster = str(portfolio.get("roster", "") or "").strip()
    benchmark = str(portfolio.get("benchmark", "") or "").strip()
    lines = [objective or "No objective was recorded. This is a named gap, not an inferred one."]
    lines.append("Mode: %s · base currency: %s · cadence: %s" % (
        str(portfolio.get("mode", "paper")).title(), portfolio.get("base_currency", ""),
        portfolio.get("cadence", "")))
    if benchmark:
        lines.append("Benchmark as declared: %s" % benchmark)
    else:
        lines.append("No benchmark was declared.")
    if roster:
        lines.append("Team: %s" % roster)
    return lines


def _performance_section(performance, currency):
    outputs = performance.get("outputs") or {}
    periods = performance.get("periods") or []
    paragraphs = [
        "Time-weighted return: %s across %s periods." % (_pct(outputs.get("twr")), _fmt(outputs.get("n_periods"))),
        "Starting NAV: %s %s · final NAV: %s %s · external flow: %s %s." % (
            currency, _fmt(outputs.get("start_nav")), currency, _fmt(outputs.get("final_nav")),
            currency, _fmt(outputs.get("total_flow"))),
        "Best period: %s · worst period: %s." % (_pct(outputs.get("best_period")), _pct(outputs.get("worst_period"))),
    ]
    if performance.get("benchmark_used"):
        paragraphs.append("Benchmark return: %s · active return: %s." % (
            _pct(outputs.get("benchmark_return")), _pct(outputs.get("active_return"))))
    elif not performance.get("benchmark_complete", True):
        paragraphs.append("No benchmark return is reported: a benchmark level was missing on at least one date. "
                          "The gap is named, not filled.")
    section = {
        "heading": "Performance",
        "paragraphs": paragraphs,
        "table": {
            "columns": ["Period", "Start NAV", "End NAV", "Flow", "Period return", "Benchmark"],
            "rows": [[row.get("label", ""), _fmt(row.get("start_nav")), _fmt(row.get("end_nav")),
                      _fmt(row.get("flow")), _pct(row.get("period_return")),
                      _pct(row.get("benchmark_return")) if row.get("benchmark_return") else "not declared"]
                     for row in periods],
        },
    }
    if performance.get("conventions"):
        section["paragraphs"].append(performance["conventions"])
    return section


_CHECK_LABELS = {
    "second_implementation_agrees": "a second route gives the same result",
    "nav_equals_invested_plus_cash": "NAV equals the holdings' value plus cash",
    "holding_weights_and_cash_sum_to_one": "the holding weights plus cash sum to one",
    "doubling_every_price_doubles_invested_value": "doubling every price doubles the invested value",
    "adding_one_unit_of_cash_raises_nav_by_one": "one more unit of cash raises NAV by one",
    "concentration_is_bounded": "the concentration measures stay between zero and one",
    "twr_equals_the_product_of_end_over_base": "the return chains every period",
    "a_period_with_no_flow_returns_the_nav_ratio": "a period with no flow equals the NAV ratio",
    "geometric_mean_lies_between_best_and_worst": "the average period sits between the best and the worst",
    "benchmark_chains_the_same_way": "the benchmark chains the same way",
    "final_nav_matches_the_last_period": "the final NAV is the last period's end",
}


def _check_lines(snapshot, performance):
    """A student reads what was verified, not the machine's check names.

    The stored snapshot keeps the machine-readable names for audit; a failure is
    always named, because a failed check blocks the result.
    """
    valuation = snapshot.get("checks") or []
    measured = (performance or {}).get("checks") or []
    rows = [("Valuation", _CHECK_LABELS.get(str(check.get("name", "")), "a declared check"), bool(check.get("ok")))
            for check in valuation]
    rows += [("Performance", _CHECK_LABELS.get(str(check.get("name", "")), "a declared check"), bool(check.get("ok")))
             for check in measured]
    if not rows:
        return ["No check result was recorded."]
    passed = sum(1 for _, _, ok in rows if ok)
    if passed == len(rows):
        return ["All %d checks passed (%d valuation, %d performance)." % (len(rows), len(valuation), len(measured)),
                "The checks confirm the arithmetic and the weights; they do not confirm the prices, which are yours to verify."]
    failed = ["%s: %s" % (scope, label) for scope, label, ok in rows if not ok]
    return ["%d of %d checks passed. A failed check blocks the result." % (passed, len(rows)),
            "Failed: " + "; ".join(failed) + "."]


def _limit_lines(performance):
    lines = [
        "Prices are the dated values recorded in this snapshot, in one base currency; no FX conversion, fees, tax or dividends are applied.",
        "Weights are value / NAV, so the holding weights plus cash equal one.",
        "A snapshot is a valuation, not a sale price, a forecast or a recommendation.",
    ]
    if performance:
        lines.append("The external flow is treated as occurring at the start of its period; the return chains the declared periods.")
        lines.append("A benchmark is the level the student declared; the active return is descriptive, not a promise.")
        lines.append("Past performance is a record, not a forecast.")
    lines.append("This report was generated from the stored snapshot and the frozen method result; the figures are not recomputed here.")
    return lines


def _pct(value):
    try:
        from decimal import Decimal
        return "%.2f%%" % (Decimal(str(value)) * 100)
    except Exception:
        return str(value if value is not None else "")
