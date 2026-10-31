"""Export the 32 orphan profiles + the 8 WO-3 canvas shapes as build input."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from bp.product import framework_profiles as fp
from bp import templates as T

ORPHAN_MAP = {
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
 "template_change_organization": "CHG-15", "template_strategic_positioning": "STR-19",
 "template_strategy_4": "STR-20",
}

WO3 = ["template_business_model_canvas", "template_lean_canvas", "template_value_proposition_canvas",
       "template_project_charter", "template_wbs", "template_risk_register",
       "template_stakeholder_plan", "template_lessons_learned"]

here = os.path.dirname(os.path.abspath(__file__))
data = {"orphans": {}, "wo3": {}}
for tpl, cid in ORPHAN_MAP.items():
    pr = fp.PROFILES[tpl]
    data["orphans"][tpl] = {
        "catalogue_id": cid,
        "label": pr["label"],
        "title_prefix": pr.get("title_prefix"),
        "subject": pr.get("subject"),
        "ratings": pr.get("ratings"),
        "unit": pr.get("unit"),
        "blocks": [{"key": b["key"], "label": b["label"], "prompt": b["prompt"], "cues": b.get("cues"),
                    "fill": b.get("fill")} for b in pr["blocks"]],
    }
for tpl in WO3:
    if tpl in T.CANVAS_BLOCKS:
        data["wo3"][tpl] = {"kind": "canvas",
                            "blocks": [{"key": k, "label": v[0], "prompt": v[1]}
                                       for k, v in T.CANVAS_BLOCKS[tpl].items()],
                            "meta": T.CANVAS_META[tpl]}
    else:
        mm = T.MATRIX_META[tpl]
        data["wo3"][tpl] = {"kind": "matrix", "meta": mm,
                            "columns": T.MATRIX_COLUMNS[tpl] if hasattr(T, "MATRIX_COLUMNS") else None}

with open(os.path.join(here, "_wo_build_input.json"), "w", encoding="utf-8") as stream:
    json.dump(data, stream, indent=1, ensure_ascii=False)

print("orphans:", len(data["orphans"]), "wo3:", len(data["wo3"]))
for tpl in WO3:
    print("  ", tpl, data["wo3"][tpl]["kind"],
          [b["key"] for b in data["wo3"][tpl].get("blocks") or []])
