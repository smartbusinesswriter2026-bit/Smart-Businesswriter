"""The marketing plan's own workbook (product layer, standard library only)."""

from . import business_plan_workbook
from . import spreadsheets


def _result_rows(result):
    rows = [["Measure", "Value"]]
    for key, value in sorted((result or {}).items()):
        if not str(key).startswith("_"):
            rows.append([str(key).replace("_", " ").title(), str(value)])
    return rows


def workbook(paper, computations):
    sheets = []
    unit = (computations.get("unit_economics") or {}).get("result") or {}
    if unit:
        sheets.append(business_plan_workbook._sheet("Unit economics", _result_rows(unit), [30, 24]))
    funnel = (computations.get("sales_funnel") or {}).get("result") or {}
    if funnel:
        sheets.append(business_plan_workbook._sheet("Funnel", _result_rows(funnel), [30, 24]))
    channel = (computations.get("channel_economics") or {}).get("result") or {}
    if channel:
        rows = [["Channel", "Spend", "Customers", "CAC", "LTV", "LTV:CAC"]]
        channels = ((computations.get("channel_economics") or {}).get("inputs") or {}).get("channels") or []
        for index, row in enumerate(channels, 1):
            rows.append([row.get("name"), channel.get("spend_%d" % index),
                         channel.get("customers_%d" % index), channel.get("cac_%d" % index),
                         channel.get("ltv_%d" % index), channel.get("ltv_cac_%d" % index)])
        sheets.append(business_plan_workbook._sheet("Channels", rows, [24, 14, 14, 14, 14, 14]))
    budget = next((lines for heading, lines in paper.get("sections") or []
                   if heading == "Budget and Projections"), [])
    if budget:
        sheets.append(business_plan_workbook._sheet(
            "Marketing budget", [["Item", "Value"]] + [["Budget line", line] for line in budget],
            [24, 90]))
    if not sheets:
        return None
    return spreadsheets.write_xlsx(sheets)
