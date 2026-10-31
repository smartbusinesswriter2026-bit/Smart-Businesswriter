"""Probe 6: match the 32 orphan profiles to catalogue ids by name/alias/summary."""
import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from bp import registry

out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wo_probe6.txt"), "w", encoding="utf-8")
def p(*a): out.write(" ".join(str(x) for x in a) + "\n")

reg = registry.load()
recs = reg["records"]

ORPHANS = {
 "template_adkar": "ADKAR", "template_aida": "AIDA",
 "template_attribution": "Attribution and Campaign Measurement", "template_bcg": "BCG Growth-Share Matrix",
 "template_brand_equity": "Brand Equity", "template_burke_litwin": "Burke-Litwin",
 "template_change_organization": "Change and Organization", "template_cro": "Conversion Rate Optimisation",
 "template_digital_mix": "Digital Marketing Mix", "template_dmaic": "DMAIC",
 "template_email_crm": "Email CRM and Lifecycle", "template_funnel": "Funnel",
 "template_galbraith_star": "Galbraith Star", "template_ge_mckinsey": "GE-McKinsey Matrix",
 "template_generic_strategies": "Generic Strategies", "template_lewin": "Lewin",
 "template_logic_model": "Logic Model", "template_marketing_automation": "Marketing Automation",
 "template_mckinsey_7s": "McKinsey 7S", "template_mintzberg": "Mintzberg",
 "template_pdsa": "PDSA", "template_porters_diamond": "Porters Diamond", "template_rfm": "RFM",
 "template_seo_content": "SEO and Content", "template_social_media": "Social Media and Influencer",
 "template_stp": "STP", "template_stp_evidence": "STP Evidence Check",
 "template_strategic_positioning": "Strategic Positioning", "template_strategy_4": "Strategy 4",
 "template_tam": "Technology Acceptance Model", "template_theory_of_change": "Theory of Change",
 "template_utaut": "UTAUT",
}

def toks(s):
    return set(w for w in re.findall(r"[a-z0-9&+]+", s.lower()) if len(w) > 2)

for tpl, label in ORPHANS.items():
    want = toks(label)
    scored = []
    for r in recs:
        if r["type"] == "T":
            continue
        hay = toks(" ".join([r["name"]] + list(r.get("aliases") or []) + list(r.get("also_listed_as") or [])))
        overlap = want & hay
        if not overlap:
            continue
        scored.append((len(overlap) / max(1, len(want)), len(overlap), r["id"], r["name"], r["type"],
                       r["form"], sorted(overlap)))
    scored.sort(reverse=True)
    p("\n### %s  (%s)" % (tpl, label))
    for sc, n, cid, name, ty, fo, ov in scored[:4]:
        p("    %.2f  %-8s %-52s type=%-3s form=%-10s overlap=%s" % (sc, cid, name, ty, fo, ov))

out.close()
print("ok")
