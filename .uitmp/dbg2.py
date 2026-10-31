import json, base64, urllib.request, urllib.error
BASE="http://127.0.0.1:8777"
def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE+path, data=data, headers={"Content-Type":"application/json"}, method=method)
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e: return e.code, e.read().decode()
csv = "amount\n-100000\n40000\n40000\n40000\n40000\n"
enc = base64.b64encode(csv.encode()).decode()
for method in ("dcf_valuation", "descriptive_stats", "trend_forecast"):
    cols = {"cashflows":"amount"} if method=="dcf_valuation" else {"values":"amount"}
    s, m = call("POST","/api/ingest",{"filename":"b2.csv","content_base64":enc,"map":{"method":method,"columns":cols}})
    print(method, "->", s, str(m)[:300])
