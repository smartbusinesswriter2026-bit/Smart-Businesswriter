"""The raw ratio rows, so the case study can quote today's numbers."""
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

ratios = record["ratios"]
print("ratios keys:", list(ratios))
computed = ratios["computed"]
print("computed is a", type(computed).__name__, "of", len(computed))
print("first row raw:", json.dumps(computed[0])[:400])
print()
for row in computed:
    if isinstance(row, dict):
        name = row.get("ratio") or row.get("name")
        value = row.get("value")
        definition = row.get("definition")
        print("   %-22s %-34s %s" % (name, value, definition))
    else:
        print("   ", row)
print()
print("missing:", json.dumps(ratios.get("named_unsupported"))[:900])
