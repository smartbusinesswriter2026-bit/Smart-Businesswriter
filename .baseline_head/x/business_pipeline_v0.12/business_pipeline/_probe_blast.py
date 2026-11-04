"""One-off diagnostic: the derived-field blast radius of restoring the registry
slice to its deterministic import of the authority markdown."""
import io
import json
import subprocess
import sys

sys.path.insert(0, "src")
from bp import registry as R  # noqa: E402

HEAD = "HEAD:business_pipeline_v0.12/business_pipeline/src/bp/data/registry_v0_2.json"
raw = subprocess.run(["git", "show", HEAD], capture_output=True, cwd=r"D:\SMART BUSINESSWRITER").stdout
head_json = json.loads(raw.decode("utf-8"))
io.open("_registry_head.json", "w", encoding="utf-8").write(json.dumps(head_json, ensure_ascii=False, indent=1))

old = R.load("_registry_head.json")["records"]
new = R.load()["records"]
old_by = {r["id"]: r for r in old}
new_by = {r["id"]: r for r in new}

print("records old/new:", len(old), len(new))
print("ids added:", sorted(set(new_by) - set(old_by)))
print("ids removed:", sorted(set(old_by) - set(new_by)))

changed = {}
for rid in sorted(set(old_by) & set(new_by)):
    a, b = old_by[rid], new_by[rid]
    for key in sorted(set(a) | set(b)):
        if a.get(key) != b.get(key):
            changed.setdefault(key, []).append(rid)

print("\nchanged field -> record ids:")
for key in sorted(changed):
    ids = changed[key]
    print("  %-22s %2d  %s" % (key, len(ids), ", ".join(ids[:14]) + (" ..." if len(ids) > 14 else "")))

print("\nrecords whose form changed:")
for rid in sorted(set(old_by) & set(new_by)):
    if old_by[rid].get("form") != new_by[rid].get("form"):
        print("  %-12s %s -> %s  (template %s)" % (
            rid, old_by[rid].get("form"), new_by[rid].get("form"), new_by[rid].get("template")))
