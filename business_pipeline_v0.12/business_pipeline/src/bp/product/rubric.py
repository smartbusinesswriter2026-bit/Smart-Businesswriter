"""Reading a rubric the student attaches, so a paper can follow it (B-187).

A rubric is the student's own statement of what their assignment will be marked
against.  This module reads that statement into a structure the paper can follow,
and it **never invents a part the document does not state**:

* a criterion's **weight** is read only when the rubric states one (``30%``,
  ``30 %``, ``30 marks``, ``30 points``, or a bare number in a ``Weight`` column).
  A rubric that states no weights parses with ``weight: None`` on every criterion
  and one named problem; it never acquires an invented ``1/n``;
* a **required element** is read only from an explicit clause (``must include``,
  ``should include``, ``should show``, ``evidence of``, or a dedicated
  ``Required`` column).  The descriptor is otherwise carried verbatim;
* the **word budget** is read only when the rubric states a number of words.  A
  page limit is never converted into a word count;
* the **sections** are read only from an explicit structure label (``Required
  sections``, ``Structure``, ``Report structure``, ``Outline``).  A heading the
  reader invented would be a requirement the student never wrote;
* the **citation style** is named only when the rubric names exactly one.  Two
  named styles are reported as a problem rather than silently choosing one;
* weights that do not total 100 are **reported, never rescaled**, because
  rescaling would rewrite the student's own statement.

A rubric the reader cannot make sense of is not half-read: ``parse`` returns
``ok: False`` with the raw text preserved and ``confirm_required: True``, so the
student is asked to confirm or correct the criteria instead of the pipeline
guessing.  The same flag is set when a parse is usable but uncertain (no weights
at all, weights missing on some rows, a total that is not 100, an ambiguous
citation style).

The parse is deterministic and offline: the same text always gives the same
result, nothing here calls the network, and nothing here imports the frozen
core.  The result is JSON-safe.

**Nothing here scores a paper.**  There is no mark, no grade and no predicted
result: judging quality is a human step.  Whether a paper *addresses* a criterion
is a separate mechanical check.
"""

import json
import re

#: The format tag carried by a parsed rubric, so a stored record says what it is.
FORMAT = "bp-rubric/1"

#: A rubric longer than this is refused by name, never silently truncated.
MAX_CHARS = 200_000

#: A criterion name longer than this is a sentence, not a criterion.
MAX_NAME = 120

#: Weights are expected to total a hundred; this is the tolerance on the sum.
WEIGHT_TOLERANCE = 0.5

#: ``30%``, ``30.5 %``, ``30 marks``, ``30 points``, ``30 pts``.  The boundary is
#: taken after the *word* alternatives only: ``%`` is not a word character, so a
#: trailing ``\b`` would make ``30%`` at the end of a cell unmatchable.
WEIGHT_RE = re.compile(
    r"(?<![\w.])(\d{1,3}(?:\.\d{1,2})?)\s*(?:%|(?:percent|marks?|points?|pts?)\b)",
    re.IGNORECASE)

#: A weight column that holds a bare number.
BARE_WEIGHT_RE = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,2})?)\s*$")

#: ``2,500 words``, ``2500 words``, ``3 000 words``.
WORDS_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:[,\s]\d{3})*|\d{3,7})\s*words?\b", re.IGNORECASE)

#: ``+/- 10%``, ``±10%``.
TOLERANCE_RE = re.compile(r"(?:\+/-|\u00b1)\s*(\d{1,2}(?:\.\d)?)\s*%", re.IGNORECASE)

#: A bullet, a number, a letter or a roman numeral at the start of a line.
BULLET_RE = re.compile(r"^\s*(?:[-*\u2022\u00b7]|\(?\d{1,2}[.)]|[a-z][.)])\s+(.*)$")

