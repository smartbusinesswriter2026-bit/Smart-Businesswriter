"""Read a project brief into the project-plan record, tables first.

The project plan is deterministic: the charter, the WBS, the activities, the
resources, the RACI matrix and the risk register are what the brief states.
This reader places each labelled fact and each table cell on the field its
name matches and **never fills a cell**.  A work package with no cost, an
activity with no duration or a risk with no owner stays empty, and
`project_plan.validate` names it.

Only three things are derived, and each is structural rather than factual:

* a table row with no id is numbered by its position, because the row needs a
  name to be cited and its position is what the brief shows;
* a dotted WBS id ("1.2") gets the parent "1" **only when "1" is itself a row**;
* an activity points at the WBS row with the same id, or the same name, and at
  nothing else.

The record shape is the one `project_plan.normalise` documents.
"""

import re

FORMAT = "bp-project-read/1"

#: A header cell, normalised: "(USD)" dropped, punctuation to spaces.
def _norm(value):
    text = re.sub(r"\(.*?\)", " ", str(value or "")).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


#: Column names the reader recognises.  A table starts when two of its cells
#: are a known column name.
COLUMNS = {
    "id": ("id", "no", "number", "code", "ref", "reference"),
    "name": ("task", "tasks", "activity", "activities", "name", "description",
             "work package", "wbs", "item", "deliverable", "phase"),
    "parent": ("parent", "parent id", "parent task"),
    "level": ("level", "tier"),
    "owner": ("owner", "responsible", "assigned to", "assignee", "accountable"),
    "cost": ("cost", "budget", "amount", "estimate", "price", "value"),
    "acceptance": ("acceptance", "acceptance test", "done when", "definition of done", "test"),
    "duration": ("duration", "days", "periods", "time", "length", "weeks"),
    "predecessors": ("predecessor", "predecessors", "depends on", "dependency", "dependencies"),
    "resource": ("resource", "resources", "team", "squad", "assigned"),
    "demand": ("demand", "load", "people", "quantity", "units needed"),
    "capacity": ("capacity", "availability", "units"),
    "role": ("role", "roles", "function"),
    "likelihood": ("likelihood", "probability", "chance"),
    "impact": ("impact", "severity", "consequence"),
    "response": ("response", "mitigation", "action", "treatment", "plan"),
    "letter": ("letter", "raci", "raci letter"),
    "optimistic": ("optimistic", "best case", "o"),
    "most_likely": ("most likely", "likely", "m"),
    "pessimistic": ("pessimistic", "worst case", "p"),
    "risk": ("risk", "risks", "description of risk"),
}

#: Every normalised column name, for the header test.
NAMES = {name for aliases in COLUMNS.values() for name in aliases}

#: The charter fields a labelled line can state.
LABELS = (
    ("title", ("project title", "project name", "name of the project", "title")),
    ("objective", ("project objective", "objective", "purpose", "goal")),
    ("sponsor", ("sponsor", "client", "commissioned by", "authorised by", "authorized by")),
    ("project_manager", ("project manager", "project lead", "manager", "lead")),
    ("budget_total", ("total budget", "project budget", "budget", "funding")),
    ("currency", ("currency",)),
    ("start_date", ("start date", "starts", "commencement date")),
    ("end_date", ("end date", "due date", "finish date", "completion date")),
    ("governance", ("governance", "governance arrangement", "decision route")),
    ("change_control", ("change control", "change threshold", "change process")),
    ("scope_in", ("in scope", "scope in", "included in scope")),
    ("scope_out", ("out of scope", "scope out", "excluded from scope", "exclusions")),
    ("deliverables", ("deliverables", "deliverable")),
    ("success_measures", ("success measures", "success measure", "success criteria", "kpis", "kpi")),
    ("assumptions", ("assumptions", "assumption")),
    ("constraints", ("constraints", "constraint")),
)

LIST_FIELDS = ("scope_in", "scope_out", "deliverables", "success_measures",
               "assumptions", "constraints")

_MONEY = re.compile(r"^(?:usd|\$)?\s*(-?[\d,]+(?:\.\d+)?)\s*([km])?$", re.I)


def _number(value):
    """A declared number, or None.  No unit is guessed beyond a stated k/m."""
    text = str(value or "").strip().replace("$", "").replace("USD", "").replace("usd", "").strip()
    text = text.replace(",", "")
    match = _MONEY.match(text)
    if not match:
        return None
    try:
        number = float(match.group(1))
    except ValueError:
        return None
    suffix = (match.group(2) or "").lower()
    if suffix == "k":
        number *= 1000
    elif suffix == "m":
        number *= 1000000
    return number


