"""One-off diagnostic: exact codepoints for the en-dash names on both sides."""
import io
import json
import sys

sys.path.insert(0, "src")
from bp import catalogue_import as CI  # noqa: E402

CAT = "docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md"
shipped = json.load(io.open("src/bp/data/registry_v0_2.json", encoding="utf-8"))
fresh = CI.import_catalogue(CAT)

for rid in ("CHG-05", "PPL-01"):
    a = next(r for r in shipped["records"] if r["id"] == rid)["name"]
    b = next(r for r in fresh["records"] if r["id"] == rid)["name"]
    print(rid, "shipped codepoints:", [hex(ord(c)) for c in a[:14]])
    print(rid, "fresh   codepoints:", [hex(ord(c)) for c in b[:14]])
    print()

raw = io.open(CAT, "rb").read()
text = raw.decode("utf-8")
line = next(l for l in text.splitlines() if "Burke" in l)
print("markdown row bytes:", line.encode("utf-8")[:70])
print("markdown row codepoints:", [hex(ord(c)) for c in line[:60]])
