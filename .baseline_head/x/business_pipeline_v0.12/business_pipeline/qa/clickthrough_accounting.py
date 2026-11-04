"""Live click-through for the accounting shelf against a running workbench (port 8001).

There is no browser automation in this environment, so the click-through is done in the
two layers the session work order allows: a Python page/contract check against the served
HTML, and a real HTTP run of every accounting tool through the same routes the page calls
(create a session, confirm it, read the delivered report).

Writes `qa/evidence/accounting/clickthrough.json` and a Markdown summary; it changes no
product state beyond the in-memory sessions the server keeps.

Usage:  PYTHONPATH=src python qa/clickthrough_accounting.py http://127.0.0.1:8001
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "src")

from bp.product import subjects  # noqa: E402
from bp.server import PRESETS  # noqa: E402

PAGE_MARKERS = ("railSubject", "markCurrentRailItem", "activate(\"new\")", "calculator",
                "subjectgallery", "Honesty: what was not done",
                "Confirm the account mapping and post")
PAGE_ABSENT = ("Reviewer name", "Sign-off", "Review status")


def _request(base, path, payload=None, method=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(base + path, data=data,
                                     method=method or ("POST" if data else "GET"))
    if data:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read() or b"{}")


def main(argv):
    base = (argv[1] if len(argv) > 1 else "http://127.0.0.1:8001").rstrip("/")
    out_dir = os.path.join("qa", "evidence", "accounting")
    os.makedirs(out_dir, exist_ok=True)
    lines, rows, failures = [], [], []

    with urllib.request.urlopen(base + "/", timeout=30) as response:
        html = response.read().decode("utf-8", "replace")
    for marker in PAGE_MARKERS:
        ok = marker in html
        lines.append("%s  page marker %r" % ("PASS" if ok else "FAIL", marker))
        if not ok:
            failures.append("missing page marker %r" % marker)
    for marker in PAGE_ABSENT:
        ok = marker not in html
        lines.append("%s  no reviewer surface %r" % ("PASS" if ok else "FAIL", marker))
        if not ok:
            failures.append("reviewer surface leaked: %r" % marker)

    status, detail = _request(base, "/api/cases/subjects/accounting")
    lines.append("%s  GET /api/cases/subjects/accounting -> %d, %d tools"
                 % ("PASS" if status == 200 and len(detail["tools"]) == 12 else "FAIL",
                    status, len(detail["tools"])))
    if status != 200 or len(detail["tools"]) != 12:
        failures.append("subject page did not serve twelve tools")

    for item in detail["tools"]:
        preset = json.loads(json.dumps(PRESETS[item["preset"]]))
        try:
            status, created = _request(base, "/api/sessions", preset)
            planned = created.get("status")
            status2, confirmed = _request(base, "/api/sessions/%s/confirm" % created["id"], {})
            checkpoints = 1
            if confirmed.get("status") == "awaiting_mapping_confirmation":
                # The engagement's second mandatory checkpoint: the page shows
                # "Confirm the account mapping and post" and posts the same route.
                status2, confirmed = _request(base, "/api/sessions/%s/confirm" % created["id"], {})
                checkpoints = 2
            report = (confirmed.get("delivery") or {}).get("report") or ""
            states = confirmed.get("stage_states") or {}
            ok = (planned in ("awaiting_confirmation", "awaiting_mapping_confirmation")
                  and status2 == 200 and confirmed.get("status") == "delivered"
                  and report and "{{" not in report
                  and all(value in ("passed", "not_run") for value in states.values()))
            rows.append({"tool": item["key"], "preset": item["preset"],
                         "method": item["method"], "planned": planned,
                         "status": confirmed.get("status"), "checkpoints": checkpoints,
                         "checks": len((confirmed.get("delivery") or {}).get("appendix", {})
                                       .get("tests") or []),
                         "first_line": report.split(". ")[0][:180], "ok": ok})
            lines.append("%s  %-16s %s -> %s (%d checkpoint%s)" % (
                "PASS" if ok else "FAIL", item["key"], item["preset"],
                confirmed.get("status"), checkpoints, "" if checkpoints == 1 else "s"))
            if not ok:
                failures.append("%s did not deliver through the product path" % item["key"])
        except (urllib.error.URLError, KeyError, ValueError) as error:
            rows.append({"tool": item["key"], "error": str(error), "ok": False})
            failures.append("%s raised %s" % (item["key"], error))
            lines.append("FAIL  %-16s %s" % (item["key"], error))

    with open(os.path.join(out_dir, "clickthrough.json"), "w", encoding="utf-8") as handle:
        json.dump({"base": base, "page_checks": lines, "runs": rows,
                   "failures": failures}, handle, indent=1)
    summary = "\n".join(lines) + "\n\n%d failure(s)\n" % len(failures)
    with open(os.path.join(out_dir, "clickthrough.md"), "w", encoding="utf-8") as handle:
        handle.write("# Accounting click-through on %s\n\n```\n%s```\n" % (base, summary))
    print(summary)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
