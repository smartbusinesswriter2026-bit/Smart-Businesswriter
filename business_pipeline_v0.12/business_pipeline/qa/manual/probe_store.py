import os
import sys
sys.path.insert(0, "src")
from bp.product import statement_library as L

print("real store:", L._STORE_DIR)
c = L._conn()
print("rows:", c.execute("select count(*) from problems").fetchone()[0])
for origin, count in c.execute("select origin, count(*) from problems group by origin").fetchall():
    print("  origin", origin, "->", count)
print("kinds:", c.execute("select kind, count(*) from problems group by kind").fetchall())
c.close()
temp = os.path.join(os.environ.get("TEMP", ""), "bp_test_statement_library")
print("test store:", temp, "exists:", os.path.exists(temp))
if os.path.exists(os.path.join(temp, "library.db")):
    import sqlite3
    t = sqlite3.connect(os.path.join(temp, "library.db"))
    print("test rows:", t.execute("select count(*) from problems").fetchone()[0])
    t.close()
