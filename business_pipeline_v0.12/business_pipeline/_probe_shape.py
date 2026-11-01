"""Read-only: subject list/discipline/claim shape; tiles; orphan check."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from bp.product import subjects  # noqa: E402

print("=== per subject: catalogue_ids mode, disciplines, tiles ===")
for s in subjects.SUBJECT_DEFS:
    mode = "AUTO" if s["catalogue_ids"] is None else "EXPLICIT(%d)" % len(s["catalogue_ids"])
    tiles = s.get("tiles")
    print("  %-18s %-12s tiles=%-4s disc=%s" % (
        s["id"], mode, "none" if not tiles else len(tiles), s["disciplines"]))

print()
print("=== who claims 'strategy' / 'change and organization' ? ===")
for tag in ("strategy", "change and organization", "risk and decision analysis"):
    ids = [r["id"] for r in subjects.CATALOGUE.values() if tag in (r.get("disciplines") or [])]
    owners = [s["id"] for s in subjects.SUBJECT_DEFS if tag in s["disciplines"]]
    print("  %-30s records=%-3d subject_declares=%s" % (tag, len(ids), owners))

print()
print("=== every registry record claimed by some subject? ===")
claimed = set()
for s in subjects.SUBJECT_DEFS:
    claimed |= set(subjects.detail(s["id"])["catalogue"] and
                   [r["id"] for r in subjects.detail(s["id"])["catalogue"]])
allrec = set(subjects.CATALOGUE.keys())
orphan = sorted(allrec - claimed)
print("  total records=%d claimed=%d orphaned=%d" % (len(allrec), len(claimed), len(orphan)))
print("  orphans:", orphan)

print()
print("=== management page: tiles? groups of records? ===")
m = subjects.detail("management")
print("  tiles:", m["tiles"])
recs = m["records"]
byd = {}
for r in recs:
    byd.setdefault(r["discipline_label"], []).append(r["id"])
for k, v in byd.items():
    print("   group %-34r %s" % (k, v))
print("  theories:", [(t["id"], t["name"][:40]) for t in m["theories"]])
