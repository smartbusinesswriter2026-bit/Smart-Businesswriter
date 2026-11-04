"""One-off diagnostic: the exact field-level drift between the shipped registry
slice and a fresh import of the authority markdown."""
import io
import json
import sys

sys.path.insert(0, "src")
from bp import catalogue_import as CI  # noqa: E402

CAT = "docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md"
MOJI = "\u00e2\u20ac"


def repair(value):
    if isinstance(value, str):
        if MOJI in value:
            try:
                return value.encode("latin-1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                return value
        return value
    if isinstance(value, list):
        return [repair(item) for item in value]
    if isinstance(value, dict):
        return {key: repair(item) for key, item in value.items()}
    return value


shipped = json.load(io.open("src/bp/data/registry_v0_2.json", encoding="utf-8"))
fresh = CI.import_catalogue(CAT)
fixed = repair(shipped)

sh = {r["id"]: r for r in fixed["records"]}
fr = {r["id"]: r for r in fresh["records"]}
print("records shipped/repaired:", len(sh), " fresh:", len(fr))
print("ids only in repaired shipped:", sorted(set(sh) - set(fr)))
print("ids only in fresh:", sorted(set(fr) - set(sh)))

print("\nfield differences (repaired shipped vs fresh):")
diffs = 0
for rid in sorted(set(sh) & set(fr)):
    a, b = sh[rid], fr[rid]
    for key in sorted(set(a) | set(b)):
        if a.get(key) != b.get(key):
            diffs += 1
            if diffs <= 25:
                print("  %s.%s\n     shipped=%r\n     fresh  =%r" % (rid, key, a.get(key), b.get(key)))
print("total field differences:", diffs)

print("\ntop-level keys shipped:", sorted(shipped))
print("top-level keys fresh  :", sorted(fresh))
for key in sorted(set(shipped) | set(fresh)):
    if key == "records":
        continue
    if shipped.get(key) != fresh.get(key):
        print("  top-level %s differs:\n     shipped=%r\n     fresh  =%r" % (key, shipped.get(key), fresh.get(key)))

print("\nnewest F records shipped (by id order):")
import collections
c = collections.Counter(r["type"] for r in fixed["records"])
print("  type counts:", dict(c))
