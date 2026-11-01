"""One-off: which catalogue rows still disagree with the registry."""
import sys

sys.path.insert(0, "src")
from bp import registry as R  # noqa: E402
from bp.product import subjects as S  # noqa: E402

records = {r["id"]: r for r in R.load()["records"]}
mismatch = []
for definition in S.SUBJECT_DEFS:
    for row in S.detail(definition["id"])["catalogue"]:
        record = records[row["id"]]
        if (row["implementation_status"] != record.get("implementation_status")
                or row["template"] != record.get("template")
                or row["name"] != record["name"]):
            mismatch.append((definition["id"], row["id"], row["template"], record.get("template")))

print("catalogue rows that still disagree with the registry: %d" % len(mismatch))
for subject, cid, row_template, record_template in mismatch:
    print("  %-14s %-8s catalogue=%-26s registry=%s" % (
        subject, cid, row_template, record_template))
