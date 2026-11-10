"""Read a portfolio table from the brief (product layer).

BCG and GE-McKinsey need a per-unit table: unit, market, growth and share.  The
reader takes the table the student already wrote; it never guesses a missing
figure.  A line that is not a table is ignored, and a missing column is returned
by name so the paper can ask for it.

The reader does no arithmetic: a percentage is normalised to a decimal, and a
number is parsed; every division, comparison and weighted total belongs to the
frozen core (`framework_calc`).
"""

import re

#: Header words per field, in the order the reader looks for them.
FIELDS = {
    "unit": ("unit", "business unit", "business", "product", "segment",
             "portfolio unit", "portfolio"),
    "market": ("served market", "market definition", "market"),
    "growth": ("market growth", "growth rate", "growth"),
    "own_share": ("own share", "market share", "share"),
    "competitor_share": ("largest competitor share", "top competitor share",
                         "competitor share", "competitor"),
    "revenue": ("revenue", "sales"),
    "market_size": ("market size", "market sales", "total market"),
    "competitor_revenue": ("largest competitor sales", "competitor sales",
                           "largest competitor revenue", "competitor revenue"),
}


def _split(line):
    """Split one table line on a pipe, tab, semicolon or a wide run of spaces."""
    text = str(line or "").strip()
    if not text:
        return []
    if "|" in text:
        cells = [cell.strip() for cell in text.strip("|").split("|")]
    elif "\t" in text:
        cells = [cell.strip() for cell in text.split("\t")]
    elif ";" in text:
        cells = [cell.strip() for cell in text.split(";")]
    else:
        cells = [cell.strip() for cell in re.split(r"\s{3,}", text)]
    return [cell for cell in cells if cell != ""]


def _lower(cells):
    return [cell.lower().strip(" *`") for cell in cells]


def _column(low, field):
    """The index of the column for a field, preferring the most specific word."""
    for word in FIELDS[field]:
        for index, cell in enumerate(low):
            if cell == word or cell.startswith(word):
                return index
    # A short header such as "share" is the own share only when no competitor
    # column has already claimed it; the caller handles the ambiguity by name.
    return None


def _number(text):
    """A decimal from a written figure; a percent is divided by 100."""
    raw = str(text or "").strip()
    if not raw or raw.lower() in ("n/a", "na", "-", "?", "unknown"):
        return None
    percent = raw.endswith("%")
    raw = (raw.replace("%", "").replace(",", "").replace("$", "")
           .replace("\u20ac", "").replace("\u00a3", "").strip())
    try:
        value = float(raw)
    except ValueError:
        return None
    if percent or (1 < value <= 100):
        value = value / 100
    return value


def read(text):
    """The portfolio table in the brief, or a named reason it is not there.

    Returns ``{"ok", "units", "columns", "problems"}``.  A unit with a missing
    field keeps the missing field as ``None``; the caller names it, never fills
    it.
    """
    lines = [line for line in str(text or "").splitlines() if line.strip()]
    header = None
    for index, line in enumerate(lines):
        cells = _split(line)
        low = _lower(cells)
        if len(cells) < 3:
            continue
        if (_column(low, "unit") is not None and _column(low, "growth") is not None
                and (_column(low, "own_share") is not None
                     or _column(low, "competitor_share") is not None)):
            header = (index, cells, low)
            break
    if header is None:
        return {"ok": False, "units": [], "columns": [],
                "problems": ["No portfolio table with Unit, Growth and Share columns was found."]}
    index, cells, low = header
    columns = {field: _column(low, field) for field in FIELDS}
    units = []
    problems = []
    for line in lines[index + 1:]:
        row = _split(line)
        if not row:
            continue
        if len(row) < 3:
            continue
        unit = row[columns["unit"]] if columns["unit"] is not None and columns["unit"] < len(row) else ""
        if not unit:
            continue
        record = {"unit": unit.strip()}
        for field in ("market", "growth", "own_share", "competitor_share",
                      "revenue", "market_size", "competitor_revenue"):
            column = columns.get(field)
            raw = row[column] if column is not None and column < len(row) else ""
            record[field] = raw.strip() or None
        record["growth"] = _number(record["growth"])
        record["own_share"] = _number(record["own_share"])
        record["competitor_share"] = _number(record["competitor_share"])
        record["revenue"] = _number(record["revenue"])
        record["market_size"] = _number(record["market_size"])
        record["competitor_revenue"] = _number(record["competitor_revenue"])
        missing = [field.replace("_", " ") for field in ("growth", "own_share",
                                                         "competitor_share")
                   if record.get(field) is None]
        # A share-only table is enough for relative share; revenue and market
        # size are only required when neither share is declared.
        if (record.get("revenue") is None and record.get("market_size") is None
                and not (record.get("own_share") is not None
                         and record.get("competitor_share") is not None)):
            missing.append("revenue or market size")
        if missing:
            problems.append("%s: no %s" % (record["unit"], ", ".join(missing)))
        units.append(record)
    if not units:
        problems.append("The table has no unit rows.")
    return {"ok": bool(units), "units": units,
            "columns": [field for field, column in columns.items() if column is not None],
            "problems": problems}
