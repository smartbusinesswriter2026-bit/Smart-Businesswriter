import sys, traceback, json
sys.path.insert(0, "src")
from bp import methods, statement_plan, schedule_math
from bp.product import statements as S
S.attach_core(build=statement_plan.build, schedules=schedule_math.compute)
print("CORE:", sorted(S._CORE))

import re
TEXT = ("Data — unadjusted trial balance: Cash 10,000 Dr; AR 20,000 Dr; Supplies 3,000 Dr; "
        "Equipment 40,000 Dr; Accumulated depreciation 8,000 Cr; AP 12,000 Cr; Unearned revenue "
        "5,000 Cr; Common stock 30,000 Cr; Retained earnings 6,000 Cr; Service revenue 45,000 Cr; "
        "Salaries expense 28,000 Dr; Rent expense 5,000 Dr.\n"
        "Adjustments: Supplies on hand 1,000; depreciation 4,000; unearned revenue earned 3,000; "
        "accrued salaries 2,000.\n"
        "Required: Journalize adjustments and create adjusted income statement and balance sheet.")

pieces = re.split(r"\badjustments?\b\s*[:\-\u2014]?", TEXT, maxsplit=1, flags=re.I)
tb_text, adj_text = pieces[0], pieces[1]
tb_text = S._split_semicolon_accounts(S._strip_preamble(tb_text))
rows, skipped = S.parse_rows(tb_text)
chart = S.build_chart(rows)
specs, stated, unread = S._adjustment_specs(adj_text, rows, chart)
period = S.period_of(TEXT)[0]
places = max([2] + [S._decimals(r["written"]) for r in rows])
print("period:", period, "places:", places)

lines = []
for r in rows:
    side, amount = S._resolve(r)
    lines.append({"account": r["code"], side: amount})
entries = [{"date": period["end"], "description": "the unadjusted trial balance as given",
            "aggregate": True, "lines": lines}]
for e in stated:
    entries.append({"date": e.get("date") or period["end"], "description": e["description"],
                    "lines": e["lines"]})
for s in specs:
    s.setdefault("date", period["end"])
print("entries:", json.dumps(entries, indent=1, default=str))

plan = {"period": period, "currency": "USD", "framework": "US_GAAP", "places": places,
        "policy": {"rounding": "half_up", "inventory_system": "periodic",
                   "depreciation": {"method": "straight_line", "convention": "pro_rata"},
                   "explicitly_stated": []},
        "prior_closing": {}, "opening": [], "entries": entries,
        "adjustments": specs, "schedules": [],
        "chart": [{k: v for k, v in a.items() if k not in ("quote", "synthesised")} for a in chart],
        "problem_type": "trial_balance"}
try:
    result = statement_plan.build(plan)
    print("BUILD OK")
except Exception:
    traceback.print_exc()
