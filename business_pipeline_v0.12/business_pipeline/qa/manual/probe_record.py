import glob, json, os

files = sorted(glob.glob("cases/statements/*.json"), key=os.path.getmtime, reverse=True)
print("records:", len(files))
with open(files[0], encoding="utf-8") as fh:
    rec = json.load(fh)
print("file:", files[0])
print("solved:", rec.get("solved"), "problem_type:", rec.get("problem_type"))
ap = ((rec.get("core") or {}).get("appendix")) or {}
print("appendix keys:", sorted(ap.keys()))
st = ap.get("statements") or {}
for k in ("income", "expenses", "assets", "liabilities", "equity", "oci", "net_income",
          "total_assets", "total_liabilities", "total_equity", "equity_with_current_earnings",
          "profit_for_period", "total_comprehensive_income"):
    v = st.get(k)
    print("  st." + k, "=", json.dumps(v)[:300] if isinstance(v, (dict, list)) else v)
ig = ap.get("income_groups") or {}
print("income_groups:")
for k, v in ig.items():
    print("   ", k, "=", json.dumps(v)[:300])
print("equity_statement:", json.dumps(ap.get("equity_statement"))[:400])
print("cash_flow keys:", list((ap.get("cash_flow") or {}).keys()))
print("checks:", json.dumps(rec.get("checks"))[:800])
