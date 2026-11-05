import sys
sys.path.insert(0, "src")
from bp.product import statement_library as L

c = L._conn()
changed = c.execute("update problems set origin='legacy' where origin is null").rowcount
c.commit()
print("rows labelled legacy:", changed)
for origin, count in c.execute("select origin, count(*) from problems group by origin").fetchall():
    print("  ", origin, count)
c.close()

print()
for probe in ("The following trial balance was extracted at 31 December 2026. Cash 7,000 Trade receivables 3,000",
              "Data: Bank statement balance 25,000; book cash balance 22,100; deposits in transit 4,000",
              "Issued common stock for 50,000 cash. Purchased inventory on account 20,000.",
              "Data: Direct materials used 50,000; direct labor 40,000; manufacturing overhead 30,000"):
    hits = L.few_shot(probe, n=2)
    print("probe:", probe[:55])
    print("  hits:", [(h["text"][:50].replace("\n", " "), h.get("origin")) for h in hits])
