"""Regenerate the committed method catalogue.

Usage:  python scripts/build_method_catalogue.py

Writes ``src/bp/product/data/method_catalogue_v1.json``.  The test
``tests/test_method_inventory.py`` fails if the committed file drifts from the
library, so this script and the catalogue are always generated from the same
source of truth.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bp.product import method_catalogue  # noqa: E402

TARGET = (Path(__file__).resolve().parents[1] / "src" / "bp" / "product" / "data"
          / "method_catalogue_v1.json")

if __name__ == "__main__":
    method_catalogue.write(TARGET)
    print("wrote", TARGET)
    print("library", method_catalogue.build()["source"]["library"], "methods")
