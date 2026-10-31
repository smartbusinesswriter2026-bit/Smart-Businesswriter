"""Drive the subject rail end to end against the running server (stdlib only)."""
import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8013"


def call(method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode("utf-8"))


status, presets = call("GET", "/api/presets")
print("presets:", status, type(presets).__name__, list(presets)[:3] if isinstance(presets, dict) else "")
npv = presets["npv"]
print("npv preset keys:", list(npv))

status, case = call("POST", "/api/cases/new", {"title": "Verification case - subject rail"})
print("new case:", status, case.get("id"), "runs:", len(case.get("runs", [])))
case_id = case["id"]

status, session = call("POST", "/api/sessions", {
    "objective": "Check the subject rail end to end",
    "method": npv.get("method", "npv"),
    "inputs": npv["inputs"],
})
print("session:", status, session.get("id"), session.get("status"))
sid = session["id"]

status, session = call("POST", "/api/sessions/%s/confirm" % sid, {})
print("confirm:", status, session.get("status"), session.get("delivery", {}).get("status"))
delivery = session["delivery"]
ap = delivery["appendix"]
run = {
    "title": "NPV run",
    "method": ap["method"]["id"],
    "tier": ap.get("tier", ""),
    "spec_hash": ap.get("spec_hash", ""),
    "outputs_hash": (ap.get("reperform") or {}).get("outputs_hash", ""),
    "session": session,
    "delivery": {"report": delivery["report"], "appendix": ap},
    "reperform": ap.get("reperform") or {},
}
status, stored = call("POST", "/api/cases/%s/runs" % case_id, run)
print("store run:", status, "runs:", len(stored.get("runs", [])))

status, ws = call("GET", "/api/cases/%s/workspace" % case_id)
print("workspace:", status, "runs:", len(ws.get("runs", [])),
      "methods:", [r.get("method") for r in ws.get("runs", [])])

status, finance = call("GET", "/api/cases?subject=finance")
print("finance filter:", status, "contains:", case_id in [c["id"] for c in finance["cases"]])
status, marketing = call("GET", "/api/cases?subject=marketing")
print("marketing filter:", status, "contains:", case_id in [c["id"] for c in marketing["cases"]])

status, charts = call("GET", "/api/cases/%s/charts" % case_id)
print("charts:", status, "specs:", len(charts.get("charts", [])),
      [c.get("kind") for c in charts.get("charts", [])])
spec = charts["charts"][0]
status, svg = call("POST", "/api/cases/%s/render" % case_id, {"chart": spec})
print("render chart:", status, "svg bytes:", len(svg.get("svg", "")))

# the artifact value the engine delivered, copied verbatim into the run
rows = ap.get("artifacts") or []
print("delivered artifact rows:", len(rows), "report mentions npv:", "NPV" in delivery["report"])

status, deleted = call("DELETE", "/api/cases/%s" % case_id)
print("cleanup:", status, deleted)
