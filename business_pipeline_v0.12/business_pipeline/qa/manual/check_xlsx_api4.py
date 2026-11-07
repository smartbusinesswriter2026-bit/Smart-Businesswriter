import json, base64, urllib.request
body = b'{"instruction": "Data: Sales 200,000. Required: income statement."}'
req = urllib.request.Request("http://localhost:8021/api/cases/statements", data=body, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
record = json.loads(resp.read())
rid = record["id"]
exp_body = b'{"format": "xlsx"}'
req2 = urllib.request.Request("http://localhost:8021/api/cases/statements/" + rid + "/export", data=exp_body, headers={"Content-Type": "application/json"})
resp2 = urllib.request.urlopen(req2)
data = json.loads(resp2.read())
b64 = data["data"]
print("has newlines:", "\n" in b64)
print("has spaces:", " " in b64)
print("length:", len(b64))
# Try decoding with Python's base64 (same as atob would)
decoded = base64.b64decode(b64)
print("decoded length:", len(decoded))
import zipfile, io
z = zipfile.ZipFile(io.BytesIO(decoded))
print("zip valid:", z.testzip() is None)
