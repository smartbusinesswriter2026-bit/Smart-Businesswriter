import sys, traceback
sys.path.insert(0, "src")
from bp import methods, statement_plan, schedule_math
from bp.product import statements as S
S.attach_core(build=statement_plan.build, schedules=schedule_math.compute)

TEXT = ("Data — unadjusted trial balance: Cash 10,000 Dr; AR 20,000 Dr; Supplies 3,000 Dr; "
        "Equipment 40,000 Dr; Accumulated depreciation 8,000 Cr; AP 12,000 Cr; Unearned revenue "
        "5,000 Cr; Common stock 30,000 Cr; Retained earnings 6,000 Cr; Service revenue 45,000 Cr; "
        "Salaries expense 28,000 Dr; Rent expense 5,000 Dr.\n"
        "Adjustments: Supplies on hand 1,000; depreciation 4,000; unearned revenue earned 3,000; "
        "accrued salaries 2,000.\n"
        "Required: Journalize adjustments and create adjusted income statement and balance sheet.")

pieces = S.re.split(r"\badjustments?\b\s*[:\-\u2014]?", TEXT, maxsplit=1, flags=S.re.I)
print("pieces:", len(pieces))
tb_text, adj_text = pieces[0], pieces[1]
tb_text = S._split_semicolon_accounts(S._strip_preamble(tb_text))
print("--- TB TEXT ---"); print(tb_text)
rows, skipped = S.parse_rows(tb_text)
print("rows:", len(rows), "skipped:", skipped)
for r in rows:
    print("  ", r["label"], "|", r["written"], "|", S._resolve(r))
try:
    S.preflight_rows(rows)
    print("preflight ok")
except Exception as e:
    print("PREFLIGHT FAILED:", type(e).__name__, e)
chart = S.build_chart(rows)
print("chart:", [(a["code"], a["name"], a["type"], a["line"]) for a in chart])
specs, stated, unread = S._adjustment_specs(adj_text, rows, chart)
print("specs:", specs)
print("stated:", stated)
print("unread:", unread)
print("chart after:", [(a["code"], a["name"], a["type"], a.get("contra"), a.get("section")) for a in chart])


def noisy_build(plan):
    try:
        return statement_plan.build(plan)
    except Exception:
        traceback.print_exc()
        raise


S.attach_core(build=noisy_build, schedules=schedule_math.compute)
try:
    out = S._solve_adjusted_trial_balance(TEXT)
    print("route returned:", None if out is None else out.get("problem_type"))
except Exception:
    traceback.print_exc()
