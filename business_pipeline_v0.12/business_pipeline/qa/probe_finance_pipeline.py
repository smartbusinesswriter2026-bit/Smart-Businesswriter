"""Drive every finance tool through the real pipeline and record what it delivers.

Read-only probe: for each tool on the finance shelf it takes the tool's own
preset request, runs `bp.orchestrator.Pipeline().run(...)` to completion and
prints the delivery status, the tier, the appendix checks and whether the
report is complete (no unresolved `{{ref:` token).  Nothing is written except
the file named on the command line.

Usage:  PYTHONPATH=src python qa/probe_finance_pipeline.py [out.json]
"""
import json
import sys
import traceback

sys.path.insert(0, "src")

from bp import server  # noqa: E402
from bp.orchestrator import Delivery, Pipeline  # noqa: E402
from bp.product import subjects  # noqa: E402


def request_for(tool):
    preset = tool.get("preset")
    if preset and preset in server.PRESETS:
        base = dict(server.PRESETS[preset])
        base.setdefault("objective", tool.get("what") or tool.get("label"))
        return base, preset
    return None, None


def main(argv):
    detail = subjects.detail("finance")
    rows = []
    for tool in detail.get("tools") or []:
        request, preset = request_for(tool)
        row = {"tool": tool["key"], "method": tool["method"], "preset": preset}
        if request is None:
            row["result"] = {"note": "tool has no preset request"}
            rows.append(row)
            continue
        try:
            delivery = Pipeline().run(request, confirm_spec=lambda spec: True)
        except Exception as exc:  # noqa: BLE001
            row["result"] = {"raised": "%s: %s" % (type(exc).__name__, exc)}
            rows.append(row)
            continue
        if isinstance(delivery, Delivery):
            appendix = delivery.appendix or {}
            checks = appendix.get("checks")
            row["result"] = {
                "status": delivery.status, "tier": delivery.tier,
                "blocked_reason": delivery.blocked_reason,
                "report_chars": len(delivery.report or ""),
                "unresolved_refs": (delivery.report or "").count("{{ref:"),
                "appendix_keys": sorted(appendix.keys()),
                "checks": checks,
                "checks_all_true": (all(bool(v) for v in checks.values())
                                    if isinstance(checks, dict) else None),
            }
        else:
            row["result"] = {"status": "paused", "detail": str(delivery.__class__.__name__)}
        rows.append(row)
    text = json.dumps({"rows": rows}, indent=1, default=str)
    if len(argv) > 1:
        open(argv[1], "w", encoding="utf-8").write(text)
        print("wrote %s" % argv[1])
    else:
        print(text)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        raise SystemExit(1)
