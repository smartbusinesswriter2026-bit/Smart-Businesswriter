"""Check the new chart plan against the runs the previous session recorded."""
import io
import json
import os
import sys

REPO = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
sys.path.insert(0, os.path.join(REPO, "src"))

from bp.product import workspace as ws  # noqa: E402
from bp.product import charts  # noqa: E402

case = json.load(io.open(r"D:\SMART BUSINESSWRITER\.uitmp\cases\22a752403f9c.json", encoding="utf-8"))
for index, run in enumerate(case["runs"]):
    bundle = ws.run_bundle("x", run) if False else {
        "format": "bp-case/2",
        "delivery": {"report": run["delivery"]["report"], "appendix": run["delivery"]["appendix"]},
        "reperform": run["reperform"],
    }
    plan = ws.chart_plan(bundle)
    print("run %d (%s): %d specs" % (index, run["method"], len(plan)))
    for spec in plan:
        print("   ", spec.get("kind"), "|", spec.get("title"), "|", spec.get("source") or spec.get("series"))
    for spec in plan:
        if spec.get("kind") == "profile":
            svg = charts.render_svg(bundle, spec)
            print("    drawn svg bytes:", len(svg), "| has -100000:", "-100000" in svg, "| has 40000:", "40000" in svg)
