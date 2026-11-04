"""Dump the economics student-facing catalogue facts for the manual.

Read-only. Writes qa/baseline/econ_facts.md.
"""
import json
import pathlib
import sys

sys.path.insert(0, "src")

from bp.product import subjects   # noqa: E402

APP = pathlib.Path(__file__).resolve().parent.parent


def main():
    detail = subjects.detail("economics")
    lines = []

    def block(title, value):
        lines.append("## " + title)
        lines.append("")
        if isinstance(value, list):
            for item in value:
                lines.append("- " + str(item))
        else:
            lines.append(str(value))
        lines.append("")

    block("guidance", detail.get("guidance"))
    block("start_steps", detail.get("start_steps") or [])
    block("does_not", detail.get("does_not") or [])
    block("disciplines", detail.get("disciplines") or [])
    block("discipline_labels", detail.get("discipline_labels") or [])

    lines.append("## tiles")
    lines.append("")
    lines.append("| key | label | what | need | worksheets | tools |")
    lines.append("|---|---|---|---|---|---|")
    for tile in detail["tiles"]:
        lines.append("| `%s` | %s | %s | %s | %s | %d |"
                     % (tile["key"], tile["label"], (tile.get("what") or "").replace("|", "/"),
                        (tile.get("need") or "**none**").replace("|", "/"),
                        ", ".join(tile.get("worksheets") or []) or "-",
                        len(tile.get("tools") or [])))
    lines.append("")

    lines.append("## records")
    lines.append("")
    lines.append("| id | name | type | form | template | linked methods | status |")
    lines.append("|---|---|---|---|---|---|---|")
    for record in detail["records"]:
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s |"
                     % (record.get("id"), record.get("name"), record.get("type"),
                        record.get("form"), record.get("template") or "-",
                        ", ".join(record.get("linked_methods") or []) or "-",
                        (record.get("status_short") or "")))
    lines.append("")
    for record in detail["records"]:
        lines.append("**%s %s** — %s" % (record.get("id"), record.get("name"),
                                         record.get("status_note") or ""))
        lines.append("")

    lines.append("## glossary (%d terms)" % len(detail["glossary"]))
    lines.append("")
    lines.append("| term | definition |")
    lines.append("|---|---|")
    for entry in detail["glossary"]:
        lines.append("| %s | %s |" % (entry["term"], entry["definition"].replace("|", "/")))
    lines.append("")

    lines.append("## worksheets")
    lines.append("")
    lines.append("_%d worksheets on this shelf._" % len(detail["worksheets"]))
    lines.append("")
    lines.append("## theories")
    lines.append("")
    lines.append("_%d theories on this shelf._" % len(detail["theories"]))

    text = "\n".join(lines)
    (APP / "qa" / "baseline" / "econ_facts.md").write_text(text, encoding="utf-8")
    print("wrote %d chars" % len(text))


if __name__ == "__main__":
    main()
