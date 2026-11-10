"""Read a student's chart input and say what it understood.

The reader is deterministic and fail-closed.  It reads the figures the student
typed or uploaded, names every value it could not read, and returns a report the
screen shows *before* a chart is made.  It never sums, rounds, invents a number,
or silently changes the chart kind.

Two input shapes are read:

* **lines** - ``label, value`` (a pareto adds a running total).  The separator
  may be a comma, tab, semicolon, colon, pipe, two or more spaces, or the last
  space before the value.  A bare number gets a marked, editable ``Item N`` label.
* **tables** - a CSV/TSV/XLSX table, or a Word table.  The reader picks a label
  column and a value column, keeps every row it can read, and reports the rows it
  could not.

The report is the contract between the reader and the screen::

    {"format": "bp-visual-read/1", "ok": true,
     "source": {"kind": "typed" | "data" | "instruction", "filename": ...},
     "title": {"value": ..., "source": ...},
     "kind": {"value": ..., "source": ..., "reason": ...},
     "columns": {"label": ..., "value": ..., "cumulative": ...},
     "columns_available": [...],
     "points": [{"label": ..., "value": ..., "cumulative": ..., ...}],
     "skipped": [...], "ignored": [...], "warnings": [...], "needs": [...],
     "blocked": [...], "plan": [...], "normalized_text": ...}

Nothing here imports the frozen method library or computes a business number.
"""

import base64
import binascii
import os
import re
from decimal import Decimal, InvalidOperation

FORMAT = "bp-visual-read/1"

#: A chart with one point is a sentence, not a chart.  A table may keep one row.
MIN_CHART_POINTS = 2
MAX_POINTS = 200
MAX_LABEL = 120

#: Currency signs a student may type before or after a figure.
_CURRENCY = "$€£¥₹₱₩₽₺₫฿"
_CURRENCY_CODES = ("USD", "EUR", "GBP", "JPY", "PHP", "INR", "AUD", "CAD",
                   "CHF", "CNY", "KRW", "SGD", "HKD", "NZD", "ZAR", "BRL",
                   "MXN", "IDR", "MYR", "THB", "VND", "TRY", "AED", "SAR")

#: A grouped number (``1 200 000``, ``1,200,000``, ``1.200.000``) or a plain
#: number.  The look-behind keeps the ``1`` in ``Q1`` from becoming a value.
_GROUPED = r"\d{1,3}(?:[ \u00a0\u202f,.'’]\d{3})+(?:[.,]\d+)?"
_INDIAN = r"\d{1,2}(?:,\d{2})*,\d{3}(?:\.\d+)?"
_PLAIN = r"\d+(?:[.,]\d+)?"
_NUMBER_TOKEN = re.compile(
    r"(?<![\w.])"
    r"(?:\(?\s*[+\-\u2212\u2013\u2014]?\s*"
    r"(?:[" + re.escape(_CURRENCY) + r"]\s*)?"
    r"(?:" + _INDIAN + r"|" + _GROUPED + r"|" + _PLAIN + r")"
    r"\s*[kKmMbB]?\s*%?"
    r"(?:\s*(?:" + "|".join(_CURRENCY_CODES) + r"))?"
    r"\s*\)?)"
    r"(?![\w.])",
    re.IGNORECASE,
)

_DATE_ONLY = re.compile(
    r"^\s*(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}"
    r"|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}"
    r"|(?:q[1-4]|fy\s*\d{2,4})\s*)\s*$",
    re.IGNORECASE,
)

#: Column names that usually hold a label rather than a measure.
_LABEL_CUES = re.compile(
    r"\b(year|date|period|quarter|month|week|day|label|name|category|item|"
    r"product|region|country|segment|channel|store|customer|supplier|account|"
    r"department|division|team|group|brand|sku|code)\b",
    re.IGNORECASE,
)
_VALUE_CUES = re.compile(
    r"\b(value|revenue|sales|amount|profit|cost|price|total|count|qty|quantity|"
    r"score|rate|margin|income|expense|cash|units|volume|balance)\b",
    re.IGNORECASE,
)
_CUMULATIVE_CUES = re.compile(r"\b(cum|run|running|total|accum|percent|%)\b", re.IGNORECASE)

_KIND_PHRASES = (
    ("pareto", ("pareto chart", "pareto", "vital few", "running total", "cumulative")),
    ("waterfall", ("waterfall", "bridge", "walk", "step change")),
    ("candlestick", ("candlestick", "ohlc", "open high low close", "open-high-low-close")),
    ("scatter", ("scatter plot", "scatter graph", "scattergraph", "scatter",
                 "x and y")),
    ("stacked_bar", ("stacked bar", "stacked column", "stacked")),
    ("pie", ("pie chart", "pie", "donut", "doughnut")),
    ("area", ("area chart", "area graph")),
    ("line", ("line chart", "line graph", "trend line", "trend", "over time")),
    ("bar", ("bar chart", "bar graph", "column chart", "bar", "column")),
    ("table", ("table", "grid")),
)


#: The frozen ingestion callable, attached by `bp.server` (B-080).  The product
#: package never imports the frozen core itself.
TABLE_READER = None


def set_table_reader(reader):
    """Attach the frozen `ingest.read_table` callable for data-file uploads."""
    global TABLE_READER
    TABLE_READER = reader


class VisualInputError(ValueError):
    """The input cannot be read; the message says why."""


# --- numbers ---------------------------------------------------------------

