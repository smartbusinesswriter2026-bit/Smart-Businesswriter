"""Read a business-plan case into the uploaded guide's schema.

The reader is structural: it knows the schema's fields (plan_schema.FIELDS), not any case.
It reads a `label | figure` table or a labelled sentence, places the figure on the field
whose alias it matches, and returns every label it could not place as `unplaced` exactly
as written.  Nothing is dropped and nothing is invented.

An alias the reader did not know can be taught once with `learn(alias, field)`; it is
stored in state/plan_vocab.json and used by every later case.  That is how the pipeline
learns a case's wording without a code change.
"""

import json
import os
import re

from . import plan_schema

FORMAT = "bp-plan-read/1"

#: Overridable so a test never writes the real registry.
REGISTRY = None


def _registry_path():
    if REGISTRY:
        return REGISTRY
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "state", "plan_vocab.json")


def _norm(text):
    return re.sub(r"\s+", " ", str(text or "").strip().lower()).strip(" .:;,-")


def _learned():
    path = _registry_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def learn(alias, field):
    """Teach the reader one alias.  Persisted, so the next case uses it."""
    alias = _norm(alias)
    if not alias:
        raise ValueError("an empty alias cannot be learned")
    if field not in plan_schema.FIELDS:
        raise ValueError("unknown field %r" % (field,))
    data = _learned()
    rows = data.setdefault(field, [])
    if alias not in rows:
        rows.append(alias)
    data[field] = rows
    path = _registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
    return field


def _aliases():
    index = []
    for field, spec in plan_schema.FIELDS.items():
        for alias in spec.get("aliases") or ():
            index.append((_norm(alias), field))
    for field, aliases in _learned().items():
        if field not in plan_schema.FIELDS:
            continue
        for alias in aliases:
            index.append((_norm(alias), field))
    # longest alias first: "loan annual interest rate" beats "rate"
    return sorted(set(index), key=lambda row: len(row[0]), reverse=True)


_ALIASES = None


def _assign(fields, field, value):
    """Store a value, reading a growth given as a multiplier (1.08) as a rate (8%)."""
    if field and str(field).endswith("_growth"):
        try:
            number = float(str(value))
        except (TypeError, ValueError):
            number = None
        if number is not None and 1.0 <= number <= 3.0:
            value = ("%.6f" % (number - 1.0)).rstrip("0").rstrip(".")
    fields[field] = value


def _match(label):
    global _ALIASES
    if _ALIASES is None:
        _ALIASES = _aliases()
    text = _norm(label)
    if not text:
        return None
    for alias, field in _ALIASES:
        if text == alias:
            return field
    for alias, field in _ALIASES:
        if re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", text):
            return field
    return None


_MONEY = re.compile(r"^(?:usd|\$)?\s*(-?[\d,]+(?:\.\d+)?)\s*(%|percent)?$", re.I)


def _value(text):
    """(kind, value) for a cell, or None when the cell is not a figure."""
    raw = str(text or "").strip()
    if not raw:
        return None
    percent = raw.endswith("%")
    cleaned = raw.replace("$", "").replace("USD", "").replace("usd", "").strip()
    cleaned = re.sub(r"\s*(per|a)\s+.*$", "", cleaned, flags=re.I).strip()
    match = _MONEY.match(cleaned)
    if match:
        number = match.group(1).replace(",", "")
        if percent or match.group(2):
            try:
                return ("percent", str(round(float(number) / 100.0, 10)).rstrip("0").rstrip("."))
            except ValueError:
                return None
        return ("number", number)
    # a number with a trailing word: "26 days", "6 cafés"
    head = re.match(r"^(-?[\d,]+(?:\.\d+)?)\b", cleaned)
    if head:
        return ("number", head.group(1).replace(",", ""))
    return None


def _split_row(line):
    parts = re.split(r"\t|\s{2,}|\s*\|\s*", line.strip())
    return [part.strip() for part in parts if part.strip()]


def _category(label):
    text = _norm(label)
    if any(word in text for word in ("rent", "deposit", "lease", "premises")):
        return "premises"
    if any(word in text for word in ("equipment", "kitchen", "furniture", "fixture", "pos", "it setup", "signage", "branding")):
        return "equipment"
    if "inventory" in text:
        return "inventory"
    if "contingency" in text:
        return "contingency"
    if "working capital" in text:
        return "working_capital"
    if any(word in text for word in ("permit", "licen", "legal", "accounting", "marketing", "training", "pre-opening")):
        return "pre_opening"
    return "other"


def _escalation_field(label):
    """A labelled escalation line belongs to the cost group its label names."""
    text = _norm(label)
    if "rent" in text or "lease" in text:
        return "escalation.rent"
    if any(word in text for word in ("wage", "salar", "staff")):
        return "escalation.wages"
    if "other" in text:
        return "escalation.other"
    return None


def _table_kind(line):
    cells = _split_row(line)
    if cells and _value(cells[-1]) is not None:
        return None
    text = _norm(line)
    for kind, spec in plan_schema.LINE_TABLES.items():
        if any(cue in text for cue in spec["heading_cues"]):
            return kind
    return None


