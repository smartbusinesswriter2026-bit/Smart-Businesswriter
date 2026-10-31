"""End-to-end check of the case-first surface against the owner's own material.

Nothing here is mocked: every call goes over HTTP to a server started for this
run, and the case study is the owner's own file from TESTS/INITIAL TEST.

The numbers are checked against an **independent** calculation made here, in
this file, under the timing convention the method declares:

* `npv` (T1) discounts the first cash flow at t=0 - it is the method for the
  owner's question, because the outlay is made today;
* `dcf_valuation` (T2) discounts every flow from t=1, so its answer is
  legitimately lower for the same cash flows.  Both are checked, and the
  difference is reported rather than hidden.

The server is started and stopped by this script, so the run is reproducible.
"""

import base64
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

REPO = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
OWNER = r"D:\SMART BUSINESSWRITER\TESTS\INITIAL TEST"
PORT = 8777
BASE = "http://127.0.0.1:%d" % PORT
LOG = io.open(r"D:\SMART BUSINESSWRITER\.uitmp\e2e.log", "w", encoding="utf-8")


def say(line):
    LOG.write(line + "\n")
    LOG.flush()


def call(method, path, body=None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        try:
            return error.code, json.loads(payload)
        except ValueError:
            return error.code, payload


ok = True


def check(label, condition, detail=""):
    global ok
    ok = ok and bool(condition)
    say("%s %s %s" % ("PASS" if condition else "FAIL", label, detail))


def start_server(cases_dir):
    # A server left running on the port would answer these calls with old code,
    # which is exactly how a check can pass against the wrong build.  Refuse.
    probe = socket.socket()
    try:
        probe.bind(("127.0.0.1", PORT))
    except OSError:
        probe.close()
        raise SystemExit("port %d is already in use: stop that server first, or this "
                         "run would test someone else's build" % PORT)
    probe.close()
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(REPO, "src")
    env["BP_CASES_DIR"] = cases_dir
    process = subprocess.Popen([sys.executable, "-m", "bp.server", str(PORT)],
                               cwd=os.path.join(REPO, "src"), env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(120):
        if process.poll() is not None:
            raise SystemExit("the server did not start: %s"
                             % process.stdout.read().decode("utf-8", "replace")[-800:])
        try:
            with urllib.request.urlopen(BASE + "/api/health", timeout=2) as response:
                if response.status == 200:
                    return process
        except Exception:
            time.sleep(0.5)
    raise SystemExit("the server did not become healthy")


# -- the owner's numbers, computed here, independently of the product --------

def npv_at_zero(rate, cashflows):
    """The value of a cash flow series whose first flow happens today."""
    total = 0.0
    for index, flow in enumerate(cashflows):
        total += float(flow) / ((1.0 + rate) ** index)
    return total


def npv_at_one(rate, cashflows):
    """The value of a cash flow series whose first flow is one period away."""
    total = 0.0
    for index, flow in enumerate(cashflows):
        total += float(flow) / ((1.0 + rate) ** (index + 1))
    return total


def close(left, right):
    return abs(float(left) - float(right)) <= 0.01


def main():
    cases_dir = tempfile.mkdtemp(prefix="bp-e2e-", dir=r"D:\SMART BUSINESSWRITER\.uitmp")
    server = start_server(cases_dir)
    try:
        run_checks()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:
            server.kill()
        LOG.close()
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def run_checks():
    # 1. a case that exists before anything is run
    status, case = call("POST", "/api/cases/new", {"title": "Owner INITIAL TEST - B2 NPV"})
    check("a case is created before any run", status == 201 and case["shell"], status)
    case_id = case["id"]
    say("case id: %s" % case_id)

    # 2. the owner's own case study is attached to it
    with open(os.path.join(OWNER, "1.docx"), "rb") as handle:
        data = handle.read()
    chunks = [data[i:i + 48 * 1024] for i in range(0, len(data), 48 * 1024)]
    record = None
    for index, piece in enumerate(chunks):
        status, record = call("POST", "/api/cases/%s/documents" % case_id, {
            "filename": "1.docx", "chunk_index": index, "total_chunks": len(chunks),
            "data": base64.b64encode(piece).decode("ascii")})
    check("the owner's 1.docx is attached", status == 201, status)
    say("document kind=%s provenance=%s chars=%s" % (
        record.get("kind"), record.get("provenance"), record.get("text_chars")))

    status, view = call("GET", "/api/cases/%s/workspace" % case_id)
    text = view["document_texts"].get("1.docx", "")
    check("the case study text is kept with the case", "initial outlay" in text and "100,000" in text)
    check("the owner's B2 question survives the extraction",
          "40,000 per year for 4 years" in text and "10%" in text)
    check("the case is still a shell before its first run", view["shell"] is True)

    # 3. the spreadsheet of problem B2
    csv = "amount\n-100000\n40000\n40000\n40000\n40000\n"
    encoded = base64.b64encode(csv.encode("utf-8")).decode("ascii")
    status, table = call("POST", "/api/ingest", {"filename": "b2.csv", "content_base64": encoded})
    check("the spreadsheet is read by the ingester", status == 200 and table["table"]["n_rows"] == 5, status)

    status, attached = call("POST", "/api/cases/%s/data-files" % case_id, {
        "filename": "b2.csv", "table": table["table"], "sha256": table["table"]["sha256"]})
    check("the spreadsheet is attached to the case", status == 201, status)

    # 4. its columns become the inputs of a run
    status, mapped = call("POST", "/api/ingest", {
        "filename": "b2.csv", "content_base64": encoded,
        "map": {"method": "descriptive_stats", "columns": {"values": "amount"}}})
    check("the columns map to the method inputs",
          status == 200 and "values" in mapped["mapped_request"]["inputs"], status)
    say("mapped: %s" % json.dumps(mapped["mapped_request"]["inputs"]))

    inputs = dict(mapped["mapped_request"]["inputs"])
    status, session = call("POST", "/api/sessions", {
        "objective": "Summarise the cash flows of the B2 project",
        "method": "descriptive_stats", "currency": "PHP", "inputs": inputs})
    check("the session is created from the mapped inputs", status == 201, status)

    status, delivered = call("POST", "/api/sessions/%s/confirm" % session["id"], {})
    check("the run is delivered", status == 200 and delivered["delivery"]["status"] == "delivered", status)

    # 5. the run belongs to the case
    appendix = delivered["delivery"]["appendix"]
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
    status, stored = call("POST", "/api/cases/%s/runs" % case_id, run)
    check("the run is attached to the case", status == 201, status)

    status, runs = call("GET", "/api/cases/%s/runs" % case_id)
    check("the case owns its run", status == 200 and len(runs["runs"]) == 1, status)

    status, view = call("GET", "/api/cases/%s/workspace" % case_id)
    check("the case is no longer a shell", view["shell"] is False)

    # 6. the charts of the run are drawn by the server
    status, plan = call("GET", "/api/cases/%s/charts" % case_id)
    check("the case owns a chart plan", status == 200 and plan["charts"], status)
    say("chart plan: %s" % json.dumps(plan["charts"]))

    drawn = 0
    for spec in plan["charts"]:
        if spec.get("kind") == "table":
            continue
        status, rendered = call("POST", "/api/cases/%s/render" % case_id, {"chart": spec, "run_index": 0})
        if status == 200 and "<svg" in rendered["svg"]:
            drawn += 1
            say("chart %r drawn, %d bytes" % (spec.get("title"), len(rendered["svg"])))
    check("the charts are drawn by the server", drawn >= 1, "%d drawn" % drawn)

    # 7. the owner's question, answered by the method that declares t=0
    cashflows = ["-100000", "40000", "40000", "40000", "40000"]
    status, session2 = call("POST", "/api/sessions", {
        "objective": "Should we invest in the B2 project?",
        "method": "npv", "currency": "PHP",
        "inputs": {"rate": "0.10", "cashflows": cashflows}})
    check("the second session is created", status == 201, status)
    status, delivered2 = call("POST", "/api/sessions/%s/confirm" % session2["id"], {})
    check("the second run is delivered", status == 200 and delivered2["delivery"]["status"] == "delivered", status)

    appendix2 = delivered2["delivery"]["appendix"]
    run2 = {
        "title": "Should we invest in the B2 project?",
        "method": "npv",
        "tier": appendix2.get("tier", ""),
        "spec_hash": appendix2.get("spec_hash", ""),
        "outputs_hash": (appendix2.get("reperform") or {}).get("outputs_hash", ""),
        "session": delivered2,
        "delivery": {"report": delivered2["delivery"]["report"], "appendix": appendix2},
        "reperform": appendix2.get("reperform") or {},
    }
    status, stored2 = call("POST", "/api/cases/%s/runs" % case_id, run2)
    check("the second run is attached to the same case", status == 201, status)

    status, runs = call("GET", "/api/cases/%s/runs" % case_id)
    check("the case now owns two runs", len(runs["runs"]) == 2, len(runs["runs"]))
    check("the runs keep their order", [r["run_index"] for r in runs["runs"]] == [0, 1])

    # 8. the recorded NPV is the one an independent calculation gives
    outputs = (appendix2.get("reperform") or {}).get("outputs", {})
    say("recorded outputs of the NPV run: %s" % json.dumps(outputs))
    expected = npv_at_zero(0.10, cashflows)
    say("expected NPV under the declared t=0 convention: %.2f" % expected)
    recorded = outputs.get("npv", "")
    check("the recorded NPV matches an independent calculation",
          close(recorded, expected), "recorded=%s expected=%.2f" % (recorded, expected))
    report = delivered2["delivery"]["report"]
    check("the delivered report shows the computed NPV", "26,794.62" in report,
          report.strip()[:120])
    check("the recorded decision follows from a positive NPV",
          "clears the hurdle" in report and float(recorded) > 0, recorded)

    # 9. the other valuation method, with its own declared convention
    status, session3 = call("POST", "/api/sessions", {
        "objective": "What is the enterprise value of the B2 project?",
        "method": "dcf_valuation", "currency": "PHP",
        "inputs": {"cashflows": cashflows, "discount_rate": "0.10"}})
    status, delivered3 = call("POST", "/api/sessions/%s/confirm" % session3["id"], {})
    check("the third run is delivered", status == 200 and delivered3["delivery"]["status"] == "delivered", status)
    outputs3 = ((delivered3["delivery"]["appendix"].get("reperform") or {}).get("outputs") or {})
    say("recorded outputs of the DCF run: %s" % json.dumps(outputs3))
    expected3 = npv_at_one(0.10, cashflows)
    say("expected enterprise value under the declared t=1 convention: %.2f" % expected3)
    recorded3 = outputs3.get("enterprise_value", "")
    check("the recorded enterprise value matches an independent calculation",
          close(recorded3, expected3), "recorded=%s expected=%.2f" % (recorded3, expected3))
    check("the two methods differ because their declared conventions differ",
          not close(recorded, recorded3), "npv=%s dcf=%s" % (recorded, recorded3))

    # 10. each run of the case has its own chart plan
    status, plan0 = call("GET", "/api/cases/%s/charts?run_index=0" % case_id)
    status, plan1 = call("GET", "/api/cases/%s/charts?run_index=1" % case_id)
    check("each run of the case has its own chart plan", plan0["charts"] != plan1["charts"])
    status, rendered0 = call("POST", "/api/cases/%s/render" % case_id, {
        "chart": {"kind": "bar", "title": "Recorded results",
                  "series": [{"label": "Mean", "artifact": "mean"}]}, "run_index": 0})
    check("the first run charts on its own", status == 200, status)

    # 11. the assistant: the contract the button must use
    status, payload = call("POST", "/api/assist", {"task": "challenge", "request": {}})
    check("the old broken assistant call never reaches a provider",
          status == 503 and "not configured" in str(payload.get("error", "")), "%s %s" % (status, payload))
    status, payload = call("POST", "/api/assist", {"task": "facts", "consent": True, "case_text": text})
    check("the corrected assistant call is refused honestly when no provider is set",
          status == 503 and "not configured" in str(payload.get("error", "")), "%s %s" % (status, payload))
    say("note: the server-side consent refusal is covered by the frozen suite (tests/test_assist.py)")

    # 12. the page the browser gets
    with urllib.request.urlopen(BASE + "/") as response:
        page = response.read().decode("utf-8")
    for needle in ("Draft work plan", "Account mapping", "Download financial statements",
                   "Assistant (optional)", "Challenge my analysis", "Ingest file",
                   "Data ingestion (structured files)", "no PDF text extraction or OCR",
                   "References (optional)", "Retrieval audit"):
        check("the served page carries %r" % needle, needle in page)
    for needle in ('task: "facts"', 'task: "alternatives"', 'task: "critique"', "consent: true"):
        check("the served page calls the assistant with %r" % needle, needle in page)
    check("the served page no longer calls the broken assistant task", 'task: "challenge"' not in page)
    for needle in ("/api/cases/", "/workspace", "/documents", "/data-files", "/arguments", "/render"):
        check("the served page uses the case route %r" % needle, needle in page)
    check("the hero no longer says 'To be supplied'", "To be supplied" not in page)


if __name__ == "__main__":
    sys.exit(main())
