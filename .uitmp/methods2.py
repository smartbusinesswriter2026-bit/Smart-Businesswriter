import json, urllib.request
with urllib.request.urlopen("http://127.0.0.1:8777/api/methods") as r:
    methods = json.loads(r.read().decode())
for m in methods:
    if m["method_id"] in ("dcf_valuation", "descriptive_stats", "trend_forecast"):
        print("=" * 60)
        print(m["method_id"], "| tier:", m.get("tier"))
        for k, v in (m.get("input_schema") or {}).items():
            print("   %-14s type=%-12s %s" % (k, v.get("type"), v.get("desc", "")))
