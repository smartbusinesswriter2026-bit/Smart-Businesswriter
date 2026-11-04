"""Live click-through for the entrepreneurship shelf against a running workbench.

There is no browser automation in this environment, so the click-through is done in the two
layers the work order allows: a page/contract check against the served HTML, and a real HTTP
run of every entrepreneurship tool through the same routes the page calls (create a session,
confirm it, read the delivered report) — plus the plan's marking-guide path, which is the
surface this session changed.

Every tool is expected to deliver: after D-ENT-04 there is no known-blocked entrepreneurship
tool. A tool that does not deliver is a failure here, not a silent pass.

Writes `qa/evidence/entrepreneurship/clickthrough.json` and a Markdown summary; it changes no
product state beyond the in-memory sessions the server keeps.

Usage:  PYTHONPATH=src python qa/clickthrough_entrepreneurship.py http://127.0.0.1:8003
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "src")

from bp.server import PRESETS  # noqa: E402

PAGE_MARKERS = ("railSubject", "markCurrentRailItem", 'activate("new")', "planbrief",
                "function rubricNoteHtml", 'id="planrubricgate"', "Honesty: what was not done",
                "Business plan")
PAGE_ABSENT = ("Reviewer name", "Sign-off", "Review status", "pending_named_reviewer")

PLAN_BRIEF = ("A coffee shop selling specialty coffee to university students in a mid-sized city. "
              "It needs start-up funding for equipment, a kiosk lease and two staff.")
PLAN_INPUTS = {"business_name": "Bean There", "product": "specialty coffee and pastries",
               "customers": "university students", "location": "a mid-sized city",
               "positioning": "affordable specialty coffee", "channels": "a campus kiosk",
               "pricing_note": "mid-market pricing", "operations": "a single kiosk with two staff",
               "suppliers": "a local roaster", "capacity_note": "120 cups a day",
               "team": "the owner and one barista", "roles": "the owner buys; the barista serves",
               "risks": ["a rent increase", "low student footfall"]}
PLAN_BLOCKS = {
    "frommarket": {"market_size": "60000000", "target_share": "0.03", "price": "120"},
    "breakeven": {"fixed": "300000", "price": "120", "variable": "55"},
    "depreciation": {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"},
    "proforma": {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
                 "operating_costs": ["300000", "320000", "340000"],
                 "depreciation": ["90000", "90000", "90000"],
                 "interest": ["40000", "30000", "20000"],
                 "principal_repayment": ["100000", "100000", "100000"],
                 "capex": ["0", "0", "0"], "tax_rate": "0.25", "receivable_days": "30",
                 "inventory_days": "45", "payable_days": "30", "opening_cash": "200000",
                 "opening_fixed_assets": "450000", "opening_receivables": "0",
                 "opening_inventory": "0", "opening_payables": "0", "opening_loan": "400000",
                 "opening_equity": "250000"},
    "sensitivity": {"base_price": "120", "base_units": "10000", "base_variable_cost": "55",
                    "base_fixed_cost": "300000", "price_changes": ["-0.1", "0", "0.1"],
                    "volume_changes": ["-0.2", "0", "0.2"]}}
RUBRIC = """Assessment criteria
1. Market analysis - 25% - must include the market size and the target segment
2. Financial plan - 35% - must include a break-even quantity
3. Operations plan - 20%
4. Risks and limitations - 10%
5. Referencing - 10%

