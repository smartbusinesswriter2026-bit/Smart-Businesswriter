"""Restore src/bp/templates.py from the writer's own recovered git diff.

The sibling session's transcript holds the writer's `git diff` for
templates.py.  Its base is HEAD; the file on disk is HEAD plus three later
CANVAS_BLOCKS entries, so hunks are applied by content anchor, in reverse
order, using each hunk's leading context as the insertion point.
"""

import os
import re
import sys

ROOT = os.path.join(os.getcwd(), "src", "bp", "templates.py")
DIFF = os.path.join(os.getcwd(), ".uishot", "people_meta_0.txt")


def parse_hunks(diff_lines):
    hunks = []
    current = None
    for line in diff_lines:
        if line.startswith("@@"):
            if re.match(r"@@ -\d+(,\d+)? \+\d+(,\d+)? @@", line):
                current = {"body": [], "header": line}
                hunks.append(current)
            continue
        if current is None:
            continue
        if line.startswith("diff --git") or line.startswith("index "):
            current = None
            continue
        if line.startswith("\\") or not line:
            continue
        current["body"].append((line[0], line[1:]))
    return hunks


def split_body(body):
    """Return (leading_context, removed, added, trailing_context)."""
    leading, trailing = [], []
    index = 0
    while index < len(body) and body[index][0] == " ":
        leading.append(body[index][1])
        index += 1
    removed, added = [], []
    while index < len(body) and body[index][0] in "+-":
        marker, text = body[index]
        (removed if marker == "-" else added).append(text)
        index += 1
    while index < len(body) and body[index][0] == " ":
        trailing.append(body[index][1])
        index += 1
    return leading, removed, added, trailing


def find_sequence(lines, sequence, start=0):
    if not sequence:
        return start
    for position in range(start, len(lines) - len(sequence) + 1):
        if lines[position:position + len(sequence)] == sequence:
            return position
    for position in range(0, start):
        if lines[position:position + len(sequence)] == sequence:
            return position
    return -1


def main():
    apply_changes = "--apply" in sys.argv
    diff_lines = open(DIFF, encoding="utf-8").read().split("\n")
    hunks = parse_hunks(diff_lines)
    print("hunks: %d" % len(hunks))

    with open(ROOT, encoding="utf-8", newline="") as handle:
        raw = handle.read()
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.replace("\r\n", "\n").split("\n")

    for index in reversed(range(len(hunks))):
        hunk = hunks[index]
        leading, removed, added, trailing = split_body(hunk["body"])
        anchor = find_sequence(lines, leading + removed)
        if anchor == -1:
            anchor = find_sequence(lines, leading)
            if anchor == -1:
                print("  hunk %d: NO ANCHOR (%s)" % (index, hunk["header"]))
                return 1
            anchor += len(leading)
        end = anchor + len(leading) + len(removed)
        lines[anchor:end] = added
        print("  hunk %d: inserted %d lines at %d (%s)" % (
            index, len(added), anchor + 1, hunk["header"][:52]))

    text = newline.join(lines)
    if apply_changes:
        with open(ROOT, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        print("WROTE %s (%d bytes)" % (ROOT, len(text)))
    else:
        print("dry run: pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
