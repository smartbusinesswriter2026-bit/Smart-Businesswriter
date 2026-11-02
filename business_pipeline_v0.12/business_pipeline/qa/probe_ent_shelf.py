"""Per-tool sweep for the entrepreneurship shelf: preset, delivery, checks, typing.

For all 46 entrepreneurship tools, driving the *preset* (the documented launch path):
  * the tile names a frozen method and a preset that launches that same method
  * the preset's declared inputs validate and the pipeline delivers
  * every one of the method's own checks passes
  * the report carries no unresolved template token
  * the same inputs twice give a byte-identical result
  * the output typing is not obviously mislabelled (a share or a count typed as money)

Usage:  python qa/probe_ent_shelf.py
Writes: qa/baseline/ent_shelf.txt, qa/baseline/ent_shelf.json,
        qa/baseline/ent_catalogue.json
"""
import json
import pathlib
import sys

sys.path.insert(0, "src")

from bp import server, templates          # noqa: E402
from bp.methods import LIBRARY             # noqa: E402
from bp.orchestrator import Pipeline       # noqa: E402
from bp.product import subjects            # noqa: E402

APP = pathlib.Path(__file__).resolve().parent.parent
OUT = APP / "qa" / "baseline"
YES = lambda _reason: True                 # noqa: E731

#: Units the core legitimately emits. `@unit` is a per-unit amount in the request's own
#: currency and is resolved by the orchestrator, so it is not a mislabelling.
KNOWN_UNITS = {"currency", "units", "ratio", "percent", "count", "index", "days",
               "years", "periods", "rate", "score", "text", "probability", "correlation",
               "coefficient", "@unit"}

#: Names that legitimately carry money even though a share word appears in them: a per-unit
#: margin or a cost per unit is money, and "operations" contains "ratio".
MONEY_NAMES = ("margin", "cost", "price", "value", "cash", "npv", "pv_", "revenue",
               "profit", "amount", "investment", "benefit", "expense", "loan", "tax",
               "equity", "asset", "liabilit", "share_of")
SHARE_TAILS = ("share", "rate", "ratio", "pct", "percent", "percentage", "elasticity",
               "probability", "index", "growth")


def suspicious(key, unit):
    """A metric whose unit contradicts its own name (the D-ECO-01 / B-190 defect class).

    Deliberately narrow: only a money unit on a metric whose *last* token is a share word,
    and never on a name that says it is money per unit.  A probe that cries wolf is worse
    than one that says less.
    """
    lowered = str(key).lower()
    if unit not in KNOWN_UNITS:
        return "unit %r is not a known unit" % (unit,)
    if unit != "currency":
        return None
    tail = [token for token in lowered.split("_") if token][-1:]
    if not tail or tail[0] not in SHARE_TAILS:
        return None
    if any(name in lowered for name in MONEY_NAMES):
        return None
    return "a %s is typed as currency" % key


def main():
    page = subjects.detail("entrepreneurship")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ent_catalogue.json").write_text(
        json.dumps(page, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    report = {"tools": [], "findings": [], "counts": {
        "tools": len(page["tools"]), "worksheets": len(page["worksheets"]),
        "records": len(page["records"]), "theories": len(page.get("theories") or []),
        "glossary": len(page["glossary"]), "catalogue": len(page["catalogue"])}}

    def flag(kind, text, tool=None):
        report["findings"].append({"kind": kind, "detail": text, "tool": tool})

    for tool in page["tools"]:
        row = {"tool": tool["key"], "method": tool["method"], "preset": tool["preset"]}
        method = LIBRARY.get(tool["method"]) or templates.TEMPLATES.get(tool["method"])
        if method is None:
            flag("METHOD_MISSING", "method %r is neither a frozen method nor a template"
                 % tool["method"], tool["key"])
            row["status"] = "NO_METHOD"
            report["tools"].append(row)
            continue
        preset = server.PRESETS.get(tool["preset"])
        if preset is None:
            flag("PRESET_MISSING", "preset %r is absent from server.PRESETS" % tool["preset"], tool["key"])
            row["status"] = "NO_PRESET"
            report["tools"].append(row)
            continue
        if preset["method"] != tool["method"]:
            flag("PRESET_MISMATCH", "preset launches %r, the tile names %r"
                 % (preset["method"], tool["method"]), tool["key"])
        request = {"objective": preset["objective"], "method": preset["method"],
                   "inputs": preset["inputs"], "currency": preset.get("currency"),
                   "period": preset.get("period")}
        first = Pipeline().run(request, YES)
        row["status"] = first.status
        row["checks"] = [{"name": name, "ok": ok} for name, ok, *_ in first.appendix.get("tests", [])]
        if first.status != "delivered":
            flag("BLOCKED", str(first.blocked_reason)[:200], tool["key"])
            report["tools"].append(row)
            continue
        row["failed_checks"] = [item["name"] for item in row["checks"] if not item["ok"]]
        if row["failed_checks"]:
            flag("CHECK_FAILED", ", ".join(row["failed_checks"]), tool["key"])
        if "{{ref:" in first.report:
            flag("TEMPLATE_TOKEN", "an unresolved token remains in the report", tool["key"])
        second = Pipeline().run(request, YES)
        row["deterministic"] = first.report == second.report
        if not row["deterministic"]:
            flag("DETERMINISM", "two runs of the same request differ", tool["key"])
        # The typing hook is per metric: `method.typing(metric) -> (unit, precision)`.
        typing = {}
        if callable(getattr(method, "typing", None)):
            try:
                outputs = method.impl(preset["inputs"])
            except Exception as error:                     # a method must not crash the sweep
                outputs = {}
                flag("IMPL_ERROR", str(error)[:160], tool["key"])
            for key in outputs:
                try:
                    value = method.typing(key)
                except Exception:
                    continue
                typing[key] = value[0] if isinstance(value, (list, tuple)) else value
        row["units"] = {}
        for key, unit in typing.items():
            row["units"][key] = unit
            problem = suspicious(key, unit)
            if problem:
                flag("UNITS", problem, tool["key"])
        report["tools"].append(row)

    lines = ["entrepreneurship shelf sweep  (python qa/probe_ent_shelf.py)", ""]
    lines.append("counts: %s" % json.dumps(report["counts"], sort_keys=True))
    delivered = len([row for row in report["tools"] if row.get("status") == "delivered"])
    lines.append("delivered through their own preset: %d of %d" % (delivered, len(report["tools"])))
    lines.append("")
    for row in report["tools"]:
        unit_text = ", ".join("%s:%s" % (key, unit)
                              for key, unit in sorted((row.get("units") or {}).items()))
        lines.append("%-16s %-28s %-10s %s%s" % (
            row["tool"], row["method"], row.get("status"),
            "checks ok" if row.get("checks") and not row.get("failed_checks") else "see findings",
            ("  [" + unit_text + "]") if unit_text else ""))
    lines.append("")
    if report["findings"]:
        lines.append("FINDINGS")
        for finding in report["findings"]:
            lines.append("  %-16s %-16s %s" % (finding["kind"], finding.get("tool") or "-",
                                               finding["detail"]))
    else:
        lines.append("FINDINGS: none")
    text = "\n".join(lines) + "\n"
    (OUT / "ent_shelf.txt").write_text(text, encoding="utf-8")
    (OUT / "ent_shelf.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
