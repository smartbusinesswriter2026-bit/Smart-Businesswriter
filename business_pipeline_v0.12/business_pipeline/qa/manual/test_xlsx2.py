import sys, zipfile, io, re
sys.path.insert(0, "src")
from bp import methods, schedule_math, statement_plan
from bp.product import statements as S, xlsx as X
S.attach_core(build=statement_plan.build, schedules=schedule_math.compute)
text = "Data: Sales 200,000; sales returns 5,000; beginning inventory 20,000; purchases 120,000; purchase returns 4,000; freight-in 6,000; ending inventory 25,000; selling expenses 30,000; administrative expenses 20,000; interest expense 3,000; tax rate 25%.\nRequired: Create a multi-step income statement and compute gross margin %."
r = S.solve(text)
data = X.render_bytes(r)
z = zipfile.ZipFile(io.BytesIO(data))
wb = z.read("xl/workbook.xml").decode("utf-8")
print("sheet names:", re.findall(r'name="([^"]+)"', wb))
