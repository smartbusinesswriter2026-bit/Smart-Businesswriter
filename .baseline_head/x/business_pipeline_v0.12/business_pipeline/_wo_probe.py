"""Throwaway probe: measure the WO-2 / WO-3 registration gaps."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from bp.product import subjects, framework_profiles as fp

profiles = fp.PROFILES
catalogue = subjects.CATALOGUE
worksheets = subjects.WORKSHEETS

print("profiles:", len(profiles))
print("catalogue:", len(catalogue))
print("worksheets:", len(worksheets))

# templates referenced by catalogue
cat_templates = {}
for cid, rec in catalogue.items():
    t = rec.get("template")
    if t:
        cat_templates.setdefault(t, []).append(cid)

ws_templates = {}
for wid, rec in worksheets.items():
    ws_templates.setdefault(rec.get("template"), []).append(wid)

print()
print("=== PROFILES with no catalogue entry referencing their template ===")
orphans = []
for t in sorted(profiles):
    if t not in cat_templates:
        orphans.append(t)
print(len(orphans))
for t in orphans:
    print("  ", t, "| label:", profiles[t]["label"])

print()
print("=== PROFILES with no worksheet ===")
no_ws = [t for t in sorted(profiles) if t not in ws_templates]
print(len(no_ws))
for t in no_ws:
    print("  ", t, "| label:", profiles[t]["label"], "| cat:", cat_templates.get(t))

print()
print("=== WORKSHEETS draftable=True pointing at a template with NO profile ===")
missing_profile = []
for wid, rec in sorted(worksheets.items()):
    if rec.get("draftable") and rec.get("template") not in profiles:
        missing_profile.append((wid, rec.get("template"), rec.get("label")))
print(len(missing_profile))
for row in missing_profile:
    print("  ", row)

print()
print("=== WORKSHEETS draftable=False (no draftable key) ===")
for wid, rec in sorted(worksheets.items()):
    if not rec.get("draftable"):
        t = rec.get("template")
        print("  ", wid, "|", t, "| profile?", t in profiles, "|", rec.get("label"))

print()
print("=== catalogue entries whose template is not a profile and not None ===")
for cid, rec in sorted(catalogue.items()):
    t = rec.get("template")
    if t and t not in profiles:
        print("  ", cid, t, rec.get("form"), rec.get("status_short"))

print()
print("=== catalogue entries with template None, count:", sum(1 for r in catalogue.values() if not r.get("template")))
for cid, rec in sorted(catalogue.items()):
    if not rec.get("template"):
        print("  ", cid, "|", rec.get("name"), "| type", rec.get("type"), "|", rec.get("status_short"))
