import json
from bp import statement_plan as sp

plan = {
    "period": {"start": "2026-01-01", "end": "2026-12-31"},
    "currency": "USD", "framework": "US_GAAP", "places": 2,
    "policy": {"rounding": "half_up", "inventory_system": "periodic",
               "depreciation": {"method": "straight_line", "convention": "pro_rata"},
               "explicitly_stated": []},
    "prior_closing": {}, "opening": [],
    "entries": [
        {"date": "2026-12-31", "description": "sale", "lines": [
            {"account": "1000", "debit": "10000"}, {"account": "4000", "credit": "10000"}]},
    ],
    "adjustments": [], "schedules": [],
    "chart": [
        {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "section": "current", "activity": "operating", "role": "cash"},
        {"code": "4000", "name": "Revenue", "type": "income", "line": "Revenue", "activity": "operating"},
        {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"},
    ],
    "problem_type": "transactions",
}
r = sp.build(plan)
ap = r.get("_appendix") or {}
print("APPENDIX KEYS:", sorted(ap.keys()))
for k in sorted(ap.keys()):
    v = ap[k]
    if isinstance(v, dict):
        print(" ", k, "-> dict keys:", list(v.keys())[:14])
    elif isinstance(v, list):
        print(" ", k, "-> list len", len(v), "first:", repr(v[0])[:200] if v else None)
    else:
        print(" ", k, "->", type(v).__name__, str(v)[:120])
print()
print("== statements ==")
st = ap.get("statements") or {}
print(list(st.keys()) if isinstance(st, dict) else type(st))
if isinstance(st, dict):
    for k, v in st.items():
        print("  ", k, type(v).__name__, (list(v.keys())[:12] if isinstance(v, dict) else str(v)[:120]))
print()
print("== statements_export ==")
se = ap.get("statements_export") or {}
print(list(se.keys()))
