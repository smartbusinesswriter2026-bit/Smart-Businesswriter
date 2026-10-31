"""Drive the intake plan route against the running server and print the real shapes."""
import json
import urllib.request

BASE = "http://127.0.0.1:8012"


def call(method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", "replace"))


status, created = call("POST", "/api/cases/new", {"title": "Plan probe"})
print("=== POST /api/cases/new ->", status)
print("top-level keys:", sorted(created.keys()) if isinstance(created, dict) else type(created))
case_id = created.get("id") or created.get("case_id")
print("case id:", case_id)

brief = ("Evaluate the proposed new plant investment. "
         "Compute the NPV and IRR of the cash flows. "
         "Recommend whether to proceed and explain the risks.")

status, resp = call("POST", "/api/cases/%s/intake/plan" % case_id, {
    "engine_url": BASE,
    "objective": "Decide whether to proceed with the new plant investment.",
    "brief": brief,
    "rubric_items": [],
    "angle": "The company should proceed because the new plant lowers unit cost.",
    "inputs": {},
    "swaps": {},
    "round": 1,
})
print("\n=== POST /api/cases/{id}/intake/plan ->", status)
print("response keys:", sorted(resp.keys()) if isinstance(resp, dict) else type(resp))
print("agent:", json.dumps(resp.get("agent"), indent=1)[:600])
plan = resp.get("plan") or {}
print("\nplan keys:", sorted(plan.keys()))
print("plan.status:", plan.get("status"))
print("plan.notice:", plan.get("notice"))
print("rubric:", json.dumps(plan.get("rubric"), indent=1))
print("item_status:", json.dumps(plan.get("item_status"), indent=1))
print("coverage:", json.dumps(plan.get("coverage"), indent=1))
print("model:", json.dumps(plan.get("model"), indent=1))
print("log:", json.dumps(plan.get("log"), indent=1))
print("gates:", json.dumps(plan.get("gates"), indent=1))
print("angle:", json.dumps(plan.get("angle"), indent=1))
print("uncovered:", json.dumps(plan.get("uncovered"), indent=1))
print("structures:", json.dumps(plan.get("structures"), indent=1)[:1500])
print("unsupported:", json.dumps(plan.get("unsupported"), indent=1)[:1500])
print("questions:", json.dumps(plan.get("questions"), indent=1)[:2500])
print("\n--- analyses (full, first 3) ---")
for a in (plan.get("analyses") or [])[:3]:
    print(json.dumps(a, indent=1))

print("\n=== GET /api/cases/{id}/intake ->")
s2, r2 = call("GET", "/api/cases/%s/intake" % case_id)
print(s2, "keys:", sorted(r2.keys()) if isinstance(r2, dict) else r2)
print("plan is:", type(r2.get("plan")), "plans len:", len(r2.get("plans") or []))

print("\n=== POST /api/cases/{id}/intake/confirm ->")
s3, r3 = call("POST", "/api/cases/%s/intake/confirm" % case_id, {"plan": plan})
print(s3, "keys:", sorted(r3.keys()) if isinstance(r3, dict) else r3)
print("recorded_at:", r3.get("recorded_at"))

print("\n=== POST /api/sessions (a ready analysis) ===")
ready = [a for a in (plan.get("analyses") or []) if a.get("status") == "ready"]
print("ready analyses:", len(ready))
if ready:
    a = ready[0]
    inputs = {}
    print("first ready analysis method:", a["method"], "missing:", a["missing"])
else:
    # supply the missing values for the first analysis and re-plan
    a = (plan.get("analyses") or [])[0]
    print("no ready analysis; first analysis:", a["method"], "missing:", a["missing"])
    print("inputs decl:", json.dumps(a.get("inputs"), indent=1))

with open("D:\SMART BUSINESSWRITER\.uitmp\plan.json", "w", encoding="utf-8") as f:
    json.dump({"case_id": case_id, "plan": plan}, f, indent=1)
print("\nsaved plan to .uitmp/plan.json")
