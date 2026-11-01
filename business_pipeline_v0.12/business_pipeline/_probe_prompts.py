"""One-off: the canvas block prompts for the eight People frameworks that have
no worked example yet."""
import sys

sys.path.insert(0, "src")
from bp import templates as T  # noqa: E402

for kind in ("template_job_characteristics", "template_kirkpatrick", "template_amo",
             "template_tuckman", "template_nine_box", "template_kotter",
             "template_competing_values", "template_org_design"):
    print("=" * 72)
    print(kind, "|", T.CANVAS_META[kind]["name"])
    for key, (label, prompt) in T.CANVAS_BLOCKS[kind].items():
        print("   %-22s %-34s %s" % (key, label, prompt))
