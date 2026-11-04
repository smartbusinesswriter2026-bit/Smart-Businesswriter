"""Measure the wordiness of a shelf's student-facing copy (read-only).

Reports, per field, the word count of every tool's `what`, `formula`, each `step`, each
`common_mistake` and `need`, plus the shelf `guidance`, so a ceiling can be set from data rather
than taste.

Usage:  PYTHONPATH=src python qa/probe_wordiness.py finance [out.txt]
"""
import statistics
import sys

sys.path.insert(0, "src")

from bp.product import subjects  # noqa: E402


def words(text):
    return len(str(text or "").split())


def main(argv):
    subject = argv[1] if len(argv) > 1 else "finance"
    detail = subjects.detail(subject)
    lines = []
    emit = lines.append
    emit("shelf: %s" % subject)
    emit("guidance: %d words" % words(detail.get("guidance")))
    fields = {"what": [], "formula": [], "need": [], "step": [], "mistake": []}
    worst = []
    for tool in detail.get("tools") or []:
        fields["what"].append((words(tool.get("what")), tool["key"]))
        fields["formula"].append((words(tool.get("formula")), tool["key"]))
        fields["need"].append((words(tool.get("need")), tool["key"]))
        for step in tool.get("steps") or []:
            fields["step"].append((words(step), tool["key"]))
        for item in tool.get("common_mistakes") or []:
            fields["mistake"].append((words(item), tool["key"]))
    emit("")
    emit("%-8s %5s %6s %6s %6s   %s" % ("field", "count", "mean", "median", "max", "longest"))
    for name, rows in fields.items():
        if not rows:
            emit("%-8s %5d" % (name, 0))
            continue
        counts = [row[0] for row in rows]
        top = max(rows)
        emit("%-8s %5d %6.1f %6.1f %6d   %s (%d words)"
             % (name, len(rows), statistics.mean(counts), statistics.median(counts),
                top[0], top[1], top[0]))
    emit("")
    emit("== the 20 longest lines ==")
    every = []
    for name, rows in fields.items():
        every.extend((count, name, key) for count, key in rows)
    for count, name, key in sorted(every, reverse=True)[:20]:
        emit("%4d  %-8s %s" % (count, name, key))
    emit("")
    emit("== over the ceiling (what >20, step >18, mistake >18, guidance >90) ==")
    over = []
    if words(detail.get("guidance")) > 90:
        over.append((words(detail.get("guidance")), "guidance", subject))
    for tool in detail.get("tools") or []:
        if words(tool.get("what")) > 20:
            over.append((words(tool.get("what")), "what", tool["key"]))
        for step in tool.get("steps") or []:
            if words(step) > 18:
                over.append((words(step), "step", tool["key"]))
        for item in tool.get("common_mistakes") or []:
            if words(item) > 18:
                over.append((words(item), "mistake", tool["key"]))
    for count, name, key in sorted(over, reverse=True):
        emit("%4d  %-8s %s" % (count, name, key))
    emit("(%d over the ceiling)" % len(over))
    text = "\n".join(lines) + "\n"
    if len(argv) > 2:
        open(argv[2], "w", encoding="utf-8").write(text)
        print("wrote %s" % argv[2])
    else:
        print(text)


if __name__ == "__main__":
    main(sys.argv)
