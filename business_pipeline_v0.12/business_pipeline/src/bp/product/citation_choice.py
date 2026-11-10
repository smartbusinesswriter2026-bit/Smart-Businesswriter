"""The citation style a brief asks for.

A student who writes "in Harvard style" in the brief means it.  The quiet lanes
ask no questions, so the brief is the only place the style can be stated; the
guide route's style select still wins when the student sets one there.

Only the styles the product already carries are recognised.  A name the product
does not support is ignored, so the paper falls back to APA rather than
pretending to render a style it cannot.
"""

import re

from . import citation_styles

FORMAT = "bp-citation-choice/1"

#: The names a brief may use, the style each one means, and whether the name
#: says on its own that it is the style to use ("Harvard referencing" does;
#: a bare "Harvard" does not).
NAMES = (
    ("harvard", "harvard", False),
    ("harvard", "harvard style", True),
    ("harvard", "harvard referencing", True),
    ("harvard", "harvard citation", True),
    ("harvard", "harvard system", True),
    ("harvard", "huddersfield", False),
    ("apa", "apa", False),
    ("apa", "apa 7", False),
    ("apa", "apa 6", False),
    ("apa", "apa style", True),
    ("apa", "apa format", True),
    ("apa", "american psychological association", True),
    ("mla", "mla", False),
    ("mla", "mla 9", False),
    ("mla", "mla style", True),
    ("mla", "mla format", True),
    ("mla", "modern language association", True),
    ("chicago_ad", "chicago author-date", True),
    ("chicago_ad", "chicago author date", True),
    ("chicago_nb", "chicago notes-bibliography", True),
    ("chicago_nb", "chicago notes bibliography", True),
    ("vancouver", "vancouver", False),
    ("vancouver", "vancouver style", True),
    ("ieee", "ieee", False),
    ("ieee", "ieee style", True),
    ("oscola", "oscola", False),
    ("oscola", "oscola style", True),
)

#: A style must be stated as the one to use, not merely named.
CUE = re.compile(r"(in|use|using|follow|follows|according to|cite|citing|cited|"
                 r"citation|reference|referencing|references|bibliograph\w*|style|"
                 r"format)\W*$", re.I)


def _cued(body, start, end):
    """The name is used as the style to use: a cue word stands before or after it."""
    if CUE.search(body[max(0, start - 40):start]):
        return True
    return bool(CUE.search(body[end:end + 30]))


def read(text):
    """The citation style the brief states, or "" when it states none."""
    body = str(text or "").lower()
    if not body.strip():
        return ""
    supported = set(citation_styles.STYLES)
    best = ("", None)
    for style, name, self_cue in NAMES:
        if style not in supported:
            continue
        match = re.search(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])", body)
        if not match:
            continue
        if not self_cue and not _cued(body, match.start(), match.end()):
            continue
        if best[1] is None or match.start() < best[1]:
            best = (style, match.start())
    return best[0]
