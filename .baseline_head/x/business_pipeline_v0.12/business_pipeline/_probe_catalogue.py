"""One-off diagnostic: the exact CATALOGUE drift between the committed snapshot
and the regenerated one."""
import io
import subprocess
import sys

sys.path.insert(0, "src")
from bp.product import subjects as S  # noqa: E402

HEAD = "HEAD:business_pipeline_v0.12/business_pipeline/src/bp/product/subjects.py"
raw = subprocess.run(["git", "show", HEAD], capture_output=True, cwd=r"D:\SMART BUSINESSWRITER").stdout.decode("utf-8")
io.open("_subjects_head.py", "w", encoding="utf-8").write(raw)
sys.path.insert(0, ".")
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("subjects_head", "_subjects_head.py")
head = importlib.util.module_from_spec(spec)
spec.loader.exec_module(head)

old, new = head.CATALOGUE, S.CATALOGUE
print("catalogue rows old/new:", len(old), len(new))
print("ids added:", sorted(set(new) - set(old)))
print("ids removed:", sorted(set(old) - set(new)))

changed = {}
for cid in sorted(set(old) & set(new)):
    for key in sorted(set(old[cid]) | set(new[cid])):
        if old[cid].get(key) != new[cid].get(key):
            changed.setdefault(key, []).append(cid)
print("\nchanged field -> ids:")
for key in sorted(changed):
    ids = changed[key]
    print("  %-22s %2d  %s" % (key, len(ids), ", ".join(ids[:16]) + (" ..." if len(ids) > 16 else "")))

print("\nrecords whose form or template changed:")
for cid in sorted(set(old) & set(new)):
    if old[cid].get("form") != new[cid].get("form") or old[cid].get("template") != new[cid].get("template"):
        print("  %-8s %-10s -> %-10s  template %s -> %s" % (
            cid, old[cid].get("form"), new[cid].get("form"),
            old[cid].get("template"), new[cid].get("template")))

print("\nname changes:")
for cid in sorted(set(old) & set(new)):
    if old[cid].get("name") != new[cid].get("name"):
        print("  %-8s %r" % (cid, new[cid].get("name")))
