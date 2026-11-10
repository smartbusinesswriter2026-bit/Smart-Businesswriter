"""Read a feasibility brief into the three-table record, and never fill a cell.

The simplified feasibility route is table-first, like the project plan.  The
brief states the project in labels, a market table and a cost table; this reader
places each labelled fact and each table row on the field its own name matches.
A row fills nothing else, and a missing demand, price, fixed cost, variable cost
or investment item stays missing for `feasibility_plan.validate` to name.

Only one thing is derived, and it is structural: a table row with no separate id
is known by its own label, which is what the brief shows.
"""

import re

FORMAT = "bp-feasibility-read/1"

#: A header cell, normalised: "(USD)" dropped, punctuation to spaces.
def _norm(value):
    text = re.sub(r"\(.*?\)", " ", str(value or "")).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


#: Header words that make a line a table header.
ITEM_WORDS = ("item", "name", "metric", "description", "cost", "investment", "expense")
VALUE_WORDS = ("value", "amount", "figure", "units", "estimate")
HEADER_WORDS = set(ITEM_WORDS + VALUE_WORDS)

_MONEY = re.compile(r"^(?:(?:usd|php|eur|gbp|\$|€|£)\s*)?(-?[\d,]+(?:\.\d+)?)\s*([km])?$", re.I)


def _number(value):
    """A declared number, or None.  No unit is guessed beyond a stated k/m."""
    text = str(value or "").strip()
    text = text.replace("USD", "").replace("usd", "").replace("$", "").strip()
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
    words = [_norm(cell) for cell in cells or []]
    known = sum(1 for word in words if word in HEADER_WORDS)
    return known >= 2 or (known >= 1 and len(cells) == 2)


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


def _kind(columns):
    """What a table is, from its own header words.  Costs win over metrics."""
    words = [_norm(column) for column in columns]
    joined = " ".join(words)
    if any(word in joined for word in ("amount", "cost", "investment", "expense")):
        return "costs"
    if any(word in joined for word in ("value", "metric", "figure", "units", "estimate")):
        return "market"
    return None


def _label(norm):
    """The field a row label names, or None."""
    if "target market" in norm or norm in ("market", "audience", "customers"):
        return "target_market"
    if "demand" in norm or norm in ("units", "volume", "expected units", "expected sales"):
        return "demand"
    if "price" in norm or norm in ("unit price", "selling price"):
        return "price"
    if "variable" in norm:
        return "variable"
    if "fixed" in norm or "overhead" in norm:
        return "fixed"
    return None


#: The labelled facts the brief can state besides the tables.
LABELS = (
    ("name", ("project name", "project", "feasibility study", "title", "name of the project")),
    ("description", ("project description", "description", "what the project is about", "purpose")),
    ("location", ("location", "site", "address")),
    ("proponents", ("proponents", "proposed by", "proponent", "owner", "sponsor")),
    ("currency", ("currency",)),
    ("target_market", ("target market", "market", "customers", "audience")),
    ("demand", ("demand", "demand estimate", "expected demand", "units a year", "annual demand")),
    ("price", ("price", "unit price", "selling price", "price per unit")),
    ("fixed", ("fixed cost", "fixed costs", "annual fixed cost", "monthly fixed cost")),
    ("variable", ("variable cost", "variable cost per unit", "unit variable cost")),
    ("technology", ("technology", "method", "process")),
    ("capacity", ("capacity",)),
    ("inputs", ("inputs", "resources", "materials")),
    ("team", ("management team", "team")),
    ("skills", ("skills",)),
    ("permits", ("permits", "licenses", "licences")),
    ("regulations", ("regulations", "regulatory")),
    ("risks", ("risks", "risk", "key risks")),
)


def _labelled(lines, table_lines):
    """The labelled facts, from lines that are not table rows."""
    values, declared = {}, {"risks": []}
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
        if not field:
            continue
        if field == "risks":
            declared["risks"] = [part.strip(" .") for part in re.split(r"[;•]", value) if part.strip(" .")]
        elif field in ("demand", "price", "fixed", "variable"):
            number = _number(value)
            if number is not None:
                values[field] = number
        elif field == "currency":
            values[field] = value.strip().upper()[:8]
        elif field in ("name", "description", "location", "proponents", "target_market"):
            values[field] = value
        else:
            declared[field] = value
    return values, declared


def _title_from_prose(text):
    patterns = (
        r"feasibility study\s+(?:for|of|called|named|titled)\s+([^\n.;]{2,90})",
        r"project\s+(?:title|name)\s+(?:is|:)\s*([^\n.;]{2,90})",
        r"project\s*:\s*([^\n.;]{2,90})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
    return ""


def read(brief):
    """The three-table record the brief states."""
    text = str(brief or "")
    lines = text.splitlines()
    table_lines = {line for line in lines
                   if _cells(line) and _header(_cells(line) or [])}
    # rows are table lines too, but a labelled row is read by the table loop
    label_values, declared = _labelled(lines, table_lines)

    market = {"target_market": label_values.get("target_market", ""),
              "demand": label_values.get("demand"),
              "price": label_values.get("price")}
    operating = {"fixed": label_values.get("fixed"), "variable": label_values.get("variable")}
    costs = []
    for table in _tables(lines):
        columns = table["columns"]
        kind = _kind(columns)
        if kind == "costs":
            for row in table["rows"]:
                label = _norm(row[0] if row else "")
                field = _label(label)
                if field in ("fixed", "variable", "demand", "price"):
                    if len(row) > 1:
                        number = _number(row[1])
                        if number is None:
                            continue
                        if field == "fixed":
                            operating["fixed"] = number
                        elif field == "variable":
                            operating["variable"] = number
                        else:
                            market[field] = number
                    continue
                amount = _number(row[1]) if len(row) > 1 else None
                if str(row[0] if row else "").strip() and amount is not None:
                    costs.append({"item": str(row[0]).strip(), "amount": amount})
        elif kind == "market":
            for row in table["rows"]:
                field = _label(_norm(row[0] if row else ""))
                if field and len(row) > 1:
                    if field in ("demand", "price"):
                        number = _number(row[1])
                        if number is not None:
                            market[field] = number
                    else:
                        market[field] = str(row[1]).strip()

    project = {"name": label_values.get("name", ""),
               "description": label_values.get("description", ""),
               "location": label_values.get("location", ""),
               "proponents": label_values.get("proponents", ""),
               "currency": label_values.get("currency", "USD")}
    if not project["name"]:
        title = _title_from_prose(text)
        if title:
            project["name"] = title
    return {
        "format": FORMAT,
        "project": project,
        "market": market,
        "costs": costs,
        "operating": operating,
        "declared": declared,
    }


def has_tables(record):
    """Whether the record carries the three-table shape this route needs."""
    record = record or {}
    market = record.get("market") or {}
    operating = record.get("operating") or {}
    return bool((market.get("demand") is not None and market.get("price") is not None)
                or (operating.get("fixed") is not None and operating.get("variable") is not None)
                or record.get("costs"))