#: The label that opens an explicit structure list.
SECTIONS_RE = re.compile(
    r"^\s*(?:required\s+(?:sections?|headings?|structure)|report\s+structure|structure|"
    r"sections?|outline|headings?|format\s+of\s+the\s+(?:report|paper))\s*[:\-\u2013]?\s*(.*)$",
    re.IGNORECASE)

#: A line that labels a word budget.
WORDS_LABEL_RE = re.compile(
    r"(?:word\s*(?:count|limit|budget|length)|length)\s*[:\-\u2013]?", re.IGNORECASE)

#: The citation styles the product can name; one named style is taken, two are a problem.
CITATION_STYLES = (("apa", "APA"), ("harvard", "Harvard"), ("mla", "MLA"),
                   ("chicago", "Chicago"), ("ieee", "IEEE"), ("vancouver", "Vancouver"))

#: Header spellings, mapped to the role each column plays.
COLUMN_WORDS = {
    "name": ("criterion", "criteria", "assessment", "assessed", "item", "element",
             "component", "area", "task", "question"),
    "weight": ("weight", "weighting", "%", "percent", "percentage", "marks", "points",
               "value", "alloc"),
    "descriptor": ("descriptor", "description", "criteria for", "standard", "expectation",
                   "what is required", "requirement", "detail", "comment"),
    "required": ("required", "must include", "should include", "evidence", "includes",
                 "elements"),
}

#: Clause words that introduce required elements inside a descriptor.
ELEMENTS_RE = re.compile(
    r"(?:must\s+include|should\s+include|should\s+show|must\s+show|evidence\s+of|"
    r"includes?|comprising|containing)\s*[:\-]?\s*(.+)$", re.IGNORECASE)

#: Separators that put a name on the left and its descriptor on the right.
NAME_SPLIT_RE = re.compile(r"\s*[:\u2013\u2014]\s*|\s+-\s+")


def _clean(text):
    """Strip the invisible characters a PDF or Word file leaves behind."""
    text = str(text or "").replace("\x00", "").replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _lines(text):
    return [line for line in (raw.strip() for raw in text.split("\n")) if line]


def _cell_text(value):
    return str(value or "").strip().strip("|").strip()


def _is_separator(line):
    """The ``|---|---|`` line under a markdown table header."""
    return bool(re.fullmatch(r"\s*\|?[\s:\-|]{3,}\|?\s*", line)) and "-" in line


def _cells(line):
    return [_cell_text(part) for part in line.strip().strip("|").split("|")]


def _columns(header):
    """Map each role a column can play to its position; unknown columns are ignored."""
    mapping = {}
    for position, cell in enumerate(header):
        lowered = cell.lower().strip(" :*")
        for role, words in COLUMN_WORDS.items():
            if role in mapping:
                continue
            if any(lowered == word or lowered.startswith(word) for word in words):
                mapping[role] = position
                break
    return mapping


def _read_table(lines):
    """A pipe table: a header row, a separator row, then one row per criterion."""
    for index, line in enumerate(lines):
        if line.count("|") < 2 or index + 1 >= len(lines):
            continue
        if not _is_separator(lines[index + 1]):
            continue
        mapping = _columns(_cells(line))
        if "name" not in mapping:
            continue
        rows = []
        for later in lines[index + 2:]:
            if later.count("|") < 2:
                break
            cells = _cells(later)
            if len(cells) < 2:
                break
            rows.append({role: cells[position] if position < len(cells) else ""
                         for role, position in mapping.items()})
        if rows:
            return rows, "table"
    return [], "none"


def _find_weight(text):
    """The weight a piece of text states, as a number and as written; never invented."""
    text = _cell_text(text)
    if not text:
        return None, None
    match = WEIGHT_RE.search(text)
    if match:
        try:
            return float(match.group(1)), match.group(0).strip()
        except ValueError:
            return None, None
    bare = BARE_WEIGHT_RE.match(text)
    if bare:
        try:
            return float(bare.group(1)), bare.group(0).strip()
        except ValueError:
            return None, None
    return None, None


