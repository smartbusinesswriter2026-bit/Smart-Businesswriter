"""Read a student's own source list into a declared table (product layer, standard library only).

**B-182: a declared source is cited, never evidence.**  This module only *reads* what the
student wrote; it resolves no DOI, fetches no page and asserts nothing about whether a
source exists.  A declared source may appear in the paper's References as the student's own
citation, and it never satisfies an evidence gate or fills a named gap.

Formats, and only these (an unrecognised extension is refused with an actionable message):

* ``.bib`` — a BibTeX subset: ``@type{key, field = {value} | "value", ...}``; ``%`` starts a
  comment.  Nested braces inside a value are balanced, not guessed.
* ``.ris`` — one record per ``TY  - `` … ``ER  - `` block; ``AU``, ``TI``, ``PY``, ``DO``,
  ``UR`` and ``ID`` are read and the rest is kept as given.
* ``.csv`` — a header row that must name ``title`` and may name
  ``key, authors, year, doi, url, publisher``.

Every entry that cannot be read becomes a **named problem** with its record or line number;
nothing is dropped silently.  An entry needs a title and nothing else, because a student's
own citation is theirs: this module does not require a DOI, and it does not invent one.
"""

import csv
import io
import re

FORMAT = "bp-sources/1"

#: The extensions this reader opens.
EXT = (".bib", ".ris", ".csv")

#: A hard ceiling, so one attachment cannot become a paper's whole bibliography by accident.
MAX_ENTRIES = 500

#: The longest single field value accepted; longer is a named problem, never a truncation.
MAX_VALUE = 1000

_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)
_HTTP = re.compile(r"^https?://", re.I)


class SourcesError(Exception):
    """The file cannot be read at all; the message says why."""


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _doi(value):
    text = _clean(value)
    if not text:
        return None
    return _DOI_PREFIX.sub("", text) or None


def _entry(number, key=None, kind=None, title="", authors=None, year=None, doi=None,
           url=None, publisher=None):
    return {"n": number, "key": key, "type": kind, "title": title,
            "authors": list(authors or []), "year": year, "doi": doi, "url": url,
            "publisher": publisher}


def _problem(number, problem, line=None, raw=""):
    return {"n": number, "problem": problem, "line": line, "raw": _clean(raw)[:200]}


def _year(value):
    match = re.search(r"(1[5-9]\d{2}|20\d{2}|21\d{2})", _clean(value))
    return match.group(1) if match else None


def _read_bib(text):
    """Parse the declared BibTeX subset.  Returns (entries, problems)."""
    entries, problems = [], []
    without_comments = re.sub(r"(?m)^\s*%.*$", "", text)
    position = 0
    while True:
        at = without_comments.find("@", position)
        if at == -1:
            break
        brace = without_comments.find("{", at)
        if brace == -1:
            problems.append(_problem(len(entries) + 1, "an '@' with no opening brace",
                                     line=without_comments.count("\n", 0, at) + 1,
                                     raw=without_comments[at:at + 60]))
            break
        depth, cursor = 0, brace
        while cursor < len(without_comments):
            if without_comments[cursor] == "{":
                depth += 1
            elif without_comments[cursor] == "}":
                depth -= 1
                if depth == 0:
                    break
            cursor += 1
        if depth != 0:
            problems.append(_problem(len(entries) + 1, "an entry is not closed with '}'",
                                     line=without_comments.count("\n", 0, at) + 1,
                                     raw=without_comments[at:at + 60]))
            break
        body = without_comments[brace + 1:cursor]
        kind = _clean(without_comments[at + 1:brace]).lower() or None
        position = cursor + 1
        head, _, rest = body.partition(",")
        key = _clean(head) or None
        fields, line = {}, without_comments.count("\n", 0, at) + 1
        for chunk in _split_fields(rest):
            name, _, value = chunk.partition("=")
            name = _clean(name).lower()
            if not name:
                continue
            value = _clean(value.strip().strip("{}\"").strip())
            if len(value) > MAX_VALUE:
                problems.append(_problem(len(entries) + 1,
                                         "the field %r is longer than %d characters"
                                         % (name, MAX_VALUE), line=line, raw=value))
                continue
            fields[name] = value
        title = fields.get("title") or ""
        if not title:
            problems.append(_problem(len(entries) + 1, "the entry has no title",
                                     line=line, raw=key or body[:60]))
            continue
        authors = [part.strip() for part in re.split(r"\s+and\s+", fields.get("author", ""))
                   if part.strip()]
        url = fields.get("url") or None
        if url and not _HTTP.match(url):
            problems.append(_problem(len(entries) + 1,
                                     "the url %r is not an http(s) address" % url[:80],
                                     line=line, raw=url))
            url = None
        entries.append(_entry(len(entries) + 1, key=key, kind=kind, title=title,
                              authors=authors, year=_year(fields.get("year")),
                              doi=_doi(fields.get("doi")), url=url,
                              publisher=fields.get("publisher") or None))
    return entries, problems



