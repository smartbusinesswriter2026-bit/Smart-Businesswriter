"""Unified problem-type classifier (Tip 5 Types 1-7).

The four engines each have their own detector; this module names the problem type once, in
the record, so a reader (and the tile's routing) can see which kind of problem was solved.
The order is specific-to-general:

1. **Type 4 — correcting an erroneous entry.** The most specific cue: the text states an
   error and asks for the correction.
2. **Type 2 — reconstructing a missing figure.** The text asks for a figure a relation can
   solve.
3. **Type 6 — from a trial balance.** The text says "trial balance".
4. **Type 5 — statement of cash flows.** The text asks for a cash-flow statement with its
   three activities.
5. **Type 3 — ratio analysis.** The text names ratios.
6. **Type 7 — integrated case.** Several transaction cues in one case.
7. **Type 1 — preparing statements from transactions.** One or two transaction cues.

A text no cue matches is `type=None`, never a guess.
"""

from __future__ import annotations

import re

from . import error_correction as ec
from . import reconstruction as recon
from . import financial_computations as fc


TYPES = {
    1: "Preparing statements from transactions",
    2: "Reconstructing a missing figure",
    3: "Ratio analysis",
    4: "Correcting an erroneous entry",
    5: "Statement of cash flows (indirect)",
    6: "Preparing statements from a trial balance",
    7: "Integrated case problem",
}

TRANSACTION_CUES = re.compile(
    r"\b(?:started|began|bought|sold|paid|received|purchased|borrowed|invested|"
    r"issued|collected|provided|earned|incurred|charged|recorded)\b", re.I)


def classify_problem(text: str) -> dict:
    """Classify a problem text into one of Tip 5's seven types.

    Returns ``{"type": 1-7 or None, "label": str, "why": str}``.
    """
    low = str(text or "").lower()
    # 1. Error correction — the most specific cue.
    if ec.detect_error_problem(text):
        return {"type": 4, "label": TYPES[4],
                "why": "the text states an error and asks for the correction"}
    # 2. An explicit missing RAW figure (not a ratio) is a reconstruction.
    target = re.search(r"\b(?:find|compute|calculate|determine|what is|what was)\s+(?:the\s+)?([a-z ]+?)(?:\?|\.|,|$)", low)
    if (target and not re.search(r"\bratios?\b", target.group(1))
            and re.search(
                r"\b(?:assets|liabilities|capital|inventory|purchases|sales|revenue|profit|"
                r"income|equity|cogs|cost of goods sold|retained earnings|working capital)\b",
                target.group(1))):
        return {"type": 2, "label": TYPES[2],
                "why": "the text asks for a missing figure"}
    # 3. Ratio analysis — the text names ratios.
    if re.search(r"\bratios?\b", low):
        return {"type": 3, "label": TYPES[3],
                "why": "the text names ratios"}
    # 4. Any other reconstruction a relation can solve.
    if recon.detect_reconstruction_problem(text):
        return {"type": 2, "label": TYPES[2],
                "why": "the text asks for a missing figure a relation can solve"}
    # 5. A trial balance.
    if re.search(r"\btrial balance\b", low):
        return {"type": 6, "label": TYPES[6], "why": "the text is a trial balance"}
    # 6. A cash-flow statement with its activities named.
    if (re.search(r"\bcash ?flows? statement\b|\bstatement of cash ?flows?\b", low)
            and re.search(r"\b(?:operating|investing|financing)\b", low)):
        return {"type": 5, "label": TYPES[5],
                "why": "the text asks for a cash-flow statement with its activities"}
    # 7/8. Transaction count decides case vs preparation.
    cues = len(TRANSACTION_CUES.findall(text))
    if cues >= 3:
        return {"type": 7, "label": TYPES[7],
                "why": f"{cues} transaction cues in one case"}
    if cues >= 1:
        return {"type": 1, "label": TYPES[1],
                "why": f"{cues} transaction cue(s)"}
    return {"type": None, "label": "Unclassified", "why": "no problem-type cue matched"}


__all__ = ["TYPES", "TRANSACTION_CUES", "classify_problem"]
