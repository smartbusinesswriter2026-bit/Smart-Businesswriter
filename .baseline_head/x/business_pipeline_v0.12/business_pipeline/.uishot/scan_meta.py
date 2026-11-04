"""Find every transcript blob that carries a specific canvas-meta entry.

Used to recover the People CANVAS_META entries that one slice elided.
"""

import json
import os
import sys

ROOT = os.path.expanduser("~/.minimax")
OUT = os.path.join(os.getcwd(), ".uishot")
TARGETS = [b'"registry_ids": ["CHG-01"]', b'"registry_ids": ["CHG-12"]',
           b'"registry_ids": ["CHG-11"]', b'"registry_ids": ["PPL-01"]',
           b'"registry_ids": ["PPL-04"]', b'"registry_ids": ["PPL-05"]']


def walk(node, out):
    if isinstance(node, str):
        enc = node.encode("utf-8", "replace")
        if any(sig in enc for sig in TARGETS):
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
    scored = []
    for blob in blobs:
        enc = blob.encode("utf-8", "replace")
        found = sum(1 for sig in TARGETS if sig in enc)
        scored.append((found, len(blob), blob))
    scored.sort(key=lambda item: (-item[0], -item[1]))
    for index, (found, size, blob) in enumerate(scored[:4]):
        path = os.path.join(OUT, "meta_scan_%d.txt" % index)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(blob)
        print("  meta_scan_%d.txt  targets=%d len=%d" % (index, found, size))


if __name__ == "__main__":
    main()