def _cells(line):
    """The cells of one table line, or None when the line is not a table line."""
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
    """Every table in the brief: its header cells and its rows."""
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
    """The column position for a field, or None.  Exact names win over a part."""
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


def _kinds(columns):
    """What a table is, from its own column names.  A table can be two things."""
    names = [_norm(column) for column in columns]
    joined = " ".join(names)
    if "risk" in joined or "likelihood" in joined or "impact" in joined:
        return {"risks"}
    kinds = set()
    if "predecessor" in joined or "depends on" in joined or "duration" in joined \
            or "optimistic" in joined:
        kinds.add("activities")
    if "activity" in joined and not kinds and "cost" not in joined and "capacity" not in joined:
        kinds.add("raci")
    if ("role" in joined or "capacity" in joined) and "activity" not in joined:
        kinds.add("resources")
    if "letter" in joined and ("activity" in joined or "role" in joined):
        kinds.add("raci")
    if "cost" in joined or "acceptance" in joined or "done when" in joined or "budget" in joined:
        kinds.add("wbs")
    return kinds


def _charter(lines):
    """The labelled charter facts.  A line without a label states nothing."""
    charter, options = {}, {"pert": False, "contingency_pct": None}
    for raw in lines:
        line = str(raw or "").strip()
        if not line or _cells(line) and _header(_cells(line) or []):
            continue
        match = re.match(r"^([A-Za-z][A-Za-z0-9 /&'()-]{1,40}?)\s*[:\-]\s*(.+)$", line)
        if not match:
            continue
        label, value = _norm(match.group(1)), match.group(2).strip()
        if not value:
            continue
        if "contingency" in label:
            number = _number(value.replace("%", ""))
            if number is not None:
                options["contingency_pct"] = number
            continue
        field = None
        for key, aliases in LABELS:
            if any(label == alias or label.endswith(" " + alias) for alias in aliases):
                field = key
                break
        if not field or field in charter:
            continue
        if field in LIST_FIELDS:
            items = [part.strip(" .") for part in re.split(r"[;•]", value) if part.strip(" .")]
            if items:
                charter[field] = items
        elif field == "budget_total":
            number = _number(value)
            if number is not None:
                charter[field] = number
        elif field == "currency":
            charter[field] = value.strip().upper()[:8]
        else:
            charter[field] = value
    return charter, options


