import sys, os
sys.path.insert(0, "src")
os.environ.setdefault("BP_STATEMENT_LIBRARY_DIR", os.path.join(os.environ.get("TEMP",""), "bp_test_statement_library"))
os.environ.setdefault("BP_STATEMENT_LIBRARY_ORIGIN", "test")

from bp import methods, schedule_math, statement_plan, server as srv, statement_extract

# Get a model
models = srv._statement_models()
print("Model:", models)

TEXT = """2025 transactions:

Issued common stock for $100,000 cash.

Purchased raw materials for $60,000 cash.

Paid direct labor of $40,000 cash.

Paid manufacturing overhead costs of $25,000 cash.

Recorded factory depreciation of $10,000.

Paid office salaries of $18,000 cash.

Sales on account: $210,000.

Cash collected from customers: $190,000.

Paid other operating expenses of $12,000 cash.

Recorded office depreciation of $4,000.

No beginning inventories. Ending inventories: raw materials $6,000; work in process $9,000; finished goods $15,000.

Dividends paid: $10,000.

Income tax rate: 25%.

Required: Prepare the income statement, classified balance sheet, and indirect-method statement of cash flows."""

# Try extract directly
period = srv.statement_period.period_of(TEXT)[0] if hasattr(srv, 'statement_period') else None
from bp import statement_period as sp
period = sp.period_of(TEXT)[0]
print("Period:", period)

try:
    raw = statement_extract.extract(TEXT, statement_plan.DEFAULT_CHART, models, consent=True, period=period, default_date=period["end"])
    print("Extract succeeded")
    print("Entries:", len(raw.get("entries", [])))
except Exception as e:
    print("Extract failed:", type(e).__name__, str(e)[:500])
