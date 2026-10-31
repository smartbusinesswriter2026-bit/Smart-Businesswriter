"""Extract the largest templates.py-like text blobs from a session transcript.

The sibling session read the good templates.py before it was reverted; the read
result is stored verbatim in the transcript.  This finds the candidate blob.
"""

import json
import os
import sys

PATH = sys.argv[1]
KEYS = ("CANVAS_META", "CANVAS_BLOCKS", "template_job_characteristics")


def walk(node, out):
    if isinstance(node, str):
        if all(k in node for k in KEYS):
            out.append(node)
    elif isinstance(node, dict):
        for v in node.values():
            walk(v, out)
    elif isinstance(node, list):
        for v in node:
            walk(v, out)


def main():
    blobs = []
    with open(PATH, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            walk(record, blobs)
    print("candidate blobs:", len(blobs))
    seen = set()
    for blob in sorted(blobs, key=len, reverse=True):
        if len(blob) in seen:
            continue
        seen.add(len(blob))
        print("  len=%-9d lines=%-6d has_CANVAS_META_def=%s" % (
            len(blob), blob.count("\n"),
            "CANVAS_META = {" in blob))
        if len(blob) > 3000:
            out = os.path.join(os.getcwd(), ".uishot", "recovered_templates_candidate.txt")
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(blob)
            print("     -> written to", out)


if __name__ == "__main__":
    main()
