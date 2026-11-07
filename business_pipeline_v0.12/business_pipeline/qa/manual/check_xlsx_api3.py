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
print("data field length:", len(data["data"]))
print("mime:", data["mime"])
print("filename:", data["filename"])
