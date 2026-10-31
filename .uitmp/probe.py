"""Probe: start the server the way the e2e does and ask for the chart plan."""
import json
import os
import subprocess
import sys
import time
import urllib.request

REPO = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
PORT = 8791
BASE = "http://127.0.0.1:%d" % PORT

env = dict(os.environ)
env["PYTHONPATH"] = os.path.join(REPO, "src")
env["BP_CASES_DIR"] = r"D:\SMART BUSINESSWRITER\.uitmp\cases"
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
    for path in ("/api/cases", "/api/cases/2d78bc03dbb5/charts",
                 "/api/cases/2d78bc03dbb5/charts?run_index=0",
                 "/api/cases/2d78bc03dbb5/charts?run_index=1"):
        with urllib.request.urlopen(BASE + path, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if path == "/api/cases":
            print(path, "->", [c["id"] for c in payload["cases"]])
        else:
            print(path, "->", json.dumps(payload["charts"]))
finally:
    server.terminate()
    try:
        server.wait(timeout=10)
    except Exception:
        server.kill()
