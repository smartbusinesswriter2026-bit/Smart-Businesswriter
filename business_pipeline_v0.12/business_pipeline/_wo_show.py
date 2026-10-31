"""Print the orphan block structure for authoring the template metadata."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "_wo_build_input.json"), encoding="utf-8"))
for tpl, v in data["orphans"].items():
    print("%s -> %s | %s | ratings=%s" % (tpl, v["catalogue_id"], v["label"], v["ratings"]))
    print("   unit: %s" % json.dumps(v["unit"], ensure_ascii=False))
    for b in v["blocks"]:
        print("   - %-26s %-36s %s" % (b["key"], b["label"], b["prompt"]))
    print()
