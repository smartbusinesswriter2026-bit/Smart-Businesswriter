"""One-off repair: undo one layer of cp1252 double encoding in the shipped
registry slice, then report exactly what the repaired slice still disagrees
with a fresh import of the authority markdown.

The authority markdown is clean UTF-8; the shipped slice carries the same
strings one cp1252 round-trip later ('â€“' for an en dash).  The importer is
deterministic, so the slice must equal its source.  Nothing here invents text:
only bytes that decode back to the source's characters are touched.
"""
import io
import json
import sys

sys.path.insert(0, "src")
from bp import catalogue_import as CI  # noqa: E402

CAT = "docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md"
SHIPPED = "src/bp/data/registry_v0_2.json"
MARK = "\u00e2\u20ac"


def repair(value):
    """Reverse one cp1252 mis-decode, where the bytes decode cleanly as UTF-8."""
    if isinstance(value, str):
        if MARK in value:
            try:
                back = value.encode("cp1252").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                return value
            return back
        return value
    if isinstance(value, list):
        return [repair(item) for item in value]
    if isinstance(value, dict):
        return {key: repair(item) for key, item in value.items()}
    return value


shipped = json.load(io.open(SHIPPED, encoding="utf-8"))
fresh = CI.import_catalogue(CAT)
fixed = repair(shipped)

changed = 0
for record in fixed["records"]:
    for key in list(record):
        if record[key] != shipped["records"][0].get(key) and False:
            continue
for before, after in zip(shipped["records"], fixed["records"]):
    for key in after:
        if before[key] != after[key]:
            changed += 1
            print("  %-12s %-16s %r -> %r" % (before["id"], key, before[key][:44], after[key][:44]))
print("strings repaired:", changed)

fresh_by_id = {r["id"]: r for r in fresh["records"]}
fixed_by_id = {r["id"]: r for r in fixed["records"]}
remaining = []
for rid in sorted(set(fresh_by_id) | set(fixed_by_id)):
    a, b = fixed_by_id.get(rid), fresh_by_id.get(rid)
    if a is None or b is None:
        remaining.append((rid, "record present on one side only"))
        continue
    for key in sorted(set(a) | set(b)):
        if a.get(key) != b.get(key):
            remaining.append((rid, key))
print("\nremaining differences vs a fresh import:", len(remaining))
for rid, key in remaining:
    print("   %-12s %s" % (rid, key))

if "--write" in sys.argv:
    with io.open(SHIPPED, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(fixed, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print("\nwritten:", SHIPPED)
