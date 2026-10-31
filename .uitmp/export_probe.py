"""Reproduce the smoke script's business-plan export against a running server and
print what the export route actually returns."""
import json
import sys
import urllib.request

base = sys.argv[1].rstrip("/")


def post(path, body):
    request = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:400]


status, plan = post("/api/cases/chat", {
    "brief": "A coffee shop selling specialty coffee to university students in Cebu City.",
    "profile": "business_plan", "subject": "entrepreneurship", "level": "shs", "mode": "strict"})
print("chat", status, (plan.get("id") if isinstance(plan, dict) else plan))
case = plan["id"]
status, plan = post("/api/cases/chat/%s/plan" % case, {})
print("plan", status, ((plan.get("draft") or {}).get("missing") if isinstance(plan, dict) else plan))
status, plan = post("/api/cases/chat/%s/inputs" % case, {"values": {
    "business_name": "Bean There", "product": "specialty coffee and pastries",
    "customers": "university students", "location": "Cebu City",
    "positioning": "affordable specialty coffee", "channels": "a campus kiosk",
    "pricing_note": "mid-market pricing", "operations": "a single kiosk with two staff",
    "team": "the owner and one barista", "risks": ["a rent increase"]}})
print("inputs", status)
status, plan = post("/api/cases/chat/%s/compute" % case, {"blocks": {
    "frommarket": {"market_size": "60000000", "target_share": "0.03", "price": "120"},
    "breakeven": {"fixed": "300000", "price": "120", "variable": "55"},
    "depreciation": {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"},
    "proforma": {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
                 "operating_costs": ["300000", "320000", "340000"],
                 "depreciation": ["90000", "100000", "110000"],
                 "interest": ["40000", "50000", "60000"],
                 "principal_repayment": ["50000", "50000", "50000"],
                 "tax_rate": "0.30", "opening_cash": "200000",
                 "opening_fixed_assets": "450000", "opening_loan": "200000",
                 "opening_equity": "450000"},
    "sensitivity": {"base_price": "120", "base_units": "10000", "base_variable_cost": "55",
                    "base_fixed_cost": "300000", "price_changes": ["-0.1", "0.1"],
                    "volume_changes": ["-0.2", "0.2"]}}})
print("compute", status)
status, plan = post("/api/cases/chat/%s/draft" % case, {"accepted": []})
print("draft", status, ((plan.get("draft") or {}).get("missing") if isinstance(plan, dict) else plan))
status, export = post("/api/cases/chat/%s/export" % case, {})
if isinstance(export, dict):
    print("export", status, "keys:", sorted(export.keys()),
          "mime:", export.get("mime"), "bytes:", len(export.get("data") or ""))
    if not export.get("data"):
        print("  body:", json.dumps(export)[:600])
else:
    print("export", status, export)
