"""Probe 4: what exactly is in delivery.appendix.artifacts, and a blocked delivery."""
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


# a run that should be blocked: npv without a rate
s, sess = call("POST", "/api/sessions", {"objective": "Value the plant.", "method": "npv",
                                         "inputs": {"cashflows": [-1000, 400, 400]}})
print("session:", s, sess.get("status"))
s2, sess2 = call("POST", "/api/sessions/%s/confirm" % sess["id"], {})
print("confirm:", s2, "session status:", sess2.get("status"))
d = sess2.get("delivery") or {}
print("delivery keys:", sorted(d.keys()))
print("delivery.status:", d.get("status"))
print("delivery.tier:", d.get("tier"))
print("delivery.blocked_reason:", repr(d.get("blocked_reason")))
ap = d.get("appendix") or {}
arts = ap.get("artifacts")
print("appendix.artifacts type:", type(arts).__name__, "len:", len(arts) if arts else 0)
if arts:
    print("first artifact keys:", sorted(arts[0].keys()) if isinstance(arts[0], dict) else type(arts[0]))
    print(json.dumps(arts[0], indent=1)[:700])
print("top-level delivery.artifacts present:", "artifacts" in d)
print("honesty:", json.dumps(ap.get("honesty"), indent=1)[:400])

# a good run's artifacts
s, sess = call("POST", "/api/sessions", {"objective": "Value the plant.", "method": "irr",
                                         "inputs": {"cashflows": [-1000, 400, 400, 400, 200]}})
s2, sess2 = call("POST", "/api/sessions/%s/confirm" % sess["id"], {})
d2 = sess2.get("delivery") or {}
ap2 = d2.get("appendix") or {}
arts2 = ap2.get("artifacts")
print("\nirr delivery.status:", d2.get("status"), "tier:", d2.get("tier"),
      "blocked_reason:", repr(d2.get("blocked_reason")))
print("irr appendix.artifacts:", type(arts2).__name__, "len:", len(arts2) if arts2 else 0)
if arts2:
    print("irr first artifact keys:", sorted(arts2[0].keys()) if isinstance(arts2[0], dict) else type(arts2[0]))
    print(json.dumps(arts2[0], indent=1)[:900])
print("delivery keys again:", sorted(d2.keys()))
