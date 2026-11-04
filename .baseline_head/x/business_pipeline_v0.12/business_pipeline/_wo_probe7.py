"""Probe 7: hunt catalogue homes for change_organization, strategic_positioning, strategy_4."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from bp import registry

out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wo_probe7.txt"), "w", encoding="utf-8")
def p(*a): out.write(" ".join(str(x) for x in a) + "\n")

reg = registry.load()
recs = reg["records"]

p("=== all CHG-* and STR-* and PM-* records ===")
for r in recs:
    if r["id"].startswith(("CHG-", "STR-", "PM-")):
        p("  %-8s type=%-3s form=%-10s tpl=%-28s %s" % (r["id"], r["type"], r["form"], r.get("template"), r["name"]))
        p("           summary: %s" % r["summary"])
        p("           aliases: %s   also_listed_as: %s" % (r.get("aliases"), r.get("also_listed_as")))

def hunt(words, label):
    p("\n=== hunt: %s ===" % label)
    for r in recs:
        blob = " ".join([r["name"], r["summary"], r["structures"], " ".join(r.get("aliases") or []),
                         " ".join(r.get("also_listed_as") or [])]).lower()
        hits = [w for w in words if w in blob]
        if len(hits) >= len(words) - 1:
            p("  %-8s type=%-3s form=%-10s %s" % (r["id"], r["type"], r["form"], r["name"]))
            p("           hit: %s | summary: %s" % (hits, r["summary"]))

hunt(["perspective", "position", "plan", "pattern"], "Strategy 4 (perspective/position/plan/pattern)")
hunt(["readiness", "resistance"], "change readiness/resistance")
hunt(["differentiation", "value proposition", "target segment"], "strategic positioning")
hunt(["strategy 4"], "literal 'strategy 4'")
hunt(["johnson", "scholes"], "Johnson & Scholes")

p("\n=== records whose name mentions organization/organisation ===")
for r in recs:
    if "organis" in r["name"].lower() or "organiz" in r["name"].lower():
        p("  %-8s %s" % (r["id"], r["name"]))

p("\n=== registry record key list (what keys exist per record) ===")
p(sorted(recs[0].keys()))

out.close()
print("ok")
