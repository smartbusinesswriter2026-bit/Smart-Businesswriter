import sys, zipfile, io, re
sys.path.insert(0, "src")
from bp import methods, schedule_math, statement_plan
from bp.product import statements as S, xlsx as X
S.attach_core(build=statement_plan.build, schedules=schedule_math.compute)
text = "Data: Bank statement balance 25,000; book cash balance 22,100; deposits in transit 4,000; outstanding checks 6,000; bank service charge 100; NSF customer check 500; note collected by bank 1,500.\nRequired: Prepare a bank reconciliation, journal entries, and the cash balance to report."
r = S.solve(text)
data = X.render_bytes(r)
z = zipfile.ZipFile(io.BytesIO(data))
wb = z.read("xl/workbook.xml").decode("utf-8")
print("sheet names:", re.findall(r'name="([^"]+)"', wb))
print("sheets:", z.namelist())
