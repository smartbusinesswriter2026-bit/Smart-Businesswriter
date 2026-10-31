"""Probe 2: replay the e2e steps 1-6 and inspect what the chart plan sees."""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
PORT = 8792
BASE = "http://127.0.0.1:%d" % PORT


def call(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


env = dict(os.environ)
env["PYTHONPATH"] = os.path.join(REPO, "src")
server = subprocess.Popen([sys.executable, "-m", "bp.server", str(PORT)],
                           cwd=os.path.join(REPO, "src"), env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/api/health", timeout=2)
            break
        except Exception:
            time.sleep(0.5)

    status, case = call("POST", "/api/cases/new", {"title": "probe2"})
    case_id = case["id"]
    csv = "amount\n-100000\n40000\n40000\n40000\n40000\n"
    encoded = base64.b64encode(csv.encode("utf-8")).decode("ascii")
    status, mapped = call("POST", "/api/ingest", {
        "filename": "b2.csv", "content_base64": encoded,
        "map": {"method": "descriptive_stats", "columns": {"values": "amount"}}})
    inputs = dict(mapped["mapped_request"]["inputs"])
    status, session = call("POST", "/api/sessions", {
        "objective": "Summarise the cash flows of the B2 project",
        "method": "descriptive_stats", "currency": "PHP", "inputs": inputs})
    status, delivered = call("POST", "/api/sessions/%s/confirm" % session["id"], {})
    appendix = delivered["delivery"]["appendix"]
    print("appendix keys:", sorted(appendix.keys()))
    print("appendix.reperform keys:", sorted((appendix.get("reperform") or {}).keys()))
    print("appendix.reperform.inputs:", json.dumps((appendix.get("reperform") or {}).get("inputs"))[:200])
    run = {
        "title": "Summarise the cash flows of the B2 project",
        "method": "descriptive_stats",
        "tier": appendix.get("tier", ""),
        "spec_hash": appendix.get("spec_hash", ""),
        "outputs_hash": (appendix.get("reperform") or {}).get("outputs_hash", ""),
        "session": delivered,
        "delivery": {"report": delivered["delivery"]["report"], "appendix": appendix},
        "reperform": appendix.get("reperform") or {},
    }
    print("posted run reperform:", json.dumps(run["reperform"])[:160])
    status, stored = call("POST", "/api/cases/%s/runs" % case_id, run)
    print("store run ->", status)
    print("stored record reperform:", json.dumps(stored.get("reperform"))[:160])
    status, runs = call("GET", "/api/cases/%s/runs" % case_id)
    print("runs on disk:", len(runs["runs"]), "| reperform of run0:",
          json.dumps(runs["runs"][0].get("reperform"))[:160])
    status, plan = call("GET", "/api/cases/%s/charts" % case_id)
    print("PLAN:", json.dumps(plan["charts"]))
finally:
    server.terminate()
    try:
        server.wait(timeout=10)
    except Exception:
        server.kill()
