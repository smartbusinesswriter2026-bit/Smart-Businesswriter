"""Probe 3: matchable rubric, supply the input, swap, run."""
import json
import urllib.request
import urllib.error

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


_, created = call("POST", "/api/cases/new", {"title": "Plan probe 3"})
case_id = created["id"]
print("case:", case_id)

req = {
    "engine_url": BASE,
    "objective": "Decide whether to proceed with the new plant investment.",
    "brief": "Compute the NPV and IRR of the cash flows for the new plant.",
    "rubric_items": ["Compute the NPV and IRR of the cash flows"],
    "angle": "The company should proceed because the new plant lowers unit cost.",
    "inputs": {},
    "swaps": {},
    "round": 1,
}
s, resp = call("POST", "/api/cases/%s/intake/plan" % case_id, req)
plan = resp["plan"]
print("plan:", s, "analyses:", len(plan["analyses"]))
for a in plan["analyses"]:
    print("  ", a["id"], a["rubric_id"], a["method"], a["status"], "missing:", a["missing"],
          "alts:", [x["method"] for x in a["alternatives"]], "tier:", a["tier"], "cat:", a["category"])

# supply the input as the panel will
req["inputs"] = {"irr": {"cashflows": {"source": "student", "value": [-1000, 400, 400, 400, 200]}}}
s, resp = call("POST", "/api/cases/%s/intake/plan" % case_id, req)
plan = resp["plan"]
print("\nafter supplying cashflows: coverage:", json.dumps(plan["coverage"]))
print("item_status:", json.dumps(plan["item_status"]))
for a in plan["analyses"]:
    print("  ", a["id"], a["method"], a["status"], "missing:", a["missing"],
          "engine_check:", json.dumps(a.get("engine_check")))
    for i in a["inputs"]:
        print("      input:", json.dumps(i))

# swap to npv (a declared alternative)
req["swaps"] = {"r1": "npv"}
s, resp = call("POST", "/api/cases/%s/intake/plan" % case_id, req)
sw = resp["plan"]
print("\nafter swap r1->npv:")
for a in sw["analyses"]:
    print("  ", a["id"], a["rubric_id"], a["method"], a["status"], "missing:", a["missing"], "why:", a["why"])

# bogus swap
req["swaps"] = {"r1": "not_a_real_method"}
s, resp = call("POST", "/api/cases/%s/intake/plan" % case_id, req)
bg = resp["plan"]
print("\nafter bogus swap:", [(a["rubric_id"], a["method"]) for a in bg["analyses"]])

# run the ready analysis from the supplied-input plan
ready = [a for a in plan["analyses"] if a["status"] == "ready"]
print("\nready:", [(a["id"], a["method"]) for a in ready])
if ready:
    a = ready[0]
    flat = {n: rec["value"] for n, rec in req["inputs"].get(a["method"], {}).items()}
    print("flat inputs:", flat)
    s, sess = call("POST", "/api/sessions", {"objective": req["objective"], "method": a["method"], "inputs": flat})
    print("POST /api/sessions ->", s, "id:", sess.get("id"), "status:", sess.get("status"))
    s2, sess2 = call("POST", "/api/sessions/%s/confirm" % sess["id"], {})
    print("confirm ->", s2, "status:", sess2.get("status"))
    d = sess2.get("delivery") or {}
    print("delivery keys:", sorted(d.keys()))
    print("delivery.status:", d.get("status"), "| tier:", d.get("tier"), "| blocked_reason:", d.get("blocked_reason"))
    arts = d.get("artifacts")
    print("artifacts type:", type(arts).__name__, "len:", len(arts) if arts else 0)
    print("report head:", repr((d.get("report") or "")[:200]))
    print("appendix keys:", sorted((d.get("appendix") or {}).keys()))
    # confirm the plan on the case
    s3, rec = call("POST", "/api/cases/%s/intake/confirm" % case_id, {"plan": plan})
    print("intake confirm ->", s3, "recorded_at:", rec.get("recorded_at"))
    s4, r4 = call("GET", "/api/cases/%s/intake" % case_id)
    print("GET intake ->", s4, "plan?", bool(r4.get("plan")), "plans:", len(r4.get("plans") or []))