def _decimal_text(value):
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def parse_number(raw):
    """Read one written figure, or return ``None`` when it is not a number.

    The returned dict carries the normalised value as a string, the text as it
    was written, the unit (only ``%`` is kept) and an ``ambiguous`` flag when a
    single three-digit separator could be either thousands or a decimal.
    """
    original = str(raw or "").strip()
    if not original:
        return None
    text = original.replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    unit = ""
    if text.endswith("%"):
        unit = "%"
        text = text[:-1].strip()
    text = text.strip()
    text = re.sub(r"^[" + re.escape(_CURRENCY) + r"]\s*", "", text)
    text = re.sub(r"\s*[" + re.escape(_CURRENCY) + r"]$", "", text)
    text = re.sub(r"^(?:" + "|".join(_CURRENCY_CODES) + r")\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*(?:" + "|".join(_CURRENCY_CODES) + r")$", "", text, flags=re.IGNORECASE)
    text = text.replace("\u00a0", "").replace("\u202f", "").replace(" ", "")
    multiplier = 1
    suffix = re.search(r"([kKmMbB])$", text)
    if suffix:
        multiplier = {"k": 1000, "m": 1000000, "b": 1000000000}[suffix.group(1).lower()]
        text = text[:-1]
    text = text.replace("'", "").replace("’", "")
    if not re.match(r"^[+-]?[\d.,]+(?:[eE][+-]?\d+)?$", text):
        return None
    exponent = ""
    match = re.search(r"([eE][+-]?\d+)$", text)
    if match:
        exponent = match.group(1)
        text = text[:match.start()]
    sign = ""
    if text.startswith(("+", "-")):
        sign, text = text[0], text[1:]
    if not text:
        return None
    ambiguous = False
    note = ""
    commas, dots = text.count(","), text.count(".")
    if commas and dots:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif commas:
        parts = text.split(",")
        if len(parts) > 2:
            if all(len(part) == 3 for part in parts[1:]):
                text = "".join(parts)
            elif all(len(part) == 2 for part in parts[1:-1]) and len(parts[-1]) == 3:
                text = "".join(parts)
            elif len(parts[-1]) in (1, 2) and (
                    all(len(part) == 3 for part in parts[1:-1])
                    or all(len(part) == 2 for part in parts[1:-1])):
                text = "".join(parts[:-1]) + "." + parts[-1]
            else:
                return None
        else:
            left, right = parts
            if len(right) == 3 and 1 <= len(left) <= 3:
                text = left + right
                ambiguous = True
                note = "read as thousands"
            elif len(right) in (1, 2):
                text = left + "." + right
            else:
                return None
    elif dots:
        parts = text.split(".")
        if len(parts) > 2:
            if all(len(part) == 3 for part in parts[1:]):
                text = "".join(parts)
            elif len(parts[-1]) in (1, 2) and all(len(part) == 3 for part in parts[1:-1]):
                text = "".join(parts[:-1]) + "." + parts[-1]
            else:
                return None
        else:
            left, right = parts
            if len(right) == 3 and 1 <= len(left) <= 3:
                text = left + right
                ambiguous = True
                note = "read as thousands"
            elif len(right) in (1, 2):
                text = left + "." + right
            else:
                return None
    normalized = sign + text + exponent
    try:
        value = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None
    if multiplier != 1:
        value *= multiplier
    if negative:
        value = -value
    if not value.is_finite():
        return None
    return {"value": _decimal_text(value), "raw": original, "unit": unit,
            "ambiguous": ambiguous, "note": note}


_SEPARATORS = set("\t|;:,")


def _is_year(number):
    try:
        value = Decimal(number["value"])
    except (InvalidOperation, ValueError):
        return False
    return (value == value.to_integral_value() and 1900 <= value <= 2100
            and "." not in number["value"])


def _whole_field(line, match):
    """True when the number fills a field between explicit separators."""
    before = match.start() - 1
    while before >= 0 and line[before] in " \u00a0\u202f":
        before -= 1
    after = match.end()
    while after < len(line) and line[after] in " \u00a0\u202f":
        after += 1
    left = before < 0 or line[before] in _SEPARATORS
    right = after >= len(line) or line[after] in _SEPARATORS
    return left and right


def _space_label_ambiguous(label):
    """A space-separated label that ends in a non-year number is ambiguous."""
    text = _clean_label(label)
    if not text:
        return False
    tokens = text.split()
    if not tokens:
        return False
    last = parse_number(tokens[-1])
    return last is not None and not _is_year(last)


