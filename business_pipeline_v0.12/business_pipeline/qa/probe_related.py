"""Check the cross-reference promises of one subject shelf.

Verifies that every `related` id on a subject tool resolves to a real tool, that
the glossary is present, and that each catalogue record's `linked_methods` exist
in the frozen method library.  Read-only.

Usage:  PYTHONPATH=src python qa/probe_related.py accounting
"""
import sys

sys.path.insert(0, "src")

from bp import methods  # noqa: E402
from bp.product import subjects  # noqa: E402


def main(argv):
    subject_id = argv[1] if len(argv) > 1 else "accounting"
    page = subjects.detail(subject_id)
    tool_keys = {tool["key"] for tool in subjects.compute_tools()}
    lines = []
    lines.append("subject: %s" % subject_id)
    lines.append("glossary entries: %d" % len(page.get("glossary") or []))
    for term in (page.get("glossary") or [])[:40]:
        lines.append("   - %s" % term.get("term"))
    lines.append("")
    lines.append("== related ids ==")
    for tool in page["tools"]:
        for related in tool.get("related") or []:
            if related in tool_keys:
                status = "ok"
            elif related in methods.LIBRARY:
                status = "method-but-not-a-tool"
            else:
                status = "MISSING"
            lines.append("%-16s -> %-18s %s" % (tool["key"], related, status))
    lines.append("")
    lines.append("== catalogue records: linked methods vs library ==")
    for row in page["catalogue"]:
        lines.append("%s %s form=%s template=%s" % (row["id"], row["name"], row["form"], row.get("template")))
        for method_id in row.get("linked_methods") or []:
            lines.append("   linked: %-30s %s" % (method_id, "ok" if method_id in methods.LIBRARY else "MISSING"))
        lines.append("   status: %s" % row.get("implementation_status"))
    lines.append("")
    lines.append("== tool notes completeness ==")
    for tool in page["tools"]:
        missing = [field for field in ("level", "formula", "steps", "common_mistakes", "related")
                   if not tool.get(field)]
        lines.append("%-16s missing=%s need=%r" % (tool["key"], missing, tool.get("need")))
    text = "\n".join(lines) + "\n"
    if len(argv) > 2:
        with open(argv[2], "w", encoding="utf-8") as handle:
            handle.write(text)
        print("wrote %s" % argv[2])
    else:
        print(text)


if __name__ == "__main__":
    main(sys.argv)