def _split_name(body):
    """Split ``Analysis - 30% - shows the break-even`` into its parts."""
    text = body.strip()
    match = WEIGHT_RE.search(text)
    if match:
        name = text[:match.start()].strip(" \t:-\u2013\u2014,")
        descriptor = text[match.end():].strip(" \t:-\u2013\u2014,")
        return name, text[match.start():match.end()].strip(), descriptor
    parts = NAME_SPLIT_RE.split(text, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), None, parts[1].strip()
    return text.strip(), None, ""


def _read_list(lines):
    """A bulleted, numbered or headed list of criteria."""
    rows = []
    for line in lines:
        bullet = BULLET_RE.match(line)
        body = bullet.group(1).strip() if bullet else line.strip()
        if not body:
            continue
        if SECTIONS_RE.match(body):
            continue
        weight, weight_text = _find_weight(body)
        if weight is None and not bullet and not NAME_SPLIT_RE.search(body):
            continue  # prose, a title or a heading: not a criterion
        name, stated, descriptor = _split_name(body)
        if weight is None and not bullet and not descriptor:
            continue  # a lead-in line such as "The report is marked on:" is not a criterion
        name = name.strip(" *#\t")
        if not name or len(name) > MAX_NAME:
            continue
        rows.append({"name": name, "weight": weight_text or stated or "",
                     "descriptor": descriptor, "required": ""})
    return rows, ("list" if rows else "none")


def _elements(descriptor, dedicated):
    """The required elements a row states, verbatim: a dedicated column or a clause."""
    source = _cell_text(dedicated)
    if not source:
        match = ELEMENTS_RE.search(_cell_text(descriptor))
        if not match:
            return []
        source = match.group(1)
    parts = [part.strip(" .;") for part in re.split(r"[;\u2022]", source)]
    return [part for part in parts if part]


def _criterion(row):
    """One criterion, or None when the row is not a criterion the student stated."""
    name = _cell_text(row.get("name")).strip(" *#\t")
    if not name or len(name) < 2 or len(name) > MAX_NAME:
        return None
    stated = _cell_text(row.get("weight"))
    weight, weight_text = _find_weight(stated) if stated else (None, None)
    descriptor = _cell_text(row.get("descriptor"))
    return {"name": name, "weight": weight, "weight_text": weight_text,
            "descriptor": descriptor,
            "required_elements": _elements(descriptor, row.get("required"))}


def _sections(lines):
    """The headings the rubric asks for, read only from an explicit structure label."""
    headings = []
    for index, line in enumerate(lines):
        match = SECTIONS_RE.match(line)
        if not match:
            continue
        inline = match.group(1).strip(" :-\u2013")
        candidates = [part.strip(" .;-\u2013") for part in re.split(r"[;,]", inline)] if inline else []
        for later in lines[index + 1:]:
            bullet = BULLET_RE.match(later)
            if not bullet:
                break
            candidates.append(bullet.group(1).strip(" .;-\u2013"))
        for candidate in candidates:
            candidate = candidate.strip()
            if candidate and len(candidate) <= MAX_NAME and candidate not in headings:
                headings.append(candidate)
        if headings:
            break
    return headings


def _word_budget(lines):
    """The stated number of words and its tolerance; a page limit is never converted."""
    for line in lines:
        if not WORDS_RE.search(line):
            continue
        if re.search(r"\bpages?\b", line, re.IGNORECASE) and not WORDS_LABEL_RE.search(line):
            continue  # pages are a different unit and are not a word budget
        match = WORDS_RE.search(line)
        digits = re.sub(r"[,\s]", "", match.group(1))
        try:
            words = int(digits)
        except ValueError:
            continue
        tolerance = None
        found = TOLERANCE_RE.search(line)
        if found:
            try:
                tolerance = round(float(found.group(1)) / 100.0, 4)
            except ValueError:
                tolerance = None
        return {"words": words, "tolerance": tolerance, "text": line.strip()[:200]}
    return None


