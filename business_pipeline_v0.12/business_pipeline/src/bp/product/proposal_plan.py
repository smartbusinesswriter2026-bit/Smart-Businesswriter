"""A project proposal as a record: work plan, budget and risks, nothing invented.

The proposal is a smaller document than the project plan: it states the problem,
the objectives, the activities, the budget and how delivery is monitored.  This
module cleans and validates that record, sums the declared budget and builds the
tables the paper prints.  It computes no business number beyond the sum of the
declared budget lines.
"""

import copy

FORMAT = "bp-proposal-plan/1"
CURRENCY_DEFAULT = "USD"


def empty():
    """A blank record with the shape the composer expects."""
    return {
        "format": FORMAT,
        "project": {"title": "", "problem": "", "objectives": [], "location": "",
                    "proponents": "", "timeline": "", "funding_source": "",
                    "beneficiaries": [], "indicators": [], "baseline": "",
                    "targets": [], "currency": CURRENCY_DEFAULT},
        "work_plan": [],
        "budget": [],
        "risks": [],
    }


def _text(value, limit=2000):
    return " ".join(str(value or "").split()).strip()[:limit]


def _items(value, limit=40):
    if isinstance(value, list):
        return [_text(item, 300) for item in value if _text(item, 300)][:limit]
    text = _text(value, 4000)
    return [_text(part, 300) for part in text.replace("\n", ";").split(";") if _text(part, 300)][:limit]


def _number(value):
    text = str(value if value is not None else "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def normalise(record):
    """A clean copy.  It never adds a field the student did not supply."""
    source = copy.deepcopy(record) if isinstance(record, dict) else {}
    base = empty()
    project = source.get("project") if isinstance(source.get("project"), dict) else {}
    for key in base["project"]:
        if key in ("objectives", "beneficiaries", "indicators", "targets"):
            base["project"][key] = _items(project.get(key))
        elif key == "currency":
            base["project"][key] = _text(project.get(key), 8).upper() or CURRENCY_DEFAULT
        else:
            base["project"][key] = _text(project.get(key))
    base["work_plan"] = [{
        "activity": _text(row.get("activity"), 300),
        "duration": _text(row.get("duration"), 120),
        "deliverable": _text(row.get("deliverable"), 300),
        "owner": _text(row.get("owner"), 120),
    } for row in source.get("work_plan") or [] if isinstance(row, dict)]
    base["budget"] = [{"item": _text(row.get("item"), 200), "amount": _number(row.get("amount"))}
                      for row in source.get("budget") or [] if isinstance(row, dict)]
    base["risks"] = [{
        "description": _text(row.get("description"), 500),
        "response": _text(row.get("response"), 500),
        "owner": _text(row.get("owner"), 120),
    } for row in source.get("risks") or [] if isinstance(row, dict)]
    return base


def validate(record):
    """Every problem that would make the proposal dishonest or unbuildable."""
    record = record or {}
    project = record.get("project") or {}
    problems = []
    if not _text(project.get("title")):
        problems.append("the proposal needs a project title")
    if not _text(project.get("problem")):
        problems.append("the proposal needs a problem statement")
    if not project.get("objectives"):
        problems.append("the proposal needs at least one objective")
    plan = record.get("work_plan") or []
    if not plan:
        problems.append("the work plan needs at least one activity")
    for index, row in enumerate(plan, 1):
        if not _text(row.get("activity")):
            problems.append("work-plan row %d needs an activity" % index)
    budget = record.get("budget") or []
    if not budget:
        problems.append("the budget needs at least one line")
    for index, row in enumerate(budget, 1):
        if not _text(row.get("item")):
            problems.append("budget line %d needs an item" % index)
        if not _number(row.get("amount")) or _number(row.get("amount")) <= 0:
            problems.append("budget line %d needs an amount above zero" % index)
    for index, row in enumerate(record.get("risks") or [], 1):
        if not _text(row.get("description")):
            problems.append("risk %d needs a description" % index)
    return problems


def rollup(record):
    """The declared budget, summed, and the number of lines."""
    lines = [{"item": row.get("item") or "", "amount": _number(row.get("amount"))}
             for row in (record or {}).get("budget") or []]
    total = sum((row["amount"] or 0) for row in lines)
    return {"lines": lines, "total": total}


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


def work_plan_rows(record):
    """One row per activity: what is done, when, what it produces and who owns it."""
    return [[row.get("activity") or "", row.get("duration") or "",
             row.get("deliverable") or "", row.get("owner") or ""]
            for row in (record or {}).get("work_plan") or []]


def budget_rows(record, rolled=None):
    """The budget lines and the declared total."""
    record = record or {}
    rolled = rolled or rollup(record)
    currency = ((record.get("project") or {}).get("currency")) or CURRENCY_DEFAULT
    rows = [[row.get("item") or "", _money(row.get("amount"), currency)]
            for row in rolled.get("lines") or []]
    rows.append(["Total", _money(rolled.get("total"), currency)])
    return rows


def risk_rows(record):
    """The risk register as stated; an empty response or owner stays empty."""
    return [[row.get("description") or "", row.get("response") or "", row.get("owner") or ""]
            for row in (record or {}).get("risks") or []]
