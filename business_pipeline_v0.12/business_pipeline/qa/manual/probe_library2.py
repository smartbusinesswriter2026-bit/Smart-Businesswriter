import sys, json
sys.path.insert(0, "src")
from bp.product import statement_library as L

c = L._conn()
rows = c.execute("select text, missing, reading_source, solved from problems "
                 "where missing is not null and missing not in ('[]','null') limit 6").fetchall()
for text, missing, src, solved in rows:
    print("-" * 70)
    print("problem:", (text or "")[:70].replace("\n", " "))
    print("solved:", solved, "| source:", src)
    try:
        items = json.loads(missing)
    except Exception:
        print("  raw:", str(missing)[:200]); continue
    if isinstance(items, list):
        for it in items[:4]:
            print("   missing:", str(it)[:140])
    else:
        print("  ", str(items)[:140])

kinds = c.execute("select reading_source, count(*) from problems group by reading_source "
                  "order by 2 desc").fetchall()
print()
print("reading_source breakdown:", kinds)
c.close()
