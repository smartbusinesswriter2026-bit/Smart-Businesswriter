"""Recover the original templates.py canvas blocks from session transcripts.

Scans the agent store for text blobs that carry the People framework canvas
definitions and writes the biggest one out for inspection.
"""

import json
import os
import sys

ROOT = os.path.expanduser("~/.minimax")
OUT = os.path.join(os.getcwd(), ".uishot")

SIGNATURES = [
    b'"template_job_characteristics": {',
    b'"skill_variety": (',
    b'CANVAS_META = {',
]


def walk(node, out):
    if isinstance(node, str):
        enc = node.encode("utf-8", "replace")
        if any(sig in enc for sig in SIGNATURES):
            out.append(node)
    elif isinstance(node, dict):
        for value in node.values():
            walk(value, out)
    elif isinstance(node, list):
        for value in node:
            walk(value, out)


def main():
    blobs = []
    for dp, dn, fn in os.walk(ROOT):
        if any(x in dp for x in ("node_modules", "__pycache__", "plugins", ".git")):
            continue
        for name in fn:
            if not name.endswith((".jsonl", ".log", ".sqlite-wal")):
                continue
            path = os.path.join(dp, name)
            try:
                if os.path.getsize(path) > 80_000_000:
                    continue
                handle = open(path, encoding="utf-8", errors="replace")
            except OSError:
                continue
            with handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue
                    walk(record, blobs)
    print("blobs:", len(blobs))
    best = sorted(blobs, key=len, reverse=True)[:6]
    for index, blob in enumerate(best):
        name = "recovered_%d.txt" % index
        path = os.path.join(OUT, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(blob)
        hits = [sig.decode() for sig in SIGNATURES if sig in blob.encode("utf-8", "replace")]
        print("  %-20s len=%-8d sigs=%s" % (name, len(blob), hits))


if __name__ == "__main__":
    main()
