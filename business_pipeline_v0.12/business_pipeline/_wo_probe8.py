"""Probe 8: block keys of every profile (to confirm the 32 are real frameworks)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from bp.product import framework_profiles as fp

out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wo_probe8.txt"), "w", encoding="utf-8")
def p(*a): out.write(" ".join(str(x) for x in a) + "\n")

for tpl in sorted(fp.PROFILES):
    pr = fp.PROFILES[tpl]
    keys = [b["key"] for b in pr["blocks"]]
    p("%-36s %-40s subject=%-11s blocks(%d): %s" % (tpl, pr["label"], pr.get("subject"), len(keys), ", ".join(keys)))
    p("%-36s   outline.lead: %s" % ("", pr["outline"].get("lead", "")[:170]))

out.close()
print("ok")
