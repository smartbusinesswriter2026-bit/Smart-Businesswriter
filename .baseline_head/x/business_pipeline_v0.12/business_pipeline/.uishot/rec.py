"""Show the registry catalogue record for a worksheet id."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

import bp.registry as registry  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def show(key):
    data = registry.DATA
    record = None
    if isinstance(data, dict):
        record = data.get(key)
        if record is None and "records" in data:
            for item in data["records"]:
                if item.get("id") == key:
                    record = item
                    break
    elif isinstance(data, list):
        for item in data:
            if item.get("id") == key:
                record = item
                break
    print("=== %s ===" % key)
    if record is None:
        print("  NOT FOUND (DATA type=%s keys=%s)" % (type(data).__name__,
              list(data.keys())[:8] if isinstance(data, dict) else len(data)))
        return
    for k, v in record.items():
        print("   %-18s %s" % (k, repr(v)[:300]))


def main():
    print("DATA type:", type(registry.DATA).__name__)
    if isinstance(registry.DATA, dict):
        print("DATA keys:", list(registry.DATA.keys())[:12])
    for key in (sys.argv[1:] or ["PPL-03", "PPL-01", "CHG-01", "OPS-01", "STR-06"]):
        show(key)


if __name__ == "__main__":
    main()