def _read_ris(text):
    """Parse RIS records.  Returns (entries, problems)."""
    entries, problems = [], []
    current, start = {}, None
    for number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.rstrip()
        if not line.strip():
            continue
        match = re.match(r"^([A-Z][A-Z0-9])  -\s?(.*)$", line)
        if not match:
            if not current:
                problems.append(_problem(len(entries) + 1, "a line is not an RIS tag",
                                         line=number, raw=line))
            continue
        tag, value = match.group(1), _clean(match.group(2))
        if tag == "TY":
            if current:
                _finish_ris(current, entries, problems, start)
            current, start = {"TY": [value]}, number
            continue
        if tag == "ER":
            if current:
                _finish_ris(current, entries, problems, start)
            current, start = {}, None
            continue
        if not current:
            current, start = {}, number
        current.setdefault(tag, []).append(value)
    if current:
        _finish_ris(current, entries, problems, start)
    return entries, problems


def _finish_ris(record, entries, problems, line):
    title = (record.get("TI") or record.get("T1") or [""])[0]
    if not title:
        problems.append(_problem(len(entries) + 1, "the record has no title (TI)",
                                 line=line, raw=(record.get("ID") or [""])[0]))
        return
    url = (record.get("UR") or [None])[0]
    if url and not _HTTP.match(url):
        problems.append(_problem(len(entries) + 1,
                                 "the url %r is not an http(s) address" % url[:80], line=line, raw=url))
        url = None
    entries.append(_entry(len(entries) + 1,
                          key=(record.get("ID") or [None])[0],
                          kind=(record.get("TY") or [None])[0],
                          title=title,
                          authors=[name for name in record.get("AU", []) if name],
                          year=_year((record.get("PY") or record.get("Y1") or [""])[0]),
                          doi=_doi((record.get("DO") or [None])[0]),
                          url=url,
                          publisher=(record.get("PB") or [None])[0]))


def _read_csv(text):
    """Parse a declared CSV header.  Returns (entries, problems)."""
    reader = csv.DictReader(io.StringIO(text))
    names = [(name or "").strip().lower() for name in (reader.fieldnames or [])]
    if "title" not in names:
        raise SourcesError("the CSV needs a header row that names at least 'title' "
                           "(and may name key, authors, year, doi, url, publisher)")
    if len(names) > 20:
        raise SourcesError("the CSV has more than 20 columns; a source list needs at most 20")
    entries, problems = [], []
    for number, row in enumerate(reader, 1):
        values = {(key or "").strip().lower(): _clean(value) for key, value in row.items()}
        title = values.get("title") or ""
        if not title:
            problems.append(_problem(len(entries) + 1, "the row has no title",
                                     line=number + 1, raw=";".join(values.values())))
            continue
        url = values.get("url") or None
        if url and not _HTTP.match(url):
            problems.append(_problem(len(entries) + 1,
                                     "the url %r is not an http(s) address" % url[:80],
                                     line=number + 1, raw=url))
            url = None
        authors = [part.strip() for part in re.split(r"[;]", values.get("authors", ""))
                   if part.strip()]
        entries.append(_entry(len(entries) + 1, key=values.get("key") or None, kind=None,
                              title=title, authors=authors, year=_year(values.get("year")),
                              doi=_doi(values.get("doi")), url=url,
                              publisher=values.get("publisher") or None))
    return entries, problems


#: The same 5 MB ceiling the intake store applies.
MAX_TEXT = 5_000_000


def parse(filename, raw):
    """Read a source list into a declared table.

    Raises ``SourcesError`` when the file cannot be read at all (an extension with no
    reader, an empty file, a CSV with no ``title`` column, more than ``MAX_ENTRIES``
    entries).  An entry that cannot be read is a **problem** in the returned table, with
    its record or line number, and is never dropped silently.
    """
    name = str(filename or "")
    dot = name.rfind(".")
    ext = name[dot:].lower() if dot != -1 else ""
    if ext not in EXT:
        raise SourcesError("attach a .bib, .ris or .csv source list; %r has no reader"
                           % (ext or "that file",))
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise SourcesError("the source file is empty")
    if len(raw) > MAX_TEXT:
        raise SourcesError("the source file is larger than 5 MB; split it first")
    text = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = bytes(raw).decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise SourcesError("the source file cannot be decoded as text")
    reader = {".bib": _read_bib, ".ris": _read_ris, ".csv": _read_csv}[ext]
    entries, problems = reader(text)
    if len(entries) > MAX_ENTRIES:
        raise SourcesError("the source list has more than %d entries; split it first"
                           % MAX_ENTRIES)
    return {"format": FORMAT, "ext": ext, "n_entries": len(entries),
            "n_problems": len(problems), "entries": entries, "problems": problems,
            "note": ("Read as your own source list. These are your citations: they are not "
                     "evidence and this system has not verified them.")}


