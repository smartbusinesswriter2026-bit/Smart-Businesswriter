"""Restore src/bp/templates.py to the writer's intended state.

A concurrent writer's later cleanup reverted templates.py to HEAD, which removed
the canvas definitions for the People and Operations shelves while the
worksheets, registry links, profiles and drafting schemas that point at them
survived.  The writer's own `git diff` for the file was captured verbatim in
the sibling session's transcript, so the lost text is recovered exactly rather
than re-authored.

Everything inserted here comes from those captured slices:

  late_blocks.txt    -> 3 CANVAS_BLOCKS entries added after the diff was taken
  people_meta_0.txt  -> CANVAS_BLOCKS (Operations, People)
                     -> CANVAS_META (9 Operations entries)
  meta_scan_2.txt    -> CANVAS_META (10 further entries)
                     -> CANVAS_PREFIXES (19 entries)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), ".uishot"))

from apply_diff import parse_hunks, split_body  # noqa: E402

ROOT = os.path.join(os.getcwd(), "src", "bp", "templates.py")
SLICE_A = os.path.join(os.getcwd(), ".uishot", "people_meta_0.txt")
SLICE_B = os.path.join(os.getcwd(), ".uishot", "meta_scan_2.txt")
LATE = os.path.join(os.getcwd(), ".uishot", "late_blocks.txt")


def find_sequence(lines, sequence, start=0):
    if not sequence:
        return start
    for position in range(start, len(lines) - len(sequence) + 1):
        if lines[position:position + len(sequence)] == sequence:
            return position
    return -1


def dict_close(lines, opener):
    """Index of the line that closes the dict opened at `opener`."""
    depth = 0
    for index in range(opener, len(lines)):
        depth += lines[index].count("{") - lines[index].count("}")
        if depth == 0 and index > opener:
            return index
    raise SystemExit("no close for dict at %d" % opener)


def insert_at(lines, position, payload, label):
    lines[position:position] = payload
    print("  %-34s inserted %3d lines at %d" % (label, len(payload), position + 1))


def main():
    slice_a = open(SLICE_A, encoding="utf-8").read().split("\n")
    hunks = parse_hunks(slice_a)
    parts = [split_body(hunk["body"]) for hunk in hunks]
    slice_b_lines = open(SLICE_B, encoding="utf-8").read().split("\n")
    late = open(LATE, encoding="utf-8", newline="").read().replace("\r\n", "\n").split("\n")
    while late and not late[-1].strip():
        late.pop()

    with open(ROOT, encoding="utf-8", newline="") as handle:
        raw = handle.read()
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.replace("\r\n", "\n").split("\n")

    # --- CANVAS_BLOCKS -----------------------------------------------------
    for index, label in ((0, "CANVAS_BLOCKS operations"), (1, "CANVAS_BLOCKS people")):
        lead, removed, added, trail = parts[index]
        position = find_sequence(lines, lead + removed)
        if position == -1:
            raise SystemExit("anchor not found for %s" % label)
        at = position + len(lead)
        lines[at:at + len(removed)] = added
        print("  %-34s inserted %3d lines at %d" % (label, len(added), at + 1))

    # The three blocks the writer added after the diff was taken go last, so
    # the recovered text keeps its original order.
    blocks_opener = lines.index("CANVAS_BLOCKS = {")
    blocks_close = dict_close(lines, blocks_opener)
    insert_at(lines, blocks_close, late, "CANVAS_BLOCKS late additions")

    # --- CANVAS_META -------------------------------------------------------
    lead, removed, added, trail = parts[2]
    position = find_sequence(lines, lead + removed)
    if position == -1:
        raise SystemExit("anchor not found for CANVAS_META operations")
    at = position + len(lead)
    lines[at:at + len(removed)] = added
    print("  %-34s inserted %3d lines at %d" % ("CANVAS_META operations", len(added), at + 1))

    meta_extra = slice_b_lines[1:61]
    if not meta_extra[0].strip().startswith('"template_'):
        raise SystemExit("unexpected meta_extra start: %r" % meta_extra[0])
    if meta_extra[-1].strip() != "},":
        raise SystemExit("unexpected meta_extra end: %r" % meta_extra[-1])
    meta_opener = lines.index("CANVAS_META = {")
    meta_close = dict_close(lines, meta_opener)
    insert_at(lines, meta_close, meta_extra, "CANVAS_META people")

    # --- CANVAS_PREFIXES ---------------------------------------------------
    prefixes = slice_b_lines[91:120]
    if not prefixes[0].strip().startswith('"template_sipoc"'):
        raise SystemExit("unexpected prefixes start: %r" % prefixes[0])
    if not prefixes[-1].strip().endswith('"incentives": "IN"},'):
        raise SystemExit("unexpected prefixes end: %r" % prefixes[-1])
    prefix_opener = lines.index("CANVAS_PREFIXES = {")
    prefix_close = dict_close(lines, prefix_opener)
    insert_at(lines, prefix_close, prefixes, "CANVAS_PREFIXES")

    text = newline.join(lines)
    with open(ROOT, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    print("WROTE %s (%d bytes)" % (ROOT, len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
