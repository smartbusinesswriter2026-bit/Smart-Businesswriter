"""Probe 10: dump SUBJECT_DEFS for management, marketing, project-management, operations, people."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from bp.product import subjects

out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wo_probe10.txt"), "w", encoding="utf-8")
def p(*a): out.write(" ".join(str(x) for x in a) + "\n")

for d in subjects.SUBJECT_DEFS:
    p("=== %s (%s) ===" % (d["id"], d["label"]))
    p("  disciplines   :", d.get("disciplines"))
    p("  worksheets    :", d.get("worksheets"))
    p("  catalogue_ids :", d.get("catalogue_ids"))
    p("")

p("=== current worksheet order per subject page ===")
for d in subjects.SUBJECT_DEFS:
    page = subjects.detail(d["id"])
    p("  %-20s worksheets: %s" % (d["id"], [w["catalogue_id"] for w in page["worksheets"]]))
    p("  %-20s records  : %s" % ("", [r["id"] for r in page["records"]]))

out.close()
print("ok")
