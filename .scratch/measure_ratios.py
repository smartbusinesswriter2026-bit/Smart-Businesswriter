"""The Ashgrove case with the ratio line: exactly what the owner sees today."""
import json
import urllib.request

BASE = "http://127.0.0.1:8077"

TRIAL_BALANCE = """The following trial balance was extracted at 31 December 2026.
Equipment 30,000
Cash 15,900
Trade receivables 18,400
Inventory 22,600
Cost of sales 84,000
Wages 19,000
Rent 8,000
Utilities 3,200
Depreciation 3,000
Interest expense 1,200
Trade payables 14,800 Cr
Loan 12,000 Cr
Capital 20,000 Cr
Retained earnings 8,000 Cr
Sales 140,000 Cr
Other income 1,500 Cr
Accumulated depreciation 9,000 Cr"""

instruction = TRIAL_BALANCE + "\nAlso compute the liquidity ratios."
request = urllib.request.Request(
    BASE + "/api/cases/statements",
    data=json.dumps({"instruction": instruction}).encode("utf-8"),
    headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(request, timeout=120) as response:
    record = json.loads(response.read().decode("utf-8"))

print("status", response.status, "type", record.get("problem_type"),
      "computed", record.get("computed"), "hidden", record.get("hidden"))
print("id", record.get("id"))
print()
print("--- ratios computed: %d" % len(record["ratios"]["computed"]))
for entry in record["ratios"]["computed"]:
    print("   " + " | ".join(str(part) for part in entry))
print()
print("--- not computed: %d" % len(record["ratios"].get("missing") or []))
for entry in (record["ratios"].get("missing") or []):
    print("   " + " | ".join(str(part) for part in entry))
print()
print("--- checks: %d" % len(record["checks"]))
print("--- core scalars ---")
for key, value in sorted((record.get("core") or {}).get("scalars", {}).items()):
    print("   %-22s %s" % (key, value))
print()
print(record["statements"]["equity"])
