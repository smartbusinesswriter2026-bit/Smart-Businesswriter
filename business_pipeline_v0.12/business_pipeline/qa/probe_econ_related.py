"""Do the economics tools' `related` ids resolve anywhere in the product?

A `related` id that is not an economics tool key is legitimate only if it is a
tool key on another shelf AND the page can route to it. This probe answers the
first half mechanically.

Usage: python qa/probe_econ_related.py
"""
import json
import pathlib
import sys

sys.path.insert(0, "src")

from bp.product import subjects   # noqa: E402

APP = pathlib.Path(__file__).resolve().parent.parent


def main():
    catalogues = getattr(subjects, "SUBJECTS", None) or getattr(subjects, "SUBJECT_DEFS", [])
    if catalogues and isinstance(next(iter(catalogues)), dict):
        subject_ids = [row["id"] for row in catalogues]
    else:
        subject_ids = list(catalogues)
    global_keys = {}
    for subject_id in subject_ids:
        for tool in subjects.detail(subject_id)["tools"] or []:
            if tool.get("key"):
                global_keys.setdefault(tool["key"], subject_id)

    econ = subjects.detail("economics")
    econ_keys = {tool["key"] for tool in econ["tools"]}
    rows = []
    for tool in econ["tools"]:
        for related in tool.get("related") or []:
            if related in econ_keys:
                rows.append((tool["key"], related, "economics", "local"))
            elif related in global_keys:
                rows.append((tool["key"], related, global_keys[related], "cross-shelf"))
            else:
                rows.append((tool["key"], related, "-", "UNRESOLVED"))

    unresolved = [row for row in rows if row[3] == "UNRESOLVED"]
    lines = ["subjects: %d, global tool keys: %d" % (len(subject_ids), len(global_keys)),
             "related links: %d, cross-shelf: %d, unresolved: %d"
             % (len(rows), sum(1 for r in rows if r[3] == "cross-shelf"), len(unresolved)),
             ""]
    for tool, related, where, kind in sorted(rows):
        lines.append("%-16s -> %-16s %-16s %s" % (tool, related, where, kind))
    text = "\n".join(lines)
    (APP / "qa" / "baseline" / "econ_related.txt").write_text(text, encoding="utf-8")
    print("\n".join(lines[:8]))


if __name__ == "__main__":
    main()
