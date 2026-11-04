"""Throwaway probe 4: exact orphan list + the 8 target status. Writes to _wo_probe4.txt."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from bp.product import subjects, framework_profiles as fp

out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wo_probe4.txt"), "w", encoding="utf-8")
def p(*a):
    out.write(" ".join(str(x) for x in a) + "\n")

profiles = fp.PROFILES
cat = subjects.CATALOGUE
ws = subjects.WORKSHEETS

p("PROFILES count:", len(profiles))
p("CATALOGUE count:", len(cat))
p("WORKSHEETS count:", len(ws))

cat_by_tpl = {}
for cid, rec in cat.items():
    t = rec.get("template")
    if t:
        cat_by_tpl.setdefault(t, []).append(cid)

ws_by_tpl = {}
for wid, rec in ws.items():
    ws_by_tpl.setdefault(rec.get("template"), []).append(wid)

p("\n=== ORPHANS: profile exists, but NO catalogue entry has that template ===")
orphans = [t for t in sorted(profiles) if t not in cat_by_tpl]
p("count:", len(orphans))
for t in orphans:
    pr = profiles[t]
    p("  %-34s label=%-38s subject=%-12s key=%s" % (t, pr.get("label"), pr.get("subject"), pr.get("key")))
    p("        in WORKSHEETS? %s   in catalogue(template)? %s" % (t in ws_by_tpl, t in cat_by_tpl))

p("\n=== profiles that ARE registered (catalogue entry with template) ===")
reg = [t for t in sorted(profiles) if t in cat_by_tpl]
p("count:", len(reg))
for t in reg:
    p("  %-34s -> %s (worksheet ids: %s)" % (t, cat_by_tpl[t], ws_by_tpl.get(t, [])))

p("\n=== TEMPLATES in bp.templates with NO profile ===")
from bp import templates as T
tpls = sorted(T.TEMPLATES.keys())
noprofile = [k for k in tpls if k not in profiles]
p("templates total:", len(tpls), " without profile:", len(noprofile))
for k in noprofile:
    p("  %-40s name=%-58s registry=%s" % (k, T.TEMPLATES[k].get("name"), T.TEMPLATES[k].get("registry_ids")))

p("\n=== the 8 WO-3 targets ===")
for k in ["template_business_model_canvas", "template_lean_canvas", "template_value_proposition_canvas",
          "template_project_charter", "template_wbs", "template_risk_register",
          "template_stakeholder_plan", "template_lessons_learned"]:
    p("  %-36s in PROFILES=%-6s catalogue=%-8s worksheet=%s" % (k, k in profiles, cat_by_tpl.get(k), ws_by_tpl.get(k)))
    if k in ws_by_tpl:
        p("        WORKSHEETS record: %s" % json.dumps(ws[ws_by_tpl[k][0]], indent=10, default=str))

p("\n=== WORKSHEETS whose template has no profile ===")
for wid, rec in sorted(ws.items()):
    if rec.get("template") not in profiles:
        p("  %-8s tpl=%-40s label=%s" % (wid, rec.get("template"), rec.get("label")))

p("\n=== CATALOGUE worksheet-form entries whose template has no profile ===")
for cid, rec in sorted(cat.items()):
    if rec.get("form") == "worksheet" and rec.get("template") not in profiles:
        p("  %-8s tpl=%-40s name=%s" % (cid, rec.get("template"), rec.get("name")))

out.close()
print("written")