def _clean_label(label):
    text = str(label or "").strip()
    text = re.sub(r"^[\s,;:|]+", "", text)
    text = re.sub(r"[\s,;:|]+$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        text = text[1:-1].strip()
    return text


# --- lines -----------------------------------------------------------------

def parse_lines(text, with_running=False, with_xy=False, with_ohlc=False):
    """Read ``label, value`` lines; return ``(points, skipped, warnings)``."""
    points, skipped, warnings = [], [], []
    auto_labels = []
    capped = False
    for line_number, raw in enumerate(str(text or "").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("//"):
            continue
        if _DATE_ONLY.match(line):
            skipped.append({"line": line_number, "text": line,
                            "reason": "looks like a date, not a figure"})
            continue
        if len(points) >= MAX_POINTS:
            skipped.append({"line": line_number, "text": line,
                            "reason": "the input is over the %d-point limit" % MAX_POINTS})
            capped = True
            break
        clean = line.rstrip(" \t.,;:")
        parsed = []
        for match in _NUMBER_TOKEN.finditer(clean):
            number = parse_number(match.group(0))
            if number is not None:
                parsed.append((match, number))
        if not parsed:
            skipped.append({"line": line_number, "text": line,
                            "reason": "no number on this line"})
            continue
        whole = [(match, number) for match, number in parsed
                 if _whole_field(clean, match)]
        if with_xy:
            if len(whole) >= 2:
                extras = whole[:-2]
                if extras and not all(_is_year(number) for _match, number in extras):
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "more than two numbers on this line; a scatter "
                                              "line is label, x, y"})
                    continue
                x_match, x_number = whole[-2]
                y_match, y_number = whole[-1]
                label = clean[:x_match.start()]
            else:
                if len(parsed) < 2:
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "a scatter line needs an x value and a y value"})
                    continue
                x_match, x_number = parsed[-2]
                y_match, y_number = parsed[-1]
                label = clean[:x_match.start()]
                if _space_label_ambiguous(label):
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "more than one number on this line; the label "
                                              "ends in a number, so write a comma or tab after "
                                              "the label"})
                    continue
            value_number = y_number
            point = {"value": y_number["value"], "x": x_number["value"],
                     "x_raw": x_number["raw"], "y_raw": y_number["raw"]}
        elif with_ohlc:
            if len(whole) >= 4:
                extras = whole[:-4]
                if extras and not all(_is_year(number) for _match, number in extras):
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "more than four numbers on this line; a "
                                              "candlestick line is label, open, high, low, close"})
                    continue
                open_match, open_number = whole[-4]
                high_match, high_number = whole[-3]
                low_match, low_number = whole[-2]
                close_match, close_number = whole[-1]
                label = clean[:open_match.start()]
            else:
                if len(parsed) < 4:
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "a candlestick line needs open, high, low and close"})
                    continue
                open_match, open_number = parsed[-4]
                high_match, high_number = parsed[-3]
                low_match, low_number = parsed[-2]
                close_match, close_number = parsed[-1]
                label = clean[:open_match.start()]
                if _space_label_ambiguous(label):
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "more than four numbers on this line; the label "
                                              "ends in a number, so write a comma or tab after "
                                              "the label"})
                    continue
            try:
                open_value = Decimal(open_number["value"])
                high_value = Decimal(high_number["value"])
                low_value = Decimal(low_number["value"])
                close_value = Decimal(close_number["value"])
            except (InvalidOperation, ValueError):
                skipped.append({"line": line_number, "text": line,
                                "reason": "a candlestick line needs four numbers"})
                continue
            if high_value < low_value:
                skipped.append({"line": line_number, "text": line,
                                "reason": "the high is below the low"})
                continue
            if high_value < max(open_value, close_value) or low_value > min(open_value, close_value):
                skipped.append({"line": line_number, "text": line,
                                "reason": "the open or close is outside the high-low range"})
                continue
            value_number = close_number
            point = {"value": close_number["value"], "open": open_number["value"],
                     "high": high_number["value"], "low": low_number["value"],
                     "close": close_number["value"]}
        elif with_running:
            if len(whole) >= 2:
                extras = whole[:-2]
                if extras and not all(_is_year(number) for _match, number in extras):
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "more than two numbers on this line; a pareto "
                                              "line is label, value, running total"})
                    continue
                value_match, value_number = whole[-2]
                cumulative_match, cumulative_number = whole[-1]
                label = clean[:value_match.start()]
            else:
                if len(parsed) < 2:
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "a pareto line needs a value and a running total"})
                    continue
                value_match, value_number = parsed[-2]
                cumulative_match, cumulative_number = parsed[-1]
                label = clean[:value_match.start()]
                if _space_label_ambiguous(label):
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "more than one number on this line; the label "
                                              "ends in a number, so write a comma or tab after "
                                              "the label"})
                    continue
            point = {"value": value_number["value"],
                     "cumulative": cumulative_number["value"],
                     "cumulative_raw": cumulative_number["raw"]}
            if cumulative_number.get("ambiguous"):
                warnings.append("Line %d: '%s' was read as %s; if you meant a decimal, write it "
                                "with a point." % (line_number, cumulative_number["raw"],
                                                   cumulative_number["value"]))
        else:
            if whole:
                extras = whole[:-1]
                if extras and not (len(extras) == 1 and _is_year(extras[0][1])):
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "more than one number on this line; a chart line "
                                              "is label, value"})
                    continue
                value_match, value_number = whole[-1]
                label = clean[:value_match.start()]
            else:
                value_match, value_number = parsed[-1]
                label = clean[:value_match.start()]
                if _space_label_ambiguous(label):
                    skipped.append({"line": line_number, "text": line,
                                    "reason": "more than one number on this line; the label "
                                              "ends in a number, so write a comma or tab after "
                                              "the label"})
                    continue
            point = {"value": value_number["value"], "cumulative": None}
        label = _clean_label(label)
        if not label:
            label = "Item %d" % (len(points) + 1)
            auto_labels.append(label)
            point["label_auto"] = True
        else:
            point["label_auto"] = False
            if label.lower() in ("total", "grand total", "sum", "subtotal"):
                warnings.append("Line %d looks like a total; include it only if it belongs in "
                                "the chart." % line_number)
        if len(label) > MAX_LABEL:
            warnings.append("Line %d: the label is long; it may be cut off in the chart."
                            % line_number)
            label = label[:MAX_LABEL - 3].rstrip() + "..."
        point.update({"label": label, "raw": line, "line": line_number,
                      "unit": value_number.get("unit") or ""})
        if value_number.get("ambiguous"):
            warnings.append("Line %d: '%s' was read as %s; if you meant a decimal, write it "
                            "with a point." % (line_number, value_number["raw"],
                                               value_number["value"]))
        points.append(point)
    if auto_labels:
        warnings.append("%d line(s) had no label; they were called %s. "
                        "Rename them if you want."
                        % (len(auto_labels), ", ".join(auto_labels[:3])))
    if capped:
        warnings.append("The input has more than %d points; only the first %d are shown."
                        % (MAX_POINTS, MAX_POINTS))
    return points, skipped, warnings


# --- tables ----------------------------------------------------------------

def _cell_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _profile(values):
    numbers = texts = missing = 0
    samples = []
    seen = set()
    for value in values:
        text = _cell_text(value)
        if not text:
            missing += 1
            continue
        if parse_number(text) is not None:
            numbers += 1
        else:
            texts += 1
        if len(samples) < 5:
            samples.append(text)
        seen.add(text.lower())
    return {"numeric": numbers, "text": texts, "missing": missing,
            "distinct": len(seen), "samples": samples}


