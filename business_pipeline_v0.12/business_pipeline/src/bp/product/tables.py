"""Business tables: a figure whose cells are stored strings.

A table is not a chart.  It carries text and recorded values, not geometry, so it
has no axis and no scale to get wrong.  What it can get wrong is a number that was
never recorded, so the spec allows exactly two kinds of cell:

* a **label** the author wrote - which may not contain a digit, so a figure cannot
  smuggle a value into a caption or a cell;
* a **reference** to a stored artifact, resolved at render time from the case's
  recorded values.  A reference to something the case does not hold prints
  "not recorded" rather than a blank or a guess.

The columns are declared, so a table says what it holds; a row must fill every
column, so a short row is refused rather than silently padded.

Rendered as a Word table in the paper, a native table on a slide, and cells in a
workbook.  The same spec is the source for all three.
"""

FORMAT = "bp-table/1"
#: A table wider than this is a spreadsheet, not a figure.
MAX_COLUMNS = 8
MAX_ROWS = 40


class TableError(ValueError):
    """The table spec cannot be drawn honestly."""


def _text(value, what):
    if not isinstance(value, str) or not value.strip():
        raise TableError("%s must be non-empty text" % what)
    text = value.strip()
    if any(character.isdigit() for character in text):
        raise TableError("%s may not contain digits: numbers come only from a stored artifact (%r)"
                         % (what, text))
    return text


def _cell(cell, where):
    if isinstance(cell, str):
        return _text(cell, where)
    if isinstance(cell, dict):
        artifact = cell.get("artifact")
        if not isinstance(artifact, str) or not artifact.strip():
            raise TableError("%s must be text or an object naming a stored artifact" % where)
        return {"artifact": artifact.strip()}
    raise TableError("%s must be text or an object naming a stored artifact" % where)


def validate_spec(spec):
    """Check a table spec against its own rules."""
    if not isinstance(spec, dict):
        raise TableError("table spec must be an object")
    if spec.get("format", FORMAT) != FORMAT:
        raise TableError("unsupported table format %r, expected %r"
                         % (spec.get("format"), FORMAT))
    title = _text(spec.get("title"), "table title")
    columns = spec.get("columns")
    if not isinstance(columns, list) or len(columns) < 2:
        raise TableError("a table needs at least two columns")
    if len(columns) > MAX_COLUMNS:
        raise TableError("a table carries at most %d columns" % MAX_COLUMNS)
    clean_columns = [_text(column, "column %d" % (index + 1))
                     for index, column in enumerate(columns)]
    if len(set(clean_columns)) != len(clean_columns):
        raise TableError("column names must be unique")
    rows = spec.get("rows")
    if not isinstance(rows, list) or not rows:
        raise TableError("a table needs a non-empty 'rows' list")
    if len(rows) > MAX_ROWS:
        raise TableError("a table carries at most %d rows" % MAX_ROWS)
    clean_rows = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TableError("rows[%d] must be an object" % index)
        cells = row.get("cells")
        if not isinstance(cells, list) or len(cells) != len(clean_columns):
            raise TableError("rows[%d] must fill all %d columns"
                             % (index, len(clean_columns)))
        clean_rows.append({"cells": [_cell(cell, "rows[%d] cell %d" % (index, column + 1))
                                     for column, cell in enumerate(cells)]})
    return title, clean_columns, clean_rows


def _stored(rows, key):
    for row in rows:
        if row.get("metric") == key or row.get("id") == key:
            return row.get("value")
    return None


def resolve(spec, bundle):
    """The table as printable strings, with every artifact cell read from the record."""
    from . import export as case_export

    title, columns, rows = validate_spec(spec)
    stored = case_export.artifact_rows(bundle)
    out = []
    for row in rows:
        cells = []
        for cell in row["cells"]:
            if isinstance(cell, dict):
                value = _stored(stored, cell["artifact"])
                cells.append("not recorded" if value is None else str(value))
            else:
                cells.append(cell)
        out.append(cells)
    return {"title": title, "columns": columns, "rows": out}


def sources(spec):
    """Every artifact id the table reads, in the order it names them."""
    _, _, rows = validate_spec(spec)
    found = []
    for row in rows:
        for cell in row["cells"]:
            if isinstance(cell, dict):
                found.append(cell["artifact"])
    return found
