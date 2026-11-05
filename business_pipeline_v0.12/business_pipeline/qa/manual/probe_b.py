import sys
sys.path.insert(0, "src")
from bp import methods, schedule_math, statement_plan
from bp.product import statements as S, schedules
S.attach_core(build=statement_plan.build, schedules=schedule_math.compute)
B = "Data: Current assets 50,000; inventory 20,000; current liabilities 25,000; total assets 150,000; total liabilities 90,000; equity 60,000; sales 300,000; COGS 180,000; net income 30,000; accounts receivable 25,000.\nRequired: Compute current ratio, quick ratio, debt ratio, gross margin, net margin, ROA, ROE, asset turnover, receivables turnover, and days sales outstanding."
kind = schedules.detect(B)
print("kind:", kind)
out = schedules.run(kind, B, schedule_math.compute)
print("checks failed:", [c for c in out["checks"] if not c[1]])
print("sections:", [s["title"] for s in out["sections"]])
r = S._solve_schedule(kind, B)
print("route returned:", r is None)
