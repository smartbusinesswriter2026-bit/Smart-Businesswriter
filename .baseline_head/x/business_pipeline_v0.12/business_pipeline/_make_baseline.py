"""Assemble the baseline worktree: HEAD plus the in-flight work that was already
in the tree when this task started, minus everything this task changed.

The baseline is what the suite looked like before the People shelf work, so the
final run can be compared against it failure for failure.
"""
import io
import os
import shutil

MAIN = "D:\\SMART BUSINESSWRITER\\business_pipeline_v0.12\\business_pipeline"
BASE = "D:\\SMART BUSINESSWRITER\\_baseline_wt\\business_pipeline_v0.12\\business_pipeline"

#: Files the in-flight work had already changed; this task did not touch them.
INFLIGHT = [
    "documents/index.json",
    "src/bp/product/chat.py",
    "src/bp/product/drafting.py",
    "src/bp/product/framework_profiles.py",
    "web/index.html",
]

#: The eight worked examples this task added to the template gallery, keyed by
#: the objective line that is unique to each one.
ADDED = {
    "template_amo": "Read why service on the meal counter is slow",
    "template_competing_values": "Read the culture of the campus catering team",
    "template_job_characteristics": "Read the shape of the kitchen supervisor",
    "template_kirkpatrick": "Read the evidence from the food-safety induction",
    "template_kotter": "Read the eight steps of the move to a contactless meal card",
    "template_nine_box": "Record how the counter team is reviewed",
    "template_org_design": "Read the design of the university catering unit",
    "template_tuckman": "Read how the tray assembly team is working together",
}


def strip_examples(text):
    """Remove the eight example blocks this task added, line by line."""
    lines = text.split("\n")
    out = []
    index = 0
    while index < len(lines):
        line = lines[index]
        marker = next((objective for objective in ADDED.values()
                       if line.strip().startswith('"') and objective in line), None)
        if marker is None:
            out.append(line)
            index += 1
            continue
        # Skip to the line that closes this example block.
        depth = 0
        while index < len(lines):
            depth += lines[index].count("{") - lines[index].count("}")
            index += 1
            if depth == 0:
                break
    return "\n".join(out)


for relative in INFLIGHT:
    shutil.copyfile(os.path.join(MAIN, relative), os.path.join(BASE, relative))
    print("copied", relative)

shutil.copyfile(os.path.join(MAIN, "_subjects_before_gen.py"),
                os.path.join(BASE, "src/bp/product/subjects.py"))
print("copied subjects.py (pre-task state)")

templates = io.open(os.path.join(MAIN, "src/bp/templates.py"), encoding="utf-8").read()
stripped = strip_examples(templates)
with io.open(os.path.join(BASE, "src/bp/templates.py"), "w", encoding="utf-8", newline="") as handle:
    handle.write(stripped)
print("wrote templates.py (pre-task state): %d bytes -> %d bytes" % (len(templates), len(stripped)))
