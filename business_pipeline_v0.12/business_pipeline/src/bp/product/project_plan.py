"""A complete project plan: charter, scope, WBS, schedule, cost, roles and risk.

This module is the deterministic half.  It validates the student's project
record, rolls work-package costs up the WBS, turns activities into the rows the
frozen CPM method accepts, and checks the RACI and risk rules.  It invents no
cost, duration, date, owner or probability; a missing one is a named problem.

The record is one object::

    {
      "charter": {"title", "objective", "sponsor", "scope_in", "scope_out",
                  "deliverables", "success_measures", "budget_total",
                  "start_date", "end_date", "assumptions", "constraints",
                  "governance", "change_control"},
      "wbs": [{"id", "parent", "level", "name", "acceptance", "owner", "cost"}],
      "activities": [{"id", "name", "wbs", "duration", "predecessors", "resource"}],
      "resources": [{"name", "role", "capacity"}],
      "raci": [{"activity", "role", "letter"}],
      "risks": [{"id", "description", "likelihood", "impact", "response", "owner"}],
      "options": {"pert": false, "crash_target": null, "contingency_pct": null}
    }

Cost is carried by the **work package** (a WBS leaf).  An activity does not
carry a second cost; the cost plan is the WBS roll-up.  A parent node with a
cost is refused because the parent's cost is the sum of its children.
"""

import copy

FORMAT = "bp-project-plan/1"
CURRENCY_DEFAULT = "USD"
RACI_LETTERS = ("R", "A", "C", "I")
RISK_LEVELS = ("Low", "Medium", "High", "Critical")


def empty():
    """A blank record with the shape the composer expects."""
    return {
        "format": FORMAT,
        "charter": {"title": "", "objective": "", "sponsor": "", "scope_in": [],
                    "scope_out": [], "deliverables": [], "success_measures": [],
                    "budget_total": 0, "currency": CURRENCY_DEFAULT,
                    "start_date": "", "end_date": "", "assumptions": [],
                    "constraints": [], "governance": "", "change_control": ""},
        "wbs": [], "activities": [], "resources": [], "raci": [], "risks": [],
        "options": {"pert": False, "crash_target": None, "contingency_pct": None},
    }


def _text(value, limit=2000):
    return " ".join(str(value or "").split()).strip()[:limit]


def _items(value, limit=40):
    if isinstance(value, list):
        return [_text(item, 300) for item in value if _text(item, 300)][:limit]
    text = _text(value, 4000)
    return [_text(part, 300) for part in text.replace("\n", ";").split(";") if _text(part, 300)][:limit]


def _number(value):
    try:
        return float(str(value or "0").replace(",", "").strip() or 0)
    except (TypeError, ValueError):
        return None


