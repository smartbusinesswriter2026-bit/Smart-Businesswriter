"""One-off diagnostic: for every record the registry calls a worksheet, is the
engine actually able to run it end to end?"""
import sys

sys.path.insert(0, "src")
from bp import registry as R  # noqa: E402
from bp import templates as T  # noqa: E402
from bp.product import drafting, framework_profiles  # noqa: E402

PEOPLE_TEN = {"CHG-02", "CHG-03", "CHG-04", "CHG-05", "CHG-06", "CHG-07", "CHG-08",
              "CHG-09", "CHG-10", "CHG-13"}

print("%-8s %-30s %-8s %-8s %-8s %-8s %s" % (
    "id", "template", "canvas", "draft", "profile", "example", "profile.subject"))
ready, not_ready = [], []
for record in R.load()["records"]:
    template = record.get("template")
    if not template:
        continue
    has_canvas = template in T.CANVAS_BLOCKS
    has_draft = drafting.supported(template)
    has_profile = template in framework_profiles.PROFILES
    has_example = template in T.EXAMPLES
    subject = framework_profiles.get(template).get("subject") if has_profile else None
    flag = "READY" if (has_canvas and has_draft and has_profile and has_example) else "no "
    row = "%-8s %-30s %-8s %-8s %-8s %-8s %s" % (
        record["id"], template, has_canvas, has_draft, has_profile, has_example, subject)
    (ready if flag == "READY" else not_ready).append((record["id"], row, record["id"] in PEOPLE_TEN))

print("--- ready end to end (%d) ---" % len(ready))
for rid, row, is_ten in ready:
    print(("  [ten] " if is_ten else "       ") + row)

print("\n--- not ready end to end (%d) ---" % len(not_ready))
for rid, row, is_ten in not_ready:
    print(("  [ten] " if is_ten else "       ") + row)
