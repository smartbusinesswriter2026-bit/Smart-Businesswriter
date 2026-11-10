"""Read a project-proposal brief into its work plan, budget and risk record.

A proposal is table-first, like the project plan: the brief states the project in
labels, a work plan table and a budget table.  This reader places each labelled
fact and each table row on the field its name matches and fills nothing else; a
missing objective, activity, cost or indicator stays missing for
`proposal_plan.validate` to name.

Only one thing is derived, and it is structural: a work-plan row with no separate
id is known by the activity it states.
"""

import re

FORMAT = "bp-proposal-read/1"


def _norm(value):
    text = re.sub(r"\(.*?\)", " ", str(value or "")).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


COLUMNS = {
    "activity": ("activity", "activities", "task", "step", "work item", "action"),
    "duration": ("duration", "timeline", "period", "time", "days", "weeks", "months"),
    "deliverable": ("deliverable", "output", "result", "milestone"),
    "owner": ("owner", "responsible", "assigned to", "lead", "who"),
    "item": ("item", "budget item", "line item", "description", "cost item"),
    "amount": ("amount", "cost", "budget", "total", "price", "estimate"),
    "risk": ("risk", "risks", "description of risk"),
    "response": ("response", "mitigation", "action", "treatment"),
}
NAMES = {name for aliases in COLUMNS.values() for name in aliases}


def _cells(line):
    text = str(line or "").strip().strip("`")
    if not text:
        return None
    if "|" in text:
        cells = [cell.strip() for cell in text.strip("|").split("|")]
        return cells if len(cells) >= 2 else None
    if "\t" in text:
        cells = [cell.strip() for cell in text.split("\t")]
        return cells if len(cells) >= 2 else None
    cells = [cell.strip() for cell in re.split(r"\s{2,}", text)]
    return cells if len(cells) >= 2 else None


def _header(cells):
    return sum(1 for cell in cells or [] if _norm(cell) in NAMES) >= 2


def _tables(lines):
    tables, index = [], 0
    while index < len(lines):
        cells = _cells(lines[index])
        if cells and _header(cells):
            columns, rows = cells, []
            index += 1
            while index < len(lines):
                nxt = _cells(lines[index])
                if not nxt or len(nxt) < 2:
                    break
                if _header(nxt) and len(nxt) == len(columns):
                    break
                rows.append(nxt)
                index += 1
            tables.append({"columns": columns, "rows": rows})
            continue
        index += 1
    return tables


def _index(columns, key):
    names = [_norm(column) for column in columns]
    for alias in COLUMNS[key]:
        if alias in names:
            return names.index(alias)
    for alias in COLUMNS[key]:
        if len(alias) < 4:
            continue
        for position, name in enumerate(names):
            if name and alias in name:
                return position
    return None


def _cell(row, position):
    if position is None or position >= len(row):
        return ""
    return str(row[position] or "").strip()


def _kind(columns):
    words = [_norm(column) for column in columns]
    joined = " ".join(words)
    if "risk" in joined:
        return "risks"
    if any(word in joined for word in ("amount", "cost", "budget", "price", "estimate")):
        return "budget"
    if any(word in joined for word in ("activity", "task", "step", "work item", "action")):
        return "work_plan"
    return None


_MONEY = re.compile(r"^(?:(?:usd|php|eur|gbp|\$|€|£)\s*)?(-?[\d,]+(?:\.\d+)?)\s*([km])?$", re.I)


def _number(value):
    text = str(value or "").strip().replace("$", "").replace("USD", "").strip().replace(",", "")
    match = _MONEY.match(text)
    if not match:
        return None
    try:
        number = float(match.group(1))
    except ValueError:
        return None
    suffix = (match.group(2) or "").lower()
    return number * (1000 if suffix == "k" else 1000000 if suffix == "m" else 1)