def _title_from_prose(text):
    patterns = (
        r"project plan\s+(?:for|called|named|titled)\s+([^\n.;]{2,90})",
        r"project\s+(?:title|name)\s+(?:is|:)\s*([^\n.;]{2,90})",
        r"project\s*:\s*([^\n.;]{2,90})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
    return ""


def read(brief):
    """The project record the brief states, in the shape `project_plan` expects."""
    text = str(brief or "")
    lines = text.splitlines()
    charter, options = _charter(lines)
    if not charter.get("title"):
        title = _title_from_prose(text)
        if title:
            charter["title"] = title
    if not charter.get("title"):
        first = next((line.strip() for line in lines if line.strip()), "")
        if (first and ":" not in first and len(first) <= 90
                and not (_cells(first) and _header(_cells(first) or []))):
            charter["title"] = first.rstrip(" .")
    charter.setdefault("currency", "USD")

    wbs, activities, resources, raci, risks = [], [], [], [], []
    for table in _tables(lines):
        columns = table["columns"]
        kinds = _kinds(columns)
        positions = {key: _index(columns, key) for key in COLUMNS}
        if "optimistic" in " ".join(_norm(column) for column in columns):
            options["pert"] = True
        for order, row in enumerate(table["rows"], 1):
            if "wbs" in kinds:
                node_id = _cell(row, positions["id"]) or str(order)
                wbs.append({
                    "id": node_id,
                    "name": _cell(row, positions["name"]),
                    "parent": _cell(row, positions["parent"]) or None,
                    "level": _number(_cell(row, positions["level"])),
                    "owner": _cell(row, positions["owner"]) or _cell(row, positions["resource"]),
                    "cost": _number(_cell(row, positions["cost"])),
                    "acceptance": _cell(row, positions["acceptance"]),
                })
            if "activities" in kinds:
                activity = {
                    "id": _cell(row, positions["id"]) or str(order),
                    "name": _cell(row, positions["name"]),
                    "duration": _number(_cell(row, positions["duration"])),
                    "predecessors": [part.strip() for part in re.split(r"[,;\s]+",
                                                                       _cell(row, positions["predecessors"]))
                                      if part.strip()],
                    "resource": _cell(row, positions["resource"]),
                    "demand": _number(_cell(row, positions["demand"])),
                    "wbs": _cell(row, positions["id"]) if "wbs" in kinds else "",
                    "optimistic": _number(_cell(row, positions["optimistic"])),
                    "most_likely": _number(_cell(row, positions["most_likely"])),
                    "pessimistic": _number(_cell(row, positions["pessimistic"])),
                }
                activities.append(activity)
            if "resources" in kinds:
                resources.append({"name": _cell(row, positions["name"]),
                                  "role": _cell(row, positions["role"]),
                                  "capacity": _number(_cell(row, positions["capacity"]))})
            if "raci" in kinds:
                raci.extend(_raci_rows(columns, row, positions))
            if "risks" in kinds:
                risks.append({
                    "id": _cell(row, positions["id"]) or "R" + str(order),
                    "description": _cell(row, positions["risk"]) or _cell(row, positions["name"]),
                    "likelihood": _cell(row, positions["likelihood"]),
                    "impact": _cell(row, positions["impact"]),
                    "response": _cell(row, positions["response"]),
                    "owner": _cell(row, positions["owner"]),
                })
    _nest(wbs)
    _link_wbs(activities, wbs)
    _add_resources(resources, activities)
    return {
        "format": FORMAT,
        "charter": charter,
        "wbs": wbs,
        "activities": activities,
        "resources": resources,
        "raci": raci,
        "risks": risks,
        "options": options,
    }


def _nest(wbs):
    """A dotted id gets the parent its own prefix names, only when that row exists."""
    ids = {str(row.get("id") or "") for row in wbs}
    for row in wbs:
        if row.get("parent"):
            continue
        node_id = str(row.get("id") or "")
        parent = node_id.rsplit(".", 1)[0] if "." in node_id else ""
        if parent and parent in ids:
            row["parent"] = parent
        if row.get("level") is None:
            row["level"] = node_id.count(".") + 1


def _raci_rows(columns, row, positions):
    """One row per declared letter: the direct form and the matrix form."""
    activity = _cell(row, positions["id"]) or _cell(row, positions["name"]) or ""
    if not activity:
        return []
    if positions["letter"] is not None and positions["role"] is not None:
        letter = _cell(row, positions["letter"]).upper()[:1]
        role = _cell(row, positions["role"])
        return [{"activity": activity, "role": role, "letter": letter}] if letter else []
    if positions["letter"] is not None:
        letter = _cell(row, positions["letter"]).upper()[:1]
        return [{"activity": activity, "role": _cell(row, positions["role"]), "letter": letter}] if letter else []
    # A matrix: every other column is a role and its cell carries the letters.
    found = []
    for position, header in enumerate(columns):
        name = _norm(header)
        if name in ("activity", "id", "task", "name", "no", "number", "code"):
            continue
        letters = re.findall(r"[RACI]", _cell(row, position).upper())
        for letter in letters:
            found.append({"activity": activity, "role": str(header).strip(), "letter": letter})
    return found


def _link_wbs(activities, wbs):
    """An activity points at the WBS row with its id or its name, and nowhere else."""
    by_id = {str(row.get("id") or ""): row for row in wbs}
    by_name = {_norm(row.get("name")): row for row in wbs if _norm(row.get("name"))}
    for activity in activities:
        current = str(activity.get("wbs") or "")
        if current in by_id:
            continue
        target = by_id.get(str(activity.get("id") or ""))
        if target is None:
            target = by_name.get(_norm(activity.get("name")))
        activity["wbs"] = str(target.get("id") or "") if target else ""


def _add_resources(resources, activities):
    """A resource the activity table names is declared; its role is not invented."""
    known = {str(row.get("name") or "").strip() for row in resources}
    for activity in activities:
        name = str(activity.get("resource") or "").strip()
        if name and name not in known:
            known.add(name)
            resources.append({"name": name, "role": "", "capacity": None})


CUES = ("project plan", "complete project plan", "project management plan",
        "work breakdown structure")


def is_project_plan(brief, reading=None):
    """Whether a brief asks for a project plan: an explicit cue or a WBS table."""
    text = str(brief or "").lower()
    if any(cue in text for cue in CUES) or re.search(r"\bwbs\b", text):
        return True
    reading = reading if reading is not None else read(brief)
    return bool(reading.get("wbs") and (reading.get("charter") or {}).get("title"))
