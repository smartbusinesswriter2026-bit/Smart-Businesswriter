"""The sources a brief declares, read exactly as the student wrote them.

A declared source is the student's own fact, so it belongs in the paper's
reference list.  This module reads two shapes:

* a labelled line - ``Sources: City Health Department (2025); Ministry of Health (2024)``
  - whose value is split on ``;`` and on the bullet character;
* a sources table - a header that names a source, citation, publication or
  bibliography column - whose rows become one entry each.

Two rules hold throughout:

* **nothing is parsed into author and year.**  The text is copied, because a
  guessed author or a guessed year is an invented fact;
* **nothing is fetched.**  A declared source is never retrieved, never resolved
  and never verified, and the paper says so where it is printed.

A label that names a *funding* source is not a source list, so the labels are
matched exactly and a short list of unambiguous phrases.
"""

import re

FORMAT = "bp-declared-sources/1"

#: The labels that state a source list.  A match is exact: "funding source"
#: states where the money comes from, not what was read.
LABELS = ("sources", "source", "references", "reference list", "bibliography",
          "citations", "declared sources", "sources used", "sources cited",
          "references cited", "works cited")

#: A table header that names a source column makes a sources table.
COLUMNS = ("source", "sources", "citation", "citations", "publication",
           "publications", "reference", "references", "bibliography")


def _norm(value):
    """A label, normalised: punctuation to spaces, lower case."""
    text = re.sub(r"\(.*?\)", " ", str(value or "")).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
    """A header is a line whose cells name known columns."""
    names = {_norm(cell) for cell in cells or []}
    if any(name in COLUMNS for name in names):
        return True
    return False


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


def read(text):
    """The sources the brief declares, as the student wrote them.

    A declared source is copied, never parsed and never fetched.  A brief that
    declares none returns an empty list, and the paper then says that no
    sources were used.
    """
    lines = str(text or "").splitlines()
    found = []
    for raw in lines:
        line = str(raw or "").strip()
        if not line:
            continue
        cells = _cells(line)
        if cells and _header(cells):
            continue
        match = re.match(r"^([A-Za-z][A-Za-z0-9 /&'()-]{1,40}?)\s*[:\-]\s*(.+)$", line)
        if not match:
            continue
        if _norm(match.group(1)) not in LABELS:
            continue
        for part in re.split(r"[;•]", match.group(2)):
            item = part.strip(" .")
            if item:
                found.append(item)
    for table in _tables(lines):
        for row in table["rows"]:
            cells = [str(cell).strip() for cell in row if str(cell).strip()]
            if cells:
                found.append(", ".join(cells))
    seen, unique = set(), []
    for item in found:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def as_source(text):
    """A declared source as a source record, read from the student's own words.

    Nothing is invented.  The author and the year are the ones the student
    wrote; a source with no year keeps the product's "n.d." convention, and a
    source with no author keeps its title as the title.
    """
    item = str(text or "").strip()
    if not item:
        return {}
    match = re.match(r"^(?P<author>[^()]{2,120}?)\s*\((?P<year>\d{4}[a-z]?)\)\.?\s*(?P<title>.+)$", item)
    if not match:
        match = re.match(r"^(?P<author>[^,]{2,120}?),\s*(?P<year>\d{4})\.?\s+(?P<title>.+)$", item)
    if match:
        return {"authors": match.group("author").strip(" .,"),
                "year": match.group("year"),
                "title": match.group("title").strip(" .")}
    return {"title": item.rstrip(" .")}