def _citation_style(text):
    """The one citation style the rubric names, or None when it names none or several."""
    found = []
    lowered = text.lower()
    for key, label in CITATION_STYLES:
        if re.search(r"\b" + key + r"\b", lowered):
            found.append((key, label))
    if len(found) == 1:
        return found[0][0], None
    if len(found) > 1:
        return None, ("The rubric names more than one citation style ("
                      + ", ".join(label for _, label in found)
                      + "); confirm which one applies before the paper is written.")
    return None, None


def _total(criteria):
    """The stated total, only when every criterion states a weight."""
    weights = [criterion["weight"] for criterion in criteria if criterion["weight"] is not None]
    if not weights or len(weights) != len(criteria):
        return None
    return round(sum(weights), 4)


def parse(text):
    """Read a rubric.  Returns a structure, never a score.

    ``ok`` is True only when at least one criterion was read.  ``confirm_required``
    asks the student to check the parsed criteria before a paper follows them; it
    is set whenever the parse failed or is uncertain.
    """
    original = text if isinstance(text, str) else ""
    clean = _clean(original)
    result = {"format": FORMAT, "ok": False, "layout": "none", "criteria": [],
              "sections": [], "word_budget": None, "citation_style": None,
              "total_weight": None, "problems": [], "confirm_required": True,
              "chars": len(clean), "text": original, "scores_nothing": True}
    if len(clean) < 15:
        result["problems"].append(
            "The rubric text is empty or too short to read. Attach the rubric file, or paste "
            "the criteria with their weights.")
        return result
    if len(clean) > MAX_CHARS:
        result["problems"].append(
            "The rubric is longer than the %d-character limit; attach only the assessment "
            "criteria, or split the document." % MAX_CHARS)
        return result
    lines = _lines(clean)
    rows, layout = _read_table(lines)
    if not rows:
        rows, layout = _read_list(lines)
    criteria = []
    for row in rows:
        criterion = _criterion(row)
        if criterion is not None:
            criteria.append(criterion)
    result["criteria"] = criteria
    result["layout"] = layout
    result["sections"] = _sections(lines)
    result["word_budget"] = _word_budget(lines)
    style, style_problem = _citation_style(clean)
    result["citation_style"] = style
    if style_problem:
        result["problems"].append(style_problem)
    if not criteria:
        result["problems"].append(
            "No assessment criterion could be read from this rubric. Confirm the criteria in "
            "your own words, or attach the rubric as a table or a numbered list.")
        return result
    result["ok"] = True
    known = [criterion for criterion in criteria if criterion["weight"] is not None]
    total = _total(criteria)
    result["total_weight"] = total
    if not known:
        result["problems"].append(
            "The rubric states no weights, so every criterion is carried without one. No weight "
            "has been assumed.")
    elif len(known) != len(criteria):
        result["problems"].append(
            "%d of %d criteria state no weight; the paper carries them without one rather than "
            "assuming a share." % (len(criteria) - len(known), len(criteria)))
    if total is not None and abs(total - 100.0) > WEIGHT_TOLERANCE:
        result["problems"].append(
            "The stated weights total %s, not 100. They are reported as written and never "
            "rescaled." % ("%g" % total))
    result["confirm_required"] = bool(result["problems"])
    return result


def summary(parsed):
    """A short JSON-safe description for a page badge; the long fields stay in ``parse``."""
    parsed = parsed or {}
    criteria = parsed.get("criteria") or []
    budget = parsed.get("word_budget") or {}
    return {"ok": bool(parsed.get("ok")), "layout": parsed.get("layout"),
            "criteria": len(criteria),
            "weighted": len([row for row in criteria if row.get("weight") is not None]),
            "total_weight": parsed.get("total_weight"),
            "sections": len(parsed.get("sections") or []),
            "words": budget.get("words"), "citation_style": parsed.get("citation_style"),
            "confirm_required": bool(parsed.get("confirm_required")),
            "problems": list(parsed.get("problems") or [])}


