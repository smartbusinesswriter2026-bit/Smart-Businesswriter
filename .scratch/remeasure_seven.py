"""Re-measure what the statements tile can actually solve, over HTTP.

The same seven shapes the WORKLOG measured on 2026-11-04, posted to the running
workbench with no model configured.  The preamble is the WORKLOG's own wording.
"""
import json
import sys
import time
import urllib.error
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

NARRATIVE = ("Alder Trading opened on 1 January 2025. The owner invested 50,000 cash in the business "
             "for shares on 1 January 2025. The business purchased a delivery van for 30,000 cash on "
             "2 January 2025. It paid 6,000 cash rent on 3 March 2025. It paid 8,000 cash salaries on "
             "31 March 2025.")

ADJUSTMENTS = ("On 1 January 2025 the business bought equipment for 30,000 cash. "
               "The equipment is depreciated at 20% a year; 1,500 of income is still unpaid.")

RATIO_QUESTION = ("Compute the current ratio and the return on assets from the following figures: "
                  "cash 5,000, trade receivables 2,000, inventory 3,000, trade payables 1,500.")

CASH_FLOW = ("Alder Trading opened on 1 January 2025. The owner invested 50,000 cash in the business. "
             "The business sold goods for 90,000 cash during the year and paid 60,000 cash to suppliers "
             "and 12,000 cash in salaries.")

EXAM_PREAMBLE = ("Prepare the income statement for the year ended 31 December 2026 from the following "
                 "trial balance, and show your working.\n"
                 "Cash 18,000\nSales 8,000 Cr\nCapital 10,000 Cr")

EUR_BALANCE = ("The following trial balance was extracted at 31 December 2026.\n"
               "Cash 2,000\nSales 8,000\nCapital 10,000")

CASES = [
    ("a bare trial balance", TRIAL_BALANCE, {}),
    ("a single-year transactions narrative", NARRATIVE, {}),
    ("an adjustments narrative", ADJUSTMENTS, {}),
    ("a ratio question with figures but no trial balance", RATIO_QUESTION, {}),
    ("a cash-flow narrative", CASH_FLOW, {}),
    ("an exam question with a preamble before the figures", EXAM_PREAMBLE, {}),
    ("a trial balance in EUR", EUR_BALANCE, {"currency": "EUR"}),
]


def post(payload):
    request = urllib.request.Request(
        BASE + "/api/cases/statements",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST")
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
            return response.status, body, time.time() - started
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8"), time.time() - started


for label, instruction, extra in CASES:
    payload = {"instruction": instruction}
    payload.update(extra)
    status, body, seconds = post(payload)
    print("=" * 100)
    print("%s  ->  %s  in %.1fs" % (label, status, seconds))
    try:
        data = json.loads(body)
    except ValueError:
        print("   ", body[:400])
        continue
    if status == 201:
        record = data.get("record") or data
        checks = record.get("checks") or []
        ok = sum(1 for c in checks if c.get("ok"))
        na = sum(1 for c in checks if c.get("ok") is None)
        print("    id:", record.get("id"), "solved:", record.get("solved"),
              "type:", record.get("problem_type"), "reading:", (record.get("reading") or {}).get("source"))
        print("    checks:", ok, "ok /", na, "not applicable /", len(checks), "total")
        core = record.get("core") or {}
        print("    net income:", core.get("net_income"), "total assets:", core.get("total_assets"))
        ratios = record.get("ratios") or {}
        print("    ratios computed:", len(ratios.get("computed") or {}),
              "named unsupported:", len(ratios.get("missing") or {}))
        if ratios.get("computed"):
            sample = list((ratios.get("computed") or {}).items())[:2]
            print("    ratio sample:", sample)
        print("    missing:", ((record.get("reading") or {}).get("missing") or [])[:2])
    else:
        print("   ", json.dumps(data)[:600])