def normalise(record):
    """A clean copy.  It never adds a field the student did not supply."""
    source = copy.deepcopy(record) if isinstance(record, dict) else {}
    base = empty()
    charter = source.get("charter") if isinstance(source.get("charter"), dict) else {}
    for key in base["charter"]:
        if key in ("scope_in", "scope_out", "deliverables", "success_measures",
                   "assumptions", "constraints"):
            base["charter"][key] = _items(charter.get(key))
        elif key == "budget_total":
            base["charter"][key] = _number(charter.get(key)) or 0
        elif key == "currency":
            base["charter"][key] = _text(charter.get(key), 8).upper() or CURRENCY_DEFAULT
        else:
            base["charter"][key] = _text(charter.get(key))
    base["wbs"] = []
    for row in source.get("wbs") or []:
        if not isinstance(row, dict):
            continue
        base["wbs"].append({
            "id": _text(row.get("id"), 20),
            "parent": _text(row.get("parent"), 20) or None,
            "level": int(row.get("level") or 0) if str(row.get("level") or "").isdigit() else None,
            "name": _text(row.get("name"), 300),
            "acceptance": _text(row.get("acceptance"), 500),
            "owner": _text(row.get("owner"), 120),
            "cost": _number(row.get("cost")),
        })
    base["activities"] = []
    for row in source.get("activities") or []:
        if not isinstance(row, dict):
            continue
        preds = row.get("predecessors")
        if isinstance(preds, str):
            preds = [part.strip() for part in preds.split(",") if part.strip()]
        base["activities"].append({
            "id": _text(row.get("id"), 20),
            "name": _text(row.get("name"), 300),
            "wbs": _text(row.get("wbs"), 20),
            "duration": _number(row.get("duration")),
            "predecessors": [_text(p, 20) for p in (preds or []) if _text(p, 20)],
            "resource": _text(row.get("resource"), 120),
            "optimistic": _number(row.get("optimistic")),
            "most_likely": _number(row.get("most_likely")),
            "pessimistic": _number(row.get("pessimistic")),
            "normal_duration": _number(row.get("normal_duration")),
            "crash_duration": _number(row.get("crash_duration")),
            "crash_cost": _number(row.get("crash_cost")),
        })
    base["resources"] = [{"name": _text(row.get("name"), 120),
                          "role": _text(row.get("role"), 120),
                          "capacity": _number(row.get("capacity"))}
                         for row in source.get("resources") or [] if isinstance(row, dict)]
    base["raci"] = [{"activity": _text(row.get("activity"), 20),
                     "role": _text(row.get("role"), 120),
                     "letter": _text(row.get("letter"), 1).upper()}
                    for row in source.get("raci") or [] if isinstance(row, dict)]
    base["risks"] = []
    for row in source.get("risks") or []:
        if not isinstance(row, dict):
            continue
        base["risks"].append({
            "id": _text(row.get("id"), 20),
            "description": _text(row.get("description"), 500),
            "likelihood": _text(row.get("likelihood"), 20),
            "impact": _text(row.get("impact"), 20),
            "response": _text(row.get("response"), 500),
            "owner": _text(row.get("owner"), 120),
        })
    options = source.get("options") if isinstance(source.get("options"), dict) else {}
    base["options"] = {"pert": bool(options.get("pert")),
                       "crash_target": _number(options.get("crash_target")),
                       "contingency_pct": _number(options.get("contingency_pct"))}
    return base


def validate(record):
    """Every problem that would make the plan dishonest or unbuildable."""
    record = record or {}
    problems = []
    charter = record.get("charter") or {}
    for key, label in (("title", "a project title"), ("objective", "a charter objective"),
                       ("sponsor", "a sponsor")):
        if not _text(charter.get(key)):
            problems.append("the charter needs " + label)
    for key, label in (("scope_in", "what is in scope"), ("scope_out", "what is out of scope"),
                       ("deliverables", "at least one deliverable"),
                       ("success_measures", "at least one success measure")):
        if not charter.get(key):
            problems.append("the charter needs " + label)
    if not _number(charter.get("budget_total")):
        problems.append("the charter needs a declared budget total")

    nodes = {}
    for row in record.get("wbs") or []:
        node_id = _text(row.get("id"))
        if not node_id:
            problems.append("a WBS row has no id")
            continue
        if node_id in nodes:
            problems.append("duplicate WBS id " + node_id)
            continue
        nodes[node_id] = row
    if not nodes:
        problems.append("the WBS needs at least one row")
    for node_id, row in nodes.items():
        parent = _text(row.get("parent"))
        if parent and parent not in nodes:
            problems.append("WBS " + node_id + " cites a parent that does not exist: " + parent)
        if parent == node_id:
            problems.append("WBS " + node_id + " cannot be its own parent")
    # cycles
    for node_id in nodes:
        seen, current = set(), node_id
        while current:
            if current in seen:
                problems.append("the WBS contains a cycle at " + node_id)
                break
            seen.add(current)
            current = _text((nodes.get(current) or {}).get("parent"))
    leaves = [row for row in nodes.values() if not any(_text(other.get("parent")) == _text(row.get("id"))
                                                       for other in nodes.values())]
    for row in leaves:
        node_id = _text(row.get("id"))
        if not _text(row.get("owner")):
            problems.append("work package " + node_id + " has no owner")
        if (_number(row.get("cost")) or 0) <= 0:
            problems.append("work package " + node_id + " has no cost")
        if not _text(row.get("acceptance")):
            problems.append("work package " + node_id + " has no acceptance test")
    for node_id, row in nodes.items():
        has_children = any(_text(other.get("parent")) == node_id for other in nodes.values())
        if has_children and _number(row.get("cost")):
            problems.append("WBS " + node_id + " is a parent; its cost is the sum of its children, so leave it blank")

    activity_ids = set()
    for row in record.get("activities") or []:
        activity_id = _text(row.get("id"))
        if not activity_id:
            problems.append("an activity has no id")
            continue
        if activity_id in activity_ids:
            problems.append("duplicate activity id " + activity_id)
        activity_ids.add(activity_id)
        if _text(row.get("wbs")) not in nodes:
            problems.append("activity " + activity_id + " points at a WBS node that does not exist")
        if _number(row.get("duration")) is None and not (
                _number(row.get("optimistic")) is not None
                and _number(row.get("most_likely")) is not None
                and _number(row.get("pessimistic")) is not None):
            problems.append("activity " + activity_id + " has no duration")
    for row in record.get("activities") or []:
        activity_id = _text(row.get("id"))
        for pred in row.get("predecessors") or []:
            if pred not in activity_ids:
                problems.append("activity " + activity_id + " cites an unknown predecessor " + pred)
            if pred == activity_id:
                problems.append("activity " + activity_id + " cannot be its own predecessor")

    roles = set()
    for row in record.get("resources") or []:
        for key in ("name", "role"):
            if _text(row.get(key)):
                roles.add(_text(row.get(key)))
    by_activity = {}
    for row in record.get("raci") or []:
        activity_id = _text(row.get("activity"))
        letter = _text(row.get("letter")).upper()
        role = _text(row.get("role"))
        if activity_id not in activity_ids:
            problems.append("RACI row names an activity that does not exist: " + activity_id)
        if letter not in RACI_LETTERS:
            problems.append("RACI letter must be R, A, C or I: " + (letter or "(blank)"))
        if roles and role not in roles:
            problems.append("RACI role is not in the resource list: " + role)
        by_activity.setdefault(activity_id, []).append(letter)
    for activity_id in activity_ids:
        letters = by_activity.get(activity_id, [])
        if letters.count("A") != 1:
            problems.append("activity " + activity_id + " needs exactly one accountable role (A)")
        if "R" not in letters:
            problems.append("activity " + activity_id + " needs at least one responsible role (R)")

    for row in record.get("risks") or []:
        risk_id = _text(row.get("id")) or "(no id)"
        for key, label in (("description", "a description"), ("response", "a response"),
                           ("owner", "an owner")):
            if not _text(row.get(key)):
                problems.append("risk " + risk_id + " needs " + label)
        for key in ("likelihood", "impact"):
            value = _text(row.get(key))
            if value and value not in RISK_LEVELS:
                problems.append("risk " + risk_id + " " + key + " must be Low, Medium, High or Critical")
    return problems


