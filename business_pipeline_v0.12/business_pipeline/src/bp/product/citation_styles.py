"""Citation styles supported by the Home chat conductor.

The conductor records the style in the paper contract and uses it when it
drafts and exports the paper.  A style is data here: its label, whether it is
author-date or numbered, the heading of its reference list, and the separator
between authors.

Rules this module keeps:
- data only: no formula, no number invented by the model;
- an unknown style is refused with the real options, never substituted;
- the style is frozen in the paper contract once approved.
"""

FORMAT = "bp-citation-styles/1"

STYLES = {
    "apa": {"label": "APA 7", "kind": "author_date", "reference_heading": "References", "author_sep": " & "},
    "harvard": {"label": "Harvard", "kind": "author_date", "reference_heading": "Bibliography", "author_sep": " and "},
    "chicago_ad": {"label": "Chicago author-date", "kind": "author_date", "reference_heading": "Bibliography", "author_sep": " and "},
    "mla": {"label": "MLA 9", "kind": "author_date", "reference_heading": "Works Cited", "author_sep": " and "},
    "vancouver": {"label": "Vancouver", "kind": "numbered", "reference_heading": "Bibliography", "author_sep": ", "},
    "ieee": {"label": "IEEE", "kind": "numbered", "reference_heading": "Bibliography", "author_sep": ", "},
    "oscola": {"label": "OSCOLA", "kind": "numbered", "reference_heading": "Bibliography", "author_sep": ", "},
    "chicago_nb": {"label": "Chicago notes-bibliography", "kind": "numbered", "reference_heading": "Bibliography", "author_sep": ", "},
}

AUTHOR_DATE_STYLES = tuple(key for key, value in STYLES.items() if value["kind"] == "author_date")
NUMBERED_STYLES = tuple(key for key, value in STYLES.items() if value["kind"] == "numbered")


def is_style(key):
    return str(key or "").strip().lower() in STYLES


def style(key):
    return STYLES.get(str(key or "").strip().lower())


def kind(key):
    row = style(key)
    return row["kind"] if row else None


def reference_heading(key):
    row = style(key)
    return row["reference_heading"] if row else "References"


def is_numbered(key):
    return kind(key) == "numbered"


def is_author_date(key):
    return kind(key) == "author_date"


def all_styles():
    return list(STYLES)


def validate(key):
    key = str(key or "").strip().lower()
    if key not in STYLES:
        return ["unknown citation style " + str(key) + "; choose one of: " + ", ".join(STYLES)]
    return []