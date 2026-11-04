"""Read a workbook back, so a renderer can be tested on what it actually wrote.

The render lane writes `.xlsx` bytes with `zipfile` and XML (no third-party package; see
`tests/test_product_boundary.py`).  A test that only asserts "a file exists" proves nothing, so this
helper unzips the workbook and returns its sheets as rows of cells — text as `str`, numeric cells as
`Decimal`, empty cells as `""`.

It reads the shapes a hand-rolled writer can emit: inline strings, shared strings, numeric cells,
booleans, and cells with a style but no value.  Both the current text-dump writer (`inlineStr`
everywhere) and a typed writer (numbers in `<v>`) come back the same way, so the render lane can
upgrade the writer without changing its tests.

Not a test module: `unittest discover` ignores it (the pattern is `test*.py`).
"""

import io
import re
import zipfile
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"

#: A written amount: optional parentheses for a negative, thousands separators, decimals.
_AMOUNT = re.compile(r"^\(?-?\d[\d,]*(?:\.\d+)?\)?$")


def _shared_strings(archive):
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(node.text or "" for node in item.iter("{%s}t" % MAIN))
            for item in root.findall("{%s}si" % MAIN)]


def _sheet_targets(archive):
    """Relationship id -> worksheet path, as the workbook names them."""
    root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {}
    for link in root.findall("{%s}Relationship" % PKG):
        target = link.get("Target") or ""
        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = "xl/" + target
        targets[link.get("Id")] = target
    return targets


def _sheets(archive):
    root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    targets = _sheet_targets(archive)
    found = []
    for sheet in root.find("{%s}sheets" % MAIN).findall("{%s}sheet" % MAIN):
        path = targets.get(sheet.get("{%s}id" % REL))
        if path:
            found.append((sheet.get("name") or "Sheet", path))
    return found


def _column_index(reference):
    letters = "".join(ch for ch in str(reference or "") if ch.isalpha()).upper()
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch) - 64)
    return max(index - 1, 0)


def _cell_value(cell, shared):
    """The cell's value: Decimal for a number, str for text, "" for empty."""
    kind = cell.get("t")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.iter("{%s}t" % MAIN))
    raw = cell.find("{%s}v" % MAIN)
    if raw is None or raw.text is None:
        return ""
    text = raw.text
    if kind == "s":
        try:
            return shared[int(text)]
        except (ValueError, IndexError):
            return text
    if kind == "b":
        return text == "1"
    if kind == "str":
        return text
    try:
        return Decimal(text)
    except InvalidOperation:
        return text


def _rows(archive, path, shared):
    root = ElementTree.fromstring(archive.read(path))
    rows = []
    for row in root.iter("{%s}row" % MAIN):
        cells = {}
        for cell in row.findall("{%s}c" % MAIN):
            cells[_column_index(cell.get("r"))] = _cell_value(cell, shared)
        width = (max(cells) + 1) if cells else 0
        rows.append([cells.get(index, "") for index in range(width)])
    return rows


def read(data):
    """The workbook as an ordered dict of sheet name -> rows (a list of lists of cells)."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        shared = _shared_strings(archive)
        return {name: _rows(archive, path, shared) for name, path in _sheets(archive)}


def numbers(rows):
    """Every numeric cell on a sheet, in row order."""
    return [cell for row in rows for cell in row
            if isinstance(cell, Decimal) and not isinstance(cell, bool)]


def amount(text):
    """Parse a written amount ("9,000.00", "(60,000.00)") to Decimal, or None."""
    written = str(text or "").strip()
    if not _AMOUNT.match(written):
        return None
    negative = written.startswith("(") and written.endswith(")")
    cleaned = written.strip("()").replace(",", "")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -value if negative else value


def numbers_in_text(rows):
    """Amounts written as text (a cell like "9,000.00"), as Decimals."""
    found = []
    for row in rows:
        for cell in row:
            if isinstance(cell, str):
                value = amount(cell)
                if value is not None:
                    found.append(value)
    return found


def line_value(line):
    """(label, Decimal) for a rendered line that ends in an amount, else (line, None).

    The statement text puts the amount last and pads with two or more spaces, e.g.
    ``"  Cash                                              104,600.00"``.  A line with trailing prose
    after the amount (the equity movement lines) returns None: it is not a simple label/amount row.
    """
    text = str(line or "").rstrip()
    match = re.match(r"^(.*?)\s{2,}(\S+)$", text)
    if not match:
        return text.strip(), None
    value = amount(match.group(2))
    if value is None:
        return text.strip(), None
    return match.group(1).strip(), value


def statement_rows(text):
    """The label/amount pairs of a rendered statement, skipping headings and prose lines."""
    return [(label, value) for label, value in (line_value(line) for line in str(text or "").splitlines())
            if label and value is not None]


def find(rows, label):
    """The first amount whose label equals ``label`` (case-insensitive), or None."""
    wanted = str(label).strip().lower()
    for row in rows:
        for cell in row:
            if isinstance(cell, str) and cell.strip().lower() == wanted:
                index = row.index(cell)
                for following in row[index + 1:]:
                    value = following if isinstance(following, Decimal) else amount(following)
                    if value is not None:
                        return value
    return None