def rollup(record):
    """Cost by WBS node, rolled up from the leaves.  No estimate is added."""
    nodes = {row.get("id"): dict(row) for row in (record or {}).get("wbs") or []}
    children = {}
    for node_id, row in nodes.items():
        parent = _text(row.get("parent"))
        if parent:
            children.setdefault(parent, []).append(node_id)
    computed = {}
    visiting = set()

    def cost_of(node_id):
        if node_id in computed:
            return computed[node_id]
        if node_id in visiting:
            return 0.0
        visiting.add(node_id)
        kids = children.get(node_id) or []
        if kids:
            total = sum(cost_of(kid) for kid in kids)
        else:
            total = _number(nodes[node_id].get("cost")) or 0.0
        visiting.discard(node_id)
        computed[node_id] = total
        return total

    for node_id in nodes:
        cost_of(node_id)
    roots = [node_id for node_id, row in nodes.items() if not _text(row.get("parent"))]
    total = sum(computed.get(root, 0.0) for root in roots)
    leaves = [node_id for node_id in nodes
              if not any(_text(row.get("parent")) == node_id for row in nodes.values())]
    uncosted = [node_id for node_id in leaves
                if (_number(nodes[node_id].get("cost")) or 0) <= 0]
    budget = _number((record or {}).get("charter", {}).get("budget_total")) or 0.0
    contingency_pct = _number(((record or {}).get("options") or {}).get("contingency_pct"))
    contingency = total * (contingency_pct or 0) / 100.0 if contingency_pct else 0.0
    return {"by_node": computed, "total": total, "contingency": contingency,
            "with_contingency": total + contingency, "budget": budget,
            "variance": total - budget, "uncosted": uncosted}


