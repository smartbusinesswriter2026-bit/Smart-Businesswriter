"""Capture the three late CANVAS_BLOCKS entries the writer added after the diff.

These are not in the recovered diff slice (they were added later), so they are
saved aside before templates.py is reset and re-restored.
"""

import os
import re
import sys

ROOT = os.path.join(os.getcwd(), "src", "bp", "templates.py")
OUT = os.path.join(os.getcwd(), ".uishot", "late_blocks.txt")
WANTED = ["template_mckinsey_7s", "template_raci", "template_porters_diamond"]


def main():
    with open(ROOT, encoding="utf-8", newline="") as handle:
        raw = handle.read()
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.replace("\r\n", "\n").split("\n")

    blocks = []
    for name in WANTED:
        start = None
        for index, line in enumerate(lines):
            if line.strip().startswith('"%s": {' % name):
                start = index
                break
        if start is None:
            raise SystemExit("not found: " + name)
        end = start
        depth = 0
        for index in range(start, len(lines)):
            depth += lines[index].count("{") - lines[index].count("}")
            if depth == 0 and index > start:
                end = index
                break
            if depth == 0 and index == start:
                end = index
                break
        blocks.append(lines[start:end + 1])
        print("%-30s lines %d-%d (%d lines)" % (name, start + 1, end + 1, end - start + 1))

    payload = []
    for block in blocks:
        payload.extend(block)
    with open(OUT, "w", encoding="utf-8", newline="") as handle:
        handle.write(newline.join(payload) + newline)
    print("saved ->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
