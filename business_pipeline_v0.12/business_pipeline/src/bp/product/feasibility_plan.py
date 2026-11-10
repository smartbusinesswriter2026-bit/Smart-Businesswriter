"""A simplified feasibility study: three declared tables and the frozen break-even.

The full feasibility profile is a guide of thirteen sections and a form of required
fields.  This module is the smaller route the owner asked for: the brief supplies a
market table (target market, demand, price), a cost table (investment items, fixed
cost, variable cost) and the study prints a third table of the returns the frozen
`breakeven` method computes.  Nothing is inferred: a missing figure is named by
`validate`, never filled.

The record is one object::

    {
      "project": {"name", "description", "location", "proponents", "currency"},
      "market": {"target_market", "demand", "price"},
      "costs": [{"item", "amount"}],
      "operating": {"fixed", "variable"},
      "declared": {"technology", "capacity", "team", "skills", "permits",
                    "regulations", "risks"}
    }

Every money figure is in the declared currency.  The break-even run is the frozen
core's own; this module does not re-implement it.
"""

import copy

FORMAT = "bp-feasibility-plan/1"
CURRENCY_DEFAULT = "USD"


def empty():
    """A blank record with the shape the composer expects."""
    return {
        "format": FORMAT,
        "project": {"name": "", "description": "", "location": "", "proponents": "",
                    "currency": CURRENCY_DEFAULT},
        "market": {"target_market": "", "demand": None, "price": None},
        "costs": [],
        "operating": {"fixed": None, "variable": None},
        "declared": {"technology": "", "capacity": "", "team": "", "skills": "",
                     "permits": "", "regulations": "", "risks": []},
    }


def _text(value, limit=2000):
    return " ".join(str(value or "").split()).strip()[:limit]


