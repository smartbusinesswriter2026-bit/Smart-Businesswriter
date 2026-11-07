import json, base64, urllib.request, zipfile, io, re
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
z = zipfile.ZipFile(io.BytesIO(b))
ct = z.read("[Content_Types].xml").decode("utf-8")
overrides = re.findall(r"sheet\d+\.xml", ct)
print("overrides:", overrides)
print("total overrides:", len(overrides))
wb = z.read("xl/workbook.xml").decode("utf-8")
sheets = re.findall(r'sheetId="(\d+)"', wb)
print("sheets in workbook:", len(sheets))
