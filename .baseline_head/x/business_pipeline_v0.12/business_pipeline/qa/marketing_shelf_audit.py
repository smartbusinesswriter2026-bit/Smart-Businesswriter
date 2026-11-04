"""Measure the marketing shelf's four audited claims (QA tool, session 8).

Nothing here is a test: it prints the values the ledger rows in
``qa/QA_DEFECTS.md`` are written from, so a claim can be re-measured instead of
remembered.  Every number the audit quotes comes from this output.

    $env:PYTHONPATH='src'; python qa/marketing_shelf_audit.py

S1  SERVQUAL (MKT-07) -- which form the template actually implements.
S2  the worksheets that are built and offered by no shelf (D-PLAN-02).
S3  RFM (MKT-08) -- one record under two ids, and where its computed half lives.
S4  the marketing-plan document door -- sections, gate wording, export bytes.
"""
import io
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

sys.path = [item for item in sys.path if os.path.abspath(item or ".") != HERE]
sys.path.insert(0, os.path.join(ROOT, "src"))
os.chdir(ROOT)

from bp import methods, registry, templates  # noqa: E402
from bp.product import api, chat, framework_profiles, paper, subjects  # noqa: E402


def s1_servqual():
    kind = "template_servqual"
    template = templates.TEMPLATES[kind]
    described = templates.describe(kind)
    print("S1 SERVQUAL -- which form does the template implement?")
    print("  in CANVAS_BLOCKS :", kind in templates.CANVAS_BLOCKS)
    print("  in CANVAS_META   :", kind in templates.CANVAS_META)
    print("  in MATRIX_META   :", kind in templates.MATRIX_META)
    print("  describe form_kind:", described["form_kind"])
    print("  describe blocks   :", [block["key"] for block in described["blocks"]])
    print("  describe matrix   :", bool(described["matrix"]))
    print("  planned_checks    :", len(described["planned_checks"]))
    print("  input_help keys   :", sorted(described["input_help"]))
    print("  builder           :", template["build"].__name__)
    print("  renderer          :", template["render"].__name__)
    print("  declared in both  :", sorted(set(templates.CANVAS_BLOCKS) & set(templates.MATRIX_META)))
    out = templates.run_template(kind, templates.EXAMPLES[kind]["inputs"])
    print("  counts            :", sorted(out["counts"]))
    print("  checks that ran   :", len(out["results"]), "all ok:", all(ok for _, ok in out["results"]))


def s2_unserved():
    served = set()
    for definition in subjects.SUBJECT_DEFS:
        served.update(definition.get("worksheets") or [])
    unserved = sorted(set(subjects.WORKSHEETS) - served)
    marketing = [row for row in unserved if row.startswith("MKT-")]
    print("S2 unserved worksheets")
    print("  WORKSHEETS built  :", len(subjects.WORKSHEETS))
    print("  served by a shelf :", len(served))
    print("  unserved total    :", len(unserved), unserved)
    print("  unserved marketing:", len(marketing), marketing)
    page = subjects.detail("marketing")
    print("  marketing page    : worksheets=%d records=%d tools=%d tiles=%d"
          % (len(page["worksheets"]), len(page["records"]), len(page["tools"]), len(page["tiles"])))
    for tile in page["tiles"]:
        print("  tile %-38s worksheets=%d tools=%d records=%d"
              % (tile["key"], len(tile["worksheets"]), len(tile["tools"]), len(tile["records"])))
    badges = {}
    for row in page["records"]:
        if row["id"] in marketing:
            badges.setdefault(row["status_short"], []).append(row["id"])
    for badge, ids in sorted(badges.items()):
        print("  badge %-16s %2d %s" % (badge, len(ids), ", ".join(ids)))


def s3_rfm():
    first = registry.get("MKT-08")
    alias = registry.get("QNT-MKT-04")
    print("S3 RFM (MKT-08)")
    print("  same record       :", first is alias or first == alias)
    print("  also_listed_as    :", first.get("also_listed_as"))
    print("  form              :", first.get("form"))
    print("  template          :", first.get("template"))
    print("  linked_methods    :", [(m["method_id"], m["coverage"]) for m in first.get("linked_methods") or []])
    print("  implementation    :", first.get("implementation_status", "")[:120])


def s4_plan():
    print("S4 marketing-plan document door")

    def _run(method_id, inputs):
        method = methods.LIBRARY[method_id]
        errors = methods.validate_inputs(method, inputs)
        if errors:
            raise ValueError("; ".join(errors))
        return method.impl(inputs)

    api.attach_methods(_run, methods.describe)
    state = chat.start("A coffee shop selling specialty coffee to commuters in a mid-sized city.",
                       subject="marketing", profile="marketing_plan", level="shs")
    state = chat.confirm_plan(state)
    print("  sections          :", [row["key"] for row in state["plan"]["sections"]])
    print("  gate knows it     :", state["plan"]["profile"] in paper.DRAFT_PROFILES)
    declared = paper.missing(state)
    labels = {field["label"] for field in state["plan"]["fields"] if field.get("required")}
    print("  gate names        :", declared[:4], "+%d more" % max(0, len(declared) - 4))
    print("  names plan fields :", bool(labels & set(declared)))
    print("  demands implications:", "implications" in declared)

    required = [field["key"] for field in state["plan"]["fields"] if field.get("required")]
    state = chat.set_inputs(state, {key: "a detail the student supplies" for key in required})
    BLOCKS = {"frommarket": {"market_size": "60000000", "target_share": "0.03", "price": "120"},
              "breakeven": {"fixed": "300000", "price": "120", "variable": "55"}}
    wanted = [block["key"] for block in state["plan"]["blocks"] if block.get("required")]
    state = chat.compute(state, {key: BLOCKS[key] for key in wanted if key in BLOCKS})
    draft = chat.draft(state)["draft"]
    print("  draft missing     :", draft["missing"])
    data = chat.docx_bytes(chat.draft(state))
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        text = archive.read("word/document.xml").decode("utf-8").lower()
    print("  docx bytes        :", len(data), "(%0.1f KB)" % (len(data) / 1024.0))
    print("  hashes in docx    :", "specification hash" in text or "can be re-run" in text)
    print("  profilename in doc:", "template_servqual" in framework_profiles.PROFILES)


if __name__ == "__main__":
    s1_servqual()
    print()
    s2_unserved()
    print()
    s3_rfm()
    print()
    s4_plan()
