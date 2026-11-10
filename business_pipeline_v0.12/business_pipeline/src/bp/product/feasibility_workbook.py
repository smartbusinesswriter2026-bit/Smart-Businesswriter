"""The simplified feasibility study as an Excel workbook: market, costs, returns.

One sheet per declared or computed table, written with the product's own xlsx
writer.  No figure is recomputed here: the returns are the frozen break-even
result already stored on the state.
"""

from . import business_plan_workbook
from . import feasibility_plan
from . import spreadsheets


def sheets(state):
    record = feasibility_plan.normalise((state or {}).get("feasibility") or {})
    rolled = (state or {}).get("feasibility_cost") or feasibility_plan.rollup(record)
    computed = (state or {}).get("feasibility_run") or {}
    currency = ((record.get("project") or {}).get("currency")) or "USD"

    out = [business_plan_workbook._sheet("Project", [
        ["Field", "Value"],
        ["Name", (record.get("project") or {}).get("name") or ""],
        ["Description", (record.get("project") or {}).get("description") or ""],
        ["Location", (record.get("project") or {}).get("location") or ""],
        ["Proponents", (record.get("project") or {}).get("proponents") or ""],
        ["Currency", currency],
    ], [20, 70])]

    market = [["Item", "Value"]] + feasibility_plan.market_rows(record, computed)
    out.append(business_plan_workbook._sheet("Market", market, [40, 28]))

    costs = [["Item", "Amount"]] + feasibility_plan.cost_rows(record, rolled)
    out.append(business_plan_workbook._sheet("Costs", costs, [40, 20]))

    if computed.get("ok"):
        returns = [["Metric", "Value"]] + feasibility_plan.return_rows(record, computed)
        out.append(business_plan_workbook._sheet("Returns", returns, [40, 28]))
    return out


def workbook(state):
    """The workbook as .xlsx bytes, or None when the record carries no table."""
    out = sheets(state)
    if not out:
        return None
    return spreadsheets.write_xlsx(out)