Word limit: 2,500 words +/- 10%
"""
GAP_RUBRIC = "Assessment criteria\n1. Appendices with raw survey data - 100%\n"




def _request(base, path, payload=None, method=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(base + path, data=data,
                                     method=method or ("POST" if data else "GET"))
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        body = error.read()
        try:
            return error.code, json.loads(body or b"{}")
        except ValueError:
            return error.code, {"error": body[:200].decode("utf-8", "replace")}


def main(argv):
    base = (argv[1] if len(argv) > 1 else "http://127.0.0.1:8003").rstrip("/")
    out_dir = os.path.join("qa", "evidence", "entrepreneurship")
    os.makedirs(out_dir, exist_ok=True)
    lines, rows, failures = [], [], []

    def check(name, ok, detail=""):
        lines.append("%s  %s%s" % ("PASS" if ok else "FAIL", name,
                                   ("  " + detail) if detail and not ok else ""))
        if not ok:
            failures.append(name)

    with urllib.request.urlopen(base + "/", timeout=30) as response:
        html = response.read().decode("utf-8", "replace")
    for marker in PAGE_MARKERS:
        check("page marker %r" % marker, marker in html)
    for marker in PAGE_ABSENT:
        check("no reviewer surface %r" % marker, marker not in html)

    status, detail = _request(base, "/api/cases/subjects/entrepreneurship")
    check("GET the shelf answers 200 with 46 tools, 5 worksheets, 6 records",
          status == 200 and len(detail.get("tools") or []) == 46
          and len(detail.get("worksheets") or []) == 5
          and len(detail.get("records") or []) == 6,
          "status=%s tools=%s worksheets=%s" % (status, len(detail.get("tools") or []),
                                                len(detail.get("worksheets") or [])))
    check("the marketing plan is not offered on this shelf",
          "MKT-02" not in [row.get("catalogue_id") for row in detail.get("worksheets") or []])

    for item in detail.get("tools") or []:
        preset_id = item.get("preset")
        if preset_id not in PRESETS:
            rows.append({"tool": item["key"], "preset": preset_id, "ok": False,
                         "note": "no preset"})
            failures.append("%s has no preset" % item["key"])
            lines.append("FAIL  %-16s no preset" % item["key"])
            continue
        try:
            status, created = _request(base, "/api/sessions", PRESETS[preset_id])
            status2, confirmed = _request(base, "/api/sessions/%s/confirm" % created["id"], {})
            report = (confirmed.get("delivery") or {}).get("report") or ""
            states = confirmed.get("stage_states") or {}
            ok = (created.get("status") in ("awaiting_confirmation",
                                            "awaiting_mapping_confirmation")
                  and status2 == 200 and confirmed.get("status") == "delivered"
                  and bool(report) and "{{" not in report
                  and all(value in ("passed", "not_run") for value in states.values()))
            rows.append({"tool": item["key"], "preset": preset_id, "method": item["method"],
                         "planned": created.get("status"), "status": confirmed.get("status"),
                         "first_line": report.split(". ")[0][:180], "ok": ok})
            lines.append("%s  %-16s %s -> %s" % ("PASS" if ok else "FAIL", item["key"],
                                                 preset_id, confirmed.get("status")))
            if not ok:
                failures.append("%s did not deliver through the product path" % item["key"])
        except (urllib.error.URLError, KeyError, ValueError) as error:
            rows.append({"tool": item["key"], "error": str(error), "ok": False})
            failures.append("%s raised %s" % (item["key"], error))
            lines.append("FAIL  %-16s %s" % (item["key"], error))

    # -- the plan, and the marking guide the page now carries into it ------------
    def run_plan(rubric_text):
        status, state = _request(base, "/api/cases/chat",
                                 {"brief": PLAN_BRIEF, "profile": "business_plan",
                                  "subject": "entrepreneurship", "level": "shs",
                                  "mode": "strict", "rubric": rubric_text})
        plan_id = state.get("id")
        for action, body in (("plan", {}), ("inputs", {"values": PLAN_INPUTS}),
                             ("compute", {"blocks": PLAN_BLOCKS}), ("draft", {"accepted": []})):
            status, state = _request(base, "/api/cases/chat/%s/%s" % (plan_id, action), body)
        return plan_id, state

    plan_id, state = run_plan(RUBRIC)
    headings = [item["heading"] for item in (state.get("draft") or {}).get("outline") or []]
    check("the plan carries a Rubric coverage table before its references",
          "Rubric coverage" in headings and headings.index("Rubric coverage")
          < headings.index("References"), str(headings))
    check("a complete plan whose guide is satisfied has nothing missing",
          (state.get("draft") or {}).get("missing") == [],
          str((state.get("draft") or {}).get("missing")))
    status, payload = _request(base, "/api/cases/chat/%s/export" % plan_id, {})
    check("the plan export answers bytes", status == 200 and bool(payload.get("data")),
          "status=%s" % status)

    gap_id, gapped = run_plan(GAP_RUBRIC)
    status, refused = _request(base, "/api/cases/chat/%s/export" % gap_id, {})
    check("an unaddressed weighted criterion blocks the download and is named",
          status == 409 and any("criterion your rubric states" in str(item)
                                for item in refused.get("missing") or []),
          "status=%s %s" % (status, refused.get("missing")))
    status, accepted = _request(base, "/api/cases/chat/%s/rubric-gate" % gap_id,
                                {"enabled": False})
    check("the student may accept the gap", status == 200
          and (accepted.get("draft") or {}).get("missing") == [],
          str((accepted.get("draft") or {}).get("missing")))
    status, payload = _request(base, "/api/cases/chat/%s/export" % gap_id, {})
    check("the accepted gap still downloads", status == 200 and bool(payload.get("data")),
          "status=%s" % status)
    gaps = [row["name"] for row in (accepted.get("rubric") or {}).get("criteria") or []
            if row.get("status") == "gap"]
    check("the coverage table still names the accepted gap", bool(gaps), str(gaps))

    with open(os.path.join(out_dir, "clickthrough.json"), "w", encoding="utf-8") as handle:
        json.dump({"base": base, "checks": lines, "runs": rows, "failures": failures}, handle,
                  indent=1)
    summary = "\n".join(lines) + "\n\n%d failure(s), %d tool(s) run\n" % (len(failures), len(rows))
    with open(os.path.join(out_dir, "clickthrough.md"), "w", encoding="utf-8") as handle:
        handle.write("# Entrepreneurship click-through on %s\n\n```\n%s```\n" % (base, summary))
    print(summary)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
