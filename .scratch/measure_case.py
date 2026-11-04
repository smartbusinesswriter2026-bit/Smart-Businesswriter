"""One clean measurement of the owner's case, for the case study.

Posts the Ashgrove trial balance twice — once alone, once with the ratio line —
and prints everything the case study quotes.
"""
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

OUT = r"D:\SMART BUSINESSWRITER\.scratch\case-measurement.txt"
lines = []


def post(instruction):
    request = urllib.request.Request(
        BASE + "/api/cases/statements",
        data=json.dumps({"instruction": instruction}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def say(text=""):
    lines.append(text)
    print(text)


say("=" * 78)
say("1. THE TRIAL BALANCE ALONE")
say("=" * 78)
status, record = post(TRIAL_BALANCE)
say("status %s  id %s  problem_type %s  computed %s  hidden %s"
    % (status, record.get("id"), record.get("problem_type"),
       record.get("computed"), record.get("hidden")))
say("reading source: %s" % (record.get("reading") or {}).get("source"))
say("cue: %s" % (record.get("why") or ""))
say("")
say("--- checks ---")
for check in record.get("checks") or []:
    say("   [%s] %s" % ("ok" if check.get("ok") else "na", check.get("name")))
say("")
say("--- income statement ---")
say(record["statements"]["income_statement"])
say("")
say("--- equity ---")
say(record["statements"]["equity"])
say("")
say("--- balance sheet ---")
say(record["statements"]["balance_sheet"])
say("")
say("--- cash flow withheld because ---")
say(record["statements"]["cash_flow_withheld_because"])
say("")
say("--- notes ---")
say(record["statements"]["notes"])
say("")
say("--- named missing ---")
for item in (record.get("reading") or {}).get("missing") or []:
    say("   %s" % json.dumps(item))
say("")
say("--- core scalars ---")
for key, value in sorted((record.get("core") or {}).get("scalars", {}).items()):
    say("   %-24s %s" % (key, value))

say("")
say("=" * 78)
say("2. THE SAME TRIAL BALANCE PLUS THE RATIO LINE")
say("=" * 78)
status, record2 = post(TRIAL_BALANCE + "\nAlso compute the liquidity ratios.")
say("status %s  id %s  problem_type %s  computed %s  hidden %s"
    % (status, record2.get("id"), record2.get("problem_type"),
       record2.get("computed"), record2.get("hidden")))
say("--- ratios computed (%d) ---" % len(record2["ratios"]["computed"]))
for row in record2["ratios"]["computed"]:
    say("   %-22s %-10s %s" % (row.get("ratio"), row.get("value"), row.get("definition")))
say("--- named unsupported (%d) ---" % len(record2["ratios"].get("named_unsupported") or []))
for row in record2["ratios"].get("named_unsupported") or []:
    say("   %-22s %s" % (row.get("ratio"), row.get("reason")))

say("")
say("=" * 78)
say("3. THE SAME TRIAL BALANCE WITH AN ERROR IN IT")
say("=" * 78)
broken = TRIAL_BALANCE.replace("Cash 15,900", "Cash 13,300")
request = urllib.request.Request(
    BASE + "/api/cases/statements",
    data=json.dumps({"instruction": broken}).encode("utf-8"),
    headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(request, timeout=120) as response:
        say("status %s" % response.status)
        say(response.read().decode("utf-8")[:1200])
except urllib.error.HTTPError as error:
    say("status %s" % error.code)
    say(error.read().decode("utf-8")[:1600])

with open(OUT, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")
print("\nwritten to", OUT)
