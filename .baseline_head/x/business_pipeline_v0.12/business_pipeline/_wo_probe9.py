"""Probe 9: dump the 8 target WORKSHEETS records + the 29 orphan-target catalogue records."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from bp.product import subjects

out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wo_probe9.txt"), "w", encoding="utf-8")
def p(*a): out.write(" ".join(str(x) for x in a) + "\n")

p("=== WORKSHEETS: the 8 WO-3 targets ===")
for wid in ["STR-15", "STR-16", "STR-17", "PM-05", "PM-09", "PM-06", "PM-15", "PM-16"]:
    p("\n--- %s ---" % wid)
    p(json.dumps(subjects.WORKSHEETS.get(wid), indent=2, default=str))

p("\n\n=== WORKSHEETS: a reference marketing entry (MKT-03 AIDA) ===")
p(json.dumps(subjects.WORKSHEETS.get("MKT-03"), indent=2, default=str))

p("\n\n=== CATALOGUE records for the 29 matched orphans ===")
for cid in ["CHG-02", "CHG-03", "CHG-04", "CHG-05", "CHG-06", "CHG-07", "CHG-08", "CHG-09", "CHG-10", "CHG-13",
            "STR-02", "STR-05", "STR-10", "STR-11",
            "MKT-01", "MKT-03", "MKT-05", "MKT-08", "MKT-09", "MKT-10", "MKT-11", "MKT-12", "MKT-13",
            "MKT-14", "MKT-16", "MKT-17", "MKT-19", "MKT-20", "MKT-21"]:
    r = subjects.CATALOGUE[cid]
    p("\n--- %s --- %s" % (cid, r["name"]))
    p(json.dumps(r, indent=2, default=str))

out.close()
print("ok")