def _column_names(table):
    return [str(column.get("name") or "") for column in table.get("columns") or []]


def _rows_of(table):
    return [[_cell_text(cell) for cell in row] for row in table.get("rows") or []]


def _is_headerless(columns):
    """A numeric last column name means the first row was data, not a header."""
    return bool(columns) and parse_number(columns[-1]) is not None


def _rebuild_headerless(table):
    columns = _column_names(table)
    rows = _rows_of(table)
    header_row = list(columns)
    rows = [header_row] + rows
    names = ["Column %d" % (index + 1) for index in range(len(header_row))]
    return names, rows, True


def _index_of(name, columns):
    wanted = str(name or "").strip().lower()
    for index, column in enumerate(columns):
        if column.strip().lower() == wanted:
            return index
    raise VisualInputError("the file has no column named %r; it has: %s"
                           % (name, ", ".join(columns)))


def _choose_columns(columns, profiles, kind, label_column, value_column, cumulative_column):
    """Pick the label/value/running-total columns, or name what is missing."""
    warnings = []
    names = list(columns)
    numeric = [index for index, profile in enumerate(profiles)
               if profile["numeric"] and profile["numeric"] >= profile["text"]]
    if not numeric:
        numeric = [index for index, profile in enumerate(profiles) if profile["numeric"]]
    if not numeric:
        raise VisualInputError("no column in this file holds numbers")
    # A numeric column whose name says year/period is a label, not a measure.
    label_like = [index for index in numeric if _LABEL_CUES.search(names[index])]
    value_like = [index for index in numeric if _VALUE_CUES.search(names[index])]
    value_candidates = [index for index in numeric if index not in label_like] or numeric
    if value_column:
        value_index = _index_of(value_column, names)
    elif value_like:
        value_index = value_like[0]
    else:
        value_index = value_candidates[0]
    if label_column:
        label_index = _index_of(label_column, names)
    else:
        candidates = [index for index in range(len(names)) if index != value_index
                      and index not in value_candidates]
        if label_like:
            candidates = label_like + [index for index in candidates if index not in label_like]
        if candidates:
            label_index = max(candidates, key=lambda index: profiles[index]["distinct"])
        else:
            label_index = None
    if label_index is not None and label_index == value_index:
        label_index = None
    cumulative_index = None
    if kind == "pareto":
        if cumulative_column:
            cumulative_index = _index_of(cumulative_column, names)
        else:
            candidates = [index for index in numeric
                          if index not in (value_index, label_index)
                          and _CUMULATIVE_CUES.search(names[index])]
            if not candidates:
                candidates = [index for index in numeric
                              if index not in (value_index, label_index)]
            if not candidates:
                raise VisualInputError("a pareto needs a running-total column; this file has "
                                       "only one number column")
            cumulative_index = candidates[0]
            warnings.append("I used '%s' as the running total." % names[cumulative_index])
    if len(numeric) > 1 and not value_column:
        other = [names[index] for index in numeric
                 if index not in (value_index, cumulative_index)]
        if other:
            warnings.append("The file has more than one number column; I used '%s'. "
                            "Choose another column if that is wrong." % names[value_index])
            warnings.append("The other number column(s): " + ", ".join(other) + ".")
    return label_index, value_index, cumulative_index, warnings


def read_table(table, filename=None, sha256=None, kind=None, label_column=None,
               value_column=None, cumulative_column=None):
    """Read a typed table into points and a report fragment."""
    if not isinstance(table, dict) or not isinstance(table.get("rows"), list):
        raise VisualInputError("the file did not produce a table")
    columns = _column_names(table)
    rows = _rows_of(table)
    headerless = bool(table.get("headerless")) or _is_headerless(columns)
    warnings = []
    if headerless and not table.get("headerless"):
        columns, rows, headerless = _rebuild_headerless(table)
        warnings.append("The first row looked like data, not a header; I kept it.")
    if not rows:
        raise VisualInputError("the file has no data rows")
    profiles = [_profile([row[index] if index < len(row) else "" for row in rows])
                for index in range(len(columns))]
    label_index, value_index, cumulative_index, more = _choose_columns(
        columns, profiles, kind, label_column, value_column, cumulative_column)
    warnings.extend(more)
    points, skipped = [], []
    auto_labels = []
    capped = False
    header_offset = 1 if not headerless else 0
    for row_number, row in enumerate(rows, 1):
        line_number = row_number + header_offset
        if len(points) >= MAX_POINTS:
            skipped.append({"line": line_number, "text": " | ".join(row),
                            "reason": "the input is over the %d-point limit" % MAX_POINTS})
            capped = True
            break
        value_raw = row[value_index] if value_index < len(row) else ""
        number = parse_number(value_raw)
        if number is None:
            skipped.append({"line": line_number, "text": " | ".join(row),
                            "reason": "the value column has no number"})
            continue
        label = _clean_label(row[label_index]) if label_index is not None and label_index < len(row) else ""
        if not label:
            label = "Item %d" % (len(points) + 1)
            auto_labels.append(label)
            label_auto = True
        else:
            label_auto = False
        if label.lower() in ("total", "grand total", "sum", "subtotal"):
            warnings.append("Row %d looks like a total; include it only if it belongs in the "
                            "chart." % line_number)
        if len(label) > MAX_LABEL:
            warnings.append("Row %d: the label is long; it may be cut off in the chart."
                            % line_number)
            label = label[:MAX_LABEL - 3].rstrip() + "..."
        point = {"label": label, "value": number["value"], "cumulative": None,
                 "label_auto": label_auto, "raw": " | ".join(row), "line": line_number,
                 "unit": number.get("unit") or ""}
        if kind == "pareto":
            cumulative_raw = row[cumulative_index] if cumulative_index is not None and cumulative_index < len(row) else ""
            cumulative = parse_number(cumulative_raw)
            if cumulative is None:
                skipped.append({"line": line_number, "text": " | ".join(row),
                                "reason": "the running-total column has no number"})
                continue
            point["cumulative"] = cumulative["value"]
            point["cumulative_raw"] = cumulative["raw"]
            if cumulative.get("ambiguous"):
                warnings.append("Row %d: '%s' was read as %s; if you meant a decimal, write it "
                                "with a point." % (line_number, cumulative["raw"],
                                                   cumulative["value"]))
        if number.get("ambiguous"):
            warnings.append("Row %d: '%s' was read as %s; if you meant a decimal, write it "
                            "with a point." % (line_number, number["raw"], number["value"]))
        points.append(point)
    if auto_labels:
        warnings.append("%d row(s) had no label; they were called %s. "
                        "Rename them if you want."
                        % (len(auto_labels), ", ".join(auto_labels[:3])))
    if capped:
        warnings.append("The input has more than %d points; only the first %d are shown."
                        % (MAX_POINTS, MAX_POINTS))
    labels = [point["label"].lower() for point in points]
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        warnings.append("More than one point is called %s; the chart cannot tell them apart."
                        % ", ".join(duplicates[:3]))
    columns_report = {"label": columns[label_index] if label_index is not None else None,
                      "value": columns[value_index] if value_index is not None else None,
                      "cumulative": columns[cumulative_index] if cumulative_index is not None else None}
    available = [{"name": name, "type": "number" if profile["numeric"] else "text",
                  "numeric": profile["numeric"], "text": profile["text"],
                  "missing": profile["missing"], "sample": profile["samples"]}
                 for name, profile in zip(columns, profiles)]
    return {"points": points, "skipped": skipped, "warnings": warnings,
            "columns": columns_report, "columns_available": available,
            "headerless": headerless, "rows": len(rows), "filename": filename,
            "sha256": sha256}


