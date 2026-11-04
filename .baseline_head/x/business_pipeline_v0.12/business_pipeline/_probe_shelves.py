"""One-off diagnostic: for every subject, which catalogue rows claim a worksheet
and whether the subject actually lists them."""
import sys

sys.path.insert(0, "src")
from bp import registry as R  # noqa: E402
from bp.product import subjects as S  # noqa: E402

for definition in S.SUBJECT_DEFS:
    sid = definition["id"]
    listed = set(definition["worksheets"])
    rows = definition.get("catalogue_ids") or []
    claimed = []
    for cid in rows:
        row = S.CATALOGUE.get(cid)
        if row and row.get("template"):
            claimed.append(cid)
    missing = [cid for cid in claimed if cid not in listed]
    extra = [cid for cid in listed if cid not in claimed]
    print("%-12s listed=%2d  claimed=%2d  MISSING=%s  EXTRA=%s"
          % (sid, len(listed), len(claimed), missing, extra))

print("\nregistry records with a template, grouped by discipline:")
by_disc = {}
for record in R.load()["records"]:
    if record.get("template"):
        for disc in record.get("disciplines") or []:
            by_disc.setdefault(disc, []).append(record["id"])
for disc in sorted(by_disc):
    print("  %-45s %2d  %s" % (disc, len(by_disc[disc]), ", ".join(sorted(by_disc[disc]))))
