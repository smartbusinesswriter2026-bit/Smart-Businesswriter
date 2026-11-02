import json, sys
sys.path.insert(0, r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\src")
from bp import case_decision as cd
from bp.methods import LIBRARY

alts = [
    {"id": "A1", "name": "Office catering at the new park",
     "cashflows": ["-1850000", "700000", "780000", "820000"],
     "supports": ["F2", "F3"], "cashflow_provenance": "user"},
    {"id": "A2", "name": "Second plant on the coastal road",
     "cashflows": ["-4200000", "900000", "1050000", "1150000", "1200000", "1250000", "1300000", "1350000", "1400000"],
     "supports": ["F1", "F4"], "cashflow_provenance": "user"},
    {"id": "A3", "name": "Defend: extend opening hours and a loyalty card",
     "cashflows": ["-320000", "900000", "980000", "1050000"],
     "supports": ["F1", "F4"], "cashflow_provenance": "user"},
]
inp = {
    "facts": [
        {"id": "F1", "text": "Regional bakery segment was 186.4 million pesos in 2025", "provenance": "sourced", "source": "p.12"},
        {"id": "F2", "text": "Eleven shops operate in the surveyed districts", "provenance": "sourced", "source": "p.12"},
        {"id": "F3", "text": "Regional average monthly revenue per shop is 4680 pesos", "provenance": "sourced", "source": "p.12"},
        {"id": "F4", "text": "A supermarket chain opened a bakery counter in the central district", "provenance": "sourced", "source": "p.4"},
    ],
    "alternatives": alts,
    "rate": "0.12", "rate_range": ["0.08", "0.18"],
    "decision_rule": "highest_npv", "currency": "PHP",
}
a = cd.build(inp)
print("NPV at base :", json.dumps(a["npv_at_base"]))
print("ranking base:", a["ranking_at_base"])
print("crossovers  :", json.dumps(a["crossovers"]))
print("recommend   :", json.dumps(a["recommendation"]))
m = LIBRARY["npv"]
for r in ["0.08", "0.09", "0.10", "0.11", "0.12", "0.14", "0.16", "0.18"]:
    vals = {x["id"]: str(m.impl({"rate": r, "cashflows": x["cashflows"]})) for x in alts}
    order = sorted(vals.items(), key=lambda kv: -float(kv[1]))
    print(r, {k: vals[k] for k in sorted(vals)}, "->", [k for k, _ in order])