def _number(value):
    text = str(value if value is not None else "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _items(value, limit=40):
    if isinstance(value, list):
        return [_text(item, 300) for item in value if _text(item, 300)][:limit]
    text = _text(value, 4000)
    return [_text(part, 300) for part in text.replace("\n", ";").split(";") if _text(part, 300)][:limit]


def normalise(record):
    """A clean copy.  It never adds a field the student did not supply."""
    source = copy.deepcopy(record) if isinstance(record, dict) else {}
    base = empty()
    project = source.get("project") if isinstance(source.get("project"), dict) else {}
    for key in base["project"]:
        if key == "currency":
            base["project"][key] = _text(project.get(key), 8).upper() or CURRENCY_DEFAULT
        else:
            base["project"][key] = _text(project.get(key))
    market = source.get("market") if isinstance(source.get("market"), dict) else {}
    base["market"]["target_market"] = _text(market.get("target_market"))
    base["market"]["demand"] = _number(market.get("demand"))
    base["market"]["price"] = _number(market.get("price"))
    base["costs"] = [{"item": _text(row.get("item"), 200), "amount": _number(row.get("amount"))}
                     for row in source.get("costs") or [] if isinstance(row, dict)]
    operating = source.get("operating") if isinstance(source.get("operating"), dict) else {}
    base["operating"]["fixed"] = _number(operating.get("fixed"))
    base["operating"]["variable"] = _number(operating.get("variable"))
    declared = source.get("declared") if isinstance(source.get("declared"), dict) else {}
    for key in base["declared"]:
        if key == "risks":
            base["declared"][key] = _items(declared.get(key))
        else:
            base["declared"][key] = _text(declared.get(key), 500)
    return base


def validate(record):
    """Every problem that would make the study dishonest or uncomputable."""
    record = record or {}
    project = record.get("project") or {}
    market = record.get("market") or {}
    operating = record.get("operating") or {}
    problems = []
    for key, label in (("name", "a project name"), ("description", "a project description")):
        if not _text(project.get(key)):
            problems.append("the project needs " + label)
    if not _text(market.get("target_market")):
        problems.append("the market table needs a target market")
    demand = _number(market.get("demand"))
    price = _number(market.get("price"))
    fixed = _number(operating.get("fixed"))
    variable = _number(operating.get("variable"))
    if not demand or demand <= 0:
        problems.append("the market table needs a declared demand above zero")
    if not price or price <= 0:
        problems.append("the market table needs a declared price above zero")
    if fixed is None or fixed < 0:
        problems.append("the cost table needs a declared fixed cost")
    if variable is None or variable < 0:
        problems.append("the cost table needs a declared variable cost per unit")
    if price and variable is not None and variable >= price:
        problems.append("the variable cost per unit must be below the price, or the project cannot break even")
    invested = [_number(row.get("amount")) for row in record.get("costs") or []]
    if not any(value and value > 0 for value in invested):
        problems.append("the cost table needs at least one investment item above zero")
    if not (record.get("declared") or {}).get("risks"):
        problems.append("the study needs at least one named risk")
    return problems


def rollup(record):
    """The declared investment, summed, plus the operating figures as written."""
    total = sum((_number(row.get("amount")) or 0) for row in (record or {}).get("costs") or [])
    return {"items": [{"item": row.get("item") or "", "amount": _number(row.get("amount"))}
                      for row in (record or {}).get("costs") or []],
            "total": total,
            "fixed": _number(((record or {}).get("operating") or {}).get("fixed")),
            "variable": _number(((record or {}).get("operating") or {}).get("variable"))}


def inputs(record):
    """The frozen method's own inputs, from the declared market and cost figures."""
    market = (record or {}).get("market") or {}
    operating = (record or {}).get("operating") or {}
    return {"fixed": str(_number(operating.get("fixed")) or 0),
            "price": str(_number(market.get("price")) or 0),
            "variable": str(_number(operating.get("variable")) or 0),
            "expected_units": str(_number(market.get("demand")) or 0)}


def run(record, runner):
    """Run the frozen break-even method, or return its refusal."""
    if runner is None:
        return {"ok": False, "error": "the computation core is not attached"}
    try:
        return {"ok": True, "method": "breakeven", "inputs": inputs(record),
                "result": runner("breakeven", inputs(record))}
    except Exception as error:  # a refused input is a refusal, not a crash
        return {"ok": False, "error": str(error)[:300]}


def table(caption, columns, rows, note=""):
    """A Word table figure from plain strings.  Numbers are the student's own."""
    columns = [str(column) for column in columns]
    grid_rows = [[{"label": column, "bullets": [], "role": "label"} for column in columns]]
    for row in rows:
        grid_rows.append([{"label": "", "bullets": [str(cell)]} for cell in row])
    return {"kind": "table", "caption": caption, "note": note,
            "grids": [{"rows": grid_rows, "col_widths": [1.0 / max(1, len(columns))] * len(columns)}]}


def _money(value, currency="USD"):
    try:
        return "%s %s" % (currency or CURRENCY_DEFAULT, "{:,.2f}".format(float(value)))
    except (TypeError, ValueError):
        return "not declared"


def _number_text(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return "{:,.2f}".format(number)


def market_rows(record, computed=None):
    """Table one: the declared market and the revenue it implies."""
    record = record or {}
    market = record.get("market") or {}
    currency = ((record.get("project") or {}).get("currency")) or CURRENCY_DEFAULT
    rows = [["Target market", _text(market.get("target_market"))],
            ["Declared demand (units a year)", _number_text(market.get("demand"))],
            ["Price per unit", _money(market.get("price"), currency)]]
    result = (computed or {}).get("result") or {}
    if (computed or {}).get("ok") and result.get("expected_revenue") is not None:
        rows.append(["Revenue at the declared demand", _money(result.get("expected_revenue"), currency)])
    return rows


def cost_rows(record, rolled=None):
    """Table two: the investment items and the operating figures, as declared."""
    record = record or {}
    rolled = rolled or rollup(record)
    currency = ((record.get("project") or {}).get("currency")) or CURRENCY_DEFAULT
    rows = [[row.get("item") or "", _money(row.get("amount"), currency)]
            for row in rolled.get("items") or []]
    rows.append(["Total investment", _money(rolled.get("total"), currency)])
    rows.append(["Fixed cost a year", _money(rolled.get("fixed"), currency)])
    rows.append(["Variable cost per unit", _money(rolled.get("variable"), currency)])
    return rows


def return_rows(record, computed):
    """Table three: the returns the frozen break-even method computed."""
    result = (computed or {}).get("result") or {}
    currency = (((record or {}).get("project") or {}).get("currency")) or CURRENCY_DEFAULT
    rows = []
    if result.get("expected_revenue") is not None:
        rows.append(["Revenue at the declared demand", _money(result.get("expected_revenue"), currency)])
    if result.get("contribution_margin") is not None:
        rows.append(["Contribution margin per unit", _money(result.get("contribution_margin"), currency)])
    if result.get("breakeven_units") is not None:
        rows.append(["Break-even volume", _number_text(result.get("breakeven_units")) + " units"])
    if result.get("breakeven_revenue") is not None:
        rows.append(["Break-even revenue", _money(result.get("breakeven_revenue"), currency)])
    if result.get("margin_of_safety_units") is not None:
        rows.append(["Margin of safety", _number_text(result.get("margin_of_safety_units")) + " units"])
    if result.get("margin_of_safety_ratio") is not None:
        rows.append(["Margin of safety ratio", "{:.1%}".format(float(result["margin_of_safety_ratio"]))])
    return rows
