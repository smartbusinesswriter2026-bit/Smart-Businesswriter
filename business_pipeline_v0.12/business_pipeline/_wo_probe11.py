"""Probe 11: the definitive orphan -> catalogue id mapping table."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from bp import registry
from bp.product import framework_profiles as fp

# profile template -> catalogue id
MAP = {
 "template_adkar": "CHG-02", "template_lewin": "CHG-03", "template_mckinsey_7s": "CHG-04",
 "template_burke_litwin": "CHG-05", "template_galbraith_star": "CHG-06",
 "template_theory_of_change": "CHG-07", "template_logic_model": "CHG-08", "template_pdsa": "CHG-09",
 "template_dmaic": "CHG-10", "template_mintzberg": "CHG-13",
 "template_generic_strategies": "STR-02", "template_porters_diamond": "STR-05",
 "template_bcg": "STR-10", "template_ge_mckinsey": "STR-11",
 "template_stp": "MKT-01", "template_aida": "MKT-03", "template_funnel": "MKT-05",
 "template_rfm": "MKT-08", "template_tam": "MKT-09", "template_utaut": "MKT-10",
 "template_brand_equity": "MKT-11", "template_stp_evidence": "MKT-12", "template_digital_mix": "MKT-13",
 "template_seo_content": "MKT-14", "template_email_crm": "MKT-16", "template_social_media": "MKT-17",
 "template_attribution": "MKT-19", "template_cro": "MKT-20", "template_marketing_automation": "MKT-21",
 # no catalogue home yet
 "template_change_organization": "CHG-15", "template_strategic_positioning": "STR-19",
 "template_strategy_4": "STR-20",
}

out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wo_map.txt"), "w", encoding="utf-8")
def p(*a): out.write(" ".join(str(x) for x in a) + "\n")

reg = registry.load()
by = reg["by_id"]

p("ORPHAN PROFILES: %d" % len(MAP))
for tpl in sorted(MAP):
    cid = MAP[tpl]
    pr = fp.PROFILES[tpl]
    r = by.get(cid)
    p("\n%-34s -> %s" % (tpl, cid))
    p("   profile label : %s" % pr.get("label"))
    p("   profile title : %s" % pr.get("title_prefix"))
    p("   profile subj  : %s   assumption=%s  ratings=%s  sites=%s" % (
        pr.get("subject"), pr.get("assumption"), pr.get("ratings"), pr.get("sites")))
    p("   profile unit  : %s" % json.dumps(pr.get("unit"), ensure_ascii=False))
    p("   profile gate  : %s" % json.dumps(pr.get("gate")))
    p("   blocks        : %s" % ", ".join("%s=%r" % (b["key"], b["label"]) for b in pr["blocks"]))
    if r:
        p("   catalogue name: %s  (type %s)" % (r["name"], r["type"]))
        p("   catalogue summ: %s" % r["summary"])
        p("   evidence_needs: %s" % r["evidence_needs"])
        p("   disciplines   : %s" % r["disciplines"])
        p("   linked_methods: %s" % [m["method_id"] for m in r["linked_methods"]])
    else:
        p("   catalogue     : *** NO RECORD ***")

out.close()
print("ok")
