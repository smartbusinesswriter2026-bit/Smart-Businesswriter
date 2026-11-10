"""Read a quality worksheet from the brief (product layer).

FMEA, Five-S and PDCA need a table the student already wrote.  The reader takes
that table and names a missing column; it never guesses a score.  The arithmetic
is the frozen core's (`framework_calc`), never this module's.
"""

import re

FMEA_FIELDS = {
    "id": ("id", "no", "#"),
    "failure": ("failure mode", "potential failure", "failure"),
    "severity": ("severity", "s"),
    "occurrence": ("occurrence", "o"),
    "detection": ("detection", "d"),
    "action": ("recommended action", "action"),
}
FIVE_S_FIELDS = {
    "category": ("s category", "category", "the s", "s"),
    "criterion": ("criterion", "check"),
    "score": ("score",),
    "maximum": ("maximum", "max", "possible"),
}
PDCA_FIELDS = {
    "measure": ("measure", "metric"),
    "baseline": ("baseline",),
    "target": ("target", "goal"),
    "result": ("result", "actual"),
}


def _split(line):
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


def _column(low, words):
    for word in words:
        for index, cell in enumerate(low):
            if cell == word or cell.startswith(word):
                return index
    return None


def _number(text):
    raw = str(text or "").strip()
    if not raw or raw.lower() in ("n/a", "na", "-", "?", "unknown", "not assessed"):
        return None
    raw = raw.replace(",", "").replace("%", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _read(text, fields, required, numeric):
    lines = [line for line in str(text or "").splitlines() if line.strip()]
    header = None
    for index, line in enumerate(lines):
        cells = _split(line)
        low = [cell.lower().strip(" *`") for cell in cells]
        if len(cells) < 3:
            continue
        if all(_column(low, fields[name]) is not None for name in required):
            header = (index, low)
            break
    if header is None:
        return {"ok": False, "rows": [], "problems": [
            "No table with the columns %s was found." % ", ".join(required)]}
    index, low = header
    columns = {name: _column(low, words) for name, words in fields.items()}
    rows, problems = [], []
    for line in lines[index + 1:]:
        cells = _split(line)
        if len(cells) < 3:
            continue
        row = {}
        for name, column in columns.items():
            row[name] = cells[column].strip() if column is not None and column < len(cells) else ""
        if not any(row.get(name) for name in required):
            continue
        for name in numeric:
            row[name] = _number(row.get(name))
        missing = [name for name in numeric if row.get(name) is None]
        if missing:
            problems.append("%s: no %s" % (row.get(required[0]) or "row", ", ".join(missing)))
        rows.append(row)
    return {"ok": bool(rows), "rows": rows, "problems": problems,
            "columns": [name for name, column in columns.items() if column is not None]}


def read_fmea(text):
    """The FMEA rows: id, failure mode, severity, occurrence, detection and action."""
    return _read(text, FMEA_FIELDS, ("failure", "severity", "occurrence", "detection"),
                 ("severity", "occurrence", "detection"))


def read_five_s(text):
    """The Five-S scorecard: S category, criterion, score and maximum."""
    return _read(text, FIVE_S_FIELDS, ("category", "criterion", "score", "maximum"),
                 ("score", "maximum"))


def read_pdca(text):
    """The PDCA measure table: measure, baseline, target and result."""
    return _read(text, PDCA_FIELDS, ("measure", "baseline"),
                 ("baseline", "target", "result"))
