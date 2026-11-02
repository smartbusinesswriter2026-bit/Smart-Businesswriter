"""Dump one subject shelf from the live catalogue, for the QA manual.

Read-only probe: it imports the product catalogue and prints what a subject page
actually promises.  Nothing is computed and nothing is written.

Usage:  PYTHONPATH=src python qa/probe_subject.py accounting
"""
import json
import sys

sys.path.insert(0, "src")

from bp.product import subjects  # noqa: E402


def main(argv):
    subject_id = argv[1] if len(argv) > 1 else "accounting"
    detail = subjects.detail(subject_id)
    out = {"subject": subject_id, "counts": {}, "tools": [], "worksheets": [],
           "records": [], "tiles": [], "definition": {}}
    definition = subjects._subject_definition(subject_id)
    out["definition"] = {key: definition.get(key) for key in
                         ("id", "label", "summary", "guidance", "start_steps", "does_not",
                          "disciplines", "tools", "worksheets", "catalogue_ids")}
    for tool in detail.get("tools", []):
        out["tools"].append(tool)
    for sheet in detail.get("worksheets", []):
        out["worksheets"].append(sheet)
    for row in detail.get("records", []):
        out["records"].append(row)
    for tile in detail.get("tiles", []):
        out["tiles"].append({"key": tile["key"], "label": tile["label"],
                             "what": tile.get("what"), "need": tile.get("need"),
                             "note": tile.get("note"),
                             "tools": [t["key"] for t in tile.get("tools", [])],
                             "worksheets": [w["key"] for w in tile.get("worksheets", [])],
                             "records": [r["id"] for r in tile.get("records", [])]})
    out["counts"] = {"tools": len(out["tools"]), "worksheets": len(out["worksheets"]),
                     "records": len(out["records"]), "tiles": len(out["tiles"])}
    text = json.dumps(out, indent=1, sort_keys=False, default=str)
    if len(argv) > 2:
        with open(argv[2], "w", encoding="utf-8") as handle:
            handle.write(text)
        print("wrote %s" % argv[2])
    else:
        print(text)


if __name__ == "__main__":
    main(sys.argv)
