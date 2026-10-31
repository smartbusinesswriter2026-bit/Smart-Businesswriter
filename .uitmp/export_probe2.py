"""Print the raw plan / draft / export responses of the business-plan route."""
import json
import urllib.error
import urllib.request

base = "http://127.0.0.1:8791"


def post(path, body):
    request = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:300]


status, raw = post("/api/cases/chat", {
    "brief": "A coffee shop selling specialty coffee to university students in Cebu City.",
    "profile": "business_plan", "subject": "entrepreneurship", "level": "shs", "mode": "strict"})
case = json.loads(raw)["id"]
print("plan  ->", post("/api/cases/chat/%s/plan" % case, {}))
print("draft ->", post("/api/cases/chat/%s/draft" % case, {"accepted": []}))
print("export->", post("/api/cases/chat/%s/export" % case, {}))
