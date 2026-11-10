"""The project plan's own workbook: charter, WBS, schedule, cost, RACI and risks.

One sheet per table the record holds, written with the product's own xlsx
writer.  No figure is recomputed here: the schedule is the frozen core's stored
result and the cost is the WBS roll-up already recorded on the state.
"""

from . import business_plan_workbook
from . import project_plan
from . import spreadsheets


def sheets(state):
    record = project_plan.normalise((state or {}).get("project") or {})
    rolled = (state or {}).get("project_cost") or project_plan.rollup(record)
    scheduled = ((state or {}).get("project_schedule") or {}).get("result") or {}
    charter = record.get("charter") or {}
    currency = charter.get("currency") or "USD"

    out = [business_plan_workbook._sheet("Charter", [
        ["Field", "Value"],
        ["Title", charter.get("title") or ""],
        ["Objective", charter.get("objective") or ""],
        ["Sponsor", charter.get("sponsor") or ""],
        ["Project manager", charter.get("project_manager") or ""],
        ["Budget", rolled.get("budget")],
        ["Currency", currency],
        ["Start", charter.get("start_date") or ""],
        ["End", charter.get("end_date") or ""],
    ], [24, 64])]

    wbs = [["ID", "Work package", "Owner", "Cost", "Acceptance"]]
    wbs.extend(project_plan.wbs_rows(record))
    out.append(business_plan_workbook._sheet("WBS", wbs, [10, 40, 20, 16, 30]))

    if scheduled:
        rows = [["ID", "Activity", "Duration", "ES", "EF", "LS", "LF", "Float", "Critical"]]
        rows.extend(project_plan.schedule_rows(record, scheduled))
        out.append(business_plan_workbook._sheet("Schedule", rows,
                                                 [10, 32, 10, 8, 8, 8, 8, 8, 10]))

    dated = ((state or {}).get("project_dated") or {})
    if dated.get("ok") and charter.get("start_date"):
        rows = [["ID", "Activity", "Start", "Finish", "Working days"]]
        rows.extend(project_plan.dated_rows(record, dated.get("result") or {},
                                            charter.get("start_date")))
        out.append(business_plan_workbook._sheet("Dated schedule", rows, [10, 32, 14, 14, 14]))

    levelled = ((state or {}).get("project_levelled") or {})
    if levelled.get("ok"):
        rows = [["ID", "Activity", "Levelled start", "Levelled finish", "Delay"]]
        rows.extend(project_plan.levelled_rows(record, levelled.get("result") or {}))
        out.append(business_plan_workbook._sheet("Levelled schedule", rows, [10, 32, 16, 16, 10]))

    cost = [["ID", "Item", "Cost"]]
    cost.extend(project_plan.cost_rows(record, rolled))
    out.append(business_plan_workbook._sheet("Cost", cost, [10, 48, 18]))

    columns, data = project_plan.raci_rows(record)
    out.append(business_plan_workbook._sheet("RACI", [list(columns)] + data,
                                             [12, 32] + [14] * max(0, len(columns) - 2)))

    risks = [["ID", "Risk", "Likelihood", "Impact", "Response", "Owner"]]
    risks.extend(project_plan.risk_rows(record))
    out.append(business_plan_workbook._sheet("Risks", risks, [8, 48, 12, 12, 32, 20]))
    return out


def workbook(state):
    """The workbook as .xlsx bytes, or None when the record carries no table."""
    out = sheets(state)
    if not out:
        return None
    return spreadsheets.write_xlsx(out)
