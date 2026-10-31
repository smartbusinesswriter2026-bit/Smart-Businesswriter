"""End-to-end check of the Super Agent: plan, swap, supply a value, run it."""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8012"


def call(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data,
                                     headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


status, case = call("POST", "/api/cases/new", {"title": "Super Agent full path"})
case_id = case["id"]
print("case", case_id)

brief = ("Evaluate the capital expansion. Appraise the investment with discounted cash flows. "
         "Forecast revenue for three years. Recommend a pricing strategy.")
rubric = [
    "Investment appraisal of the expansion using discounted cash flows",
    "Three year forecast of revenue and margin",
    "Strategic recommendation and risks",
]


def plan(inputs=None, swaps=None):
    body = {"engine_url": BASE,
            "objective": "Should Northwind expand into three new cities?",
            "brief": brief, "rubric_items": rubric,
            "angle": "The expansion is worth doing if the downside case holds.",
            "inputs": inputs or {}, "swaps": swaps or {}}
    status, payload = call("POST", "/api/cases/%s/intake/plan" % case_id, body)
    assert status == 200, (status, payload)
    return payload["plan"]


print("\n=== 1. the first plan")
p = plan()
for a in p["analyses"]:
    print("  %-4s %-22s %-12s missing=%s" % (a["id"], a["method"], a["status"], a["missing"]))
for s in p["structures"]:
    print("  %-4s %-22s %s" % (s["id"], s["structure"]["name"][:20], s["status"]))
for u in p["unsupported"]:
    print("  %-4s %-22s %s" % (u["rubric_id"], "-", u["status"]))
print("  item_status:", p["item_status"])
print("  coverage   :", json.dumps(p["coverage"]))
print("  gates      :", [(g["gate"], g["ok"]) for g in p["gates"]])
print("  questions  :", [q["input"] for q in p["questions"]])
print("  alternatives for a1:", [x["method"] for x in p["analyses"][0]["alternatives"]])

print("\n=== 2. swap the first analysis for an alternative")
target = "irr" if "irr" in [x["method"] for x in p["analyses"][0]["alternatives"]] else (
    p["analyses"][0]["alternatives"][0]["method"] if p["analyses"][0]["alternatives"] else None)
swaps = {}
if target:
    swaps = {p["analyses"][0]["rubric_id"]: target}
    p2 = plan(swaps=swaps)
    got = [a["method"] for a in p2["analyses"] if a["rubric_id"] == p["analyses"][0]["rubric_id"]]
    print("  swapped to:", target, "-> now:", got)
    chosen = [a for a in p2["analyses"] if a["method"] == target][0]
    print("  why:", chosen["why"])
    print("  missing now:", chosen["missing"])
else:
    print("  no alternative offered")
    p2 = p

print("\n=== 3. the student supplies a value")
method = p2["analyses"][0]["method"]
missing = p2["analyses"][0]["missing"]
print("  method:", method, "missing:", missing)
if missing:
    supplied = {"cashflows": [-100000, 60000, 60000]}.get(missing[0], "1000")
    inputs = {method: {missing[0]: {"source": "student", "value": supplied}}}
    p3 = plan(inputs=inputs, swaps=swaps)
    a = [x for x in p3["analyses"] if x["method"] == method]
    if a:
        a = a[0]
        print("  after supplying", missing[0], "-> status:", a["status"])
        print("  engine check:", json.dumps(a["engine_check"])[:220])
    print("  remaining questions:", [q["input"] for q in p3["questions"]])
else:
    p3 = p2

print("\n=== 4. confirm the plan")
status, stored = call("POST", "/api/cases/%s/intake/confirm" % case_id, {"plan": p3})
print("  status", status, "recorded_at", stored.get("recorded_at"))

print("\n=== 5. run every ready analysis through the engine")
ready = [a for a in p3["analyses"] if a["status"] == "ready"]
print("  ready analyses:", len(ready))
for a in ready:
    # The plan deliberately carries no values, so the run uses what the
    # student supplied - the same thing the interface keeps.
    supplied = (inputs or {}).get(a["method"], {})
    values = {name: entry["value"] for name, entry in supplied.items()}
    status, session = call("POST", "/api/sessions", {
        "objective": "Should Northwind expand into three new cities?",
        "method": a["method"], "inputs": values})
    print("  session", status, a["method"], "->", session.get("status"))
    if status not in (200, 201):
        print("    create failed", status, session)
        continue
    status, done = call("POST", "/api/sessions/%s/confirm" % session["id"], {})
    if status != 200:
        print("    confirm failed", status, done)
        continue
    delivery = done.get("delivery") or {}
    print("    delivery:", delivery.get("status"), "tier", delivery.get("tier"),
          "artifacts", len(delivery.get("artifacts") or []),
          ("blocked: " + str(delivery.get("blocked_reason"))[:150]) if delivery.get("blocked_reason") else "")
    report = delivery.get("report") or ""
    print("    report:", report[:300].replace("\n", " "))

print("\n=== 6. read the stored plan back")
status, read = call("GET", "/api/cases/%s/intake" % case_id)
print("  status", status, "plans:", len(read["plans"]), "latest rubric items:", len(read["plan"]["rubric"]))
