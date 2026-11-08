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
    # Split on a semicolon, or on a comma that is not a thousands separator
    # ("5,200" is one amount; "Cash 5,000, Capital 5,000" is two accounts).
    parts = [p.strip() for p in re.split(r";\s*|,(?!\d)", text) if p.strip()]
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


def normal_side(name):
    """The normal balance a statement account carries: 'debit', 'credit', or None.

    Ordered so a contra account wins over its family (`Accumulated Depreciation` is
    a credit, `Depreciation` is a debit) and a payable wins over its expense word
    (`Salaries Payable` is a credit, `Salaries Expense` a debit).  It returns None
    for a label it does not know, so a caller never guesses a side.
    """
    low = " " + str(name or "").lower().strip() + " "
    if any(k in low for k in ("accumulated depreciation", "allowance for",
                              "provision for bad", "provision for doubtful")):
        return "credit"
    if any(k in low for k in ("payable", "unearned", "accrued", "loan", "mortgage",
                              "bond", "capital", "stock", "retained earnings",
                              "equity", "revenue", "sales", "income", "earnings",
                              "gain", "fees earned", "commission")):
        return "credit"
    if any(k in low for k in ("cash", "bank", "receivable", "inventory", "equipment",
                              "furniture", "fixture", "building", "land", "vehicle",
                              "prepaid", "supplies", "patent", "goodwill",
                              "investment", "expense", "cost of goods sold", "wages",
                              "salaries", "rent", "insurance", "utilities",
                              "advertising", "depreciation", "drawings", "dividends")):
        return "debit"
    return None


#: `Cash $18,500` / `Cost of Goods Sold $22,500` / `Accounts Receivable 7,200`.
_NARRATIVE_PAIR = re.compile(
    r"((?:[A-Z][A-Za-z'\-]*)(?:\s+(?:(?:of|and|for|at|on|the|in)\s+)?[A-Z][A-Za-z'\-]*)*)"
    r"\s*\$?\s*(\d[\d,]*(?:\.\d+)?)")


def narrative_balance(problem):
    """Debits minus credits of a narrative trial balance, or None if it is not one.

    The deterministic reader only understands a tabular trial balance, so a
    generated narrative ("Cash $18,500; Accounts Receivable $7,200; ... Prepare a
    trial balance") walked past the imbalance guard and failed deep in the journal
    builder, where it was logged as a pipeline defect.  This reads the
    `Account $amount` pairs and types each one by its normal side.

    Conservative by design: it applies only when the problem asks for a trial
    balance, carries no adjustments, and every amount-bearing account label is
    recognised.  Otherwise it returns None and the caller falls back to the reader.
    """
    from decimal import Decimal

    text = str(problem or "")
    low = text.lower()
    if "trial balance" not in low:
        return None
    # Only a problem that *asks for an adjustment* is excluded: an accumulated
    # depreciation balance is part of a trial balance, not an adjusting entry.  The
    # broad ADJUSTMENT_CUES list matches "depreciation" and skipped the guard on
    # exactly the narrative trial balances that needed it.
    if any(cue in low for cue in ("adjusting entry", "adjusting entries", "adjustment",
                                  "adjust the", "after adjustment")):
        return None
    pairs = _NARRATIVE_PAIR.findall(text)
    if len(pairs) < 4:
        return None
    debits = credits = Decimal("0")
    used = 0
    for name, amount in pairs:
        side = normal_side(name)
        if side is None:
            # A date or a heading matched the shape.  Skip it only when it carries
            # no decimal thousands separator; otherwise the label is genuinely
            # unknown and the check must not guess.
            if "," not in amount:
                continue
            return None
        used += 1
        value = Decimal(amount.replace(",", ""))
        if side == "debit":
            debits += value
        else:
            credits += value
    if used < 4:
        return None
    return debits - credits


def trial_balance_imbalance(problem):
    """Debits minus credits of a problem read as a trial balance, or None if it is not one.

    A *generated* trial balance that does not balance is an invalid test fixture, not a
    pipeline failure: no pipeline change can make two figures the generator wrote agree.
    The heal loop uses this to tell the two apart before it counts a result against the
    pipeline.  A narrative problem, or one the reader cannot read as a trial balance,
    returns None (it is not classified here).

    A narrative problem that *does* declare a trial balance is read by
    `narrative_balance`: the tabular reader sees no journal there, and returning 0
    for "no lines" let an out-of-balance narrative through the guard.
    """
    from decimal import Decimal, InvalidOperation
    try:
        from . import statements
    except Exception:
        return None
    # A problem that carries adjustments is not a pure trial balance: the adjusted route
    # reads it, and the *post-solve* refusal check catches an imbalance there.  Only a
    # pure trial balance is checked here.
    try:
        needs_adjustments = statements._needs_adjustments(problem)
    except Exception:
        needs_adjustments = False
    if not needs_adjustments:
        try:
            reading = statements.read_deterministic(problem)
        except Exception:
            reading = None
        debits = credits = Decimal("0")
        lines = 0
        if isinstance(reading, dict):
            for entry in reading.get("journal") or []:
                for line in entry.get("lines") or []:
                    for side in ("debit", "credit"):
                        raw = line.get(side)
                        if not raw:
                            continue
                        try:
                            value = Decimal(str(raw).replace(",", ""))
                        except (InvalidOperation, ValueError):
                            return None
                        lines += 1
                        if side == "debit":
                            debits += value
                        else:
                            credits += value
        if lines:
            return debits - credits
    # No tabular journal: a narrative trial balance is still a trial balance, so check
    # its declared pairs rather than calling it balanced because no lines were read.
    return narrative_balance(problem)
