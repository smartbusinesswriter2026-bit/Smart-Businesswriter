"""The project proposal as an Excel workbook: overview, work plan, budget, risks."""

from . import business_plan_workbook
from . import proposal_plan
from . import spreadsheets


def sheets(state):
    record = proposal_plan.normalise((state or {}).get("proposal") or {})
    rolled = (state or {}).get("proposal_budget") or proposal_plan.rollup(record)
    project = record.get("project") or {}

    out = [business_plan_workbook._sheet("Overview", [
        ["Field", "Value"],
        ["Title", project.get("title") or ""],
        ["Problem", project.get("problem") or ""],
        ["Objectives", "; ".join(project.get("objectives") or [])],
        ["Location", project.get("location") or ""],
        ["Proponents", project.get("proponents") or ""],
        ["Timeline", project.get("timeline") or ""],
        ["Funding source", project.get("funding_source") or ""],
        ["Currency", project.get("currency") or "USD"],
        ["Budget total", rolled.get("total")],
    ], [24, 70])]

    work = [["Activity", "Duration", "Deliverable", "Owner"]]
    work.extend(proposal_plan.work_plan_rows(record))
    out.append(business_plan_workbook._sheet("Work plan", work, [36, 16, 30, 18]))

    budget = [["Item", "Amount"]]
    budget.extend(proposal_plan.budget_rows(record, rolled))
    out.append(business_plan_workbook._sheet("Budget", budget, [40, 18]))

    risks = [["Risk", "Response", "Owner"]]
    risks.extend(proposal_plan.risk_rows(record))
    out.append(business_plan_workbook._sheet("Risks", risks, [40, 34, 18]))
    return out


def workbook(state):
    """The workbook as .xlsx bytes, or None when the record carries no table."""
    out = sheets(state)
    if not out:
        return None
    return spreadsheets.write_xlsx(out)