def schedule_inputs(record, pert=None):
    """The activity rows the frozen CPM method accepts."""
    options = (record or {}).get("options") or {}
    three = bool(options.get("pert") if pert is None else pert)
    rows = []
    for row in (record or {}).get("activities") or []:
        item = {"id": _text(row.get("id")), "predecessors": ",".join(row.get("predecessors") or [])}
        if three:
            item.update({"optimistic": str(row.get("optimistic") or ""),
                         "most_likely": str(row.get("most_likely") or ""),
                         "pessimistic": str(row.get("pessimistic") or "")})
        else:
            item["duration"] = str(row.get("duration") or "")
        rows.append(item)
    return {"estimate": "three_point" if three else "single", "activities": rows}


def schedule(record, run):
    """Run CPM through the attached core, or return the core's refusal.

    ``run(method, inputs)`` is the same runner the rest of the product uses; this
    module never re-implements the method and never invents a date.
    """
    if run is None:
        return {"ok": False, "error": "the computation core is not attached"}
    try:
        return {"ok": True, "result": run("cpm_schedule", schedule_inputs(record))}
    except Exception as error:  # the core's DataError is a refusal, not a crash
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
        return "%s %s" % (currency, "{:,.2f}".format(float(value)))
    except (TypeError, ValueError):
        return "not declared"


def wbs_rows(record):
    return [[row.get("id") or "", "  " * max(0, int(row.get("level") or 1) - 1) + (row.get("name") or ""),
             row.get("owner") or "not assigned", _money(row.get("cost"), (record.get("charter") or {}).get("currency")),
             row.get("acceptance") or "not stated"] for row in (record or {}).get("wbs") or []]


def cost_rows(record, rolled):
    currency = ((record or {}).get("charter") or {}).get("currency") or "USD"
    rows = []
    for row in (record or {}).get("wbs") or []:
        node_id = row.get("id")
        rows.append([node_id or "", row.get("name") or "", _money(rolled["by_node"].get(node_id, 0), currency)])
    rows.append(["", "Total", _money(rolled["total"], currency)])
    if rolled.get("contingency"):
        rows.append(["", "Contingency", _money(rolled["contingency"], currency)])
        rows.append(["", "Total with contingency", _money(rolled["with_contingency"], currency)])
    return rows


def schedule_rows(record, result):
    """One row per activity with the core's own early/late dates and float."""
    rows = []
    for row in (record or {}).get("activities") or []:
        activity_id = row.get("id") or ""
        rows.append([activity_id, row.get("name") or "",
                     str(row.get("duration") if row.get("duration") is not None else "three-point"),
                     str(result.get("es_" + activity_id, "")), str(result.get("ef_" + activity_id, "")),
                     str(result.get("ls_" + activity_id, "")), str(result.get("lf_" + activity_id, "")),
                     str(result.get("float_" + activity_id, "")),
                     "yes" if str(result.get("critical_" + activity_id, "")) in ("1", "1.0", "True") else "no"])
    return rows


def raci_rows(record):
    roles = []
    for row in (record or {}).get("resources") or []:
        role = row.get("role") or row.get("name")
        if role and role not in roles:
            roles.append(role)
    by_activity = {}
    for row in (record or {}).get("raci") or []:
        by_activity.setdefault(row.get("activity"), {})[row.get("role")] = row.get("letter")
    rows = [[row.get("id") or "", row.get("name") or ""] +
            [by_activity.get(row.get("id"), {}).get(role, "") for role in roles]
            for row in (record or {}).get("activities") or []]
    return ["Activity", "Name"] + roles, rows


def risk_rows(record):
    return [[row.get("id") or "", row.get("description") or "", row.get("likelihood") or "",
             row.get("impact") or "", row.get("response") or "", row.get("owner") or ""]
            for row in (record or {}).get("risks") or []]


def summary(record, rolled, scheduled):
    charter = (record or {}).get("charter") or {}
    return {
        "project": charter.get("title") or "",
        "wbs_nodes": len((record or {}).get("wbs") or []),
        "work_packages": len(rolled.get("uncosted") or []) + sum(
            1 for row in (record or {}).get("wbs") or []
            if not any(other.get("parent") == row.get("id") for other in (record or {}).get("wbs") or [])),
        "activities": len((record or {}).get("activities") or []),
        "total_cost": rolled.get("total"),
        "budget": rolled.get("budget"),
        "project_duration": (scheduled or {}).get("project_duration"),
        "critical_count": (scheduled or {}).get("critical_count"),
    }
