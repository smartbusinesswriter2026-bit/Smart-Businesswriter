"""Live click-through for the finance shelf against a running workbench (port 8001).

There is no browser automation in this environment, so the click-through is done in the
two layers the work order allows: a page/contract check against the served HTML, and a
real HTTP run of every finance tool through the same routes the page calls (create a
session, confirm it, read the delivered report).

`dcfmid` is recorded as KNOWN-BLOCKED with its ledger id (D-FIN-01) rather than being
counted as a silent pass or an unexplained failure.

Writes `qa/evidence/finance/clickthrough.json` and a Markdown summary; it changes no
product state beyond the in-memory sessions the server keeps.

Usage:  PYTHONPATH=src python qa/clickthrough_finance.py http://127.0.0.1:8001
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "src")

from bp.product import subjects  # noqa: E402
from bp.server import PRESETS  # noqa: E402

PAGE_MARKERS = ("railSubject", "markCurrentRailItem", 'activate("new")', "calculator",
                "subjectgallery", "not teacher-approved")
PAGE_ABSENT = ("Reviewer name", "Sign-off", "Review status")
KNOWN_BLOCKED = {"dcfmid": "D-FIN-01"}


def _request(base, path, payload=None, method=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(base + path, data=data,
                                     method=method or ("POST" if data else "GET"))
    if data:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.status, json.loads(response.read() or b"{}")


def main(argv):
    base = (argv[1] if len(argv) > 1 else "http://127.0.0.1:8001").rstrip("/")
    out_dir = os.path.join("qa", "evidence", "finance")
    os.makedirs(out_dir, exist_ok=True)
    lines, rows, failures, known = [], [], [], []

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

    status, detail = _request(base, "/api/cases/subjects/finance")
    served = len(detail.get("tools") or [])
    lines.append("%s  GET /api/cases/subjects/finance -> %d, %d tools, %d records"
                 % ("PASS" if status == 200 and served == 35 else "FAIL", status, served,
                    len(detail.get("records") or [])))
    if status != 200 or served != 35:
        failures.append("subject page did not serve thirty-five tools")

    for item in detail.get("tools") or []:
        preset_id = item.get("preset")
        if preset_id not in PRESETS:
            lines.append("SKIP  %-16s no preset (G-fin-05)" % item["key"])
            rows.append({"tool": item["key"], "preset": preset_id, "ok": None,
                         "note": "no preset (G-fin-05)"})
            continue
        preset = json.loads(json.dumps(PRESETS[preset_id]))
        try:
            status, created = _request(base, "/api/sessions", preset)
            planned = created.get("status")
            status2, confirmed = _request(base, "/api/sessions/%s/confirm" % created["id"], {})
            report = (confirmed.get("delivery") or {}).get("report") or ""
            states = confirmed.get("stage_states") or {}
            ok = (planned in ("awaiting_confirmation", "awaiting_mapping_confirmation")
                  and status2 == 200 and confirmed.get("status") == "delivered"
                  and bool(report) and "{{" not in report
                  and all(value in ("passed", "not_run") for value in states.values()))
            rows.append({"tool": item["key"], "preset": preset_id, "method": item["method"],
                         "planned": planned, "status": confirmed.get("status"),
                         "first_line": report.split(". ")[0][:180], "ok": ok})
            if ok:
                lines.append("PASS  %-16s %s -> delivered" % (item["key"], preset_id))
            elif item["key"] in KNOWN_BLOCKED:
                known.append("%s is blocked by %s" % (item["key"], KNOWN_BLOCKED[item["key"]]))
                lines.append("KNOWN %-16s %s -> %s (%s)"
                             % (item["key"], preset_id, confirmed.get("status"),
                                KNOWN_BLOCKED[item["key"]]))
            else:
                failures.append("%s did not deliver through the product path" % item["key"])
                lines.append("FAIL  %-16s %s -> %s"
                             % (item["key"], preset_id, confirmed.get("status")))
        except (urllib.error.URLError, KeyError, ValueError) as error:
            rows.append({"tool": item["key"], "error": str(error), "ok": False})
            failures.append("%s raised %s" % (item["key"], error))
            lines.append("FAIL  %-16s %s" % (item["key"], error))

    with open(os.path.join(out_dir, "clickthrough.json"), "w", encoding="utf-8") as handle:
        json.dump({"base": base, "page_checks": lines, "runs": rows,
                   "failures": failures, "known_blocked": known}, handle, indent=1)
    summary = ("\n".join(lines) + "\n\n%d failure(s), %d known-blocked\n"
               % (len(failures), len(known)))
    with open(os.path.join(out_dir, "clickthrough.md"), "w", encoding="utf-8") as handle:
        handle.write("# Finance click-through on %s\n\n```\n%s```\n" % (base, summary))
    print(summary)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
