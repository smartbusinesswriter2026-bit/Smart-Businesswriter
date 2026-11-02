"""Per-tool sweep for the economics shelf: deliver, checks, units, determinism.

For all 59 economics tools, driving the *preset* (the documented launch path):
  * the preset launches its own method
  * the preset's declared inputs validate and the pipeline delivers
  * every one of the method's own checks passes
  * the report and appendix are produced with no unresolved token
  * the output typing is not obviously mislabelled (a share typed as currency, ...)
  * the same inputs twice give a byte-identical result

Usage:  python qa/probe_econ_tools.py
Writes: qa/baseline/econ_tools_report.txt and .json
"""
import json
import pathlib
import sys

sys.path.insert(0, "src")

from bp import server                      # noqa: E402
from bp.methods import LIBRARY             # noqa: E402
from bp.orchestrator import Pipeline       # noqa: E402
from bp.product import subjects            # noqa: E402

APP = pathlib.Path(__file__).resolve().parent.parent
YES = lambda _reason: True                 # noqa: E731

KNOWN_UNITS = {"currency", "units", "ratio", "percent", "count", "index",
               "years", "periods", "rate", "score", "text", "probability"}
SHARE_WORDS = ("share", "rate", "ratio", "elasticity", "index", "percent",
               "probability", "growth")
COUNT_WORDS = ("count", "n_", "firms", "n")


def suspicious(key, unit):
    lowered = key.lower()
    if unit not in KNOWN_UNITS:
        return "unit %r is not a known unit" % (unit,)
    if unit == "currency" and any(word in lowered for word in SHARE_WORDS):
        return "a %s is typed as currency" % key
    if unit == "currency" and (lowered.startswith("n_") or lowered.endswith("_count")
                               or lowered in ("count", "n_firms")):
        return "a count is typed as currency"
    return None


def main():
    tools = subjects.detail("economics")["tools"]
    report = {"tools": [], "findings": []}

    def flag(kind, text, tool=None):
        report["findings"].append({"kind": kind, "detail": text, "tool": tool})

    for tool in tools:
        row = {"tool": tool["key"], "method": tool["method"], "preset": tool["preset"]}
        preset = server.PRESETS.get(tool["preset"])
        if preset is None:
            flag("PRESET_MISSING", "preset %r absent" % tool["preset"], tool["key"])
            row["status"] = "NO_PRESET"
            report["tools"].append(row)
            continue
        if preset.get("method") != tool["method"]:
            flag("PRESET_METHOD_MISMATCH",
                 "%r launches %r not %r" % (tool["preset"], preset.get("method"),
                                            tool["method"]), tool["key"])
        request = dict(preset)
        request.setdefault("objective", "economics QA %s" % tool["key"])
        request.setdefault("period", "annual")
        delivery = Pipeline().run(request, YES)
        row["status"] = delivery.status
        if delivery.status != "delivered":
            flag("PRESET_BLOCKED", "preset %r blocked: %s"
                 % (tool["preset"], delivery.blocked_reason), tool["key"])
            report["tools"].append(row)
            continue
        row["report_chars"] = len(delivery.report or "")
        checks = delivery.appendix.get("tests") or []
        if isinstance(checks, dict):
            row["appendix_tests"] = {name: bool(ok) for name, ok in checks.items()}
        else:
            row["appendix_tests"] = {str(item): item is not False for item in checks}
        failing = [name for name, ok in row["appendix_tests"].items() if not ok]
        if failing:
            flag("CHECK_FAILED", "checks failing: %s" % ",".join(failing), tool["key"])
        if "{{ref:" in (delivery.report or ""):
            flag("UNRESOLVED_TOKEN", "report carries an unresolved {{ref: token", tool["key"])

        method = LIBRARY[tool["method"]]
        first = method.impl(preset["inputs"])
        second = method.impl(preset["inputs"])
        row["deterministic"] = first == second
        if not row["deterministic"]:
            flag("NONDETERMINISTIC", "two runs differ", tool["key"])

        if not isinstance(first, dict):
            flag("OUTPUT_NOT_A_ROW", "impl returned %s, not a row"
                 % type(first).__name__, tool["key"])
            first = {"value": first}
            row["outputs"] = {k: str(v) for k, v in first.items()}
            report["tools"].append(row)
            continue

        units = {}
        for key, value in first.items():
            try:
                unit, precision = method.typing(key)
            except Exception as error:                    # noqa: BLE001
                flag("TYPING_RAISED", "%s: %s" % (key, error), tool["key"])
                continue
            units[key] = "%s/%s" % (unit, precision)
            problem = suspicious(key, unit)
            if problem:
                flag("UNIT_MISLABEL", problem, tool["key"])
        row["units"] = units
        row["outputs"] = {k: str(v) for k, v in first.items()}
        report["tools"].append(row)

    (APP / "qa" / "baseline" / "econ_tools_report.json").write_text(
        json.dumps(report, indent=1, default=str), encoding="utf-8")

    lines = []
    kinds = {}
    for finding in report["findings"]:
        kinds[finding["kind"]] = kinds.get(finding["kind"], 0) + 1
    delivered = sum(1 for row in report["tools"] if row.get("status") == "delivered")
    lines.append("tools: %d, delivered via preset: %d" % (len(tools), delivered))
    lines.append("findings: %d" % len(report["findings"]))
    for kind in sorted(kinds):
        lines.append("  %-24s %d" % (kind, kinds[kind]))
    lines.append("")
    for finding in report["findings"]:
        lines.append("%-24s %-14s %s" % (finding["kind"], finding["tool"] or "",
                                         finding["detail"]))
    text = "\n".join(lines)
    (APP / "qa" / "baseline" / "econ_tools_report.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
