import json, urllib.request
with urllib.request.urlopen("http://127.0.0.1:8777/api/methods") as r:
    methods = json.loads(r.read().decode())
for m in methods:
    if m["method_id"] == "descriptive_stats":
        print(json.dumps(m, indent=1)[:1200])
