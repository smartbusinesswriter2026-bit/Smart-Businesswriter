"""Probe 5: the blocked path in detail - what the blocked session and the 400 body carry."""
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


s, sess = call("POST", "/api/sessions", {"objective": "Value the plant.", "method": "npv",
                                         "inputs": {"cashflows": [-1000, 400, 400]}})
print("POST /api/sessions ->", s)
print("session keys:", sorted(sess.keys()))
print("session.status:", sess.get("status"))
d = sess.get("delivery")
print("session.delivery:", json.dumps(d, indent=1)[:800] if d else d)
print("session.work_plan:", json.dumps(sess.get("work_plan"), indent=1)[:600])
s2, body2 = call("POST", "/api/sessions/%s/confirm" % sess["id"], {})
print("\nconfirm ->", s2, json.dumps(body2, indent=1)[:800])
