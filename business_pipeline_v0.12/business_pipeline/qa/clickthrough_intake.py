"""Live click-through of the three new file legs, against a running workbench (port 8001).

It walks the exact routes the page calls, in the order a student would:

  1. attach a .txt instruction      POST /api/intake               -> stored
  2. use it as the instruction      POST /api/intake/{id}/brief    -> text, unverified
  3. start the analysis             POST /api/sessions             -> awaiting confirmation
                                    POST /api/sessions/{id}/confirm -> delivered
  4. attach a .bib source list      POST /api/intake/{id}/sources  -> entries + citations
  5. attach a .csv dataset          POST /api/ingest (with map)    -> mapped request
                                    POST /api/sessions from it      -> delivered, provenance sourced

Writes `qa/evidence/intake/clickthrough.json` and a Markdown summary.

Usage:  PYTHONPATH=src python qa/clickthrough_intake.py http://127.0.0.1:8001
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

INSTRUCTION = (b"Compare the two expansion options for the bakery counter and recommend one. "
               b"The decision is whether to add seating this year.")
BIB = b"""@article{a1, author = {Smith, J.}, title = {Retail expansion}, year = {2019}, doi = {10.1/xyz}}
@book{b1, author = {Jones, K.}, title = {Counter operations}, year = {2021}}
"""
CSV = b"name,score\nAda,10\nBo,12.5\nCy,9\n"


def call(base, path, payload=None, method=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(base + path, data=data,
                                     method=method or ("POST" if data else "GET"))
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def upload(base, filename, raw, role=None):
    body = {"filename": filename, "content_base64": base64.b64encode(raw).decode()}
    if role:
        body["role"] = role
    return call(base, "/api/intake", body)


def main(argv):
    base = (argv[1] if len(argv) > 1 else "http://127.0.0.1:8001").rstrip("/")
    out_dir = os.path.join("qa", "evidence", "intake")
    os.makedirs(out_dir, exist_ok=True)
    rows, failures = [], []

    def check(label, ok, detail=""):
        rows.append({"step": label, "ok": bool(ok), "detail": detail})
        print("%s  %-46s %s" % ("PASS" if ok else "FAIL", label, detail))
        if not ok:
            failures.append(label)

    status, record = upload(base, "instructions.txt", INSTRUCTION, role="brief")
    check("attach an instruction file", status == 201 and record.get("kind") == "structured",
          "%s %s" % (status, record.get("kind")))
    brief_id = record.get("id")

    status, used = call(base, "/api/intake/%s/brief" % brief_id, {})
    text = (used or {}).get("text") or ""
    check("use it as the instruction", status == 200 and used.get("unverified") is True
          and "bakery counter" in text, "%s chars=%s" % (status, used.get("chars")))
    check("the instruction is labelled unverified", used.get("unverified") is True,
          str(used.get("note"))[:70])

    status, created = call(base, "/api/sessions",
                           {"objective": text, "method": "npv", "currency": "USD",
                            "inputs": {"rate": "0.10",
                                       "cashflows": ["-1000", "400", "400", "400"]}})
    planned = (created or {}).get("status")
    status2, confirmed = call(base, "/api/sessions/%s/confirm" % created.get("id"), {})
    report = ((confirmed or {}).get("delivery") or {}).get("report") or ""
    check("the paper runs from the instruction text",
          planned == "awaiting_confirmation" and status2 == 200
          and confirmed.get("status") == "delivered" and "{{" not in report,
          "%s -> %s, %d chars" % (planned, confirmed.get("status"), len(report)))

    status, record = upload(base, "refs.bib", BIB)
    check("attach a source list", status == 201 and record.get("kind") == "sources",
          "%s %s" % (status, record.get("kind")))
    status, table = call(base, "/api/intake/%s/sources" % record.get("id"), {})
    entries = ((table or {}).get("sources") or {}).get("n_entries")
    check("read the source list", status == 200 and entries == 2,
          "%s entries=%s" % (status, entries))
    status, listed = call(base, "/api/intake/%s/sources" % record.get("id"))
    citations = (listed or {}).get("citations") or []
    check("list the declared citations", status == 200 and len(citations) == 2,
          citations[0] if citations else "none")
    check("the citations are not presented as evidence",
          "not evidence" in str((listed or {}).get("note", "")), "")

    status, mapped = call(base, "/api/ingest",
                          {"filename": "scores.csv",
                           "content_base64": base64.b64encode(CSV).decode(),
                           "map": {"method": "descriptive_stats", "columns": {"values": "score"}}})
    request = (mapped or {}).get("mapped_request") or {}
    check("map a dataset column into a method",
          status == 200 and request.get("inputs", {}).get("values") == ["10", "12.5", "9"],
          str(request.get("inputs"))[:40])
    status, created = call(base, "/api/sessions",
                           {"objective": "Describe my own data", "method": request.get("method"),
                            "inputs": request.get("inputs"),
                            "provenance": request.get("input_provenance"),
                            "data_manifest": request.get("data_manifest")})
    status2, confirmed = call(base, "/api/sessions/%s/confirm" % created.get("id"), {})
    data_report = ((confirmed or {}).get("delivery") or {}).get("report") or ""
    check("run the mapped dataset",
          status2 == 200 and confirmed.get("status") == "delivered" and "10.50" in data_report,
          "%s, mean in report=%s" % (confirmed.get("status"), "10.50" in data_report))

    with open(os.path.join(out_dir, "clickthrough.json"), "w", encoding="utf-8") as handle:
        json.dump({"base": base, "steps": rows, "failures": failures}, handle, indent=1)
    summary = "\n".join("%s  %-46s %s" % ("PASS" if row["ok"] else "FAIL", row["step"],
                                          row["detail"]) for row in rows)
    with open(os.path.join(out_dir, "clickthrough.md"), "w", encoding="utf-8") as handle:
        handle.write("# Intake click-through on %s\n\n```\n%s\n\n%d failure(s)\n```\n"
                     % (base, summary, len(failures)))
    print("\n%d failure(s)" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

