"""One period model for every reader in the statements tile.

A period is a range; a date is a point.  This module is the only place that knows the
difference, so the tile's preflight and its solvers cannot disagree about it.

Before it existed the tile had three answers to "what period is this?" in three places,
and they disagreed:

* a narrative that opened "on 1 January 2025" was read as the period `2025-01-01 to
  2025-01-01` - one day - because the first date in the text was taken as the period end;
* a fiscal year whose start and end were both stated was read as *two* periods, because
  every distinct date was counted as a period;
* a transaction date ("on 2 January it bought a delivery van for 30,000") was counted as
  a second figure on one line, and the line was refused as a comparative.

So the rules live here, once:

* a **period phrase** names a range - "for the year ended 31 December 2025", "for the
  year 2025", "the financial year 2025", "for the period 1 January 2025 to 31 December
  2025";
* a **balance date** names a point - "trial balance at 31 December 2026", "extracted at
  31 December 2026", "as at 31 December 2026";
* every other date is a **transaction date**: a point inside the period, never the
  period itself.

The period the tile uses is, in order: a stated period phrase; a stated balance date;
the calendar years the transaction dates fall in; an assumed year.

Nothing here computes a business number.  It reads dates.
"""
import re
from datetime import date, timedelta

#: The months a date may name, by full name and by three-letter abbreviation.
MONTHS = {}
for _index, _month in enumerate(
        "january february march april may june july august september october "
        "november december".split()):
    MONTHS[_month] = _index + 1
    MONTHS[_month[:3]] = _index + 1

#: The year an assumed period uses.  It is fixed rather than "today", so a record built
#: without a stated period replays identically a year from now.
ASSUMED_YEAR = 2026


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

_ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_DMY = re.compile(r"(\d{1,2})\s+([a-z]{3,9})\.?\s*,?\s*(\d{4})", re.I)
_MDY = re.compile(r"([a-z]{3,9})\.?\s+(\d{1,2})\s*,?\s*(\d{4})", re.I)
#: A month and a day with no year: a date, never a figure.
_MONTH_DAY = re.compile(r"(?:(\d{1,2})\s+([a-z]{3,9})\.?|([a-z]{3,9})\.?\s+(\d{1,2}))", re.I)
#: A bare year: a date in a label, never a figure.
_YEAR = re.compile(r"(?:19|20)\d{2}")


def _month(name):
    """The month number a name gives, or None when it is not a month."""
    key = str(name or "").lower().rstrip(".")
    if key in MONTHS:
        return MONTHS[key]
    return MONTHS.get(key[:3])


def _iso(year, month, day):
    """An ISO date, or None when the day does not exist in that month."""
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except (ValueError, TypeError):
        return None


def _date_at(text, pos=0):
    """(iso, length) for a full date at `pos`, or None.  Whitespace before it is skipped."""
    while pos < len(text) and text[pos].isspace():
        pos += 1
    match = _ISO.match(text, pos)
    if match:
        value = _iso(match.group(1), match.group(2), match.group(3))
        if value:
            return value, match.end() - pos
    for pattern, order in ((_DMY, (1, 2, 3)), (_MDY, (3, 1, 2))):
        match = pattern.match(text, pos)
        if not match:
            continue
        month = _month(match.group(order[1]))
        if not month:
            continue
        value = _iso(match.group(order[2]), month, match.group(order[0]))
        if value:
            return value, match.end() - pos
    return None


def _date_spans(text):
    """(start, end) of every date-like token in the text."""
    spans = []
    for pattern, month_group in ((_ISO, None), (_DMY, 2), (_MDY, 1)):
        for match in pattern.finditer(text):
            if month_group is not None and not _month(match.group(month_group)):
                continue
            spans.append((match.start(), match.end()))
    for match in _MONTH_DAY.finditer(text):
        name = match.group(2) or match.group(3)
        if not _month(name):
            continue
        if any(start <= match.start() < end for start, end in spans):
            continue          # already covered by a full date
        spans.append((match.start(), match.end()))
    return sorted(spans)


def strip_dates(text):
    """The text with every date-like token removed: no date is ever a figure."""
    return _strip(text, _date_spans(text))


def strip_years(text):
    """The text with every date-like token and every bare year removed."""
    spans = list(_date_spans(text))
    for match in _YEAR.finditer(text):
        if any(start <= match.start() < end for start, end in spans):
            continue
        spans.append((match.start(), match.end()))
    return _strip(text, sorted(spans))


def _strip(text, spans):
    if not spans:
        return text
    out, last = [], 0
    for start, end in spans:
        out.append(text[last:start])
        last = end
    out.append(text[last:])
    return " ".join(part.strip() for part in out if part.strip())


def date_spans(text):
    """(start, end) of every date-like token in the text."""
    return _date_spans(text)


def transaction_dates(text):
    """Every full date in the text, as ISO strings, in the order they appear."""
    out = []
    for start, end in _date_spans(text):
        value = _date_at(text, start)
        if value:
            out.append(value[0])
    return out


# ---------------------------------------------------------------------------
# Period cues
# ---------------------------------------------------------------------------