def _numeric_rows(table):
    """How many rows carry a number after the first cell (a Word-table score)."""
    count = 0
    for row in table.get("rows") or []:
        cells = row[1:] if len(row) > 1 else row
        if any(parse_number(cell) is not None for cell in cells):
            count += 1
    return count


def table_from_rows(rows, filename=None, sha256=None):
    """Build a table dict from raw rows (used by the Word-table reader)."""
    clean_rows = [[_cell_text(cell) for cell in row] for row in rows]
    clean_rows = [row for row in clean_rows if any(cell for cell in row)]
    if not clean_rows:
        return None
    width = max(len(row) for row in clean_rows)
    clean_rows = [row + [""] * (width - len(row)) for row in clean_rows]
    first = clean_rows[0]
    headerless = (any(parse_number(cell) is not None for cell in first[1:])
                  or (len(first) == 1 and parse_number(first[0]) is not None))
    if headerless:
        names = ["Column %d" % (index + 1) for index in range(width)]
        data = clean_rows
    else:
        names = [cell or ("Column %d" % (index + 1)) for index, cell in enumerate(first)]
        data = clean_rows[1:]
    columns = []
    for index, name in enumerate(names):
        values = [row[index] if index < len(row) else "" for row in data]
        profile = _profile(values)
        columns.append({"name": name, "type": "number" if profile["numeric"] else "text",
                        "n_present": profile["numeric"] + profile["text"],
                        "n_missing": profile["missing"], "sample": profile["samples"]})
    return {"filename": filename, "sha256": sha256, "n_rows": len(data),
            "n_cols": len(names), "columns": columns, "rows": data,
            "headerless": headerless}


# --- documents -------------------------------------------------------------

def _infer_title(text, filename):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    for line in lines[:20]:
        match = re.match(r"^(?:chart\s+)?title\s*[:\-]\s*(.+)$", line, re.IGNORECASE)
        if match:
            return _clean_label(match.group(1))
    for line in lines[:8]:
        low = line.lower()
        if low.startswith(("make ", "create ", "draw ", "prepare ", "using ", "use ",
                           "please ", "i want ", "i need ", "the task ", "task:")):
            continue
        if line.endswith(".") or len(line) < 3 or len(line) > 80:
            continue
        if _NUMBER_TOKEN.search(line):
            continue
        return _clean_label(line)
    stem = os.path.splitext(os.path.basename(filename or ""))[0]
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    return stem.title() if stem else ""


def _infer_kind(text):
    low = (" " + str(text or "").lower() + " ")
    for kind, phrases in _KIND_PHRASES:
        for phrase in phrases:
            if phrase in low:
                return kind, "the instruction says %r" % phrase
    return None, "the instruction does not name a chart kind"


def _kind_reason(kind):
    return {
        "bar": "a bar compares the values directly",
        "line": "a line reads a trend over time",
        "area": "an area reads a trend and its volume over time",
        "scatter": "a scatter plot shows whether two values move together",
        "candlestick": "a candlestick reads the open, high, low and close of each period",
        "pie": "a pie reads a few parts as a whole",
        "stacked_bar": "a stacked bar reads the parts of a whole",
        "waterfall": "a waterfall reads the steps between a start and an end",
        "pareto": "a pareto ranks the bars and draws the running total",
        "table": "a table keeps the figures as a list",
    }.get(kind, "the data can carry this chart")


