"""Scan the agent store for blobs carrying the People canvas meta entries."""

import json
import os
import sys

ROOT = os.path.expanduser("~/.minimax")
OUT = os.path.join(os.getcwd(), ".uishot")
SIGS = [b'"registry_ids": ["PPL-', b'"registry_ids": ["CHG-']


def walk(node, out):
    if isinstance(node, str):
        enc = node.encode("utf-8", "replace")
        if any(sig in enc for sig in SIGS):
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
            if not name.endswith((".jsonl", ".log")):
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
    for index, blob in enumerate(sorted(blobs, key=len, reverse=True)[:4]):
        path = os.path.join(OUT, "people_meta_%d.txt" % index)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(blob)
        print("  people_meta_%d.txt len=%d" % (index, len(blob)))


if __name__ == "__main__":
    main()
