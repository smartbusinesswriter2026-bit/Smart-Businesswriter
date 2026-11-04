"""Dump the finance shelf's student-facing surface, for the QA manual.

Read-only probe: it imports the product catalogue and prints the definition
block (guidance, start steps, does-not list), the detail() keys and every tile
with the tools and records it links.  Nothing is computed and nothing is
written except the file named on the command line.

Usage:  PYTHONPATH=src python qa/probe_finance_surface.py [out.txt]
"""
import json
import sys

sys.path.insert(0, "src")

from bp.product import subjects  # noqa: E402


def main(argv):
    subject_id = "finance"
    detail = subjects.detail(subject_id)
    definition = subjects._subject_definition(subject_id)
    out = {"detail_keys": sorted(detail.keys()),
           "definition_keys": sorted(definition.keys()),
           "definition": {key: definition.get(key) for key in
                          ("id", "label", "summary", "guidance", "start_steps", "does_not",
                           "disciplines", "tools", "worksheets", "catalogue_ids",
                           "student_notes", "theories", "glossary")},
           "counts": {"tools": len(detail.get("tools") or []),
                      "worksheets": len(detail.get("worksheets") or []),
                      "records": len(detail.get("records") or []),
                      "tiles": len(detail.get("tiles") or []),
                      "theories": len(detail.get("theories") or []),
                      "glossary": len(detail.get("glossary") or [])},
           "tiles": [{"key": tile["key"], "label": tile.get("label"),
                      "what": tile.get("what"), "need": tile.get("need"),
                      "note": tile.get("note"),
                      "tools": [t["key"] for t in tile.get("tools") or []],
                      "worksheets": [w["key"] for w in tile.get("worksheets") or []],
                      "records": [r["id"] for r in tile.get("records") or []]}
                     for tile in detail.get("tiles") or []],
           "theories": detail.get("theories"),
           "glossary": detail.get("glossary")}
    text = json.dumps(out, indent=1, sort_keys=False, default=str)
    if len(argv) > 1:
        with open(argv[1], "w", encoding="utf-8") as handle:
            handle.write(text)
        print("wrote %s" % argv[1])
    else:
        print(text)


if __name__ == "__main__":
    main(sys.argv)
