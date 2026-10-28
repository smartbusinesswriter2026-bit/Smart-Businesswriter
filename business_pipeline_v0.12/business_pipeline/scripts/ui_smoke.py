"""Student-path smoke test against a running workbench (no browser dependency).

    python scripts/ui_smoke.py --url http://127.0.0.1:8000

It checks the served page's markers, the subject index, the worksheet form kinds and one
complete worksheet run through the same HTTP API the browser uses. It is not a DOM test:
it cannot catch a layout or click-binding regression, only a missing page, route, form kind,
token leak or failed delivery. Run it after `scripts/ci.py` when a server is up.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

MARKERS = ("worksheetForm", "matrixForm", "bp-ws-draft-", "Download the worksheet (Word)",
           "not teacher-approved", "renderPlan", "Business plan")
ABSENT = ("Reviewer name", "Sign-off", "Review status", "pending_named_reviewer")
RAIL_MARKERS = ("markCurrentRailItem", "SUBJECT_WORKSPACE", "railSubject")
SUBJECTS = ("accounting", "finance", "economics", "management", "project-management",
            "entrepreneurship", "operations", "supply-chain", "marketing", "people", "research")
FORMS = {"template_business_model_canvas": "canvas", "template_pestel": "canvas",
         "template_scenario_planning": "matrix", "template_swot": "swot",
         "template_five_forces": "five_forces"}


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=20) as response:
        return response.read()


def _post(base, path, body):
    request = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def main():
    parser = argparse.ArgumentParser(description="Smoke-test a running workbench")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    failures = []

    def check(name, condition, detail=""):
        print(("PASS  " if condition else "FAIL  ") + name + (("  " + detail) if detail and not condition else ""))
        if not condition:
            failures.append(name)

    try:
        page = _get(base, "/").decode("utf-8", "replace")
        check("served page carries the worksheet and draft markers", all(m in page for m in MARKERS))
        check("no reviewer surface in the page", not any(m in page for m in ABSENT))
        check("the rail keeps the subject marked while its workspace is open",
              all(m in page for m in RAIL_MARKERS))
        check("page has a title", "<title>" in page)

        subjects = json.loads(_get(base, "/api/cases/subjects").decode())
        ids = [row["id"] for row in subjects.get("subjects", [])]
        check("subject gallery lists every shelf", all(s in ids for s in SUBJECTS), str(ids))

        for template, form in FORMS.items():
            payload = json.loads(_get(base, "/api/templates/" + template).decode())
            check("template %s uses the %s form" % (template, form), payload.get("form_kind") == form,
                  str(payload.get("form_kind")))

        bmc = json.loads(_get(base, "/api/templates/template_business_model_canvas").decode())
        request = bmc["example_request"]
        session = _post(base, "/api/sessions", {"objective": request["objective"], "method": request["method"],
                                                "inputs": request["inputs"]})
        session = _post(base, "/api/sessions/" + session["id"] + "/confirm", {})
        delivery = session.get("delivery") or {}
        report = delivery.get("report") or ""
        checks = delivery.get("appendix", {}).get("tests") or []
        check("worksheet run delivers", delivery.get("status") == "delivered", str(session.get("status")))
        check("delivered report has no unresolved token", "{{ref:" not in report and bool(report))
        check("every check passed", all(bool(c[1]) for c in checks if len(c) > 1), str(checks))

        # -- the business-plan profile, end to end over the same routes ------
        plan = _post(base, "/api/cases/chat", {
            "brief": "A coffee shop selling specialty coffee to university students in Cebu City.",
            "profile": "business_plan", "subject": "entrepreneurship", "level": "shs", "mode": "strict"})
        plan = _post(base, "/api/cases/chat/" + plan["id"] + "/plan", {})
        plan = _post(base, "/api/cases/chat/" + plan["id"] + "/inputs", {"values": {
            "business_name": "Bean There", "product": "specialty coffee and pastries",
            "customers": "university students", "location": "Cebu City",
            "positioning": "affordable specialty coffee", "channels": "a campus kiosk",
            "pricing_note": "mid-market pricing", "operations": "a single kiosk with two staff",
            "team": "the owner and one barista", "risks": ["a rent increase"]}})
        plan = _post(base, "/api/cases/chat/" + plan["id"] + "/compute", {"blocks": {
            "frommarket": {"market_size": "60000000", "target_share": "0.03", "price": "120"},
            "breakeven": {"fixed": "300000", "price": "120", "variable": "55"},
            "depreciation": {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"},
            "proforma": {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
                         "operating_costs": ["300000", "320000", "340000"],
                         "depreciation": ["90000", "90000", "90000"],
                         "interest": ["40000", "30000", "20000"],
                         "principal_repayment": ["100000", "100000", "100000"],
                         "tax_rate": "0.25", "opening_cash": "200000",
                         "opening_fixed_assets": "450000", "opening_loan": "400000",
                         "opening_equity": "250000"},
            "sensitivity": {"base_price": "120", "base_units": "10000", "base_variable_cost": "55",
                            "base_fixed_cost": "300000", "price_changes": ["-0.1", "0.1"],
                            "volume_changes": ["-0.2", "0.2"]}}})
        plan = _post(base, "/api/cases/chat/" + plan["id"] + "/draft", {"accepted": []})
        check("business plan drafts with no missing input", plan.get("draft", {}).get("missing") == [],
              str(plan.get("draft", {}).get("missing")))
        export = _post(base, "/api/cases/chat/" + plan["id"] + "/export", {})
        check("business plan exports Word bytes", bool(export.get("data")) and export.get("mime", "").endswith("wordprocessingml.document"))
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError) as error:
        print("FAIL  smoke run raised %r" % (error,))
        failures.append("exception")

    print("\n%d failure(s)" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