def _check_kind(kind, points):
    """Return the reasons a chart kind cannot honestly carry these points."""
    reasons = []
    if not kind:
        return reasons
    if kind != "table" and len(points) < MIN_CHART_POINTS:
        reasons.append("A chart needs at least two points; a single figure is a sentence, "
                       "not a chart.")
    if kind in ("pie", "stacked_bar"):
        bad = [point for point in points if Decimal(point["value"]) <= 0]
        if bad:
            reasons.append("A %s needs positive values; line %d is %s. Choose a bar, line "
                           "or waterfall instead." % (kind.replace("_", " "), bad[0]["line"],
                                                      bad[0]["value"]))
    if kind == "scatter":
        missing = [point for point in points if point.get("x") is None]
        if missing:
            reasons.append("Line %d has no x value; a scatter plot needs label, x, y."
                           % missing[0]["line"])
    if kind == "candlestick":
        for point in points:
            if any(point.get(key) is None for key in ("open", "high", "low", "close")):
                reasons.append("Line %d needs open, high, low and close for a candlestick."
                               % point["line"])
                break
            try:
                open_value = Decimal(point["open"])
                high_value = Decimal(point["high"])
                low_value = Decimal(point["low"])
                close_value = Decimal(point["close"])
            except (InvalidOperation, ValueError):
                reasons.append("Line %d has a non-numeric candlestick value." % point["line"])
                break
            if high_value < low_value:
                reasons.append("Line %d has a high below its low." % point["line"])
                break
            if high_value < max(open_value, close_value) or low_value > min(open_value, close_value):
                reasons.append("Line %d has an open or close outside its high-low range."
                               % point["line"])
                break
    if kind == "pareto":
        bad = [point for point in points if Decimal(point["value"]) <= 0]
        if bad:
            reasons.append("A pareto draws positive bars; line %d is %s."
                           % (bad[0]["line"], bad[0]["value"]))
        last = None
        for point in points:
            if point.get("cumulative") is None:
                reasons.append("Line %d has no running total; a pareto needs a third number "
                               "on every line." % point["line"])
                continue
            value = Decimal(point["cumulative"])
            if last is not None and value < last:
                reasons.append("The running total falls at line %d (%s after %s); a pareto's "
                               "running total must never fall. Check the figures or use a "
                               "waterfall." % (point["line"], point["cumulative"], last))
                break
            last = value
    return reasons


def _normalized(points, with_running=False):
    lines = []
    for point in points:
        if point.get("x") is not None:
            parts = [point["label"], point["x"], point["value"]]
        elif point.get("open") is not None:
            parts = [point["label"], point["open"], point["high"], point["low"],
                     point["close"]]
        else:
            parts = [point["label"], point["value"]]
            if with_running and point.get("cumulative") is not None:
                parts.append(point["cumulative"])
        lines.append("\t".join(parts))
    return "\n".join(lines)


def _plan(source_kind, points, title, kind, columns, skipped, filename, sheet):
    plan = []
    if not points:
        plan.append("I found no figures to draw.")
        if skipped:
            plan.append("%d line(s) could not be read; they are listed below." % len(skipped))
        plan.append("I will not draw anything until there are figures.")
        return plan
    if source_kind == "instruction":
        plan.append("Read %s." % (filename or "your instruction file"))
        if kind == "table":
            plan.append("The instruction asks for a table.")
        elif kind == "scatter":
            plan.append("The instruction asks for a scatter plot.")
        elif kind == "candlestick":
            plan.append("The instruction asks for a candlestick chart.")
        elif kind == "area":
            plan.append("The instruction asks for an area chart.")
        elif kind:
            plan.append("The instruction asks for a %s chart." % kind.replace("_", " "))
        plan.append("I found %d figure(s) in the file." % len(points))
    elif source_kind == "data":
        where = filename or "your data file"
        if sheet:
            where += " (sheet %r)" % sheet
        plan.append("Read %d data row(s) from %s." % (len(points), where))
    else:
        plan.append("Read %d line(s) you typed." % len(points))
    if columns.get("label") and columns.get("value"):
        plan.append("Use '%s' as the label and '%s' as the value."
                    % (columns["label"], columns["value"]))
        if columns.get("cumulative"):
            plan.append("Use '%s' as the running total." % columns["cumulative"])
    if title and (kind == "table" or len(points) >= MIN_CHART_POINTS):
        if kind == "table":
            plan.append("Build a table titled %r." % title)
        elif kind == "scatter":
            plan.append("Draw a scatter plot titled %r." % title)
        elif kind == "candlestick":
            plan.append("Draw a candlestick chart titled %r." % title)
        elif kind == "area":
            plan.append("Draw an area chart titled %r." % title)
        elif kind:
            plan.append("Draw a %s chart titled %r." % (kind.replace("_", " "), title))
        else:
            plan.append("Draw a chart titled %r; I will propose the kind from the shape of the "
                        "data." % title)
    elif title:
        plan.append("I need at least two points before I can draw this chart.")
    else:
        plan.append("Give the chart a title before creating it.")
    if source_kind in ("data", "instruction"):
        plan.append("Every value comes from your file. Nothing was added, changed or summed.")
    else:
        plan.append("Every value is yours. Nothing was added, changed or summed.")
    if skipped:
        plan.append("%d line(s) could not be read; they are listed below." % len(skipped))
    return plan


def _report(source, title, kind, kind_reason, columns, columns_available, points,
            skipped, warnings, needs, blocked, plan, normalized_text, extra=None):
    report = {
        "format": FORMAT,
        "ok": not blocked,
        "source": source,
        "title": title,
        "kind": {"value": kind, "source": (extra or {}).get("kind_source", ""),
                 "reason": kind_reason},
        "columns": columns,
        "columns_available": columns_available,
        "points": points,
        "skipped": skipped,
        "ignored": (extra or {}).get("ignored", []),
        "warnings": warnings,
        "needs": needs,
        "blocked": blocked,
        "plan": plan,
        "normalized_text": normalized_text,
    }
    if extra:
        for key in ("rows", "headerless", "extraction", "sheet"):
            if key in extra:
                report[key] = extra[key]
    return report


