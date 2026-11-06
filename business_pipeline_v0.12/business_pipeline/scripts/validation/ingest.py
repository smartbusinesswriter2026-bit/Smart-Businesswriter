"""Feed a validation-harness manifest into the admin findings store.

Reads ``validation_out/manifest.json`` (default) or a path given as the first
argument, appends/updates findings in ``state/ops_log/findings.jsonl`` via
``bp.product.ops_log`` and auto-resolves findings the latest pass no longer
reports.  The same work happens when the admin page calls
``POST /api/ops/findings/ingest``; this script exists so a harness run can be
ingested without the server being up.

Usage (from ``business_pipeline/``):
    PYTHONPATH=src python scripts/validation/ingest.py [path/to/manifest.json]
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # business_pipeline/
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp.product import ops_log  # noqa: E402


def main(argv):
    manifest = argv[1] if len(argv) > 1 else None
    opened, resolved, errors = ops_log.ingest_validation_manifest(manifest)
    print("opened: %d" % opened)
    print("auto-resolved: %d" % resolved)
    for e in errors:
        print("error: %s" % e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
