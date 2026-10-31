"""Probe 2: supply an input, re-plan, swap, then run a ready analysis."""
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


status, created = call("POST", "/api/cases/new", {"title": "Plan probe 2"})
case_id = created["id"]
print("case:", case_id)

req = {
    "engine_url": BASE,
    "objective": "Decide whether to proceed with the new plant investment.",
    "brief": "Compute the NPV and IRR of the cash flows for the new plant.",
    "rubric_items": ["Compute the NPV of the project", "Compute the IRR of the project"],
    "angle": "",
    "inputs": {},
    "swaps": {},
    "round": 1,
}
s, resp = call("POST", "/api/cases/%s/intake/plan" % case_id, req)
plan = resp["plan"]
print("plan status:", s, "analyses:", len(plan["analyses"]))
for a in plan["analyses"]:
    print("  ", a["id"], a["rubric_id"], a["method"], a["status"], "missing:", a["missing"],
          "alts:", [x["method"] for x in a["alternatives"]])

# --- supply the missing inputs the way the panel will ---
req["inputs"] = {"irr": {"cashflows": {"source": "student", "value": [-1000, 400, 400, 400, 200]}}}
s, resp = call("POST", "/api/cases/%s/intake/plan" % case_id, req)
plan = resp["plan"]
print("\nafter supplying cashflows:")
print("coverage:", json.dumps(plan["coverage"]))
print("item_status:", json.dumps(plan["item_status"]))
for a in plan["analyses"]:
    print("  ", a["id"], a["rubric_id"], a["method"], a["status"], "missing:", a["missing"],
          "engine_check:", json.dumps(a.get("engine_check")))

# --- swap ---
req["swaps"] = {"r2": "npv"}
s, resp = call("POST", "/api/cases/%s/intake/plan" % case_id, req)
plan2 = resp["plan"]
print("\nafter swap r2->npv:")
for a in plan2["analyses"]:
    print("  ", a["id"], a["rubric_id"], a["method"], a["status"], "why:", a["why"], "alts:", a["alternatives"])
print("item_status:", json.dumps(plan2["item_status"]))

# --- a swap the engine does not declare (should be ignored) ---
req["swaps"] = {"r2": "not_a_real_method"}
s, resp = call("POST", "/api/cases/%s/intake/plan" % case_id, req)
plan3 = resp["plan"]
print("\nafter bogus swap r2->not_a_real_method:")
for a in plan3["analyses"]:
    print("  ", a["id"], a["rubric_id"], a["method"], a["status"])

# --- run a ready analysis ---
ready = [a for a in plan["analyses"] if a["status"] == "ready"]
print("\nready count:", len(ready))
if ready:
    a = ready[0]
    method = a["method"]
    flat = {}
    for name, rec in (req["inputs"].get(method) or {}).items():
        flat[name] = rec["value"]
    print("session inputs:", flat)
    s, sess = call("POST", "/api/sessions", {"objective": req["objective"], "method": method, "inputs": flat})
    print("POST /api/sessions ->", s, "keys:", sorted(sess.keys()))
    print("session id:", sess.get("id"), "status:", sess.get("status"))
    s2, sess2 = call("POST", "/api/sessions/%s/confirm" % sess["id"], {})
    print("POST /api/sessions/{id}/confirm ->", s2, "keys:", sorted(sess2.keys()))
    d = sess2.get("delivery") or {}
    print("delivery keys:", sorted(d.keys()))
    print("delivery.status:", d.get("status"), "tier:", d.get("tier"))
    print("blocked_reason:", d.get("blocked_reason"))
    print("artifacts type:", type(d.get("artifacts")), "len:", len(d.get("artifacts") or []))
    print("report head:", (d.get("report") or "")[:300])
    print("appendix keys:", sorted((d.get("appendix") or {}).keys()))
