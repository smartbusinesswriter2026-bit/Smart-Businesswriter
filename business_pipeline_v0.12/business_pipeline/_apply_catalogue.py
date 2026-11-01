"""Apply the generator's catalogue rows for the ten change-and-organisation
worksheets to the committed catalogue slice, and leave every other row as it was.

The committed slice was generated before `registry.TEMPLATE_LINKS` gained the
ten change-and-organisation worksheet links, so it still says "no worksheet yet"
for records the engine can already run.  Running the generator would fix those
ten and also rewrite nineteen marketing and strategy rows whose templates have
no drafting schema yet: those shelves are not built, so the generator's output
would claim a worksheet the shelf cannot offer.  This keeps the change to the
shelf that is being built.
"""
import copy
import importlib.util
import io
import pprint
import subprocess

ROOT = "D:\\SMART BUSINESSWRITER\\business_pipeline_v0.12\\business_pipeline"
HEAD = "HEAD:business_pipeline_v0.12/business_pipeline/src/bp/product/subjects.py"

#: The ten change-and-organisation frameworks this increment puts on the People shelf.
TEN = ["CHG-02", "CHG-03", "CHG-04", "CHG-05", "CHG-06", "CHG-07", "CHG-08",
       "CHG-09", "CHG-10", "CHG-13"]

raw = subprocess.run(["git", "show", HEAD], capture_output=True, cwd=r"D:\SMART BUSINESSWRITER").stdout.decode("utf-8")
io.open("_subjects_head.py", "w", encoding="utf-8").write(raw)
spec = importlib.util.spec_from_file_location("subjects_head", "_subjects_head.py")
head = importlib.util.module_from_spec(spec)
spec.loader.exec_module(head)

import sys
sys.path.insert(0, "src")
from bp.product import subjects as now  # noqa: E402

merged = copy.deepcopy(head.CATALOGUE)
for cid in TEN:
    assert cid in now.CATALOGUE, cid
    merged[cid] = copy.deepcopy(now.CATALOGUE[cid])

rendered = "CATALOGUE = " + pprint.pformat(merged, width=132, sort_dicts=True)
target = "src/bp/product/subjects.py"
source = io.open(target, encoding="utf-8").read()
start = source.index("CATALOGUE = ")
end = source.index("\n\n\ndef _fill_catalogue_ids", start)
io.open(target, "w", encoding="utf-8", newline="").write(source[:start] + rendered + source[end:])

print("catalogue rows:", len(merged))
for cid in TEN:
    row = merged[cid]
    print("  %-7s %-10s %-26s %s" % (cid, row["form"], row["template"], row["status_short"]))
