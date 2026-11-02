"""Dump the delivered report for a set of economics presets and scan it.

Looks for the presentation defects the accounting session found:
  * raw long Decimals (more than two decimal places printed as money)
  * scientific notation ("E+3")
  * an unresolved template token ("{{ref:", "@unit")
  * the word None / nan
  * a report that is empty

Usage:  python qa/probe_econ_reports.py
Writes: qa/baseline/econ_reports.txt
"""
import pathlib
import re
import sys

sys.path.insert(0, "src")

from bp import server                      # noqa: E402
from bp.orchestrator import Pipeline       # noqa: E402

APP = pathlib.Path(__file__).resolve().parent.parent
YES = lambda _reason: True                 # noqa: E731

WATCH = {
    "equilibrium", "elasticity", "taxincidence", "pricecontrol", "concentration",
    "costcurves", "profitmax", "marketpower", "cournot", "nash", "nationalincome",
    "growth", "inflation", "unemployment", "moneymultiplier", "fiscal",
    "budgetdebt", "okun", "gini", "poverty", "comparative", "tariff", "ppp",
    "irp", "bop", "hdi", "expectedutility", "prospect", "labour", "did",
    "forecast", "currency", "pricing", "demandcurve", "cba", "cea", "sroi",
    "npv", "dcf", "breakeven", "multibreakeven", "unitecon", "descriptive",
    "pearson", "ols", "welch", "anova", "chi_square", "power", "panel", "iv",
    "rdd", "probit", "externality", "publicgood", "socialwelfare",
    "taxprogressivity", "optimalpollution",
}

LONG_DECIMAL = re.compile(r"\d+\.\d{4,}")
SCI = re.compile(r"\d+(?:\.\d+)?[eE][+-]?\d+")
TOKENS = ("{{ref:", "@unit", "None", "nan", "NaN", "Infinity")


def main():
    lines = []
    problems = []
    for preset_id in sorted(WATCH):
        preset = server.PRESETS.get(preset_id)
        if preset is None:
            lines.append("%-16s NO PRESET" % preset_id)
            continue
        request = dict(preset)
        request.setdefault("objective", "economics QA %s" % preset_id)
        request.setdefault("period", "annual")
        delivery = Pipeline().run(request, YES)
        text = delivery.report or ""
        found = []
        if delivery.status != "delivered":
            found.append("status=%s (%s)" % (delivery.status, delivery.blocked_reason))
        if not text.strip():
            found.append("empty report")
        for token in TOKENS:
            if token in text:
                found.append("token %r" % token)
        for match in LONG_DECIMAL.findall(text)[:4]:
            found.append("long decimal %r" % match)
        for match in SCI.findall(text)[:4]:
            found.append("scientific %r" % match)
        lines.append("%-16s %-9s %4d chars %s"
                     % (preset_id, delivery.status, len(text),
                        "; ".join(found) if found else ""))
        if found:
            problems.append((preset_id, found, text))

    lines.append("")
    lines.append("PRESETS WITH PROBLEMS: %d" % len(problems))
    for preset_id, found, text in problems:
        lines.append("")
        lines.append("=== %s :: %s" % (preset_id, "; ".join(found)))
        lines.append(text[:1400])

    out = "\n".join(lines)
    (APP / "qa" / "baseline" / "econ_reports.txt").write_text(out, encoding="utf-8")
    print(out[:2500])


if __name__ == "__main__":
    main()
