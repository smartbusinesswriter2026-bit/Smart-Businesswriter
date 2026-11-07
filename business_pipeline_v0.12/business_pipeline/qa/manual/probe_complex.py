import sys, os
sys.path.insert(0, "src")
os.environ.setdefault("BP_STATEMENT_LIBRARY_DIR", os.path.join(os.environ.get("TEMP",""), "bp_test_statement_library"))
os.environ.setdefault("BP_STATEMENT_LIBRARY_ORIGIN", "test")

from bp import methods, schedule_math, statement_plan, server as srv
from bp.product import statements as S

S.attach_core(
    solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
    diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
        {"journal": None, "trial_balance": rows, "places": places}),
    ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
    dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
    reader=srv._statement_reader,
    extract=srv._statement_extract,
    build=srv._statement_build,
    set_tier=srv.set_statement_model_tier,
    schedules=schedule_math.compute,
)

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

Equipment costing $70,000 was purchased for cash at the beginning of the year; total depreciation of $14,000 is included above.

No beginning inventories. Ending inventories: raw materials $6,000; work in process $9,000; finished goods $15,000.

Dividends paid: $10,000.

Income tax rate: 25%.

Required: Prepare the income statement, classified balance sheet, and indirect-method statement of cash flows. Compute cost of goods sold from the inventory data."""

print("Solving...")
try:
    record = S.solve(TEXT)
    print("SOLVED:", record.get("solved"))
    print("problem_type:", record.get("problem_type"))
    print("reading_source:", record.get("reading_source"))
    print("checks:", [(c["name"], c["ok"]) for c in (record.get("checks") or [])])
    print("scalars:", {k: v for k, v in (record["core"]["scalars"] or {}).items() if not k.startswith("_")})
except Exception as e:
    import traceback
    traceback.print_exc()
