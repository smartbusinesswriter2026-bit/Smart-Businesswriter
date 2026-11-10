"""Figures the plan profiles declare in words, run through the frozen core.

The business plan reads tables.  Marketing, feasibility and project briefs often
state a price, a unit cost, an acquisition cost, a churn rate or a fixed cost in
a sentence.  This module finds only those explicit declarations, calls the
frozen methods, and returns the core's own lines.  It never derives a figure the
brief did not state.
"""

import re
from decimal import Decimal, InvalidOperation

NUMBER = r"(-?\d[\d,]*(?:\.\d+)?)"


def _n(value, places=2):
    try:
        return ("{:,.%df}" % places).format(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return str(value)


def _amount(text, *labels):
    for label in labels:
        match = re.search(label + r"\s*(?:of|is|was|:|=)?\s*" + NUMBER, text, re.I)
        if match:
            return match.group(1).replace(",", "")
    return None


def _rate(text, *labels):
    for label in labels:
        match = re.search(label + r"\s*(?:of|is|was|:|=)?\s*" + NUMBER + r"\s*%?", text, re.I)
        if match:
            value = match.group(1).replace(",", "")
            # A bare 20 next to a rate label is 20%, not 2000%.
            try:
                number = float(value)
            except ValueError:
                return None
            return str(number / 100) if number > 1 else value
    return None


def _channel_rows(text):
    lines = str(text or "").splitlines()
    start = None
    for index, line in enumerate(lines):
        if re.search(r"marketing channels?|channel plan", line, re.I):
            start = index + 1
            break
    if start is None:
        return []
    rows = []
    for line in lines[start:]:
        if not line.strip():
            break
        cells = [cell.strip() for cell in re.split(r"\t|\s{2,}|\s*\|\s*", line.strip()) if cell.strip()]
        if len(cells) < 5:
            continue
        try:
            spend = cells[1].replace(",", "")
            customers = cells[2].replace(",", "")
            margin = cells[3].replace(",", "")
            churn = cells[4].replace("%", "")
            churn = str(float(churn) / 100) if "%" in cells[4] or float(churn) > 1 else churn
        except ValueError:
            continue
        rows.append({"name": cells[0], "spend": spend, "new_customers": customers,
                     "contribution_margin": margin, "churn_rate": churn})
    return rows


def marketing(brief, run):
    """Unit economics, break-even, a declared funnel and declared channels."""
    if run is None:
        return {"lines": [], "funnel_lines": [], "channel_lines": [], "computations": {}}
    text = str(brief or "")
    price = _amount(text, r"(?:average ticket|average order value|selling price|price)")
    unit_cost = _amount(text, r"(?:unit cost|variable cost per unit|cost per unit)")
    acquisition = _amount(text, r"(?:acquisition cost|cost to acquire|CAC)")
    churn = _rate(text, r"(?:churn rate|churn)")
    fixed = _amount(text, r"(?:fixed monthly cost|monthly fixed cost|fixed cost)")
    spend = _amount(text, r"(?:marketing budget|marketing spend|advertising budget)")
    lines, funnel_lines, channel_lines, computations = [], [], [], {}
    budget_lines, measurement_lines = [], []
    funnel_result = None
    unit_result = None
    channel_result = None
    stages = []
    for name in ("leads", "visitors", "inquiries", "trials", "signups", "customers", "sales"):
        match = re.search(r"\b" + name + r"\b\s*[:=]?\s*" + NUMBER, text, re.I)
        if match:
            stages.append((match.start(), name, match.group(1).replace(",", "")))
    if len(stages) >= 2:
        stages.sort()
        inputs = {"stages": [{"name": name, "count": count} for _pos, name, count in stages]}
        if spend:
            inputs["spend"] = spend
        try:
            result = run("sales_funnel", inputs)
        except Exception:
            result = None
        if result:
            funnel_result = result
            computations["sales_funnel"] = {
                "ok": True, "method": "sales_funnel", "inputs": inputs,
                "result": {str(k): str(v) for k, v in result.items()}, "from": {}}
            funnel_lines.append("Funnel: " + " to ".join(
                "%s %s" % (name, count) for _pos, name, count in stages) +
                "; overall conversion " + _n(result.get("overall_conversion"), 4) + ".")
            if result.get("cac") is not None:
                funnel_lines.append("Cost to acquire one customer: " + _n(result.get("cac")) + ".")
    if price and unit_cost:
        inputs = {"price": price, "variable_cost": unit_cost}
        if acquisition:
            inputs["acquisition_cost"] = acquisition
        if churn:
            inputs["churn_rate"] = churn
        if len(inputs) >= 2:
            try:
                result = run("unit_economics", inputs)
            except Exception:
                result = None
            if result:
                unit_result = result
                computations["unit_economics"] = {
                    "ok": True, "method": "unit_economics", "inputs": inputs,
                    "result": {str(k): str(v) for k, v in result.items()}, "from": {}}
                lines.append("Unit margin: " + _n(result.get("unit_margin")) +
                             " per unit (" + _n(result.get("margin_pct"), 4) + " of price).")
                if result.get("ltv") is not None:
                    lines.append("Customer lifetime value: " + _n(result.get("ltv")) +
                                 "; LTV to acquisition cost: " + _n(result.get("ltv_cac"), 2) + ".")
                if result.get("payback_periods") is not None:
                    lines.append("Acquisition cost is recovered in " +
                                 _n(result.get("payback_periods"), 2) + " periods.")
    if fixed and price and unit_cost:
        inputs = {"fixed": fixed, "price": price, "variable": unit_cost}
        try:
            result = run("breakeven", inputs)
        except Exception:
            result = None
        if result:
            computations["breakeven"] = {
                "ok": True, "method": "breakeven", "inputs": inputs,
                "result": {str(k): str(v) for k, v in result.items()}, "from": {}}
            lines.append("Break-even: " + _n(result.get("breakeven_units"), 1) +
                         " units, or " + _n(result.get("breakeven_revenue")) + " in revenue.")
    channels = _channel_rows(text)
    if len(channels) >= 2:
        try:
            result = run("channel_economics", {"channels": channels})
        except Exception:
            result = None
        if result:
            channel_result = result
            computations["channel_economics"] = {
                "ok": True, "method": "channel_economics", "inputs": {"channels": channels},
                "result": {str(k): str(v) for k, v in result.items()}, "from": {}}
            channel_lines.append("Blended cost to acquire one customer: " +
                                 _n(result.get("blended_cac")) + ".")
            channel_lines.append("Channel | Spend | Customers | CAC | LTV | LTV:CAC")
            for index, row in enumerate(channels, 1):
                channel_lines.append("%s | %s | %s | %s | %s | %s" % (
                    row["name"], _n(result.get("spend_%d" % index)),
                    _n(result.get("customers_%d" % index)),
                    _n(result.get("cac_%d" % index)),
                    _n(result.get("ltv_%d" % index)),
                    _n(result.get("ltv_cac_%d" % index), 2)))
    if spend:
        try:
            monthly = Decimal(str(spend))
            budget_lines.append("Marketing budget: " + _n(monthly) + " per period; " +
                                _n(monthly * 12) + " per year.")
            if channel_result:
                for index, row in enumerate(_channel_rows(text), 1):
                    share = Decimal(str(channel_result.get("spend_share_%d" % index, "0")))
                    budget_lines.append("%s allocation: %s per period." % (
                        row["name"], _n(monthly * share)))
        except (InvalidOperation, ValueError):
            pass
    if funnel_result:
        measurement_lines.append("Funnel conversion: " +
                                 _n(funnel_result.get("overall_conversion"), 4) + ".")
        if funnel_result.get("cac") is not None:
            measurement_lines.append("Cost per customer from the funnel: " +
                                     _n(funnel_result.get("cac")) + ".")
    if unit_result:
        if unit_result.get("ltv") is not None:
            measurement_lines.append("Customer lifetime value: " + _n(unit_result.get("ltv")) + ".")
        if unit_result.get("payback_periods") is not None:
            measurement_lines.append("Acquisition payback: " +
                                     _n(unit_result.get("payback_periods"), 2) + " periods.")
    if channel_result and channel_result.get("blended_cac") is not None:
        measurement_lines.append("Blended cost per customer: " +
                                 _n(channel_result.get("blended_cac")) + ".")
    return {"lines": lines, "funnel_lines": funnel_lines,
            "channel_lines": channel_lines, "budget_lines": budget_lines,
            "measurement_lines": measurement_lines, "computations": computations}
