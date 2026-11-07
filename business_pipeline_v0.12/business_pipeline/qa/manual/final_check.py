import json, base64, urllib.request, zipfile, io, xml.etree.ElementTree as ET
body = b'{"instruction": "Data: Sales 200,000. Required: income statement."}'
req = urllib.request.Request("http://localhost:8021/api/cases/statements", data=body, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
record = json.loads(resp.read())
rid = record["id"]
exp_body = b'{"format": "xlsx"}'
req2 = urllib.request.Request("http://localhost:8021/api/cases/statements/" + rid + "/export", data=exp_body, headers={"Content-Type": "application/json"})
resp2 = urllib.request.urlopen(req2)
data = json.loads(resp2.read())
b = base64.b64decode(data["data"])
with open("C:/Users/Roderick/AppData/Local/Temp/opencode/final_check.xlsx", "wb") as f:
    f.write(b)
print("written", len(b), "bytes")
z = zipfile.ZipFile(io.BytesIO(b))
for name in z.namelist():
    if name.endswith(".xml") or name.endswith(".rels"):
        try:
            ET.fromstring(z.read(name))
        except ET.ParseError as e:
            print("XML ERROR:", name, e)
print("All XML valid")
import openpyxl
wb = openpyxl.load_workbook("C:/Users/Roderick/AppData/Local/Temp/opencode/final_check.xlsx")
print("Sheets:", wb.sheetnames)
for ws in wb.worksheets:
    print("  ", ws.title, "rows:", ws.max_row)
