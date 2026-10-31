"""End-to-end check of the Super Agent routes against the running engine."""
import json
import urllib.request

BASE = "http://127.0.0.1:8011"


def call(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data,
                                     headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


print("-- create a case")
status, case = call("POST", "/api/cases/new", {"title": "Super Agent end-to-end"})
print(status, case.get("id"))
case_id = case["id"]

print("\n-- the plan route")
body = {
    "engine_url": BASE,
    "objective": "Should Northwind expand into three new cities?",
    "brief": ("Evaluate the capital expansion. Appraise the investment with discounted cash flows. "
              "Forecast revenue for three years. Recommend a pricing strategy."),
    "angle": "The expansion is worth doing if the downside case holds.",
    "rubric_items": [
        "Investment appraisal of the expansion using discounted cash flows",
        "Three year forecast of revenue and margin",
        "Strategic recommendation and risks",
    ],
    "inputs": {},
}
status, plan = call("POST", "/api/cases/%s/intake/plan" % case_id, body)
print("status", status)
if status != 200:
    print(json.dumps(plan, indent=1))
    raise SystemExit(1)

p = plan["plan"]
print("rubric items      :", len(p["rubric"]))
print("analyses          :", len(p["analyses"]))
for a in p["analyses"]:
    print("   %-10s %-22s %-14s missing=%s" % (a["id"], a["method"], a["status"], a["missing"]))
print("questions         :", len(p["questions"]))
for q in p["questions"]:
    print("   %-28s %s" % (q["input"], q["question"]))
print("gates             :")
for g in p["gates"]:
    print("   %-20s %s  %s" % (g["gate"], "ok" if g["ok"] else "NO", g["detail"]))
print("coverage          :", json.dumps(p["coverage"]))
print("model             :", json.dumps(p["model"]))
print("angle             :", p["angle"]["status"], "-", p["angle"]["note"][:70])
print("engine checks     :")
for a in p["analyses"]:
    print("   %-10s %s" % (a["method"], json.dumps(a.get("engine_check"))))

print("\n-- the confirm route")
status, stored = call("POST", "/api/cases/%s/intake/confirm" % case_id, {"plan": p})
print("status", status, "recorded_at", stored.get("recorded_at"))

print("\n-- read it back")
status, read = call("GET", "/api/cases/%s/intake" % case_id)
print("status", status, "plans:", len(read["plans"]), "latest rubric:", len(read["plan"]["rubric"]))
print("agent config:", json.dumps(read["agent"])[:160])

print("\n-- a refused engine link")
status, refused = call("POST", "/api/cases/%s/intake/plan" % case_id,
                        {"objective": "x", "engine_url": "http://example.com"})
print("status", status, refused)

print("\n-- an empty brief")
status, empty = call("POST", "/api/cases/%s/intake/plan" % case_id,
                      {"objective": "x", "engine_url": BASE, "brief": ""})
print("status", status, empty)
