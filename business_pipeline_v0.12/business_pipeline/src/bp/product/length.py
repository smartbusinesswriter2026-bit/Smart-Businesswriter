"""Paper length as a word count, not a band.

The student states the number of body words a rubric asks for; the paper is
measured against that number with a tolerance, and the count is reported.  It is
not an export gate: a paper outside the tolerance is still the student's paper.
The one repair pass (see ``chat`` and ``completion``) tries to close the gap and
then stops.  No function here invents a fact, a section or a word.

What counts as a body word
--------------------------
The body is the prose between the introduction and the end of the conclusion.
The title page, the title, the headings, the reference list and any footnote are
not body words.  A footnote is not rendered by this product (the .docx writer
has no footnotes part), so nothing has to be subtracted for one; the rule is
stated so a later renderer cannot quietly change the unit.

Why not a band
--------------
The old short/mid/long ranges described how many sections a paper carried, not
how long the student's rubric said the paper should be.  A 2,400-word rubric
target and a 5,000-word target both produced the same 2,242-word draft.  The
band labels are kept only so older saved cases still render; a new run carries a
number.
"""

#: The smallest paper this product will accept.  A per-type floor can raise it
#: through ``minimum_for``; the owner has not supplied per-type numbers yet, so
#: every type uses this floor for now.
MIN_WORDS = 600

#: The largest target the interface accepts.  A longer target is allowed and
#: reported honestly; one repair pass will not necessarily reach it, and the
#: notice beside the count says so.
MAX_WORDS = 50000

#: The allowance the product aims at when the rubric does not state its own.
DEFAULT_TOLERANCE = 0.10

#: Per-type floors.  Empty means "use MIN_WORDS".  The key is the paper
#: archetype or the worksheet template; a later owner decision fills it without
#: changing the measurement or the repair pass.
TYPE_MINIMUMS = {}


def minimum_for(*keys):
    """The floor for the first named type that has one, else ``MIN_WORDS``.

    The keys may be an archetype, a template id or a profile key; they are tried
    in order and the first positive value wins.  Nothing is guessed from a label.
    """
    for key in keys:
        value = TYPE_MINIMUMS.get(str(key or "").strip().lower())
        if value:
            return int(value)
    return MIN_WORDS


def check(value, minimum=None):
    """Read a target as a word count, or raise ``ValueError`` with the reason.

    A named band is still accepted for old links and saved cases; it resolves to
    the old band's target.  A number is the normal path now.  ``minimum`` is the
    type's floor when the caller knows it; it defaults to the global floor.
    """
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0
    names = {"short": 600, "mid": 1200, "long": 2500}
    if text.lower() in names:
        return names[text.lower()]
    import re
    match = re.search(r"\d+", text)
    floor = int(minimum or MIN_WORDS)
    if not match:
        raise ValueError("Give a word count between %d and %d." % (floor, MAX_WORDS))
    words = int(match.group(0))
    if words < floor:
        raise ValueError("A paper below %d words cannot carry the parts this type needs. "
                         "Give %d or more." % (floor, floor))
    if words > MAX_WORDS:
        raise ValueError("A target above %d words is longer than one paper can support here; "
                         "give %d or fewer." % (MAX_WORDS, MAX_WORDS))
    return words


def band_for(words):
    """The legacy band name for a count, used only for section composition."""
    words = int(words or 0)
    if words >= 2500:
        return "long"
    if words >= 1200:
        return "mid"
    return "short"


def _heading(item):
    return str((item or {}).get("heading") or "").strip() if isinstance(item, dict) else ""


def _lines(item):
    if isinstance(item, dict):
        return [str(line) for line in (item.get("lines") or [])]
    if isinstance(item, (list, tuple)) and len(item) > 1:
        return [str(line) for line in (item[1] or [])]
    return []


#: Headings whose prose is not body prose.  The reference list is the only one
#: the current writer emits; "Appendix" is deliberately *not* excluded because a
#: marker may count it, and the product cannot know the marker's rule.
NOT_BODY = ("references", "bibliography", "works cited", "reference list")


def body_words(sections):
    """Count body words in a section list: no title page, headings or references.

    The caller passes the same section list the .docx writer receives, so the
    count and the document cannot drift.  Figure captions and table text are not
    prose and are not counted; a sourced quote is counted because it is part of
    the body the student submits.
    """
    total = 0
    for item in sections or []:
        if _heading(item).lower() in NOT_BODY:
            continue
        for line in _lines(item):
            total += len(line.split())
    return total


def report(target, actual, tolerance=DEFAULT_TOLERANCE):
    """The target, the measured count and whether it is inside the allowance.

    ``met`` is ``True`` only when the count is inside the two-sided range.  It is
    a report, not a verdict on quality and not an export gate.
    """
    target = int(target or 0)
    actual = int(actual or 0)
    if not target:
        return {"target": 0, "actual": actual, "tolerance": None, "range": None,
                "met": None, "note": "No word target was stated."}
    tolerance = DEFAULT_TOLERANCE if tolerance is None else float(tolerance)
    tolerance = max(0.0, min(0.5, tolerance))
    low = int(round(target * (1 - tolerance)))
    high = int(round(target * (1 + tolerance)))
    met = bool(low <= actual <= high)
    if met:
        note = ("The body is %d words, inside the %d-word target +/-%g%% (%d-%d)."
                % (actual, target, tolerance * 100, low, high))
    elif actual < low:
        note = ("The body is %d words, %d below the %d-word target +/-%g%% (%d-%d). "
                "The allowance is strived for, not guaranteed." % (actual, low - actual, target,
                                                                   tolerance * 100, low, high))
    else:
        note = ("The body is %d words, %d above the %d-word target +/-%g%% (%d-%d). "
                "The allowance is strived for, not guaranteed." % (actual, actual - high, target,
                                                                   tolerance * 100, low, high))
    return {"target": target, "actual": actual, "tolerance": tolerance,
            "range": [low, high], "met": met, "note": note}


def plan(target, actual, tolerance=DEFAULT_TOLERANCE):
    """How far the body is from the target, for the one repair pass.

    A positive ``shortfall`` asks for more analysed sections; a positive
    ``surplus`` asks for the optional sections to be removed.  Neither is a
    command to pad: the caller adds or removes whole sections that already carry
    the student's record.
    """
    report_ = report(target, actual, tolerance)
    if report_["met"] is not False:
        return {"report": report_, "shortfall": 0, "surplus": 0}
    low, high = report_["range"]
    return {"report": report_, "shortfall": max(0, low - actual), "surplus": max(0, actual - high)}
