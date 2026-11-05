import glob, json, os

files = glob.glob("cases/statements/*.json")
best = None
for f in files:
    try:
        rec = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    ap = ((rec.get("core") or {}).get("appendix")) or {}
    ig = ap.get("income_groups") or {}
    if ig.get("income") and ig.get("expenses"):
        score = len(ig["income"]) + len(ig["expenses"]) + len(ig.get("oci") or {})
        if best is None or score > best[0]:
            best = (score, f, rec)
if not best:
    print("none")
else:
    score, f, rec = best
    print("file:", f, "score", score)
    ap = rec["core"]["appendix"]
    print("\nincome_groups:", json.dumps(ap["income_groups"], indent=1)[:1500])
    print("\ncomprehensive_income:", json.dumps(ap.get("comprehensive_income"), indent=1)[:1200])
    print("\nbalance_sheet_groups:", json.dumps(ap.get("balance_sheet_groups"), indent=1)[:1200])
    print("\nclosing_balances:", json.dumps(ap.get("closing_balances"), indent=1)[:800])
    print("\nstatements:", json.dumps(ap.get("statements"), indent=1)[:1200])
    print("\ncash_flow detail:", json.dumps(ap.get("cash_flow"), indent=1)[:1400])
