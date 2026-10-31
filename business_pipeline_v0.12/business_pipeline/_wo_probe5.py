"""Probe 5: linked_methods for the Q-typed orphans; registry validation rules."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from bp import registry
from bp.product import subjects

out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wo_probe5.txt"), "w", encoding="utf-8")
def p(*a): out.write(" ".join(str(x) for x in a) + "\n")

reg = registry.load()
by = reg["by_id"]
for cid in ["MKT-08", "MKT-19", "MKT-20", "OPS-09", "MKT-01", "MKT-03", "MKT-05"]:
    r = by[cid]
    p("%-8s type=%-3s form=%-10s tpl=%-16s linked=%s" % (
        cid, r["type"], r["form"], r.get("template"),
        [(m["method_id"], m.get("coverage")) for m in r["linked_methods"]]))
    p("         name=%s" % r["name"])
    p("         status=%s" % r["implementation_status"])

p("\n--- are those method ids real TOOL_INFO keys? ---")
for key in ["rfm", "attribution", "campaign", "web", "funnel", "mediaplan", "cro", "abtest", "email", "social"]:
    p("  %-12s in TOOL_INFO: %s" % (key, key in subjects.TOOL_INFO))

p("\n--- registry.validate() errors on current data ---")
errs = registry.validate(reg)
p("errors:", len(errs))
for e in errs[:30]:
    p("   ", e)

p("\n--- the 'orphan' profile labels vs catalogue names, all Q orphans ---")
for cid in ["MKT-08", "MKT-19", "MKT-20"]:
    r = by[cid]
    p("  %-8s name=%-46s summary=%s" % (cid, r["name"], r["summary"]))

out.close()
print("ok")