LABELS = (
    ("title", ("project title", "project name", "project", "title", "name of the project")),
    ("problem", ("problem statement", "problem", "need", "rationale", "background")),
    ("objectives", ("objectives", "objective", "goals", "goal", "outcomes")),
    ("location", ("location", "site", "address", "place")),
    ("proponents", ("proponents", "proposed by", "proponent", "applicant", "organisation", "organization")),
    ("timeline", ("timeline", "duration", "implementation period", "period")),
    ("funding_source", ("funding source", "funding", "funder", "source of funds")),
    ("beneficiaries", ("beneficiaries", "beneficiary", "participants")),
    ("indicators", ("indicators", "success indicators", "indicator")),
    ("baseline", ("baseline", "baseline data")),
    ("targets", ("targets", "target")),
    ("currency", ("currency",)),
    ("risks", ("risks", "risk")),
)


def _labelled(lines, table_lines):
    values = {}
    for raw in lines:
        line = str(raw or "").strip()
        if not line or line in table_lines:
            continue
        match = re.match(r"^([A-Za-z][A-Za-z0-9 /&'()-]{1,40}?)\s*[:\-]\s*(.+)$", line)
        if not match:
            continue
        label, value = _norm(match.group(1)), match.group(2).strip()
        if not value:
            continue
        field = None
        for key, aliases in LABELS:
            if any(label == alias or label.endswith(" " + alias) for alias in aliases):
                field = key
                break
        if not field or field in values:
            continue
        if field in ("objectives", "beneficiaries", "indicators", "targets", "risks"):
            values[field] = [part.strip(" .") for part in re.split(r"[;•]", value) if part.strip(" .")]
        else:
            values[field] = value
    return values


def _title_from_prose(text):
    patterns = (
        r"project proposal\s+(?:for|of|called|named|titled)\s+([^\n.;]{2,90})",
        r"project\s+(?:title|name)\s+(?:is|:)\s*([^\n.;]{2,90})",
        r"project\s*:\s*([^\n.;]{2,90})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
    return ""


def read(brief):
    """The proposal record the brief states."""
    text = str(brief or "")
    lines = text.splitlines()
    table_lines = {line for line in lines if _cells(line) and _header(_cells(line) or [])}
    values = _labelled(lines, table_lines)

    work_plan, budget, risks = [], [], []
    for table in _tables(lines):
        columns = table["columns"]
        kind = _kind(columns)
        positions = {key: _index(columns, key) for key in COLUMNS}
        for order, row in enumerate(table["rows"], 1):
            if kind == "work_plan":
                work_plan.append({
                    "activity": _cell(row, positions["activity"]) or _cell(row, positions["item"]),
                    "duration": _cell(row, positions["duration"]),
                    "deliverable": _cell(row, positions["deliverable"]),
                    "owner": _cell(row, positions["owner"]),
                })
            elif kind == "budget":
                amount = _number(_cell(row, positions["amount"]))
                item = _cell(row, positions["item"]) or _cell(row, positions["activity"])
                if item and amount is not None:
                    budget.append({"item": item, "amount": amount})
            elif kind == "risks":
                risks.append({
                    "description": _cell(row, positions["risk"]) or _cell(row, positions["item"]),
                    "response": _cell(row, positions["response"]),
                    "owner": _cell(row, positions["owner"]),
                })

    project = {
        "title": values.get("title", ""),
        "problem": values.get("problem", ""),
        "objectives": values.get("objectives") or [],
        "location": values.get("location", ""),
        "proponents": values.get("proponents", ""),
        "timeline": values.get("timeline", ""),
        "funding_source": values.get("funding_source", ""),
        "beneficiaries": values.get("beneficiaries") or [],
        "indicators": values.get("indicators") or [],
        "baseline": values.get("baseline", ""),
        "targets": values.get("targets") or [],
        "currency": (values.get("currency") or "USD").upper()[:8],
    }
    if not project["title"]:
        title = _title_from_prose(text)
        if title:
            project["title"] = title
    if not risks:
        risks = [{"description": item, "response": "", "owner": ""}
                 for item in values.get("risks") or []]
    return {"format": FORMAT, "project": project, "work_plan": work_plan,
            "budget": budget, "risks": risks}


def has_tables(record):
    """Whether the record carries a work plan or a budget table."""
    record = record or {}
    return bool(record.get("work_plan") or record.get("budget"))
