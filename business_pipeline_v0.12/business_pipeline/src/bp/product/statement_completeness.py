"""Completeness gate for the statements pipeline.

Checks that every stated dollar figure in the problem text appears in at least one
entry or adjustment. If figures are missing, returns the list so the retry loop
can feed them back to the model.

This is a GATE (verification), not a restriction on the model. The model may
propose any figure; the gate checks that no stated figure was left unused.
"""
import re
from decimal import Decimal, InvalidOperation


def _norm(s):
    try:
        return Decimal(str(s).replace(",", "").replace("$", "").strip())
    except (InvalidOperation, ValueError):
        return None


def stated_figures(text):
    """Extract all dollar figures from the problem text as a set of Decimals."""
    out = set()
    for m in re.finditer(r'\$[\d,]+(?:\.\d+)?', str(text or "")):
        v = _norm(m.group(0))
        if v is not None:
            out.add(v)
    return out


def used_figures(extracted):
    """Extract all dollar figures used in entries and adjustments."""
    out = set()
    for e in (extracted.get("entries") or []):
        for line in (e.get("lines") or []):
            for key in ("debit", "credit"):
                if line.get(key) is not None:
                    v = _norm(line[key])
                    if v is not None:
                        out.add(v)
    for a in (extracted.get("adjustments") or []):
        for v in (a.get("params") or {}).values():
            nv = _norm(v)
            if nv is not None:
                out.add(nv)
    return out


def check(text, extracted):
    """Return (ok, missing_list). ok=True if all stated figures are used."""
    stated = stated_figures(text)
    used = used_figures(extracted)
    missing = stated - used
    return len(missing) == 0, sorted(missing)
