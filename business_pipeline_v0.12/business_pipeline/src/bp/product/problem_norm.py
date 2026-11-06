"""Deterministic problem normalizers (product layer, stdlib only).

These run on **every** solve, not just on Resolve, so a problem that reaches the
frozen parser is already in the shape it accepts. They never invent a figure:
each transformation is a text-level rewrite that leaves every number untouched.

Transformations, in order:
  1. split a one-line account list into one account per line
  2. drop exact duplicate lines (same normalised content; differing amounts are
     never merged)
  3. shorten an oversized input at a line or sentence boundary

Anything else is left alone: a refusal that is about the problem's *content*
(no transaction, no figures) is not a layout defect and must not be rewritten.
"""
import re

#: The statements model reader refuses inputs above 20000 characters.
MAX_INPUT = 18000


def split_inline_accounts(text):
    """Split a one-line 'Cash 5000, Capital 5000' problem into account lines.

    Only commas/semicolons between segments that each carry a number become line
    breaks, and a leading cue ("Trial balance:") is removed from the first
    account. A text that already has line breaks is returned unchanged.
    """
    text = str(text or "").strip()
    if not text or "\n" in text:
        return text
    parts = [p.strip() for p in re.split(r"[;,]", text) if p.strip()]
    if len(parts) < 2 or not all(re.search(r"\d", p) for p in parts):
        return text
    parts[0] = re.sub(r"^(?:the following balances?|trial balance|balances?)[^:]*:\s*",
                      "", parts[0], flags=re.I)
    return "\n".join(p for p in parts if p)


def drop_duplicate_lines(text):
    """Drop exact duplicate lines (same normalised content); keep the first."""
    seen, kept = set(), []
    for line in str(text or "").splitlines():
        key = re.sub(r"\s+", " ", line.strip().lower())
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        kept.append(line)
    return "\n".join(kept)


def shorten(text):
    """Shorten an over-long problem without inventing anything."""
    text = re.sub(r"[ \t]+", " ", str(text or ""))
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line and not re.fullmatch(r"[-=_*~]{3,}", line)]
    text = "\n".join(lines)
    if len(text) <= MAX_INPUT:
        return text
    cut = text[:MAX_INPUT]
    boundary = cut.rfind("\n")
    if boundary < MAX_INPUT * 0.6:
        boundary = max(cut.rfind(". "), cut.rfind("; "))
    if boundary > 0:
        cut = cut[:boundary + 1]
    return cut.rstrip()


def normalize_problem(text):
    """Apply every deterministic normalizer. Returns (text, notes: list[str])."""
    out = str(text or "")
    notes = []
    split = split_inline_accounts(out)
    if split != out:
        notes.append("split inline account list into lines")
        out = split
    deduped = drop_duplicate_lines(out)
    if deduped != out:
        notes.append("dropped duplicate account lines")
        out = deduped
    shortened = shorten(out)
    if shortened != out:
        notes.append("shortened oversized input")
        out = shortened
    return out, notes
