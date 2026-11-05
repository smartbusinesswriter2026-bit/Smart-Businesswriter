import sys
sys.path.insert(0, "src")
from bp.product import statement_library as L

c = L._conn()
q = c.execute
print("store:", L._STORE_DIR)
print("total rows:", q("select count(*) from problems").fetchone()[0])
print("distinct texts:", q("select count(distinct text_hash) from problems").fetchone()[0])
print("solved:", q("select count(*) from problems where solved=1").fetchone()[0])
print("null unplaceable:", q("select count(*) from problems where unplaceable is null").fetchone()[0])
print("null gate_failures:", q("select count(*) from problems where gate_failures is null").fetchone()[0])
print("records carrying missing:", q(
    "select count(*) from problems where missing is not null and missing not in ('[]','null')"
).fetchone()[0])
print("top duplicated texts:")
for row in q("select count(*) as n, substr(text,1,60) from problems group by text_hash "
             "order by n desc limit 5").fetchall():
    print("  ", row[0], "x", row[1].replace("\n", " "))
c.close()

for probe in ("Data: Bank statement balance 25,000; book cash balance 22,100; deposits in transit 4,000.",
              "Data: Direct materials used 50,000; direct labor 40,000; manufacturing overhead 30,000.",
              "The company purchased equipment for cash and recorded depreciation at year end."):
    hits = L.few_shot(probe, n=2)
    print()
    print("probe:", probe[:60])
    print("few_shot hits:", [(h["text"][:55].replace("\n", " "), len(h["entries"] or [])) for h in hits])