#: A phrase that names the accounting period.
_CUE = re.compile(
    r"(?P<cue>for the (?:financial |fiscal )?year(?: ended| ending| to)?"
    r"|for the period(?: ended| ending| to)?"
    r"|for the month(?: ended| ending)?"
    r"|for the (?:twelve|six|nine|three) months ended"
    r"|financial year(?: ended| ending)?"
    r"|fiscal year(?: ended| ending)?"
    r"|year of account"
    r"|year[- ]end(?:ed|ing)?"
    r"|period ended|period ending"
    r"|year ended|year ending|year to)", re.I)

#: A phrase that names a point in time: the date a set of balances is taken at.
_BALANCE = re.compile(
    r"(?P<cue>trial balance[^.\n]{0,40}?\b(?:as at|as of|at)\b"
    r"|balance sheet[^.\n]{0,40}?\b(?:as at|as of)\b"
    r"|statement of financial position[^.\n]{0,40}?\b(?:as at|as of)\b"
    r"|extracted at\b"
    r"|\bas at\b"
    r"|\bas of\b)", re.I)

#: The two dates of an explicit range: "<date> to <date>".
_RANGE = re.compile(
    r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}\s+[a-z]{3,9}\.?\s*,?\s*\d{4}|[a-z]{3,9}\.?\s+\d{1,2},?\s*\d{4})"
    r"\s*(?:to|until|through|-|–|—)\s*"
    r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}\s+[a-z]{3,9}\.?\s*,?\s*\d{4}|[a-z]{3,9}\.?\s+\d{1,2},?\s*\d{4})",
    re.I)


def _sentence(text, position):
    """The sentence around a match, so the tile can quote the cue it acted on."""
    start = max(text.rfind(".", 0, position), text.rfind("\n", 0, position)) + 1
    end = text.find(".", position)
    return text[start:end + 1 if end != -1 else len(text)].strip()[:240]


def _fiscal_start(end):
    """The start of the year that ends on `end`: the same day a year earlier, plus a day."""
    year, month, day = (int(part) for part in end.split("-"))
    try:
        return (date(year - 1, month, day) + timedelta(days=1)).isoformat()
    except ValueError:
        return (date(year - 1, month, 28) + timedelta(days=1)).isoformat()


def _range_after(text, pos):
    """(start, end) the cue at `pos` names, or None."""
    tail = text[pos:].lstrip()
    match = _RANGE.match(tail)
    if match:
        first = _date_at(match.group(1))
        second = _date_at(match.group(2))
        if first and second:
            return first[0], second[0]
    found = _date_at(tail)
    if found:
        return _fiscal_start(found[0]), found[0]
    year = _YEAR.match(tail.lstrip())
    if year:
        return "%s-01-01" % year.group(0), "%s-12-31" % year.group(0)
    return None


def periods(text):
    """Every period the text names.

    Each entry is `{"start", "end", "kind", "cue", "quote"}`, where `kind` is
    `"period"` for a stated period phrase and `"balance"` for a stated balance date.
    """
    source = str(text or "")
    out = []
    for match in _CUE.finditer(source):
        found = _range_after(source, match.end())
        if not found:
            continue
        out.append({"start": found[0], "end": found[1], "kind": "period",
                    "cue": match.group(0).strip(), "quote": _sentence(source, match.start())})
    for match in _BALANCE.finditer(source):
        found = _date_at(source, match.end())
        if not found:
            continue
        out.append({"start": found[0][:4] + "-01-01", "end": found[0], "kind": "balance",
                    "cue": match.group(0).strip(), "quote": _sentence(source, match.start())})
    return out


def periods_in(text):
    """Every distinct period end the text names - period phrases and balance dates alike.

    This is what the tile counts to refuse a comparative: a text that names two
    different period ends carries two periods.
    """
    return {p["end"] for p in periods(text)}


def period_of(text):
    """(period, source, quote).  The period the tile uses, and where it came from.

    `source` is `"declared"` when the text states the period or the balance date,
    `"derived"` when it comes from the transaction dates, and `"assumed"` when the text
    says nothing at all.
    """
    source = str(text or "")
    stated = periods(source)
    phrases = [p for p in stated if p["kind"] == "period"]
    if phrases:
        first = phrases[0]
        return {"start": first["start"], "end": first["end"]}, "declared", first["quote"]
    balances = [p for p in stated if p["kind"] == "balance"]
    if balances:
        first = balances[0]
        return {"start": first["start"], "end": first["end"]}, "declared", first["quote"]
    dates = transaction_dates(source)
    if dates:
        years = [d[:4] for d in dates]
        # A single accounting period is one calendar year. When the text's dates
        # span more than one year (e.g. a rent policy running into next year),
        # the period is the year the problem is about, not the range of dates.
        from collections import Counter
        if len(set(years)) > 1:
            year = Counter(years).most_common(1)[0][0]
        else:
            year = years[0]
        return ({"start": year + "-01-01", "end": year + "-12-31"},
                "derived", "")
    # No full dates: fall back to the most common four-digit year in the text,
    # so a problem headed "2025 transactions" is not dated to the server's year.
    import re as _re
    years = _re.findall(r"\b(19\d{2}|20\d{2})\b", source)
    if years:
        from collections import Counter
        year = Counter(years).most_common(1)[0][0]
        return {"start": year + "-01-01", "end": year + "-12-31"}, "assumed", ""
    return {"start": "%d-01-01" % ASSUMED_YEAR, "end": "%d-12-31" % ASSUMED_YEAR}, "assumed", ""
