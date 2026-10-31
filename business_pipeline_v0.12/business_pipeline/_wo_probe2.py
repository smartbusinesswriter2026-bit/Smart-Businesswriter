"""Throwaway probe: dump the shape of the 8 target templates + record shapes."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from bp import templates as T
from bp.product import subjects, framework_profiles as fp

TARGET = ["template_business_model_canvas", "template_lean_canvas",
          "template_value_proposition_canvas", "template_project_charter",
          "template_wbs", "template_risk_register", "template_stakeholder_plan",
          "template_lessons_learned"]

print("=== CANVAS_BLOCKS for targets ===")
for k in TARGET:
    if k in T.CANVAS_BLOCKS:
        print("\n--", k, "->", T.CANVAS_META.get(k, {}).get("name"))
        for bk, (label, prompt) in T.CANVAS_BLOCKS[k].items():
            print("    %-28s | %s" % (bk, label))
            print("        %s" % prompt)
    else:
        print("\n--", k, "-> NOT A CANVAS")
        if k in T.MATRIX_META:
            print("    MATRIX_META:", json.dumps(T.MATRIX_META[k], indent=6, default=str))
        else:
            print("    not in MATRIX_META either")
        print("    TEMPLATES entry name:", T.TEMPLATES.get(k, {}).get("name"))

print()
print("=== MATRIX_META keys ===")
for k, v in T.MATRIX_META.items():
    print(" ", k, "| name:", v.get("name"), "| rows:", v.get("row_label"), "| cols:", v.get("column_label"),
          "| min/max rows:", v.get("min_rows"), v.get("max_rows"), "| min/max cols:", v.get("min_columns"), v.get("max_columns"),
          "| registry_ids:", v.get("registry_ids"))

print()
print("=== registry_ids of the 8 targets ===")
for k in TARGET:
    print(" ", k, "->", T.TEMPLATES.get(k, {}).get("registry_ids"), "|", T.TEMPLATES.get(k, {}).get("name"))

print()
print("=== a WORKSHEETS record (full) ===")
print(json.dumps(subjects.WORKSHEETS["MKT-01"], indent=2, default=str))

print()
print("=== a catalogue record for a worksheet (MKT-01) ===")
print(json.dumps(subjects.CATALOGUE["MKT-01"], indent=2, default=str))

print()
print("=== a catalogue record for a non-worksheet (CHG-02) ===")
print(json.dumps(subjects.CATALOGUE["CHG-02"], indent=2, default=str))

print()
print("=== all catalogue ids, name, type, form, template, status_short ===")
for cid, rec in subjects.CATALOGUE.items():
    print("  %-8s %-46s type=%-4s form=%-12s tpl=%-34s %s" % (
        cid, rec.get("name"), rec.get("type"), rec.get("form"), rec.get("template"), rec.get("status_short")))

print()
print("=== all worksheet ids ===")
for wid, rec in subjects.WORKSHEETS.items():
    print("  %-8s %-42s tpl=%-34s draftable=%s" % (wid, rec.get("label"), rec.get("template"), rec.get("draftable")))