def read(text):
    """Read `text` into the schema.  Returns fields, line tables, and unplaced labels."""
    fields, lines, unplaced = {}, {kind: [] for kind in plan_schema.LINE_TABLES}, []
    kind = None
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            kind = None
            continue
        name_match = re.search(
            r"(?:business plan (?:for|called|named)|business plan\s*[\u2013\u2014-]\s*)\s*"
            r"([A-Z][A-Za-z0-9&'\u2019,. -]{2,60}?)(?=\s+(?:in|at|to|for|with)\b|[,;.]|$)", line, re.I)
        if name_match and "business.name" not in fields:
            fields["business.name"] = name_match.group(1).strip(" .,-")
            continue
        life = re.match(r"^(.*?)\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b.*$", line, re.I)
        if life and "useful life" in line.lower():
            field = _match(life.group(1))
            if field and str(field).startswith("asset_life."):
                fields[field] = life.group(2)
                continue
        found_kind = _table_kind(line)
        if found_kind:
            kind = found_kind
            continue
        cells = _split_row(line)
        if not cells:
            continue
        # a row is a figure row when its last cell parses as a figure
        value = _value(cells[-1]) if len(cells) >= 2 else None
        label = cells[0] if len(cells) >= 2 else cells[0].rstrip(":")
        # a ramp row is a month number; a line with a figure and another label ends the table
        if kind == "ramp" and value is not None and not label.strip().isdigit():
            kind = None
        # "Rent +4% at start of Year 2 and Year 3" / "Staff wages +3% annually"
        escalation = re.match(r"^(.*?)\s+\+?(\d+(?:\.\d+)?)\s*%.*(?:annually|per year|year)", line, re.I)
        if escalation:
            field = _escalation_field(escalation.group(1))
            if field:
                value = round(float(escalation.group(2)) / 100.0, 6)
                fields[field] = ("%.6f" % value).rstrip("0").rstrip(".")
                continue
        if len(cells) == 1:
            # "Owner equity 60000" and "Loan term 60 months": label, figure, optional unit
            tail = re.match(
                r"^(.*?)\s+((?:usd|\$)?\s?-?[\d,]+(?:\.\d+)?)\s*(%|[a-zA-Z]{1,12})?\s*$", line, re.I)
            if tail:
                label, tail_value = tail.group(1), tail.group(2)
                if tail.group(3) == "%":
                    tail_value += "%"
                parsed = _value(tail_value)
                if parsed is not None:
                    if kind:
                        lines[kind].append({"label": label, "amount": parsed[1],
                                            "category": _category(label) if kind == "startup" else kind})
                    else:
                        field = _match(label)
                        if field:
                            _assign(fields, field, parsed[1])
                        else:
                            unplaced.append({"label": label.strip(), "value": parsed[1]})
                    continue
        # a ramp row is a month number; any other line ends the ramp table
        if kind and value is not None and len(cells) >= 2:
            # a percentage named like a schema field is a rate, not a line amount
            field = _match(label)
            if value[0] == "percent" and field:
                _assign(fields, field, value[1])
                continue
            lines[kind].append({"label": label, "amount": value[1],
                                "category": _category(label) if kind == "startup" else kind})
            continue
        if len(cells) >= 2 and value is not None:
            field = _match(label)
            if field:
                fields[field] = value[1]
            elif _match(line) is None:
                unplaced.append({"label": label, "value": value[1]})
            else:
                fields[_match(line)] = value[1]
            continue
        # "loan annual interest rate: 7.5%" as one sentence
        match = re.match(r"^(.*?)[:=-]\s*(.+)$", line)
        if match:
            label, tail = match.group(1), match.group(2)
            parsed = _value(tail)
            field = _match(label)
            if parsed is not None:
                if field:
                    _assign(fields, field, parsed[1])
                else:
                    unplaced.append({"label": label.strip(), "value": parsed[1]})
            elif field and field not in fields:
                fields[field] = tail.strip()
            continue
        field = _match(line)
        if field and field not in fields:
            fields[field] = line
    return {"format": FORMAT, "fields": fields,
            "lines": {name: rows for name, rows in lines.items() if rows},
            "unplaced": unplaced,
            "counts": {"fields": len(fields),
                       "lines": sum(len(rows) for rows in lines.values()),
                       "unplaced": len(unplaced)}}

def is_business_plan(text, reading=None):
    """Whether a brief is structurally a business plan, not merely a passing cue.

    A passing mention of "startup cost" is not a plan.  The brief is a plan when the
    reader finds a startup table, a way to fund it, and a revenue driver.  This is
    the reader's own evidence, so the classification follows the case's tables
    rather than a word count.
    """
    reading = reading if reading is not None else read(text)
    lines = reading.get("lines") or {}
    fields = reading.get("fields") or {}
    startup = lines.get("startup") or []
    funding = lines.get("funding") or []
    has_funding = bool(funding) or any(fields.get(name) for name in
                                      ("sources.equity", "sources.loan", "sources.total"))
    has_revenue = bool(lines.get("ramp") or lines.get("products")) or any(
        fields.get(name) for name in
        ("revenue.average_ticket", "revenue.days_open_per_month", "revenue.total_revenue"))
    if startup and has_funding and has_revenue:
        return True
    # A brief pasted as one long line may lose its table breaks.  A strong set of
    # plan cues still identifies it, so the student is not sent back to re-encode
    # figures the case already states.
    text = str(text or "").lower()
    cues = ("startup cost", "startup budget", "funding source", "sources and uses",
            "owner equity", "bank loan", "average ticket", "business plan")
    return sum(1 for cue in cues if cue in text) >= 4