def _decode_file(payload):
    filename = payload.get("filename")
    encoded = payload.get("content_base64")
    if not isinstance(filename, str) or not filename.strip():
        raise VisualInputError("filename is required")
    if not isinstance(encoded, str) or not encoded.strip():
        raise VisualInputError("content_base64 is required")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError, binascii.Error):
        raise VisualInputError("content_base64 is not valid base64")
    if not raw:
        raise VisualInputError("the file is empty")
    if len(raw) > 5_000_000:
        raise VisualInputError("the file is over the 5 MB limit")
    return filename, raw


def _read_file(payload, mode, kind, title_in):
    from . import documents, intake

    if TABLE_READER is None:
        raise VisualInputError("the table reader is not attached, so a data file cannot be read")
    kind = kind or None
    filename, raw = _decode_file(payload)
    role = "brief" if mode == "instruction" else "dataset"
    record = intake.save(filename, raw, payload.get("content_type"), role=role)
    source = {"kind": mode, "id": record["id"], "filename": record["filename"],
              "sha256": record["sha256"], "ext": record["ext"]}
    skipped, warnings, ignored = [], [], []
    columns = {"label": None, "value": None, "cumulative": None}
    columns_available = []
    table = None
    text = ""
    inference_text = ""
    extraction = None
    if mode == "data":
        try:
            table = TABLE_READER(filename, raw, sheet=payload.get("sheet"),
                                 merged="refuse")
        except ValueError as error:
            raise VisualInputError(str(error))
        read = read_table(table, filename, record["sha256"], kind,
                          payload.get("label_column"), payload.get("value_column"),
                          payload.get("cumulative_column"))
        points, skipped, warnings = read["points"], read["skipped"], read["warnings"]
        columns, columns_available = read["columns"], read["columns_available"]
        source.update({"sheet": table.get("sheet"), "columns": columns})
    else:
        ext = os.path.splitext(filename)[1].lower()
        if ext in (".docx", ".docm"):
            try:
                tables = documents.extract_docx_tables(raw)
            except documents.DocumentError as error:
                raise VisualInputError(str(error))
            if len(tables) > 1:
                warnings.append("The document has %d tables; I used the one with the most "
                                "numeric rows." % len(tables))
            chosen = None
            chosen_score = (0, 0)
            for candidate in tables:
                built = table_from_rows(candidate.get("rows") or [], filename, record["sha256"])
                if built is None:
                    continue
                score = (_numeric_rows(built), built.get("n_rows", 0))
                if score > chosen_score:
                    chosen, chosen_score = built, score
            read = None
            if chosen is not None:
                try:
                    read = read_table(chosen, filename, record["sha256"], kind,
                                      payload.get("label_column"), payload.get("value_column"),
                                      payload.get("cumulative_column"))
                except VisualInputError:
                    read = None
            if read is not None and read.get("points"):
                table = chosen
                points, skipped, warnings = read["points"], read["skipped"], read["warnings"]
                columns, columns_available = read["columns"], read["columns_available"]
                source.update({"columns": columns, "table": "docx"})
                text = "\n".join(" | ".join(row) for row in table.get("rows") or [])
                inference_text = text
                try:
                    result = documents.extract_document(raw, filename)
                except documents.DocumentError:
                    result = None
                if result and result.get("status") == "extracted":
                    inference_text = result.get("text") or text
                    extraction = {"method": result.get("method"), "pages": result.get("pages"),
                                  "chars": result.get("chars")}
                    source["extraction"] = extraction
                    cells = {cell.strip().lower() for row in table.get("rows") or []
                             for cell in row}
                    outside = []
                    for line in inference_text.splitlines():
                        for match in _NUMBER_TOKEN.finditer(line):
                            if match.group(0).strip().lower() not in cells:
                                outside.append(line.strip())
                                break
                    if outside:
                        warnings.append("I used the table; numbers in these paragraphs were "
                                        "not used: " + " / ".join(outside[:3]))
            else:
                try:
                    result = documents.extract_document(raw, filename)
                except documents.DocumentError as error:
                    raise VisualInputError(str(error))
                if result.get("status") != "extracted":
                    raise VisualInputError(result.get("reason") or
                                           "I could not read text from this document.")
                text = result.get("text") or ""
                inference_text = text
                extraction = {"method": result.get("method"), "pages": result.get("pages"),
                              "chars": result.get("chars")}
                points, skipped, warnings = parse_lines(
                    text, kind == "pareto", kind == "scatter", kind == "candlestick")
                source["extraction"] = extraction
        else:
            try:
                result = documents.extract_document(raw, filename)
            except documents.DocumentError as error:
                raise VisualInputError(str(error))
            if result.get("status") != "extracted":
                raise VisualInputError(result.get("reason") or
                                       "I could not read text from this document.")
            text = result.get("text") or ""
            inference_text = text
            extraction = {"method": result.get("method"), "pages": result.get("pages"),
                          "chars": result.get("chars")}
            points, skipped, warnings = parse_lines(
                text, kind == "pareto", kind == "scatter", kind == "candlestick")
            source["extraction"] = extraction
    kind_source = "you" if kind else ""
    if kind is None:
        inferred, reason = _infer_kind(inference_text)
        if inferred:
            kind, kind_reason, kind_source = inferred, reason, "instruction"
            # A scatter or candlestick line carries more numbers than the
            # label/value reader accepts.  Now that the instruction has named
            # the chart, read the same text again with the right reader.
            if inferred in ("pareto", "scatter", "candlestick") and text:
                points, skipped, warnings = parse_lines(
                    text, inferred == "pareto", inferred == "scatter",
                    inferred == "candlestick")
        else:
            kind_reason = "I will propose a chart from the shape of the data."
    else:
        kind_reason = "you chose this kind"
    title = title_in
    title_source = "you" if title_in else ""
    if not title:
        inferred_title = _infer_title(inference_text, "")
        if inferred_title:
            title, title_source = inferred_title, "heading"
        else:
            title = os.path.splitext(os.path.basename(filename))[0].replace("_", " ").replace("-", " ").title()
            title_source = "file_name"
    return {"source": source, "points": points, "skipped": skipped, "warnings": warnings,
            "ignored": ignored, "columns": columns, "columns_available": columns_available,
            "title": title, "title_source": title_source, "kind": kind,
            "kind_reason": kind_reason, "kind_source": kind_source, "table": table,
            "text": text, "extraction": extraction}


