import json, base64, urllib.request, zipfile, io
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
print("workbook.xml:")
print(z.read("xl/workbook.xml").decode("utf-8"))
print()
print("workbook.xml.rels:")
print(z.read("xl/_rels/workbook.xml.rels").decode("utf-8"))