def as_json(parsed):
    """The parsed rubric as a JSON string, stable across runs."""
    return json.dumps(parsed, sort_keys=True, ensure_ascii=False, default=str)


#: Words that carry no meaning when matching a criterion to a heading.
_STOP = frozenset("a an and the of for to in on at by with or from is are be as its it this that "
                  "your their our you they we".split())


def _tokens(text):
    """The significant words of a phrase, for matching only; never shown to a student."""
    words = re.findall(r"[a-z][a-z0-9']+", str(text or "").lower().replace("\u2019", "'"))
    return [word for word in words if word not in _STOP and len(word) > 2]


def _normalise(text):
    return " ".join(_tokens(text))


def _covers(heading, criterion):
    """True when a heading names the criterion: containment either way, or overlap."""
    left, right = _normalise(heading), _normalise(criterion)
    if not left or not right:
        return False
    if left in right or right in left:
        return True
    wanted, found = set(_tokens(criterion)), set(_tokens(heading))
    if not wanted or not found:
        return False
    return len(wanted & found) / float(len(wanted)) >= 0.6


def coverage(parsed, sections, blocks=None):
    """Which criteria of a rubric a paper addresses — mechanically, and nothing more.

    A criterion is ``addressed`` when a heading names it (or its parts) **and** every
    required element it states is present; ``partially`` when some of that is true;
    ``gap`` when neither a heading nor an element mentions it.  Presence is the only
    question asked, so this never judges how well a criterion is met and never awards
    a mark: that is a human step.

    ``gate`` is ``blocked`` when a criterion that carries a weight is a gap (or, when
    the rubric states no weights, when any criterion is a gap), because a weighted
    criterion is the document's own statement of what must be there.  ``blocks`` is
    ``False`` when the student turned the gate off; the rows are then warnings.
    """
    parsed = parsed or {}
    criteria = parsed.get("criteria") or []
    headings = []
    for item in sections or []:
        if isinstance(item, dict):
            heading = item.get("heading")
        elif isinstance(item, (list, tuple)) and item:
            heading = item[0]
        else:
            heading = ""
        if str(heading or "").strip():
            headings.append(str(heading))
    body = " ".join(
        " ".join(str(line) for line in (item.get("lines") or []))
        if isinstance(item, dict) else " ".join(str(line) for line in (item[1] or []))
        for item in (sections or [])).lower()
    rows = []
    for criterion in criteria:
        where = [heading for heading in headings if _covers(heading, criterion.get("name"))]
        elements = []
        for element in criterion.get("required_elements") or []:
            wanted = _normalise(element)
            found = bool(wanted) and wanted in _normalise(body)
            elements.append({"text": element, "found": found, "where": "" if not found else "body"})
        missing = [row["text"] for row in elements if not row["found"]]
        if where and not missing:
            status = "addressed"
        elif where or any(row["found"] for row in elements):
            status = "partially"
        else:
            status = "gap"
        rows.append({"name": criterion.get("name"), "weight": criterion.get("weight"),
                     "weight_text": criterion.get("weight_text"), "status": status,
                     "where": where, "elements": elements,
                     "note": ("no heading or sentence addresses it" if status == "gap" else
                              ("stated but not yet shown: " + "; ".join(missing) if missing else ""))})
    weighted = any(row["weight"] is not None for row in rows)
    blocking = [row["name"] for row in rows
                if row["status"] == "gap" and (row["weight"] is not None or not weighted)]
    gaps = [row["name"] for row in rows if row["status"] == "gap"]
    return {"criteria": rows, "count": len(rows),
            "addressed": len([row for row in rows if row["status"] == "addressed"]),
            "partial": len([row for row in rows if row["status"] == "partially"]),
            "gaps": gaps, "blocking": blocking,
            "gate": "blocked" if blocking else "clear",
            "scored": False, "weights_stated": weighted}