def interpret(payload):
    """Read one request and return the report the screen shows."""
    if not isinstance(payload, dict):
        raise VisualInputError("the read request must be an object")
    mode = str(payload.get("mode") or "typed").strip().lower()
    if mode not in ("typed", "data", "instruction", "inputs"):
        raise VisualInputError("mode must be typed, data, instruction or inputs")
    title_in = str(payload.get("title") or "").strip()
    kind_in = str(payload.get("kind") or "").strip()
    from . import visuals
    if kind_in and kind_in not in visuals.KINDS:
        raise VisualInputError("unknown chart kind %r" % kind_in)
    if mode == "inputs":
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise VisualInputError("add at least one input, value")
        points, skipped, warnings = parse_lines(text, False)
        blocked = [] if points else ["I found no input figures. I will not invent them."]
        needs = []
        report = _report(
            {"kind": "typed", "filename": None, "sha256": None},
            {"value": title_in, "source": "typed"}, "", "",
            {"label": "Input", "value": "Value", "cumulative": None}, [],
            points, skipped, warnings, needs, blocked,
            _plan("typed", points, title_in, None, {"label": "Input", "value": "Value"},
                  skipped, None, None), _normalized(points, False))
        return report
    source_file = payload.get("file") if isinstance(payload.get("file"), dict) else None
    if mode == "typed":
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise VisualInputError("type at least one line, e.g. Q1, 120000")
        points, skipped, warnings = parse_lines(
            text, kind_in == "pareto", kind_in == "scatter", kind_in == "candlestick")
        source = {"kind": "typed", "filename": None, "sha256": None}
        if source_file and source_file.get("filename"):
            source.update({"id": source_file.get("id"),
                           "filename": source_file.get("filename"),
                           "sha256": source_file.get("sha256"),
                           "edited": bool(source_file.get("edited"))})
        title = title_in
        title_source = "you" if title else ""
        kind = kind_in
        kind_reason = "you chose this kind" if kind else ""
        kind_source = "you" if kind else ""
        columns = {"label": None, "value": None, "cumulative": None}
        columns_available = []
        table = None
        extraction = None
        ignored = []
    else:
        read = _read_file(payload, mode, kind_in, title_in)
        points, skipped, warnings = read["points"], read["skipped"], read["warnings"]
        source, columns, columns_available = read["source"], read["columns"], read["columns_available"]
        title, kind, kind_reason = read["title"], read["kind"], read["kind_reason"]
        title_source = read.get("title_source") or "file"
        kind_source = read.get("kind_source") or ""
        table, extraction, ignored = read["table"], read["extraction"], read["ignored"]
        if source_file and source_file.get("filename"):
            source["edited"] = bool(source_file.get("edited"))
    blocked = []
    needs = []
    if extraction:
        warnings.append("The text was read from your file; check it against the file before "
                        "using it.")
    if points and kind != "table" and len(points) > 30:
        warnings.append("The chart has %d points; a line chart or a table may read better."
                        % len(points))
    units = sorted({point.get("unit") for point in points if point.get("unit")})
    if units:
        warnings.append("Values carry %s; the chart shows the numbers, not the unit."
                        % ", ".join(units))
    if kind == "pareto" and not points and skipped and all(
            "running total" in str(item.get("reason") or "") for item in skipped):
        blocked.append("A pareto needs a running total on every line. Add a third number "
                       "to each line; I will not add up the bars for you.")
    elif kind == "scatter" and not points:
        blocked.append("I found no pairs to plot. A scatter line is label, x, y - e.g. "
                       "'Ad spend, 1200, 45000'. I will not invent them.")
    elif kind == "candlestick" and not points:
        blocked.append("I found no periods to draw. A candlestick line is label, open, high, "
                       "low, close - e.g. 'Day one, 100, 120, 90, 110'. I will not invent them.")
    elif not points:
        blocked.append("I found no figures in this input. I will not invent them. "
                       "Add lines like 'Q1, 120000' or upload a data file.")
    if kind == "pareto" and points and any(point.get("cumulative") is None for point in points):
        blocked.append("A pareto needs a running total on every line. Add a third number "
                       "to each line; I will not add up the bars for you.")
    if points:
        blocked.extend(_check_kind(kind, points))
    if not title:
        needs.append("Give the chart a title.")
    if not points:
        needs.append("Add at least two figures, one per line.")
    labels = [point["label"].lower() for point in points]
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        warnings.append("More than one point is called %s; the chart cannot tell them apart."
                        % ", ".join(duplicates[:3]))
    if kind == "pareto" and points:
        warnings = [warning for warning in warnings if "running total" not in warning.lower()]
    plan = _plan(mode, points, title, kind, columns, skipped,
                 source.get("filename"), source.get("sheet"))
    if blocked and points:
        plan = [line for line in plan
                if not (line.startswith("Draw a ") or line.startswith("Build a "))]
        plan.append("I will not draw anything until the points above are fixed.")
    report = _report(source, {"value": title, "source": title_source},
                     kind, kind_reason, columns, columns_available, points, skipped,
                     warnings, needs, blocked, plan, _normalized(points, kind == "pareto"),
                     {"rows": (table or {}).get("n_rows"), "headerless": (table or {}).get("headerless"),
                      "extraction": extraction, "sheet": source.get("sheet"),
                      "kind_source": kind_source})
    return report