def summary(table):
    """The small record the intake store keeps beside the file."""
    table = table if isinstance(table, dict) else {}
    return {"n_entries": table.get("n_entries"), "n_problems": table.get("n_problems"),
            "ext": table.get("ext"), "format": table.get("format")}


def citations(table, limit=None):
    """One line per declared source, in the order the student wrote them.

    This is the only place a declared source becomes prose, and it invents nothing: the
    line is the authors, the year, the title and the identifier the student supplied.
    """
    entries = (table or {}).get("entries") or []
    if limit is not None:
        entries = entries[:max(0, int(limit))]
    lines = []
    for entry in entries:
        parts = []
        if entry.get("authors"):
            parts.append("; ".join(entry["authors"]))
        if entry.get("year"):
            parts.append("(%s)" % entry["year"])
        line = " ".join(parts)
        line = (line + ". " if line else "") + str(entry.get("title") or "").strip()
        if not line.endswith("."):
            line += "."
        if entry.get("doi"):
            line += " https://doi.org/" + entry["doi"]
        elif entry.get("url"):
            line += " " + entry["url"]
        if entry.get("publisher"):
            line += " " + entry["publisher"] + "."
        lines.append(re.sub(r"\s+", " ", line).strip())
    return lines


    """Parse the declared BibTeX subset.  Returns (entries, problems)."""
    entries, problems = [], []
    without_comments = re.sub(r"(?m)^\s*%.*$", "", text)
    position = 0
    while True:
        at = without_comments.find("@", position)
        if at == -1:
            break
        brace = without_comments.find("{", at)
        if brace == -1:
            problems.append(_problem(len(entries) + 1, "an '@' with no opening brace",
                                     line=without_comments.count("\n", 0, at) + 1,
                                     raw=without_comments[at:at + 60]))
            break
        depth, cursor = 0, brace
        while cursor < len(without_comments):
            if without_comments[cursor] == "{":
                depth += 1
            elif without_comments[cursor] == "}":
                depth -= 1
                if depth == 0:
                    break
            cursor += 1
        if depth != 0:
            problems.append(_problem(len(entries) + 1, "an entry is not closed with '}'",
                                     line=without_comments.count("\n", 0, at) + 1,
                                     raw=without_comments[at:at + 60]))
            break
        body = without_comments[brace + 1:cursor]
        kind = _clean(without_comments[at + 1:brace]).lower() or None
        position = cursor + 1
        head, _, rest = body.partition(",")
        key = _clean(head) or None
        fields, line = {}, without_comments.count("\n", 0, at) + 1
        for chunk in _split_fields(rest):
            name, _, value = chunk.partition("=")
            name = _clean(name).lower()
            if not name:
                continue
            value = _clean(value.strip().strip("{}\"").strip())
            if len(value) > MAX_VALUE:
                problems.append(_problem(len(entries) + 1,
                                         "the field %r is longer than %d characters"
                                         % (name, MAX_VALUE), line=line, raw=value))
                continue
            fields[name] = value
        title = fields.get("title") or ""
        if not title:
            problems.append(_problem(len(entries) + 1, "the entry has no title",
                                     line=line, raw=key or body[:60]))
            continue
        authors = [part.strip() for part in re.split(r"\s+and\s+", fields.get("author", ""))
                   if part.strip()]
        url = fields.get("url") or None
        if url and not _HTTP.match(url):
            problems.append(_problem(len(entries) + 1,
                                     "the url %r is not an http(s) address" % url[:80],
                                     line=line, raw=url))
            url = None
        entries.append(_entry(len(entries) + 1, key=key, kind=kind, title=title,
                              authors=authors, year=_year(fields.get("year")),
                              doi=_doi(fields.get("doi")), url=url,
                              publisher=fields.get("publisher") or None))
    return entries, problems


def _split_fields(rest):
    """Split `a = {x, y}, b = "z"` on top-level commas only."""
    parts, depth, quote, current = [], 0, False, []
    for char in rest:
        if char == '"':
            quote = not quote
        elif char == "{" and not quote:
            depth += 1
        elif char == "}" and not quote:
            depth -= 1
        if char == "," and depth <= 0 and not quote:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    if "".join(current).strip():
        parts.append("".join(current))
    return parts
