import os
os.environ.setdefault("BP_STATEMENT_LIBRARY_DIR", os.path.join(os.environ.get("TEMP",""), "bp_test_statement_library"))
os.environ.setdefault("BP_STATEMENT_LIBRARY_ORIGIN", "test")
import sys
sys.path.insert(0, "src")
from bp.product import statement_library as L
marker = "PROBE GAP 14208"
L.record({"id": marker, "instruction": marker, "solved": False,
          "reading": {"missing": [{"what": marker, "why": "probe"}]}}, origin="test")
c = L._conn()
rows = c.execute("select id, text, missing from problems where text like ?", ("%" + marker + "%",)).fetchall()
print("rows with marker:", len(rows))
for r in rows: print("  ", r[0], "|", (r[2] or "")[:60])
report = L.gap_report()
print("in singles:", [p["item"] for p in report["singles"] if "PROBE GAP" in p["item"]])
print("in proposals:", [p["item"] for p in report["proposals"] if "PROBE GAP" in p["item"]])
c.close()
