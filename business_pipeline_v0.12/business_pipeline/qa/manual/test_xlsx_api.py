import sys, zipfile, io, base64, json, urllib.request
sys.path.insert(0, "src")

body = b'{"instruction": "Data: Sales 200,000; sales returns 5,000. Required: income statement."}'
req = urllib.request.Request("http://localhost:8021/api/cases/statements", data=body, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
record = json.loads(resp.read())
rid = record["id"]

exp_body = b'{"format": "xlsx"}'
req2 = urllib.request.Request("http://localhost:8021/api/cases/statements/" + rid + "/export", data=exp_body, headers={"Content-Type": "application/json"})
resp2 = urllib.request.urlopen(req2)
data = json.loads(resp2.read())
b = base64.b64decode(data["data"])
print("bytes:", len(b))
z = zipfile.ZipFile(io.BytesIO(b))
print("zip test:", z.testzip())
print("names:", z.namelist())
ct = z.read("[Content_Types].xml").decode("utf-8")
print("content types OK:", "worksheet" in ct)
# Check workbook.xml
wb = z.read("xl/workbook.xml").decode("utf-8")
print("workbook has sheets:", "sheet" in wb)
# Check sheet1
s1 = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
print("sheet1 has v= (typed):", "<v>" in s1)
print("sheet1 row count:", s1.count("<row"))
