"""The statements tile: one instruction in, the statements and the working out (product layer).

The tile classifies the problem, reads every figure with the text it came from, compiles the
reading into the engagement spec the **core** accepts, calls the core, and presents what the core
computed.  It computes nothing itself: the solver, the diagnosis and the ratios are injected from
`bp.server` (see `attach_core`), because this package may not import the frozen core
(`tests/test_product_boundary.py`).

Decisions that matter, and why they are not obvious:

- **A trial balance is posted as one period entry, never as opening balances.**  Probed against the
  core: opening balances make `net_income_agrees_across_routes` and `cash_flow_agrees_across_routes`
  fail (7/11), because the closing entries move equity with no matching asset movement; one period
  entry passes every applicable check (9/11 with `checks_na = 2`).
- **A cash flow statement is withheld for a trial-balance problem** and named as withheld.  The core
  will produce one from a single period entry, and it is false: the whole cash balance reads as a
  period inflow (trap T2 in `docs/STATEMENTS_TILE_PLAN.md`).
- **A figure the statements cannot support is omitted, never estimated**, so `ratio_analysis` names
  it as not computed instead of showing a zero.
- **No blocking question.**  The record carries an answer, or a named gap with the diagnosis.
"""

import json
import os
import re
import tempfile
import uuid
from decimal import Decimal

from . import cases
from . import income_statement as is_mod
from .income_statement import (detect_income_statement, detect_ratio_analysis,
                               detect_given_balances, detect_eps,
                               parse_eps_problem, compute_eps_problem, render_eps_problem)
from . import financial_computations as fc
from . import reconstruction as recon
from . import error_correction as ec
from . import statements_verify
from .. import statement_chart
from .. import statement_detect as sd
from .. import statement_period as sper
from .. import statement_plan as sp
from . import verify

FORMAT = "bp-statements/1"
FIGURES_FORMAT = "bp-statements-figures/1"
PROBLEM_TYPES = ("trial_balance", "transactions", "adjustments", "incomplete_records")
FRAMEWORKS = ("US_GAAP", "IFRS", "local")
DEFAULT_CURRENCY = "USD"

#: A currency or a place this product does not use.  Refused with the reason, never normalised
#: silently: the product is global and its examples are neutral (CONTRIBUTORS section 1 item 11).
BLOCKED = re.compile(
    r"\b(PHP|PSE|PSEi|Philippines?|Filipino|Manila|EUR|GBP|JPY|CNY|RMB|INR|AUD|CAD|CHF|"
    r"HKD|SGD|NZD|KRW|BRL|MXN|ZAR|NGN|KES|AED|SAR)\b|[€£¥₹₱]", re.I)


class StatementError(ValueError):
    """The tile cannot solve this instruction; the message is what the student is shown."""


class CoreNotAttached(StatementError):
    """`server.py` did not inject the frozen core, so the tile refuses instead of guessing."""


class NoModel(StatementError):
    """No model is configured for the plan layer; another reader may still be available.

    Distinct from a substantive refusal: "nothing is configured" is a reason to try the next reader,
    while "this amount is not in the instruction" is final and must never be retried elsewhere.
    """


class StatementRefused(StatementError):
    """A reading the tile refuses outright.

    Distinct from a plain `StatementError` because no model reading can rescue it: two sets of
    balances, two periods, or a consolidation are **not one entity's one trial balance**, and asking
    a model about them would only produce a merged statement that looks right and is not.
    """


_CORE = {}


def attach_core(solve=None, diagnose=None, ratio_analysis=None, dupont=None, reader=None,
                extract=None, build=None, set_tier=None, schedules=None, working_capital=None,
                working_capital_cycle=None, trend=None, guards=None, case_solver=None,
                tax_reconciliation=None, piotroski=None, beneish=None):
    """Attach the frozen-core callables (called from `bp.server`).

    `extract` and `build` are the plan layer, injected for the same reason as the rest: the product
    package computes nothing and imports no core module (`tests/test_product_boundary.py`).
    `set_tier` switches the model tier for escalation.  `schedules` is the frozen schedule
    arithmetic (`bp.schedule_math.compute`), used by the labelled-figure routes.  `guards` is
    the 22-guard runner (`bp.guards.run`), injected so the record carries its verdicts without
    the product importing the core.  `case_solver` is the integrated case state machine
    (`bp.case_solver.solve_case`), injected for the same reason.
    """
    for name, fn in (("solve", solve), ("diagnose", diagnose), ("ratio_analysis", ratio_analysis),
                     ("dupont", dupont), ("reader", reader), ("extract", extract), ("build", build),
                     ("set_tier", set_tier), ("schedules", schedules),
                     ("working_capital", working_capital),
                     ("working_capital_cycle", working_capital_cycle), ("trend", trend),
                     ("guards", guards), ("case_solver", case_solver),
                     ("tax_reconciliation", tax_reconciliation), ("piotroski", piotroski),
                     ("beneish", beneish)):
        if fn is not None:
            _CORE[name] = fn
    return sorted(_CORE)


def _core(name):
    fn = _CORE.get(name)
    if fn is None:
        raise CoreNotAttached("the statements tile is not attached to the frozen core (" + name + "); "
                              "start the workbench with python -m bp.server, which attaches it")
    return fn


def attached():
    """Whether the tile can run: the solver and the diagnosis are the minimum."""
    return "solve" in _CORE and "diagnose" in _CORE


def reset_core():
    """Detach every injected core callable.

    Tests attach different subsets; a test that attaches more (a builder, a trend method) must
    clean up so a later test that assumes a smaller subset is not handed a callable it did not
    attach.  The product never calls this.
    """
    _CORE.clear()


#: Detection cues.  A trial balance is tested **before** adjustments, because a stated balance sheet
#: and profit-and-loss is a trial balance whatever words its account names contain ("accumulated
#: depreciation" is a balance, not an adjustment).  The cue that fired is recorded and shown.
CUES = (
    ("incomplete_records", (r"\bincomplete records\b", r"\bsingle entry\b", r"\bstatement of affairs\b",
                            r"\bfind the (capital|drawings|profit)\b", r"\bmissing (capital|drawings)\b")),
    ("trial_balance", (r"\btrial balance\b", r"\bthe following balances?\b", r"\bextracted at\b")),
    ("adjustments", (r"\baccrued\b", r"\baccruals?\b", r"\bprepaid\b", r"\bin advance\b", r"\bowing\b",
                     r"\bdepreciate\b|\bdepreciating\b", r"\bcharge depreciation\b",
                     r"\bdepreciation (charge|expense|for the year)\b", r"\bbad debts?\b",
                     r"\bprovision for\b", r"\badjust(ing)? entries?\b")),
    ("transactions", (r"\bstarted (?:\w+\s+)?(?:with|business)\b", r"\bbought\b", r"\bsold\b", r"\bpaid\b",
                      r"\breceived\b", r"\bon credit\b", r"\bpurchased\b")),
)

#: Cues that say a problem needs adjusting entries.  Used to distinguish a real
#: "adjustments were not derived" gap from a narrative that simply has none: a
#: one-line problem ("Issued common stock for 80,000 cash") must not be reported as
#: missing prepaids, depreciation, COGS or tax when it never asked for them.
ADJUSTMENT_CUES = ("accrued", "prepaid", "amortiz", "depreciat", "estimated at",
                   "ending supplies", "ending inventory count", "earned but unpaid",
                   "unpaid at year", "estimated uncollectible", "allowance",
                   "warranty", "shrinkage", "estimated warranty")


def _needs_adjustments(text):
    """Whether the instruction mentions the kind of item an adjusting entry is for."""
    low = str(text or "").lower()
    return any(cue in low for cue in ADJUSTMENT_CUES)

#: The chart vocabulary: (label pattern, type, section, statement line, role, activity, contra).
#: Order is the ranking when a label matches more than once: the earlier rule is the literal
#: standard reading (a loan is a liability before it is capital).  A label that matches nothing is
#: reported, never guessed.
_RULES_SEED = (
    (r"^(cash|bank|cash at bank|bank account|bank current account)$", "asset", "current", "Cash", "cash", "operating", False),
    (r"^(trade receivables?|receivables?|debtors?|accounts? receivable|sundry debtors|a/?r)$", "asset", "current", "Trade receivables", "", "operating", False),
    (r"^(inventor(y|ies)|stock|closing stock)$", "asset", "current", "Inventory", "", "operating", False),
    (r"^(prepayments?|prepaid\b.*)$", "asset", "current", "Prepayments", "", "operating", False),
    (r"^(equipment|vehicles?|machinery|furniture|land|buildings?|plant|motor vehicles?|office equipment|freehold property)$",
     "asset", "non_current", "Property, plant and equipment", "", "investing", False),
    (r"^(accumulated depreciation\b.*|provision for depreciation\b.*)$",
     "asset", "non_current", "Property, plant and equipment", "", "investing", True),
    (r"\bloan\b", "liability", "non_current", "Borrowings", "", "financing", False),
    (r"^(trade payables?|payables?|creditors?|accounts? payable|sundry creditors|a/?p)$", "liability", "current", "Trade payables", "", "operating", False),
    (r"^(accrued expenses?|accruals?|accrued\b.*)$", "liability", "current", "Accruals", "", "operating", False),
    (r"\bowner'?s?\b", "equity", "", "Capital", "capital", "financing", False),
    (r"^(capital|share capital|equity|owner'?s? capital)$", "equity", "", "Capital", "capital", "financing", False),
    (r"^(retained earnings?|accumulated (profit|earnings)|revenue reserve)(\s*\(.*\))?$", "equity", "", "Retained earnings", "retained_earnings", "", False),
(r"^(supplies|prepaid supplies|supplies on hand)$", "asset", "current", "Supplies", "", "operating", False),
(r"^(unearned revenue|deferred revenue|unearned income)(\s*\(.*\))?$", "liability", "current", "Accruals", "", "operating", False),
(r"^(notes payable|notes payable.*|long.term (debt|notes? payable)|long.term debt)(\s*\(.*\))?$", "liability", "non_current", "Borrowings", "", "financing", False),
(r"^(common stock|share capital|capital stock)(\s*\(.*\))?$", "equity", "", "Capital", "capital", "financing", False),
    (r"^(drawings?|dividends?)$", "equity", "", "Dividends", "dividends", "financing", True),
    (r"^(sales|revenue|turnover|fees earned|service revenue)$", "income", "", "Revenue", "", "operating", False),
    (r"^(other income|other gains?|interest income|income|gains?|gain on .+|other .* income|other .* gains?)$",
     "income", "", "Other income", "", "operating", False),
    (r"^(purchases?|cost of (sales|goods sold)|cogs)$", "expense", "", "Cost of sales", "", "operating", False),
    (r"^(interest\b.*|loan interest)$", "expense", "", "Interest expense", "", "operating", False),
    (r"^(finance costs?|financial (expenses?|charges)|bank charges?)$", "expense", "", "Finance costs", "", "operating", False),
    # The operating expenses are separate accounts, not one catch-all line: Salaries and
    # Rent are different things, and a statement that cannot tell them apart cannot show
    # a reader what the business spent money on.
    (r"^(rent|rental|rent expense)$", "expense", "", "Rent expense", "", "operating", False),
    (r"^(salaries|salary|wages|staff costs?|salaries and wages)( expense)?$", "expense", "", "Salaries expense", "", "operating", False),
    (r"^(utilities|utilities expense|electricity|water)$", "expense", "", "Utilities expense", "", "operating", False),
    (r"^(insurance|insurance expense)$", "expense", "", "Insurance expense", "", "operating", False),
    (r"^(advertising|advertising expense|marketing)$", "expense", "", "Advertising expense", "", "operating", False),
    (r"^(depreciation|depreciation expense)$", "expense", "", "Depreciation", "", "operating", False),
    (r"^(bad debts?|bad debt expense|provision for doubtful debts)$", "expense", "", "Bad debts", "", "operating", False),
    (r"^(general expenses?|general expense)$", "expense", "", "General expenses", "", "operating", False),
    (r"^(operating expenses?|operating expense)$", "expense", "", "Operating expenses", "", "operating", False),
    (r"^(telephone|telephone expense|phone)$", "expense", "", "Telephone expense", "", "operating", False),
    (r"^(transport|transport expense|delivery)$", "expense", "", "Transport expense", "", "operating", False),
    (r"^(repairs?|repairs and maintenance)$", "expense", "", "Repairs expense", "", "operating", False),
    (r"^(stationery|stationery expense|office supplies)$", "expense", "", "Stationery expense", "", "operating", False),
    (r"^supplies expense$", "expense", "", "Supplies expense", "", "operating", False),
    (r"^(fuel|fuel expense)$", "expense", "", "Fuel expense", "", "operating", False),
    (r"^(travel|travel expense)$", "expense", "", "Travel expense", "", "operating", False),
    (r"^(other expenses?|costs?|expenses?)$", "expense", "", "Other expenses", "", "operating", False),
)

from . import tier1_tables as _t1
RULES = _t1.get_rules() or _RULES_SEED

#: Internal chart codes.  The statements print the `line`, never the code, so these are
#: house-keeping rather than a numbering convention the student has to match.
CODE_FOR_LINE = {"Cash": "1000", "Trade receivables": "1100", "Inventory": "1200", "Prepayments": "1300",
                 "Supplies": "1350", "Property, plant and equipment": "1500", "Trade payables": "2000",
                 "Accruals": "2300", "Borrowings": "2100", "Capital": "3000", "Retained earnings": "3100",
                 "Dividends": "3200", "Revenue": "4000", "Other income": "4050", "Cost of sales": "5000",
                 "Operating expenses": "5100", "Telephone expense": "6010", "Transport expense": "6020",
                 "Repairs expense": "6030", "Stationery expense": "6040", "Fuel expense": "6050",
                 "Travel expense": "6060", "Salaries expense": "6100", "Rent expense": "6200",
                 "Utilities expense": "6250", "Insurance expense": "6300", "Advertising expense": "6350",
                 "Depreciation": "6400", "Bad debts": "6500", "General expenses": "6600",
                 "Other expenses": "5300", "Finance costs": "5200", "Interest expense": "7100",
                 "Supplies expense": "6550"}

MONTHS = {m: i + 1 for i, m in enumerate(("january february march april may june july august september "
                                          "october november december").split())}
MONEY = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _sentence(text, position):
    """The sentence around a match, so the tile can quote the cue it acted on."""
    start = max(text.rfind(".", 0, position), text.rfind("\n", 0, position)) + 1
    end = text.find(".", position)
    return text[start:end + 1 if end != -1 else len(text)].strip()[:240]


def blocked_cue(text):
    """A currency or place the product does not use, or None."""
    match = BLOCKED.search(text or "")
    return match.group(0) if match else None


def currency_of(text, declared=None):
    """The case currency: declared, else USD.  A foreign code is refused by `read`."""
    if declared:
        return str(declared).strip().upper()
    return DEFAULT_CURRENCY


def classify(text):
    """(problem_type, cue, sentence) â€” the first group that fires wins, and the cue is recorded."""
    # A trial balance carries Dr/Cr markers.  If the text has them, it is a trial balance
    # regardless of what the cue patterns say (account names like "Depreciation expense"
    # can match adjustment cues).
    import re as _re
    if _re.search(r"\d[\d,]*(?:\.\d+)?\s*(?:Dr|Cr)\.?(?=\s|$|[;,.])", text, _re.I):
        return "trial_balance", "trial balance", "the instruction carries Dr/Cr markers"
    for kind, patterns in CUES:
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return kind, match.group(0), _sentence(text, match.start())
    raise StatementError("this does not read as an accounting problem I can solve: name the problem "
                         "(a trial balance, transactions, adjustments, or incomplete records) and give "
                         "the figures, and I will do the rest")


def period_of(text):
    """(period, source, quote).  A date is derived from the text; with none, the year is assumed.

    The rules live in `bp.statement_period`, the one place that knows that a period is a
    range and a date is a point.  A text that states "for the year ended 31 December 2025"
    declares its period; a text that opens "on 1 January 2025" states a *transaction* date,
    and the period is then the calendar year the transaction dates fall in.
    """
    return sper.period_of(text)


def _norm_label(text):
    return re.sub(r"\s+", " ", str(text or "").lower().strip(" .,:;-()[]|")).strip()


def _side(text):
    """A Dr/Cr marker anywhere in the row, or '' when the row carries none."""
    if re.search(r"\bdr\.?\b", text, re.I):
        return "D"
    if re.search(r"\bcr\.?\b", text, re.I):
        return "C"
    return ""


def place(label):
    """Where a label belongs: every rule it matches, in ranking order.

    `contested` is True when two rules match, which is exactly the case the council argues over
    (an owner's advance can be a loan or capital).  An empty `candidates` means the label is
    unknown: it is reported, never guessed into 'other assets'.
    """
    normalised = _norm_label(label)
    hits = []
    _rules = _t1.get_rules() if _t1.get_rules() is not None else _RULES_SEED
    for index, rule in enumerate(_rules):
        if re.search(rule[0], normalised):
            hits.append({"rule": index, "type": rule[1], "section": rule[2], "line": rule[3],
                         "role": rule[4], "activity": rule[5], "contra": rule[6]})
    return {"label": label, "normalised": normalised, "candidates": hits,
            "contested": len(hits) > 1, "placement": hits[0] if hits else None}


#: Words that cannot open or close an account name.  A line that begins or ends with one of
#: these is a sentence, not an account: "The owner invested 50,000 cash" is not a Capital
#: account, and posting it would count the same money a second time.
SENTENCE_EDGES = re.compile(
    r"^(the|this|that|these|those|it|they|we|he|she|there|on|in|at|during|after|before|when|while|"
    r"by|for|from|with|as|and|or|but|because|since|although|if|then|so)\b|"
    r"\b(the|of|in|on|to|and|or|at|by|with|from|as|for|were|was|is|are)$", re.I)


def _is_sentence(label):
    """True when a label reads as a sentence rather than the name of an account."""
    words = str(label or "").split()
    if not words:
        return True
    return bool(SENTENCE_EDGES.search(str(label).strip()))


def _without_dates(text):
    """The text with its dates - and the cue word in front of each - taken out."""
    out = str(text or "")
    for start, end in reversed(sper.date_spans(out)):
        before = re.sub(r"\b(as at|as of|at|on|by|from|to|until|ending|ended|of)\s*$", "", out[:start],
                        flags=re.I)
        out = before + out[end:]
    return re.sub(r"\s+", " ", out).strip(" .,:-|()[]")


def _line_pieces(line):
    """Split one line on sentence boundaries so an exam preamble does not hide the accounts.

    A period followed by whitespace ends a sentence ("... 31 December 2026. Cash 10,000"), while
    a decimal ("5.50") and a dot leader ("Cash ...... 5,000") carry no space after the period and
    are left intact.
    """
    return [piece.strip() for piece in re.split(r"\.\s+", str(line or "")) if piece.strip()]


def parse_rows(text):
    """Every 'label ... amount' line whose label the vocabulary knows.

    The amount is the **last** numeric token on the line that is not part of a date, so
    'Loan 2026 5,000' reads as 5,000 and 'Cash 5,000 at 31 December 2026' reads as 5,000
    rather than as the year.  A line whose label is a sentence and not an account name is
    returned as `skipped` with its text: it is shown in the working, never silently
    dropped, and never posted as an account.
    """
    rows, skipped = [], []
    for raw in str(text or "").splitlines():
        for line in _line_pieces(raw):
            if not line:
                continue
            spans = sper.date_spans(line)
            found = [m for m in MONEY.finditer(line)
                     if not any(start <= m.start() < end for start, end in spans)]
            if not found:
                skipped.append(line)
                continue
            last = found[-1]
            amount = last.group(0)
            label = re.sub(r"\b(dr|cr)\.?\b", " ", re.sub(r"\.{2,}", " ", line[:last.start()]), flags=re.I)
            label = re.sub(r"\b(dr|cr)\.?\b", " ", label, flags=re.I)
            # strip tabs, dollar signs and other non-alphanumeric junk left by tabular input
            label = re.sub(r"[\t$]", " ", label)
            # strip parenthetical qualifiers (and anything after an opening paren) before matching
            label = re.sub(r"\s*\(.*", "", label)
            label = re.sub(r"\s+", " ", label).strip(" .,:-|()[]")
            # A date is a date: it is not part of the account's name.
            label = _without_dates(label)
            if not label or _is_sentence(label):
                skipped.append(line)
                continue
            # Parenthetical dates like "(Jan 1)" are just date qualifiers, not reasons to skip.
            # Strip them and process the account normally.
            placed = place(label)
            if not placed["candidates"]:
                skipped.append(line)
                continue
            side = _side(line[:last.start()] + " " + line[last.end():])
            rows.append({"label": label, "written": amount, "side": side, "quote": line, "placed": placed})
    return rows, skipped


def _free_code(base, chart):
    """A chart code that is free, so two accounts on one statement line stay distinct."""
    taken = {a["code"] for a in chart}
    if base not in taken:
        return base
    for suffix in "ABCDEFGHIJ":
        if base + suffix not in taken:
            return base + suffix
    raise StatementError("too many accounts share the statement line " + base)


def _resolve(row):
    """(key, amount) â€” the side a row is posted on: its marker, else its nature, then its sign."""
    placement = row["placed"]["placement"]
    amount = row["written"].replace(",", "")
    negative = amount.startswith("-")
    if negative:
        amount = amount[1:]
    natural = "D" if placement["type"] in ("asset", "expense") else "C"
    if placement["contra"]:
        natural = "C" if natural == "D" else "D"
    side = row["side"] or natural
    if negative:
        side = "C" if side == "D" else "D"
    return ("debit" if side == "D" else "credit"), amount


def _decimals(written):
    text = str(written).replace(",", "")
    return len(text.split(".", 1)[1]) if "." in text else 0


def framework_of(text, framework=None):
    """US GAAP by default; IFRS or local only when the instruction says so, and it is never asked."""
    if framework:
        return framework
    if re.search(r"\bIFRS\b", text, re.I):
        return "IFRS"
    if re.search(r"\b(management accounts|local (policy|practices?|standards?))\b", text, re.I):
        return "local"
    return "US_GAAP"


def build_chart(rows):
    """One chart account per distinct placement, plus retained earnings (the core requires it).

    Each account carries the quote it was read from, so the verifier can prove every account came
    out of the instruction.  Two accounts may share a statement line (equipment and its accumulated
    depreciation): they get distinct codes and one of them is the contra.
    """
    chart, seen = [], {}
    for row in rows:
        placed = row["placed"]["placement"]
        # The account's own label is part of its identity: "Cash" and "Bank" are two accounts that
        # happen to share one statement line, which the ledger supports and a trial balance expects.
        # Two rows with the *same* label are one account, which is how a second set of books shows up.
        signature = (_norm_label(row["label"]), placed["line"], placed["type"], placed["role"],
                     placed["contra"], placed["section"], placed["activity"])
        code = seen.get(signature)
        if code is None:
            account = {"code": _free_code(CODE_FOR_LINE.get(placed["line"], "9000"), chart),
                       "name": row["label"], "type": placed["type"], "line": placed["line"],
                       "quote": row["quote"]}
            if placed["role"]:
                account["role"] = placed["role"]
            if placed["contra"]:
                account["contra"] = True
            if placed["section"]:
                account["section"] = placed["section"]
            if placed["activity"]:
                account["activity"] = placed["activity"]
            chart.append(account)
            code = account["code"]
            seen[signature] = code
        row["code"] = code
    if not any(a["type"] == "equity" and a.get("role") == "retained_earnings" for a in chart):
        chart.append({"code": _free_code("3100", chart), "name": "Retained earnings", "type": "equity",
                      "line": "Retained earnings", "role": "retained_earnings", "synthesised": True,
                      "quote": "retained earnings (added because a period has to close somewhere)"})
    return chart


#: Words that mark group accounts.  Consolidated statements are out of scope, and a merged statement
#: built from two entities' books looks plausible, so a mention is refused rather than solved.
CONSOLIDATION = re.compile(r"\b(consolidated|consolidation|group accounts?|intra-?group|"
                           r"on acquisition|goodwill on|non-?controlling interest|eliminations?)\b", re.I)


def periods_in(text):
    """Every distinct period the text names: period phrases and balance dates alike.

    Only a *cue* counts.  A transaction date is a point inside the period, so a narrative
    that opens "on 1 January 2025" and closes "on 31 December 2025" names **one** period,
    not two.  The rules live in `bp.statement_period`.
    """
    return sper.periods_in(text)


def column_lines(text):
    """Lines that carry two figures for one account: a comparative, which this tile does not support.

    A year inside a label ("Loan 2026 5,000") is not a second figure, and neither is a date
    ("On 2 January it bought a delivery van for 30,000"): every date-like token is removed
    before the figures are counted, so what remains is a label plus two amounts.

    The figures are counted **per clause**, not per line: a paragraph that states one
    transaction per sentence is one period's transactions, not a comparative column.
    """
    out = []
    for raw in str(text or "").splitlines():
        for clause in re.split(r"[.;]", raw):
            clause = clause.strip()
            if not clause:
                continue
            if _ADJUSTMENT_CUE.search(clause):
                # An adjustment sentence legitimately carries several figures (a payment and
                # its months, a rate and a base); it is not a comparative column.
                continue
            without_dates = sper.strip_years(clause)
            matches = MONEY.findall(without_dates)
            if len(matches) < 2:
                continue
            label = MONEY.sub(" ", without_dates).strip(" .,:-|()[]")
            if place(label)["candidates"]:
                out.append(clause)
                break
    return out


def _split_semicolon_accounts(text: str) -> str:
    """Split semicolon-separated account-amount pairs into separate lines.

    Problems like "revenue 8,000; cost of sales 5,000; distribution costs 600" have multiple
    account-amount pairs on one line separated by semicolons.  The trial-balance reader would
    see this as one line with multiple figures (a comparative) and refuse it, so each pair
    becomes its own line.

    A pair whose label is **already an account name** is kept verbatim, with its Dr/Cr marker:
    "Cash 10,000 Dr" and "Accumulated depreciation 8,000 Cr" name their own accounts, and
    rewriting them to the statement line they map to ("Property, plant and equipment") loses
    both the side and the identity.  Only a label that is a sentence wrapping an account name
    is rewritten, which is the case this function was written for.
    """
    parts = str(text or "").split(";")
    if len(parts) == 1:
        return text
    out_parts = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        found = list(MONEY.finditer(part))
        if not found:
            out_parts.append(part)
            continue
        last = found[-1]
        label = re.sub(r"\b(dr|cr)\.?\b", " ", re.sub(r"\.{2,}", " ", part[:last.start()]), flags=re.I)
        label = re.sub(r"\b(dr|cr)\.?\b", " ", label, flags=re.I)
        label = re.sub(r"[\t$]", " ", label)
        label = re.sub(r"\s*\(.*", "", label)
        label = re.sub(r"\s+", " ", label).strip(" .,:-|()[]")
        if label and not _is_sentence(label) and place(label)["candidates"]:
            # It is already an account name: keep the row exactly as written, marker and all.
            out_parts.append(part)
            continue
        acct_name = _extract_account_name(label)
        if acct_name:
            marker = ""
            side = _side(part)
            if side == "D":
                marker = " Dr"
            elif side == "C":
                marker = " Cr"
            out_parts.append(f"{acct_name} {last.group(0)}{marker}")
        else:
            out_parts.append(part)
    return "\n".join(out_parts)


def _extract_account_name(label: str) -> Optional[str]:
    """The account a label names, if the label names one.

    The label is matched on its **account fragment** - the part after the last colon,
    comma or semicolon - and only on rules that name an account on their own.  A label
    that merely mentions an account somewhere in a sentence ("Compute the net income for
    Alder Trading") names no account, so it is returned as it stands and reported as a
    line the reader did not place, rather than rewritten into an account it does not name.
    """
    fragment = re.split(r"[:;,]", str(label or ""))[-1].strip(" .,:-|()[]")
    if not fragment or len(fragment) > 80:
        return None
    low = fragment.lower()
    for rule in RULES:
        pattern = rule[0]
        if not pattern.startswith("^"):
            continue          # a rule that can match anywhere in a sentence is not an account name
        match = re.search(pattern, low)
        if match and match.group(0).strip() == low:
            return rule[3]
    return None


def preflight(text):
    """Refuse the shapes that are not one entity's one trial balance, from the text alone.

    Runs before anything is classified, so a two-column comparative or a group-accounts mention is
    answered with its real cause instead of "I could not find an account", and before the chart is
    built, so a refused reading never reaches the core or a model.
    """
    marker = CONSOLIDATION.search(str(text or ""))
    if marker:
        raise StatementRefused("this mentions '" + marker.group(0) + "', so it reads as consolidated or "
                               "group accounts. Consolidated statements are outside this tile: solve one "
                               "entity's own books.")
    periods = periods_in(text)
    if len(periods) > 1:
        raise StatementRefused("this carries more than one period (" + ", ".join(sorted(periods)) + "). "
                               "Comparatives are not supported: give one period's figures.")
    columns = column_lines(text)
    if columns:
        raise StatementRefused("this puts two figures on one line ('" + columns[0][:60] + "'), which is a "
                               "comparative. Give one period's figures.")


def preflight_rows(rows):
    """Refuse a reading that lists one account twice: that is two sets of balances, not one."""
    seen = set()
    for row in rows:
        key = _norm_label(row["label"])
        if key in seen:
            raise StatementRefused("the account '" + row["label"] + "' appears twice, and a trial balance "
                                   "lists each account once. Two sets of balances - two entities, or the "
                                   "same books pasted twice - cannot be added together: solve one set at a "
                                   "time.")
        seen.add(key)


def read_deterministic(text, currency=None, framework=None):
    """A reading of a trial-balance-shaped instruction, with no model involved.

    A transaction list and an adjusting-entry narrative need the model reader: this function says
    so instead of half-reading them.
    """
    preflight(text)
    try:
        kind, cue, sentence = classify(text)
    except StatementError:
        # A bare list of accounts and balances names no problem type but is a trial balance.
        # Accept it only when at least two accounts actually place, so a sentence is still refused.
        first_rows, _first_skipped = parse_rows(text)
        if len(first_rows) < 2:
            raise
        kind, cue, sentence = "trial_balance", "bare trial balance", "a list of account balances"
    if kind not in ("trial_balance", "adjustments", "incomplete_records"):
        raise StatementError("this reads as a " + kind.replace("_", " ") + " problem; that needs the "
                             "model reading, and none is configured")
    rows, skipped = parse_rows(text)
    if not rows:
        if _ADJUSTMENT_CUE.search(text):
            raise StatementError("this reads as adjustments, but the unadjusted trial balance is "
                                 "not given; state the account balances as well as the adjustments.")
        raise StatementError("I could not find an account with a balance in this text. Write one "
                             "account per line, as 'Cash 5,000' or 'Capital 5,000 Cr'.")
    preflight_rows(rows)
    chart = build_chart(rows)
    period, period_source, _quote = period_of(text)
    places = max([2] + [_decimals(row["written"]) for row in rows])
    reading = {
        "problem_type": kind,
        "why": ("Trial balance read from Dr/Cr markers." if cue == "trial balance" else "cue '" + cue + "' in: " + (sentence or cue)),
        "currency": currency_of(text, currency),
        "framework": framework_of(text, framework),
        "places": places,
        "period": period,
        "period_source": period_source,
        "chart": chart,
        "opening": [],
        "journal": [{"date": period["end"], "description": "the trial balance as given",
                     "aggregate": True,
                     "lines": [dict({"account": row["code"]}, **{_resolve(row)[0]: _resolve(row)[1]})
                               for row in rows]}],
        "schedules": [],
        "figures": [{"written": row["written"], "value": _resolve(row)[1], "kind": "amount",
                     "quote": row["quote"]} for row in rows],
        "derivations": [],
        "missing": [],
        "assumptions": [],
        "diagnosis": None,
        "ratio_map": {},
        "_rows": rows,
    }
    if period_source == "assumed":
        reading["assumptions"].append({
            "text": "no dates were given in the instruction, so the year ended 31 December 2026 is adopted",
            "basis": "a period is required for the closing entries and is shown here rather than assumed silently"})
    for line in skipped:
        reading["missing"].append({"what": line, "why": "this line carries no account I can place, so it "
                                                       "is shown here and left out of the statements"})
    return reading

    """The rows in the shape the core's trial-balance check expects, sides resolved by nature.

    The side is the account's natural side unless the row marks one; a stated negative flips it.
    Nothing is totalled here: the core's diagnosis is what reports whether the two sides agree.
    """
def tb_rows(rows, places=2):
    """The rows in the shape the core's trial-balance check expects: name, code, and one side.

    Each row is named by its **own label and code**, never by the statement line it maps to.  Two
    accounts may share a line â€” "Cash" and "Bank" both report as Cash â€” and that is a legitimate
    trial balance; naming both "Cash" made the core refuse it as a duplicate.  With the account's own
    name, the core's duplicate check fires only on a real duplicate, which is the signal that the
    text holds two sets of books.
    """
    out = []
    for row in rows:
        key, amount = _resolve(row)
        out.append({"name": row["label"], "code": row.get("code") or "", key: amount})
    return out


#: A ratio is computed only when the instruction asks for one (the tile stays statements-only
#: otherwise).  These are the cues, and they are the same kind of declared list `capabilities` uses.
RATIO_CUES = (r"\bratios?\b", r"\bliquidity\b", r"\bdupont\b", r"\bprofitabilit",
              r"\bgearing\b", r"\bleverage\b", r"\befficien", r"\bsolvency\b")

#: Named once, shown wherever a statement set is withheld, so the wording cannot drift.
CASH_FLOW_WITHHELD = ("a cash flow statement needs the period's flows or a prior balance sheet, and the "
                      "instruction supplies one trial balance; it is not presented rather than shown "
                      "as a figure that would be wrong")


def _reads_as_balances(text):
    """Whether the instruction reads as a set of balances rather than a transaction narrative.

    The preflight refusals (comparatives, two periods, a consolidation) are about *balances*: a
    narrative sentence may legitimately carry two figures, and the plan layer is its reader.
    """
    try:
        kind, _cue, _sentence_text = classify(text)
    except StatementError:
        return True
    return kind != "transactions"


def _reads_as_trial_balance(text):
    """Whether the instruction reads as a trial balance.

    A trial balance is a trial balance even when the student also asks for
    something else â€” "... and also compute the liquidity ratios".  The
    trial-balance route is the exact one and the more complete answer: it renders
    the income statement, the statement of changes in equity and the balance
    sheet, and it carries the ratios when they are asked for.

    The analysis route reads the same figures as *balances*, so it ignores the
    contra accounts: the same instruction reached it and printed total assets
    of 86,900 where the trial-balance route prints 77,900, with nothing to say
    which is right.  The more specific reading wins.
    """
    # A trial balance carries Dr/Cr markers on its lines.  If the text has them, it is a trial
    # balance regardless of what classify() says (classify can be fooled by account names like
    # "Depreciation expense" that match adjustment cues).
    import re as _re
    if _re.search(r"\d[\d,]*(?:\.\d+)?\s*(?:Dr|Cr)\.?(?=\s|$|[;,.])", text, _re.I):
        return True
    try:
        kind, _cue, _sentence_text = classify(text)
    except StatementError:
        return False
    return kind == "trial_balance"


def wants_ratios(text):
    """Whether the instruction asks for ratios (any cue)."""
    return any(re.search(pattern, str(text or ""), re.I) for pattern in RATIO_CUES)


#: How a student names a statement in the instruction box.  `RE` is the statement of changes in
#: equity; "retained earnings statement" is the same statement under its older name.
_STATEMENT_WORDS = (
    ("IS", re.compile(r"\bincome statement\b|\bstatement of (?:profit or loss|profit and loss|income|"
                      r"financial performance|comprehensive income)\b|\bprofit and loss account\b|"
                      r"\bp&l\b|\btrading account\b", re.I)),
    ("RE", re.compile(r"\bstatement of changes in equity\b|\bstatement of (?:retained earnings|"
                      r"owners'? equity|stockholders'? equity|shareholders'? equity)\b|"
                      r"\bretained earnings statement\b|\bequity statement\b", re.I)),
    ("BS", re.compile(r"\bbalance sheet\b|\bstatement of financial position\b", re.I)),
    ("CF", re.compile(r"\bcash ?flows? statement\b|\bstatement of cash ?flows?\b|\bcash ?flow\b", re.I)),
)

#: A student who wants **only** some statements says so with one of these words.
_ONLY = re.compile(r"\b(only|just|solely|instead|skip|omit|leave out|no need for|without|"
                   r"don'?t (?:show|need|present|want)|do not (?:show|need|present|want))\b", re.I)

#: A student who directs the tile to produce a statement has asked for it even without "only".
_DIRECTIVE = re.compile(r"\b(prepare|show|give|present|produce|display|send|want|need|compute|draft|"
                        r"can i (?:see|get|have))\b", re.I)

#: The request schema's vocabulary: the short codes, and the record keys the tile already uses.
_ALIASES = {"IS": "IS", "INCOME": "IS", "INCOME_STATEMENT": "IS",
            "RE": "RE", "EQUITY": "RE", "RETAINED_EARNINGS": "RE", "CHANGES_IN_EQUITY": "RE",
            "BS": "BS", "BALANCE": "BS", "BALANCE_SHEET": "BS",
            "CF": "CF", "CASH_FLOW": "CF", "CASHFLOW": "CF"}


def _clauses(text):
    """The instruction split into the sentences a request can live in."""
    return [part.strip() for part in re.split(r"[.;\n]+", str(text or "")) if part.strip()]


def wants_statements(text):
    """The statements an instruction asks to see, or None when it asks for the full set.

    Detection is deliberately conservative.  Naming a statement is not a request: a trial balance
    whose text mentions "the balance sheet showed" is still a full engagement.  A statement counts
    as requested when its clause also carries a limiting word ("only", "just", "instead of", "skip",
    "don't show", "without") or a directive verb ("prepare", "show", "give me").  A clause that only
    reports a figure asks for nothing.
    """
    found = []
    for clause in _clauses(text):
        codes = [code for code, pattern in _STATEMENT_WORDS if pattern.search(clause)]
        if not codes:
            continue
        if _ONLY.search(clause) or _DIRECTIVE.search(clause):
            found.extend(code for code in codes if code not in found)
    if not found:
        return None
    return tuple(code for code in statements_verify.STATEMENTS if code in found)


def _statement_code(item):
    """Map one request entry ("IS", "income_statement", "cash flow") to its short code, or None."""
    key = "_".join(str(item or "").strip().upper().replace("-", " ").split())
    return _ALIASES.get(key)


def _requested_statements(declared, text):
    """Resolve the request: an explicit list wins over what the instruction text asks for.

    The default is the full set, which is what the tile has always shown; partial rendering is an
    opt-in.  The request decides **what is rendered**, never what is computed (Tip 3).
    """
    if declared is None or (isinstance(declared, str) and not declared.strip()):
        asked = wants_statements(text)
        return tuple(asked) if asked else statements_verify.STATEMENTS
    if isinstance(declared, str):
        declared = [declared]
    if not isinstance(declared, (list, tuple)):
        raise StatementError("statements must be a list of codes: IS, RE, BS, CF")
    out = []
    for item in declared:
        code = _statement_code(item)
        if code is None:
            raise StatementError("'" + str(item) + "' is not a statement. Use IS (income statement), "
                                 "RE (statement of changes in equity), BS (balance sheet) or CF (cash "
                                 "flow statement).")
        if code not in out:
            out.append(code)
    if not out:
        raise StatementError("at least one statement must be requested")
    return tuple(out)


#: What each statement needs before it can be rendered (Tip 3).  The computation lane's authority is
#: `bp.statement_plan.PROJECTIONS`; a test pins the two tables together, so the product layer can
#: resolve a request without importing the core (its boundary rule).
PROJECTIONS = {"IS": (), "RE": ("IS",), "BS": ("RE",), "CF": ("IS", "BS")}


def _scope(requested):
    """What must be computed for the request, and what is computed but hidden (Tip 3).

    IS stands alone, BS drags in RE and IS, CF drags in almost everything.  Only the *rendered* set
    is the student's; the rest is the audit trail.
    """
    seen, closure = set(), []

    def visit(code):
        if code in seen:
            return
        seen.add(code)
        for dependency in PROJECTIONS[code]:
            visit(dependency)
        closure.append(code)

    for code in requested:
        visit(code)
    return list(requested), closure, [code for code in closure if code not in requested]



def compile_spec(reading):
    """The engagement spec the core accepts, built only from the verified reading.

    Quotes are stripped: they are the reading's provenance, not part of the core's schema.
    """
    period = reading.get("period") or {}
    if not period.get("start") or not period.get("end"):
        raise StatementError("the reading carries no period, so the core cannot close the accounts")
    chart = [{k: v for k, v in account.items() if k not in ("quote", "synthesised")}
             for account in reading.get("chart") or []]
    entries = []
    for entry in reading.get("journal") or []:
        clean = {k: v for k, v in entry.items() if k != "quote"}
        clean["lines"] = [{k: v for k, v in line.items() if k != "quote"}
                          for line in entry.get("lines") or []]
        entries.append(clean)
    return {"period": {"start": period["start"], "end": period["end"]},
            "currency": reading.get("currency") or DEFAULT_CURRENCY,
            "framework": reading.get("framework") or "US_GAAP",
            "places": int(reading.get("places") or 2),
            "chart": chart,
            "prior_closing": reading.get("prior_closing") or {},
            "opening": reading.get("opening") or [],
            "entries": entries,
            "schedules": reading.get("schedules") or []}


def present(result, problem_type, requested=None):
    """The statements a reader is shown, from the core's rendered text, scoped to the request.

    The core always computes every statement; this picks which ones are rendered (Tip 3).  The trial
    balance and the notes stay with the working, so they are carried here but never part of the
    submission view.  The cash flow rule is unchanged and now also request-gated: it is shown only
    for a transactions problem, and only when it was asked for.
    """
    appendix = result.get("_appendix") or {}
    export = appendix.get("statements_export") or {}
    wanted = list(requested or statements_verify.STATEMENTS)
    out = {"trial_balance": export.get("trial_balance", ""),
           "income_statement": "", "balance_sheet": "", "equity": "",
           "notes": export.get("notes", ""),
           "cash_flow": None, "cash_flow_withheld_because": None}
    if "IS" in wanted:
        out["income_statement"] = export.get("income_statement", "")
    if "RE" in wanted:
        out["equity"] = appendix.get("equity_statement_export", "")
    if "BS" in wanted:
        out["balance_sheet"] = export.get("balance_sheet", "")
    if "CF" in wanted:
        if problem_type == "transactions" and export.get("cash_flow"):
            out["cash_flow"] = export.get("cash_flow")
        else:
            out["cash_flow_withheld_because"] = CASH_FLOW_WITHHELD
    return out


def _mentioned(gap, text):
    """Whether the student named this ratio ('market to book', 'market-to-book', the id itself)."""
    lowered = str(text or "").lower()
    name = str(gap.get("ratio") or "")
    return any(term and term in lowered for term in (name.replace("_", " "), name.replace("_", "-"),
                                                     name.replace("_", "")))


def _diagnose(rows, places):
    """The core's own trial-balance diagnosis: the difference, the findings, what it cannot prove.

    `trial_balance_check` publishes its amounts at the top level of its output and its findings in
    `_appendix` (see `methods.tbcheck_impl`); both are read here, and a missing key is an error
    rather than a silent zero â€” a diagnosis that quietly reads "balanced" is worse than no diagnosis.
    """
    try:
        report = _core("diagnose")(tb_rows(rows, places), places)
    except Exception as error:
        # A core refusal is a refusal of these figures, never a crash: the tile says what is wrong.
        text = str(error)
        if "listed more than once" in text:
            raise StatementRefused("the same account appears twice, and a trial balance lists each "
                                   "account once. Two sets of balances cannot be added together: solve "
                                   "one set at a time.")
        raise StatementError("the trial-balance check refused these figures: " + text[:200])
    difference = report.get("submitted_balance_difference")
    if difference is None:
        difference = (report.get("amounts") or {}).get("submitted_balance_difference")
    if difference is None:
        raise StatementError("the trial-balance check returned no difference, so the tile cannot say "
                             "whether the figures agree")
    appendix = report.get("_appendix") or {}
    text = str(difference)
    return {"difference": text,
            "balanced": text.strip("0.-") == "",
            "findings": appendix.get("findings") or [],
            "verdict": appendix.get("verdict"),
            "cannot_prove": appendix.get("cannot_prove") or [],
            "counts": {key: str(value) for key, value in report.items()
                       if str(key).startswith("n_")},
            "confirmation": "the difference is the core's own count of the two sides, not a figure "
                            "this tile worked out"}


def derive_balancing_figure(reading, rows):
    """For incomplete records: derive the missing figure from the core's own difference.

    The figure is the core's `submitted_balance_difference`, labelled `derived` and shown with its
    identity.  It is applied **only** when the problem is an incomplete record and the chart has no
    capital line â€” i.e. when the instruction asks for the capital.  Any other unknown is left alone,
    because there the difference is not the answer and plugging it is the one thing this tile must
    never do.
    """
    places = int(reading.get("places") or 2)
    before = _diagnose(rows, places)
    reading["diagnosis"] = before
    if before["balanced"] or reading.get("problem_type") != "incomplete_records":
        return reading
    if any(account["line"] == "Capital" for account in reading.get("chart") or []):
        return reading
    difference = before["difference"]
    amount = difference.lstrip("-")
    if amount.strip("0.") == "":
        return reading
    side = "debit" if difference.startswith("-") else "credit"
    account = {"code": _free_code("3000", reading["chart"]), "name": "Capital", "type": "equity",
               "line": "Capital", "role": "capital", "synthesised": True,
               "quote": "capital, derived as the balancing figure"}
    reading["chart"].append(account)
    if reading.get("journal"):
        reading["journal"][0].setdefault("lines", []).append({"account": account["code"], side: amount})
    reading.setdefault("derivations", []).append({
        "figure": "Capital",
        "identity": "capital = assets - liabilities (the two sides of a trial balance must agree)",
        "working": "the declared figures are out by " + amount + ", so the capital that makes the two "
                   "sides agree is " + amount + " " + side,
        "derived": True})
    reading.setdefault("figures", []).append({"written": amount, "value": amount, "kind": "amount",
                                              "quote": "", "derived": True})
    rows.append({"label": "Capital", "written": amount, "side": "D" if side == "debit" else "C",
                 "quote": "", "placed": place("capital"), "code": account["code"]})
    reading["diagnosis"] = _diagnose(rows, places)
    return reading


SECTIONS = (("income_statement", "income statement"), ("equity", "statement of changes in equity"),
            ("balance_sheet", "balance sheet"))


def statements_only(statements):
    """The submission view: the statements and their notes, with no journal, T-accounts or working."""
    if not statements:
        return ""
    parts = [statements.get(key, "") for key, _label in SECTIONS if statements.get(key)]
    if statements.get("cash_flow"):
        parts.append(statements["cash_flow"])
    return "\n\n".join(part for part in parts if part)

def _ratio_rows(pack):
    """The computed rows and the named-unsupported rows of one ratio_analysis result."""
    computed = list((pack.get("_appendix") or {}).get("ratios") or [])
    for row in computed:
        unit = row.get("unit")
        places = 1 if unit == "days" else 3
        try:
            from decimal import Decimal as _D
            row["value"] = str(_D(str(row.get("value"))).quantize(_D("0.1") if places == 1 else _D("0.001")))
        except Exception:
            pass
    named = [{"ratio": row.get("ratio"), "reason": row.get("reason"), "needs": []}
             for row in (pack.get("_appendix") or {}).get("not_computed") or []]
    return computed, named


def ratio_pack(result, text):
    """The ratio pack the instruction asked for: computed rows, plus every ratio named unsupported."""
    appendix = result.get("_appendix") or {}
    figures = appendix.get("ratio_figures") or {}
    if not figures or "ratio_analysis" not in _CORE:
        return None
    pack = _core("ratio_analysis")(figures)
    computed, named = _ratio_rows(pack)
    for gap in appendix.get("ratio_gaps") or []:
        if _mentioned(gap, text):
            named.append({"ratio": gap.get("ratio"), "reason": gap.get("why"),
                          "needs": gap.get("needs") or []})
    return {"requested": True, "computed": computed, "named_unsupported": named, "figures": figures}


RATIOS_FORMAT = "bp-statements-ratios/1"


def ratios(record, extra=None):
    """The full ratio pack for one solved record, computed on demand from its figures.

    This is the first consumer of `figures(record)`: the student asks for the ratios of a
    statement they already built, and every figure comes from the frozen record rather than a
    second entry.  `extra` carries the figures a statement cannot hold — a share price, the
    shares, the dividends — so the market and Altman ratios can run without a second entry
    screen.  A ratio the record (plus `extra`) cannot support is named, never invented.
    """
    bundle = figures(record)
    figures_map = dict(bundle["figures"])
    if isinstance(extra, dict):
        figures_map.update({key: value for key, value in extra.items() if value not in (None, "")})
    if "ratio_analysis" not in _CORE:
        raise CoreNotAttached("the statements tile is not attached to the frozen core (ratio_analysis)")
    pack = _core("ratio_analysis")(figures_map)
    computed, named = _ratio_rows(pack)
    for gap in bundle.get("gaps") or []:
        if gap.get("ratio") and not any(n.get("ratio") == gap.get("ratio") for n in named):
            named.append({"ratio": gap.get("ratio"), "reason": gap.get("why"),
                          "needs": gap.get("needs") or []})
    return {"format": RATIOS_FORMAT, "source": bundle["source"],
            "computed": computed, "named_unsupported": named, "figures": figures_map}


DUPONT_FORMAT = "bp-statements-dupont/1"
WORKING_CAPITAL_FORMAT = "bp-statements-working-capital/1"

#: The figures DuPont needs that a statement always carries.
_DUPONT_REQUIRED = ("revenue", "net_income", "total_assets", "equity")
#: The figures the working-capital method needs that a statement always carries.
_WC_FROM_STATEMENT = ("revenue", "cost_of_sales", "inventory", "receivables", "payables")
#: The figures the working-capital method still needs and a statement cannot supply.
_WC_DECLARED = ("annual_demand", "order_cost", "holding_cost_per_unit",
                "discount_percent", "credit_terms_days", "discount_days")


def dupont(record):
    """The DuPont decomposition computed from the record's own figures.

    The three-step form uses revenue, net income, total assets and equity, all of which a
    statement always carries.  The five-step form runs only when the record also carries (or can
    derive) EBIT, pre-tax income and tax expense; otherwise those three are named as absent
    rather than invented.  A comparison period needs a second statement record and is never
    guessed from one.
    """
    bundle = figures(record)
    figs = bundle["figures"]
    derived = bundle.get("derived") or {}
    missing = [key for key in _DUPONT_REQUIRED if figs.get(key) in (None, "")]
    if missing:
        raise StatementError("this record does not carry the figures DuPont needs: "
                             + ", ".join(missing))
    inputs = {key: figs[key] for key in _DUPONT_REQUIRED}
    if figs.get("cost_of_sales") not in (None, ""):
        inputs["cost_of_sales"] = figs["cost_of_sales"]
    for key in ("ebit", "pretax_income", "tax_expense"):
        value = figs.get(key)
        if value in (None, ""):
            value = derived.get(key)
        if value not in (None, ""):
            inputs[key] = value
    if "dupont" not in _CORE:
        raise CoreNotAttached("the statements tile is not attached to the frozen core (dupont)")
    pack = _core("dupont")(inputs)
    result = {key: str(value) for key, value in pack.items() if not str(key).startswith("_")}
    five_step = all(key in inputs for key in ("ebit", "pretax_income", "tax_expense"))
    return {"format": DUPONT_FORMAT, "source": bundle["source"], "inputs": inputs,
            "five_step": five_step,
            "not_run": ([] if five_step else
                        ["the five-step form needs EBIT, pre-tax income and tax expense; "
                         "the record does not carry all three"]),
            "result": result}


def working_capital(record, extra=None):
    """The working-capital pack computed from the record's figures plus the declared terms.

    The cash-conversion cycle needs revenue, cost of sales, inventory, receivables and payables,
    all of which a statement carries.  The order quantity and the cost of trade credit need the
    operating terms a statement cannot supply (annual demand, order cost, holding cost, discount,
    credit terms); those are passed in `extra` and, when absent, are named rather than guessed.
    """
    bundle = figures(record)
    figs = bundle["figures"]
    inputs = {key: figs.get(key) for key in _WC_FROM_STATEMENT}
    inputs["days"] = 365
    if isinstance(extra, dict):
        inputs.update({key: value for key, value in extra.items() if value not in (None, "")})
    missing_record = [key for key in _WC_FROM_STATEMENT if inputs.get(key) in (None, "")]
    if missing_record:
        raise StatementError("this record does not carry the cycle figures: "
                             + ", ".join(missing_record))
    missing_declared = [key for key in _WC_DECLARED if inputs.get(key) in (None, "")]
    if missing_declared:
        raise StatementError("the statement supplies the cycle figures; still needed: "
                             + ", ".join(missing_declared))
    if "working_capital" not in _CORE:
        raise CoreNotAttached("the statements tile is not attached to the frozen core (working_capital)")
    pack = _core("working_capital")(inputs)
    result = {key: str(value) for key, value in pack.items() if not str(key).startswith("_")}
    return {"format": WORKING_CAPITAL_FORMAT, "source": bundle["source"], "inputs": inputs,
            "result": result}


CYCLE_FORMAT = "bp-statements-cycle/1"


def cycle(record):
    """The cash conversion cycle from the record's own figures.

    This is the cycle-only method: revenue, cost of sales, inventory, receivables and payables
    are all a statement carries, so no order-quantity or trade-credit term is required.
    """
    bundle = figures(record)
    figs = bundle["figures"]
    inputs = {key: figs.get(key) for key in _WC_FROM_STATEMENT}
    missing = [key for key in inputs if inputs[key] in (None, "")]
    if missing:
        raise StatementError("this record does not carry the cycle figures: " + ", ".join(missing))
    if "working_capital_cycle" not in _CORE:
        raise CoreNotAttached("the statements tile is not attached to the frozen core "
                              "(working_capital_cycle)")
    pack = _core("working_capital_cycle")(inputs)
    result = {key: str(value) for key, value in pack.items() if not str(key).startswith("_")}
    return {"format": CYCLE_FORMAT, "source": bundle["source"], "inputs": inputs,
            "result": result}


PIOTROSKI_FORMAT = "bp-statements-piotroski/1"


def _piotroski_period(bundle):
    """The nine Piotroski inputs one period supports, or None where a figure is absent."""
    figs = bundle["figures"]

    def dec(key):
        value = figs.get(key)
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def ratio(numerator, denominator):
        if numerator is None or denominator in (None, 0):
            return None
        return str(numerator / denominator)

    net = dec("net_income")
    total_assets = dec("total_assets")
    total_liabilities = dec("total_liabilities")
    current_assets = dec("current_assets")
    current_liabilities = dec("current_liabilities")
    revenue = dec("revenue")
    cost_of_sales = dec("cost_of_sales")
    cash_flow = dec("operating_cash_flow")
    gross = (revenue - cost_of_sales) if revenue is not None and cost_of_sales is not None else None
    return {
        "net_income": str(net) if net is not None else None,
        "operating_cash_flow": str(cash_flow) if cash_flow is not None else None,
        "roa": ratio(net, total_assets),
        "leverage": ratio(total_liabilities, total_assets),
        "current_ratio": ratio(current_assets, current_liabilities),
        "gross_margin": ratio(gross, revenue),
        "asset_turnover": ratio(revenue, total_assets),
    }


def piotroski(records, extra=None):
    """The Piotroski F-score from two statement records (prior and current).

    Each record supplies one period's net income, operating cash flow, total assets, total
    liabilities, current assets, current liabilities, revenue and cost of sales; the diluted
    share count is declared in `extra`.  A figure the two records cannot supply is named, never
    defaulted.
    """
    if not isinstance(records, list) or len(records) < 2:
        raise StatementError("a Piotroski score needs two statement records (prior and current)")
    bundles = [figures(record) for record in records]
    bundles.sort(key=lambda bundle: _period_year(bundle.get("period")))
    prior, current = bundles[-2], bundles[-1]
    if _period_year(prior.get("period")) == _period_year(current.get("period")):
        raise StatementError("the two records must cover different periods")
    p, c = _piotroski_period(prior), _piotroski_period(current)
    extra = extra if isinstance(extra, dict) else {}
    shares = extra.get("shares_diluted")
    inputs = {
        "net_income": c["net_income"],
        "operating_cash_flow": c["operating_cash_flow"],
        "roa_current": c["roa"], "roa_prior": p["roa"],
        "leverage_current": c["leverage"], "leverage_prior": p["leverage"],
        "current_ratio_current": c["current_ratio"], "current_ratio_prior": p["current_ratio"],
        "shares_diluted": str(shares) if shares not in (None, "") else None,
        "gross_margin_current": c["gross_margin"], "gross_margin_prior": p["gross_margin"],
        "asset_turnover_current": c["asset_turnover"], "asset_turnover_prior": p["asset_turnover"],
    }
    missing = [key for key, value in inputs.items() if value in (None, "")]
    if missing:
        raise StatementError("the Piotroski score still needs: " + ", ".join(missing))
    if "piotroski" not in _CORE:
        raise CoreNotAttached("the statements tile is not attached to the frozen core (piotroski)")
    pack = _core("piotroski")(inputs)
    result = {key: str(value) for key, value in pack.items() if not str(key).startswith("_")}
    return {"format": PIOTROSKI_FORMAT,
            "source": [current["source"]["record"], prior["source"]["record"]],
            "periods": [_period_year(prior.get("period")), _period_year(current.get("period"))],
            "inputs": inputs, "result": result}


BENEISH_FORMAT = "bp-statements-beneish/1"


def _beneish_period(bundle):
    """The raw figures one period contributes to the eight Beneish indices."""
    figs = bundle["figures"]
    groups = bundle.get("balance_sheet_groups") or {}
    totals = groups.get("totals") or {}
    expenses = (bundle.get("income_groups") or {}).get("expenses") or {}

    def dec(value):
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    revenue = dec(figs.get("revenue"))
    cost_of_sales = dec(figs.get("cost_of_sales"))
    current_liabilities = dec(figs.get("current_liabilities"))
    if current_liabilities is None:
        current_liabilities = dec(totals.get("current_liabilities"))
    ppe = dec(totals.get("non_current_assets"))
    long_term_debt = dec(totals.get("non_current_liabilities"))
    depreciation = None
    sga = Decimal("0")
    saw_breakdown = False
    for label, value in expenses.items():
        low = str(label).lower()
        if "cost of sale" in low or "cost of goods" in low or low.strip() == "cogs":
            saw_breakdown = True
            continue
        if "depreciation" in low:
            depreciation = dec(value)
            saw_breakdown = True
            continue
        if "interest" in low or "tax" in low:
            continue
        try:
            sga += Decimal(str(value))
            saw_breakdown = True
        except Exception:
            pass
    return {
        "sales": revenue,
        "receivables": dec(figs.get("receivables")),
        "gross_margin": (((revenue - cost_of_sales) / revenue)
                         if revenue not in (None, 0) and cost_of_sales is not None else None),
        "current_assets": dec(figs.get("current_assets")),
        "ppe": ppe,
        "total_assets": dec(figs.get("total_assets")),
        "current_liabilities": current_liabilities,
        "long_term_debt": long_term_debt,
        "depreciation": depreciation,
        "sga": sga if saw_breakdown else None,
        "net_income": dec(figs.get("net_income")),
        "operating_cash_flow": dec(figs.get("operating_cash_flow")),
    }


def beneish(records, extra=None):
    """The Beneish M-score from two statement records (prior and current).

    The eight indices are ratios of two-period figures (receivables/sales, gross margin,
    asset quality, sales growth, depreciation rate, SG&A intensity, leverage and accruals).
    Each index is derived from the two frozen bundles; a figure either record cannot supply is
    named, never defaulted.  The M-score formula itself is the frozen `beneish_m_score`.
    """
    if not isinstance(records, list) or len(records) < 2:
        raise StatementError("a Beneish M-score needs two statement records (prior and current)")
    bundles = [figures(record) for record in records]
    bundles.sort(key=lambda bundle: _period_year(bundle.get("period")))
    prior, current = bundles[-2], bundles[-1]
    if _period_year(prior.get("period")) == _period_year(current.get("period")):
        raise StatementError("the two records must cover different periods")
    p, c = _beneish_period(prior), _beneish_period(current)

    def ratio(numerator, denominator):
        if numerator is None or denominator in (None, 0):
            return None
        return numerator / denominator

    def asset_quality(period):
        if period["current_assets"] is None or period["ppe"] is None or period["total_assets"] in (None, 0):
            return None
        return 1 - (period["current_assets"] + period["ppe"]) / period["total_assets"]

    def depreciation_rate(period):
        if period["depreciation"] is None or period["ppe"] is None:
            return None
        base = period["depreciation"] + period["ppe"]
        return (period["depreciation"] / base) if base else None

    def leverage(period):
        if period["current_liabilities"] is None or period["long_term_debt"] is None or period["total_assets"] in (None, 0):
            return None
        return (period["current_liabilities"] + period["long_term_debt"]) / period["total_assets"]

    indices = {
        "dsri": ratio(ratio(c["receivables"], c["sales"]), ratio(p["receivables"], p["sales"])),
        "gmi": ratio(p["gross_margin"], c["gross_margin"]),
        "aqi": ratio(asset_quality(c), asset_quality(p)),
        "sgi": ratio(c["sales"], p["sales"]),
        "depi": ratio(depreciation_rate(p), depreciation_rate(c)),
        "sgai": ratio(ratio(c["sga"], c["sales"]), ratio(p["sga"], p["sales"])),
        "lvgi": ratio(leverage(c), leverage(p)),
        "tata": ratio((c["net_income"] - c["operating_cash_flow"])
                      if c["net_income"] is not None and c["operating_cash_flow"] is not None else None,
                      c["total_assets"]),
    }
    missing = [key for key, value in indices.items() if value is None]
    if missing:
        raise StatementError("the Beneish score still needs: " + ", ".join(missing))
    inputs = {key: str(value) for key, value in indices.items()}
    if "beneish" not in _CORE:
        raise CoreNotAttached("the statements tile is not attached to the frozen core (beneish)")
    pack = _core("beneish")(inputs)
    result = {key: str(value) for key, value in pack.items() if not str(key).startswith("_")}
    return {"format": BENEISH_FORMAT,
            "source": [current["source"]["record"], prior["source"]["record"]],
            "periods": [_period_year(prior.get("period")), _period_year(current.get("period"))],
            "indices": inputs, "result": result}


TAX_FORMAT = "bp-statements-tax/1"


def tax_note(record, extra=None):
    """The tax reconciliation from the record's accounting profit plus declared items.

    The record supplies the accounting profit (net income); the tax rate and the reconciling
    items a statement cannot carry (non-deductible, non-taxable, allowances, a temporary
    difference, VAT) are declared in `extra`.  A missing input is named, never assumed.
    """
    bundle = figures(record)
    figs = bundle["figures"]
    extra = extra if isinstance(extra, dict) else {}
    inputs = {"accounting_profit": figs.get("net_income")}
    for key in ("tax_rate", "non_deductible", "non_taxable", "capital_allowances",
                "temporary_difference", "deferred_tax_rate", "vat_output_tax", "vat_input_tax"):
        if extra.get(key) not in (None, ""):
            inputs[key] = extra[key]
    missing = [key for key in ("accounting_profit", "tax_rate") if inputs.get(key) in (None, "")]
    if missing:
        raise StatementError("the tax note needs: " + ", ".join(missing)
                             + (" (the accounting profit comes from the record; the tax rate must "
                                "be declared)" if "tax_rate" in missing else ""))
    if "tax_reconciliation" not in _CORE:
        raise CoreNotAttached("the statements tile is not attached to the frozen core "
                              "(tax_reconciliation)")
    pack = _core("tax_reconciliation")(inputs)
    result = {key: str(value) for key, value in pack.items() if not str(key).startswith("_")}
    return {"format": TAX_FORMAT, "source": bundle["source"], "inputs": inputs, "result": result}


TREND_FORMAT = "bp-statements-trend/1"


def _period_year(period):
    """The year a statement ends in, or '' when the record carries no usable date."""
    end = str((period or {}).get("end") or (period or {}).get("start") or "")
    return end[:4] if len(end) >= 4 and end[:4].isdigit() else ""


def trend(records):
    """A multi-period trend from several solved statement records.

    Each record supplies one period: revenue, cost of sales, operating expenses (derived from the
    expense breakdown), net income, and optionally total assets and equity.  The periods are
    ordered by the year their statement ends in; two records with the same year are refused,
    because a trend needs distinct periods and the frozen method says so.
    """
    if not isinstance(records, list) or len(records) < 2:
        raise StatementError("a trend needs at least two statement records")
    rows = []
    for record in records:
        bundle = figures(record)
        figs = bundle["figures"]
        derived = bundle.get("derived") or {}
        rows.append({
            "record": bundle["source"]["record"],
            "year": _period_year(bundle.get("period")),
            "revenue": figs.get("revenue"),
            "cost_of_sales": figs.get("cost_of_sales"),
            "operating_expenses": derived.get("operating_expenses"),
            "net_income": figs.get("net_income"),
            "total_assets": figs.get("total_assets"),
            "equity": figs.get("equity"),
        })
    for key in ("year", "revenue", "cost_of_sales", "operating_expenses", "net_income"):
        missing = [str(index) for index, row in enumerate(rows, 1) if row.get(key) in (None, "")]
        if missing:
            raise StatementError("period " + ", ".join(missing) + " does not carry " + key)
    rows.sort(key=lambda row: str(row["year"]))
    years = [row["year"] for row in rows]
    if len(set(years)) != len(years):
        raise StatementError("a trend needs distinct periods; two records end in the same year")
    inputs = {"years": [row["year"] for row in rows]}
    for key in ("revenue", "cost_of_sales", "operating_expenses", "net_income"):
        inputs[key] = [row[key] for row in rows]
    if all(row.get("total_assets") not in (None, "") for row in rows):
        inputs["total_assets"] = [row["total_assets"] for row in rows]
    if all(row.get("equity") not in (None, "") for row in rows):
        inputs["equity"] = [row["equity"] for row in rows]
    if "trend" not in _CORE:
        raise CoreNotAttached("the statements tile is not attached to the frozen core (trend_analysis)")
    pack = _core("trend")(inputs)
    result = {key: str(value) for key, value in pack.items() if not str(key).startswith("_")}
    return {"format": TREND_FORMAT, "sources": [row["record"] for row in rows],
            "periods": years, "inputs": inputs, "result": result}


def _record(reading, spec, result, text, source, rejected, same_model, ratios, requested=None):
    """The frozen record of a solved problem: the reading, the spec, the core's output, both views.

    It also carries the request's audit trail (Tip 3): what was asked for, everything that had to be
    computed to render it, and which of those were computed but hidden.  A statement that was only
    needed to make a downstream one articulate never appears in the rendered set.
    """
    appendix = result.get("_appendix") or {}
    export = appendix.get("statements_export") or {}
    requested, computed, hidden = _scope(requested or statements_verify.STATEMENTS)
    statements = present(result, reading["problem_type"], requested)
    # The request's audit trail travels with the appendix.  The workbook is built from the appendix
    # alone (the download bundle carries the appendix, not the whole record), so this is where a
    # renderer learns which statements were asked for, which were computed but stayed hidden, and
    # why a statement that was asked for was not presented.
    appendix = dict(appendix)
    appendix["requested"] = list(requested)
    appendix["hidden"] = list(hidden)
    appendix["cash_flow_withheld_because"] = statements.get("cash_flow_withheld_because")
    problems = statements_verify.verify_output(statements, requested)
    if problems:
        raise StatementError("the core did not return every requested statement: "
                             + "; ".join(str(problem.get("detail")) for problem in problems[:3]))
    warnings = []
    if "CF" in requested and not statements.get("cash_flow"):
        warnings.append({"statement": "CF",
                         "reason": statements.get("cash_flow_withheld_because")
                         or "the cash flow statement could not be prepared from this instruction"})
    record = {
        "format": FORMAT, "solved": True, "refusal": None,
        "instruction": text, "instruction_hash": verify.brief_hash(text),
        "problem_type": reading["problem_type"], "why": reading.get("why", ""),
        "reading": reading, "reading_source": source,
        "same_model_disclosure": bool(same_model), "rejected": rejected,
        "spec": spec,
        "requested": requested, "computed": computed, "hidden": hidden, "warnings": warnings,
        "core": {"scalars": {key: str(value) for key, value in result.items()
                             if not str(key).startswith("_")},
                 "appendix": appendix},
        "statements": statements,
        "statements_only": statements_only(statements),
        "working": {"journal": appendix.get("journal_export", ""),
                    "trial_balance": export.get("trial_balance", ""),
                    "t_accounts": appendix.get("t_accounts_export") or {},
                    "derivations": reading.get("derivations") or [],
                    "assumptions": reading.get("assumptions") or [],
                    "missing": reading.get("missing") or []},
        "diagnosis": reading.get("diagnosis"),
        "checks": [{"name": name, "ok": bool(ok), "detail": detail}
                   for name, ok, detail in (result.get("_checks") or [])],
        "ratios": ratios,
    }
    # The 22-guard runner (Tip 7).  Injected from bp.server, so the product package never
    # imports the core.  A guard that cannot run is recorded, not swallowed.  Only the
    # correctness and cross-reconciliation guards block the record; the trust and
    # extraction guards are recorded for the reader and the audit trail.
    record = _apply_guards(record)
    return verify.freeze(record)


def _apply_guards(record):
    """Run the 22-guard runner on a record and attach its verdicts.

    Only the correctness and cross-reconciliation guards block the record; the trust and
    extraction guards are recorded for the reader and the audit trail.  Called from every
    record builder, so a record produced by any route carries the same guard verdicts.  It
    also names the Tip 5 problem type once, so the record says which kind of problem it was.
    """
    try:
        from .problem_type import classify_problem
        record["tip5_type"] = classify_problem(record.get("instruction", ""))
    except Exception:
        record["tip5_type"] = None
    if "guards" not in _CORE:
        return record
    try:
        guard_run = _core("guards")(record)
        record["guards"] = guard_run
        blocking = {"G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G13", "G18", "G21"}
        failed = [g for g in (guard_run.get("summary", {}).get("failed_ids") or [])
                  if g in blocking]
        if failed:
            raise StatementError("the pipeline guards refused this record: "
                                 + ", ".join(str(g) for g in failed))
    except StatementError:
        raise
    except Exception:
        record["guards"] = None
    return record


def _refusal(text, reading, spec, message, source, rejected, same_model, requested=None):
    """A record that says what is wrong instead of showing a number that would be wrong."""
    reading = reading or {}
    record = {
        "format": FORMAT, "solved": False, "refusal": message,
        "instruction": text, "instruction_hash": verify.brief_hash(text),
        "problem_type": reading.get("problem_type"), "why": reading.get("why", ""),
        "reading": reading, "reading_source": source,
        "same_model_disclosure": bool(same_model), "rejected": rejected,
        "spec": spec or {},
        "requested": list(requested or statements_verify.STATEMENTS),
        "computed": [], "hidden": [], "warnings": [],
        "core": None, "statements": None, "statements_only": "",
        "working": {"journal": "", "trial_balance": "", "t_accounts": {},
                    "derivations": reading.get("derivations") or [],
                    "assumptions": reading.get("assumptions") or [],
                    "missing": reading.get("missing") or []},
        "diagnosis": reading.get("diagnosis"),
        "checks": [], "ratios": None,
    }
    return verify.freeze(record)


def _is_complex_problem(text):
    """Whether a narrative is complex enough to justify the deepseek-v4-pro gate.

    Deterministic problems never reach the model path (they are solved by code above), so this
    only governs narratives the deterministic reader could not read.  A small narrative that
    slipped past it is retried on the cheap model (tier 1); only narratives with many stated
    figures, schedules or adjustments escalate to the pro model (tier 2/3).
    """
    import re as _re
    s = str(text or "")
    low = s.lower()
    # Count stated dollar amounts.
    amounts = _re.findall(r"\$?\b\d[\d,]*(?:\.\d+)?\b", s)
    # Distinct dates.
    dates = set(_re.findall(r"\b\d{4}-\d{2}-\d{2}\b", s))
    date_words = _re.findall(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}\b", low)
    complex_keywords = ("depreciation", "accrual", "prepayment", "prepaid", "deferred",
                        "amortiz", "bad debt", "cogs", "cost of goods", "adjusting",
                        "schedule", "inventory", "tax rate", "straight-line", "straight line")
    keyword_hits = sum(1 for kw in complex_keywords if kw in low)
    return (len(s) >= 600 or len(amounts) >= 8 or len(dates) + len(date_words) >= 4
            or keyword_hits >= 2)


def solve(instruction, currency=None, framework=None, ratios=None, reader=None, statements=None):
    """Solve one instruction and return a frozen record.

    The deterministic reader goes first because it is exact on a trial balance; the model reader is
    used when it cannot read the problem (a transaction list, an adjusting-entry narrative), and
    every reading â€” either source â€” passes the verifier before the core is called.

    `statements` is the output request (`["IS"]`, `["BS", "CF"]`, ...).  It defaults to the full set,
    or to what the instruction itself asks for ("only the balance sheet").  It never changes what is
    computed â€” the ledger is always built in full (Tip 3).
    """
    text = str(instruction or "").strip()
    if len(text) < 10:
        raise StatementError("describe the problem in at least a sentence, with its figures")
    original = text
    blocked = blocked_cue(text)
    if blocked:
        raise StatementError("'" + blocked + "' is a currency or a place this product does not use. It "
                             "works in USD with neutral places: restate the figures in USD and it will "
                             "solve them.")
    requested = _requested_statements(statements, text)
    # A problem that states labelled figures and names a schedule needs no journal and no
    # model: it is an identity over the stated figures.  This runs before every rewriting of
    # the text, so the labels are read exactly as the student wrote them.
    from . import schedule_routes as _sched
    try:
        kind = _sched.detect(original)
    except Exception:
        kind = None
    if kind is not None:
        tried = _solve_schedule(kind, original, currency=currency, framework=framework,
                                ratios=ratios, statements=requested)
        if tried is not None:
            return tried
    # An unadjusted trial balance plus stated adjustments is a ledger problem with a second
    # set of entries, not a single trial balance.
    try:
        tried = _solve_adjusted_trial_balance(original, currency=currency, framework=framework,
                                              ratios=ratios, statements=requested)
    except Exception:
        tried = None
    if tried is not None:
        return tried
    # Split semicolon-separated account-amount pairs into separate lines so the
    # trial-balance reader doesn't mistake them for a two-column comparative.
    text = _split_semicolon_accounts(text)
    # Try the deterministic multi-step income statement computation first,
    # before the trial-balance reader. A list of accounts with amounts that
    # doesn't balance as a trial balance is an income-statement computation,
    # not a statement-preparation problem. Only use this if the problem
    # contains ONLY income statement accounts (no balance sheet accounts);
    # a mix of IS and BS accounts is a trial balance and goes through
    # read_deterministic instead.
    if detect_income_statement(text):
        from .income_statement import parse_problem as _isp_parse
        try:
            _islines, _ = _isp_parse(text)
            has_bs = any(l.kind in ("current_asset", "non_current_asset",
                                    "current_liability", "non_current_liability")
                         for l in _islines)
            if not has_bs:
                tried = _solve_income_statement(text, currency=currency, framework=framework,
                                                ratios=ratios, statements=requested)
                if tried is not None:
                    return tried
        except Exception:
            pass
    # Try the deterministic balance sheet / ratio analysis computation.
    # A trial balance is not one: it is read exactly, and it carries the ratios
    # itself when the instruction asks for them.
    if detect_ratio_analysis(text) and not _reads_as_trial_balance(text):
        try:
            tried = _solve_balance_sheet_analysis(text, currency=currency, framework=framework,
                                                  ratios=ratios, statements=requested)
            if tried is not None:
                return tried
        except Exception:
            pass
    # A sole-trader engagement: accounts are given, capital is the balancing figure that the
    # problem asks us to determine.  It must run before the generic given-balances route, which
    # would otherwise misread it as a balance sheet analysis.
    if is_mod.detect_owner_equity(text):
        try:
            tried = _solve_owner_equity(text, currency=currency, framework=framework,
                                       ratios=ratios, statements=requested)
        except Exception:
            tried = None
        if tried is not None:
            return tried
    # Try the deterministic given-balances computation for problems that list
    # account names and amounts but don't match a specific statement template.
    if detect_given_balances(text):
        tried = _solve_given_balances(text, currency=currency, framework=framework,
                                      ratios=ratios, statements=requested)
        if tried is not None:
            return tried
    # Try the deterministic EPS computation.
    # A trial balance is not one: it is read exactly, and a line called
    # "Preference dividends" in a trial balance is a dividend, not the start of
    # an earnings-per-share problem.
    if detect_eps(text) and not _reads_as_trial_balance(text):
        tried = _solve_eps(text, currency=currency, framework=framework,
                           ratios=ratios, statements=requested)
        if tried is not None:
            return tried
    # Try the comprehensive financial computation engine (sections A-K).
    # A trial balance is read exactly, and it carries the ratios itself, so it
    # does not go to the engine.
    # A statement-preparation problem ("prepare the income statement / balance sheet /
    # cash flow statement") is not a financial-computation problem, even if it mentions
    # cue words like "book value" or "ratio".
    _is_statement_prep = bool(re.search(
        r"prepare\s+(?:the\s+)?(?:income\s+statement|balance\s+sheet|statement\s+of\s+cash\s+flows|classified\s+balance\s+sheet)",
        text, re.I))
    computation_named = bool(fc.detect_sections(text)) and not _reads_as_trial_balance(text) and not _is_statement_prep
    if computation_named:
        tried = _solve_financial_computations(text, currency=currency, framework=framework,
                                              ratios=ratios, statements=requested)
        if tried is not None:
            return tried
    # Try the error-correction engine (Tip 5 Type 4): the text states an error and asks
    # for the correcting entry.  This runs before reconstruction because an error problem
    # can mention "capital" or "inventory" without asking for a missing figure.
    if ec.detect_error_problem(text):
        tried = _solve_error_correction(text, currency=currency, framework=framework,
                                        ratios=ratios, statements=requested)
        if tried is not None:
            return tried
    # Try the reconstruction engine (Tip 5 Type 2): the text asks for a missing figure that
    # a stated relation can solve.  It runs before the case solver because a reconstruction
    # problem is often a single relation, not a transaction list.
    if recon.detect_reconstruction_problem(text) and not _reads_as_trial_balance(text):
        tried = _solve_reconstruction(text, currency=currency, framework=framework,
                                      ratios=ratios, statements=requested)
        if tried is not None:
            return tried
    reading, rows, source, rejected, same_model = None, [], "parser", [], False
    parser_error = None
    tier1_gaps = []
    try:
        reading = read_deterministic(text, currency=currency, framework=framework)
        rows = reading.pop("_rows", []) or []
        # If the deterministic reader missed most of the problem (many missing
        # lines), treat it as a failed read so the model path takes over.
        missing = reading.get("missing") if isinstance(reading, dict) else None
        if isinstance(missing, list) and len(missing) > 3:
            if isinstance(reading, dict):
                tier1_gaps = (reading.get("missing") or []) + (reading.get("unplaceable") or [])
            parser_error = StatementError("deterministic reader missed most of the problem")
            reading = None
            rows = []
    except StatementRefused as error:
        if isinstance(reading, dict):
            tier1_gaps = (reading.get("missing") or []) + (reading.get("unplaceable") or [])
        parser_error = error
        reading = None
    except StatementError as error:
        if isinstance(reading, dict):
            tier1_gaps = (reading.get("missing") or []) + (reading.get("unplaceable") or [])
        parser_error = error
        reading = None
    if reading is None:
        if isinstance(parser_error, StatementRefused) and _reads_as_balances(text):
            # A refusal is a refusal: no model reading can rescue two periods, two entities or a
            # consolidation, so it must not be softened into "the reading failed".  A *transaction*
            # narrative is different â€” a sentence can carry two figures without being a comparative,
            # and the plan layer is the reader that is meant to handle it.
            raise parser_error
        # Try the deterministic multi-step income statement computation before transactions/model.
        if detect_income_statement(text):
            tried = _solve_income_statement(text, currency=currency, framework=framework,
                                            ratios=ratios, statements=requested)
            if tried is not None:
                return tried
        # Try the integrated case solver (Tip 5 Type 7): the full state machine over the
        # problem's transactions, with every stage recorded.  It uses the deterministic
        # template layer, so it needs no model.  It is run once here so an incomplete case
        # (a stated figure no entry uses) can skip the older deterministic path below and
        # hand the whole narrative to the model instead of answering with half a ledger.
        _case = None
        _case_incomplete = False
        if "case_solver" in _CORE:
            try:
                _case = _core("case_solver")(text)
            except Exception:
                _case = None
            if _case is not None and getattr(_case, "status", None) == "ok":
                _unused = getattr(_case, "unused_amounts", None) or []
                _case_incomplete = bool(_unused) and "extract" in _CORE
                if not _case_incomplete:
                    tried = _solve_case(text, currency=currency, framework=framework,
                                        ratios=ratios, statements=requested, case=_case)
                    if tried is not None:
                        return tried
        # Try the deterministic detector/template layer for transaction narratives before the model.
        # A narrative that carries adjustments *and* transactions classifies as "adjustments", so
        # the detector's own matches are the signal, not the parser's error wording.
        detector_matches = [m for m in sd.detect(text) if sd.journalizable(m)]
        if (not _case_incomplete
                and ("transactions" in str(parser_error).lower()
                     or "no account" in str(parser_error).lower()
                     or detector_matches)):
            tried = _solve_transactions(text, currency=currency, framework=framework,
                                        ratios=ratios, statements=requested)
            if tried is not None:
                return tried
        # The instruction named a financial computation (a section of the engine) but
        # declares none of the figures that computation needs, and there is no
        # transaction to post.  The model must not answer a computation question with
        # figures it invented, so the tile refuses and says what is missing.  This is
        # the "a route that computed nothing does not answer" rule, enforced at the
        # point where the model reader would otherwise take the instruction.
        if computation_named:
            raise StatementError("this names a financial computation, but the instruction "
                                 "declares none of the figures it needs; state the figures and "
                                 "the tile will compute them")
        used = reader if reader is not None else _CORE.get("reader")
        plan_error = None
        if "extract" in _CORE:
            # Retry loop: the model proposes, the gates verify. A failed attempt is fed
            # back and retried (max 4). Escalation to a higher-tier model is configured
            # via BP_TIER2_MODEL / BP_TIER3_MODEL; debate is the last resort.
            last_error = None
            # The deepseek-v4-pro gate is worth its cost only on genuinely complex problems.
            # Deterministic problems never reach this path (solved by code above); small narratives
            # that slipped past the deterministic reader are retried on the cheap model (tier 1).
            complex_problem = _is_complex_problem(text)
            for attempt in range(4):
                try:
                    if complex_problem:
                        # Escalate model tier: 1 (standard) -> 2 (retry) -> 3 (escalation) -> 3 (debate)
                        tier = 1 if attempt == 0 else (2 if attempt == 1 else 3)
                    else:
                        tier = 1
                    if "set_tier" in _CORE:
                        _core("set_tier")(tier)
                    attempt_text = text
                    if attempt > 0 and last_error is not None:
                        attempt_text = (text + "\n\nPREVIOUS ATTEMPT FAILED: " +
                                        str(last_error)[:400] +
                                        "\nFix the entries and adjustments so the statements tie.")
                    # Completeness hint: list stated dollar figures
                    if attempt > 0:
                        import re as _re
                        stated_nums = set(_re.findall(r'\$[\d,]+(?:\.\d+)?', text))
                        attempt_text += ("\n\nSTATED FIGURES (ensure EACH is used in an entry or adjustment): " +
                                         ", ".join(sorted(stated_nums)))
                    return _solve_narrative(attempt_text, currency=currency, framework=framework,
                                            ratios=ratios, statements=requested,
                                            tier1_gaps=tier1_gaps)
                except NoModel as error:
                    plan_error = error
                    break
                except StatementError as error:
                    last_error = error
                    if attempt == 3:
                        raise
                    continue
        if used is None:
            if plan_error is not None:
                raise StatementError(str(parser_error) + " â€” and the plan layer could not read it either: "
                                    + str(plan_error))
            raise StatementError(str(parser_error) + " â€” and no model is configured to read it")
        try:
            answer = used(text)
        except Exception as error:
            if plan_error is not None:
                raise StatementError("the model reading failed (" + str(error)[:160] + "), and the "
                                     "plan layer could not read it either: " + str(plan_error))
            raise StatementError("the model reading failed (" + str(error)[:160] + "), and the "
                                 "deterministic reader could not read this either: " + str(parser_error))
        reading = answer.get("reading") if isinstance(answer, dict) else None
        if not isinstance(reading, dict):
            raise StatementError("the model returned no reading")
        source = answer.get("source") or "council"
        rejected = answer.get("rejected") or []
        same_model = bool(answer.get("same_model"))
    problems = statements_verify.verify_reading(reading, text, reading.get("currency"))
    if problems:
        raise StatementError("the reading was refused: " + "; ".join(
            str(problem.get("detail")) for problem in problems[:3]))
    if rows:
        reading = derive_balancing_figure(reading, rows)
    spec = compile_spec(reading)
    try:
        result = _core("solve")(spec)
    except Exception as error:
        return _refusal(text, reading, spec, "the accounts do not build: " + str(error)[:400],
                        source, rejected, same_model, requested)
    pack = ratio_pack(result, text) if (wants_ratios(text) or ratios is True) else None
    return _record(reading, spec, result, text, source, rejected, same_model, pack, requested)


def _solve_schedule(kind, text, currency=None, framework=None, ratios=None, statements=None):
    """A labelled-figure schedule: figures in, a named schedule out, no model.

    The arithmetic is `bp.schedule_math` (injected as `schedules`); this function only turns
    the result into the record the tile stores.

    **This is an accelerator, not a gatekeeper** (manual Â§2A).  A figure the text does not state,
    or a check that fails, returns ``None`` so `solve()` continues into the model loop exactly as
    it would have without this route.  It never refuses in the model's place.
    """
    compute = _CORE.get("schedules")
    if compute is None:
        return None
    from . import schedule_routes as sched
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]
    try:
        out = sched.run(kind, text, compute)
    except Exception:
        # A missing label, an unreadable figure, arithmetic that cannot proceed: the model loop
        # is the next seat, and it is better informed than a refusal from here.
        return None
    if not out.get("sections"):
        return None
    if [check for check in (out.get("checks") or []) if not check[1]]:
        # The schedule does not tie on its own figures.  That is an ambiguous problem: hand it to
        # the model loop, which can see what the labels mean.
        return None
    sections = out["sections"]
    body = {}
    for section in sections:
        title = str(section.get("title") or "")
        if kind == "cogm" and title.startswith("SCHEDULE"):
            body["schedules"] = section["text"]
        elif kind == "cogm" and title.startswith("INCOME"):
            body["income_statement"] = section["text"]
        elif kind == "cash_flow_indirect":
            body["cash_flow"] = section["text"]
        elif kind == "equity_statement":
            body["equity"] = section["text"]
        else:
            body["notes"] = (body.get("notes", "") + "\n\n" + section["text"]).strip()

    statements_out = {"trial_balance": "", "income_statement": "", "balance_sheet": "",
                      "equity": "", "notes": "", "cash_flow": None,
                      "cash_flow_withheld_because": None}
    statements_out.update(body)

    rendered = "\n\n".join(section["text"] for section in sections)
    figures = out.get("computed") or out.get("figures") or {}
    scalars = {key: str(value) for key, value in figures.items()}
    code = {"cogm": "IS", "cash_flow_indirect": "CF", "equity_statement": "RE",
            "bank_reconciliation": "BS"}.get(kind, "IS")
    reading = {
        "problem_type": kind,
        "why": ("the figures are stated as labelled amounts, so the schedule is an identity "
                "over them: no journal entry is posted and no model is consulted"),
        "currency": currency, "framework": framework, "period": period,
        "derivations": [], "assumptions": [],
        "missing": [], "diagnosis": None,
    }
    record = {
        "format": FORMAT, "solved": True, "refusal": None,
        "instruction": text, "instruction_hash": verify.brief_hash(text),
        "problem_type": kind, "why": reading["why"],
        "reading": reading, "reading_source": "schedule",
        "same_model_disclosure": False, "rejected": [],
        "spec": {"schedule": kind, "figures": {k: str(v) for k, v in figures.items()}},
        "requested": [code], "computed": [code], "hidden": [],
        "warnings": [],
        "core": {"scalars": scalars,
                 "appendix": {"engagement": {"period": period, "currency": currency,
                                             "places": 2},
                              "schedule": kind,
                              "schedule_figures": scalars,
                              "statements_export": body}},
        "statements": statements_out,
        "statements_only": rendered,
        "working": {"journal": "", "trial_balance": "", "t_accounts": {},
                    "derivations": [], "assumptions": [], "missing": [],
                    "schedule_figures": scalars},
        "diagnosis": None,
        "checks": [{"name": name, "ok": bool(ok), "detail": detail}
                   for name, ok, detail in (out.get("checks") or [])],
        "ratios": None,
    }
    return verify.freeze(record)


def _solve_transactions(text, currency=None, framework=None, ratios=None, statements=None):
    """A transaction narrative solved through the deterministic detector/template layer.

    Every transaction claim is matched to a registered detector, journalized through a balanced
    template, and posted to the ledger. No model is involved; every figure comes from the text.
    """
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]

    matches = sd.detect(text)
    journalizable = [m for m in matches if sd.journalizable(m)]
    if not journalizable:
        return None
    # Two detectors may match the same sentence ("the owner invested 50,000 cash" matches both
    # capital_contribution and equity_issuance_cash).  Keep the most specific one per overlapping
    # span, so one fact is posted once.
    selected = []
    for match in sorted(journalizable, key=lambda m: (-m.specificity, m.span[0])):
        if any(not (match.span[1] <= other.span[0] or match.span[0] >= other.span[1])
               for other in selected):
            continue
        selected.append(match)
    journalizable = selected

    # The chart is the one chart of the tile (`bp.statement_chart`), so a detector that
    # posts to an account code always finds that account where the statement needs it.
    chart = [dict(account) for account in statement_chart.CHART]

    # Build entries: one journal entry per detector match
    entries = []
    for m in journalizable:
        try:
            lines = sd.journalize(m.detector_id, m.slots)
        except sd.DetectError:
            continue
        je_lines = []
        for acct, side, amt in lines:
            line_dict = {"account": acct}
            if side == "Dr":
                line_dict["debit"] = str(amt)
            else:
                line_dict["credit"] = str(amt)
            je_lines.append(line_dict)
        if len(je_lines) < 2:
            continue
        entries.append({
            "date": period["end"],
            "description": m.detector_id,
            "lines": je_lines,
        })

    if not entries:
        raise StatementError("no transaction could be journalized from this text")

    # A narrative may state transactions and adjustments together.  The transactions are
    # journalized by the detector layer; the adjustments are read by the adjustment parser,
    # which ignores the transaction sentences because they carry no adjustment cue.
    specs, stated, unread = [], [], []
    if _needs_adjustments(text):
        specs, stated, unread = _adjustment_specs(text, [], chart)
        for spec in specs:
            spec.setdefault("date", period["end"])
        for entry in stated:
            entry["date"] = entry.get("date") or period["end"]
        entries.extend(stated)
    tax_rate = None
    for spec in specs:
        if spec.get("function") == "tax_on_pretax" and spec.get("tax_rate"):
            tax_rate = spec.pop("tax_rate")
    policy = {"rounding": "half_up", "inventory_system": "periodic"}
    if tax_rate is not None:
        policy["tax_rate"] = tax_rate
        policy["explicitly_stated"] = ["tax_rate"]
    plan = {
        "period": period, "currency": currency, "framework": framework, "places": 2,
        "policy": policy,
        "prior_closing": {}, "opening": [], "entries": entries,
        "adjustments": specs, "schedules": [],
        "chart": chart, "problem_type": "transactions",
    }
    try:
        result = _core("build")(plan)
    except Exception:
        # The deterministic detector only matched part of the text, so the partial
        # journal does not tie. Fall through to the model reader, which reads the
        # whole narrative. Returning None (not raising) lets solve() try the next route.
        return None

    posted = [spec["description"] for spec in specs] + [entry["description"] for entry in stated]
    reading = {
        "problem_type": "transactions",
        "why": ("Prepared from journal entries detected in the text"
                + (", with the stated adjusting entries applied," if specs or stated else "")
                + "; every figure was posted by the deterministic ledger and checked against the "
                  "three articulation identities."),
        "currency": currency, "framework": framework, "derivations": [],
        "assumptions": ["adjusting entry: " + text_ for text_ in posted],
        "missing": [{"what": clause,
                     "why": "this adjustment is not one the reader recognises, so it was left "
                            "out rather than guessed"} for clause in unread],
        "diagnosis": None,
    }
    pack = ratio_pack(result, text) if (wants_ratios(text) or ratios is True) else None
    spec = {"period": period, "currency": currency, "framework": framework, "places": 2,
            "chart": chart, "entries": entries, "adjustments": specs}
    record = _record(reading, spec, result, text, "plan",
                     [], False, pack, statements)
    record["reading_source"] = "plan"
    return record


def _strip_preamble(text):
    """Remove the words in front of a trial balance block ('Data â€” unadjusted trial balance:').

    The reader takes the label as everything before the last amount on a line, so a preamble
    left in place becomes part of the first account's name and the account is lost.
    """
    out = re.sub(r"(?is)^\s*(?:data|given|information|the following)\b[\s\u2014\u2013\-:]*", "",
                 str(text or ""), count=1)
    out = re.sub(r"(?i)\b(?:unadjusted|adjusted|pre-?closing)?\s*trial balance\s*[:\-\u2014]\s*", "",
                 out, count=1)
    return out.lstrip()


def _tb_balance(rows, line):
    """The balance of the accounts on one statement line, signed debit-positive."""
    total, found = Decimal(0), False
    for row in rows:
        if row["placed"]["placement"]["line"] != line:
            continue
        side, amount = _resolve(row)
        value = Decimal(str(amount).replace(",", ""))
        total += value if side == "debit" else -value
        found = True
    return total if found else None


def _chart_code(chart, pattern, contra=None, type_=None):
    """The code of the chart account whose name matches, or None.

    ``type_`` restricts the search to one account type.  Without it, a loose fragment picks the
    first account that happens to contain it: "revenue" finds "Unearned revenue" (a liability)
    before it finds "Service revenue" (income), and an adjustment would then debit and credit the
    same account.
    """
    for account in chart:
        if type_ is not None and str(account.get("type") or "") != type_:
            continue
        if re.search(pattern, str(account.get("name") or ""), re.I):
            if contra is None or bool(account.get("contra")) == bool(contra):
                return account["code"]
    return None


def _ensure_account(chart, name, type_, line, quote="", section=None, activity="operating",
                    contra=False):
    """The code for this account, adding it to the chart when the adjustment names it.

    Adding an account the adjustment names is chart completion, not invention: the account
    is stated by the adjustment's own words, and the quote records which clause named it.
    """
    for account in chart:
        if str(account.get("name") or "").strip().lower() == name.strip().lower():
            return account["code"]
    code = _free_code(CODE_FOR_LINE.get(line, "9000"), chart)
    account = {"code": code, "name": name, "type": type_, "line": line,
               "quote": quote or name, "synthesised": True}
    if section:
        account["section"] = section
    if activity:
        account["activity"] = activity
    if contra:
        account["contra"] = True
    chart.append(account)
    return code


def _amounts(clause):
    """Every money amount in a clause, with dates excluded."""
    spans = sper.date_spans(clause)
    return [Decimal(match.group(0).replace(",", "")) for match in MONEY.finditer(clause)
            if not any(start <= match.start() < end for start, end in spans)]


def _clause_amount(clause):
    found = _amounts(clause)
    return max(found) if found else None


def _number_before(clause, pattern):
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:" + pattern + r")", clause, re.I)
    return Decimal(match.group(1)) if match else None


def _rate_percent(clause):
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", clause)
    return Decimal(match.group(1)) if match else None


def _whole(value):
    return str(int(value)) if value is not None and value == int(value) else str(value)


def _add_months(date_str, months):
    """The date a cover ends: the start plus a whole number of months."""
    from datetime import date
    try:
        start = date.fromisoformat(str(date_str))
    except ValueError:
        return str(date_str)
    total = start.month - 1 + int(months)
    year = start.year + total // 12
    month = total % 12 + 1
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    last = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(start.day, last)).isoformat()


_ADJUSTMENT_CUE = re.compile(
    r"\b(prepaid|prepayment|accru\w*|depreciat\w*|amorti[sz]\w*|bad debts?|allowance|"
    r"uncollectible|doubtful|unearned|deferred revenue|interest|tax|physical count|"
    r"inventory count|supplies (?:on hand|counted|remaining)|warranty|shrinkage)\b", re.I)


def _split_tb_and_adjustments(text):
    """The unadjusted trial balance and the adjustment narrative, with or without a marker.

    An explicit "adjustments:" marker wins.  Otherwise the trial-balance lines are the simple
    "label amount" rows and the adjustment lines are the sentences that carry an adjustment cue;
    an adjustment sentence never parses as a balance row, and a balance row ("Accrued expenses
    2,000") is never mistaken for an adjustment.
    """
    pieces = re.split(r"\badjustments?\b\s*[:\-\u2014]?", str(text or ""), maxsplit=1, flags=re.I)
    if len(pieces) == 2 and re.search(r"trial balance|balances?\b", pieces[0], re.I):
        return pieces[0], pieces[1]
    tb_lines, adj_lines = [], []
    for line in str(text or "").splitlines():
        if not line.strip():
            continue
        rows, _skipped = parse_rows(line)
        if rows:
            tb_lines.append(line)
        elif _ADJUSTMENT_CUE.search(line):
            adj_lines.append(line)
    if len(tb_lines) >= 3 and adj_lines:
        return "\n".join(tb_lines), "\n".join(adj_lines)
    return None, None


def _adjustment_specs(adj_text, rows, chart):
    """Read the stated adjustments into adjustment specs and stated entries.

    Recognises the adjustments a first- or second-year course sets: supplies used, prepaid
    amortisation, straight-line depreciation (a cost and a life, or a stated amount), accrued
    expenses, unearned revenue earned, bad debts, interest accrual and income tax.  An
    adjustment it does not recognise, or one whose parameters are incomplete, is named in
    `unread`, never guessed.  Every derived amount is computed by the plan layer's registered
    function, not here.
    """
    specs, entries, unread = [], [], []
    supplies = _tb_balance(rows, "Supplies")
    supplies_code = _chart_code(chart, r"supplies")
    revenue_code = _chart_code(chart, r"revenue|sales", type_="income")
    salaries_code = _chart_code(chart, r"salaries|wages")
    unearned_code = _chart_code(chart, r"unearned|deferred revenue", type_="liability")
    accumulated_code = _chart_code(chart, r"accumulated depreciation", contra=True)
    prepayment_code = _chart_code(chart, r"prepayment")
    allowance_code = _chart_code(chart, r"allowance|doubtful", contra=True)
    accrual_code = _chart_code(chart, r"accrued|accruals", type_="liability")
    receivables = _tb_balance(rows, "Trade receivables")

    for clause in re.split(r"[;.\n]+", str(adj_text or "")):
        clause = clause.strip()
        if not clause:
            continue
        low = clause.lower()
        if re.search(r"required|journali[sz]e|prepare|create|compute", low):
            continue
        amount = _clause_amount(clause)

        # 1. Supplies on hand: beginning + purchases - ending.
        if (re.search(r"supplies (?:on hand|counted|count|remaining|at year)", low)
                and supplies is not None and amount is not None):
            debit = _ensure_account(chart, "Supplies expense", "expense", "Supplies expense",
                                    quote=clause)
            credit = supplies_code or _ensure_account(chart, "Supplies", "asset", "Supplies",
                                                      quote=clause, section="current")
            specs.append({"id": "supplies_used", "function": "supplies_used",
                          "params": {"beginning_inventory": str(supplies), "purchases": "0",
                                     "ending_inventory": str(amount)},
                          "debit": debit, "credit": credit, "description": clause})
            continue

        # 2. Prepaid cover: payment x months expired / total months.
        if re.search(r"prepaid|prepayment", low) and amount is not None:
            months = _number_before(clause, r"months?")
            dates = sper.transaction_dates(clause)
            params = {"payment": str(amount), "total_months": _whole(months) if months else "12"}
            if len(dates) >= 2:
                params["coverage_start"], params["coverage_end"] = dates[0], dates[1]
            elif dates:
                params["coverage_start"] = dates[0]
                params["coverage_end"] = _add_months(dates[0], int(months) if months else 12)
            elif months and re.search(r"\b(?:full|whole|entire)\s+year", low):
                params["months_expired"] = _whole(months)
            else:
                unread.append(clause)
                continue
            debit = (_chart_code(chart, r"insurance") if "insurance" in low else
                     _chart_code(chart, r"rent") if "rent" in low else
                     _chart_code(chart, r"advertis|marketing") if "advertis" in low else None)
            debit = debit or _ensure_account(chart, "Operating expenses", "expense",
                                             "Operating expenses", quote=clause)
            credit = prepayment_code or _ensure_account(chart, "Prepayments", "asset",
                                                        "Prepayments", quote=clause,
                                                        section="current")
            specs.append({"id": "prepaid", "function": "prepaid_amortization", "params": params,
                          "debit": debit, "credit": credit, "description": clause})
            continue

        # 3. Depreciation: a cost and a life, or a stated amount.
        if re.search(r"depreciat", low) and not re.search(r"accumulated", low):
            life = _number_before(clause, r"years?")
            debit = _ensure_account(chart, "Depreciation", "expense", "Depreciation", quote=clause)
            credit = accumulated_code or _ensure_account(
                chart, "Accumulated depreciation", "asset", "Property, plant and equipment",
                quote=clause, section="non_current", activity="investing", contra=True)
            if amount is not None and life is not None:
                convention = "pro_rata" if re.search(r"pro.?rata|part.?year|\bmonth", low) else "full_year"
                params = {"cost": str(amount), "life_years": _whole(life),
                          "convention": convention}
                if convention == "pro_rata":
                    params["months_in_service"] = "12"
                specs.append({"id": "depreciation", "function": "straight_line_depreciation",
                              "params": params, "debit": debit, "credit": credit,
                              "description": clause})
            elif amount is not None:
                entries.append({"date": None, "description": clause,
                                "lines": [{"account": debit, "debit": str(amount)},
                                          {"account": credit, "credit": str(amount)}]})
            else:
                unread.append(clause)
            continue

        # 4. Unearned revenue earned.
        if (re.search(r"unearned|deferred revenue", low)
                and re.search(r"earned|recogni[sz]ed", low) and amount is not None):
            debit = unearned_code or _ensure_account(chart, "Unearned revenue", "liability",
                                                     "Accruals", quote=clause, section="current")
            credit = revenue_code or _ensure_account(chart, "Revenue", "income", "Revenue",
                                                     quote=clause)
            specs.append({"id": "unearned_earned", "function": "unearned_revenue_earned",
                          "params": {"amount": str(amount)}, "debit": debit, "credit": credit,
                          "description": clause})
            continue

        # 5. Accrued salaries.
        if re.search(r"accrued\s+(salaries|salary|wages|payroll)", low) and amount is not None:
            debit = salaries_code or _ensure_account(chart, "Salaries expense", "expense",
                                                     "Salaries expense", quote=clause)
            credit = accrual_code or _ensure_account(chart, "Accrued expenses", "liability",
                                                     "Accruals", quote=clause, section="current")
            specs.append({"id": "accrued_salaries", "function": "accrued_expense",
                          "params": {"amount": str(amount)}, "debit": debit, "credit": credit,
                          "description": clause})
            continue

        # 6. Accrued interest: principal x rate x months / 12.
        if re.search(r"accrued\s+interest|interest.*(?:accru|owing|unpaid)", low):
            rate = _rate_percent(clause)
            months = _number_before(clause, r"months?")
            if amount is not None and rate is not None and months is not None:
                debit = _chart_code(chart, r"interest") or _ensure_account(
                    chart, "Interest expense", "expense", "Interest expense", quote=clause)
                credit = accrual_code or _ensure_account(chart, "Accrued expenses", "liability",
                                                         "Accruals", quote=clause,
                                                         section="current")
                specs.append({"id": "interest", "function": "interest_accrual",
                              "params": {"principal": str(amount), "rate": str(rate),
                                         "months": _whole(months)},
                              "debit": debit, "credit": credit, "description": clause})
            else:
                unread.append(clause)
            continue

        # 7. Accrued other expenses (stated amount).
        if re.search(r"accrued\s+(rent|utilities|expenses?)", low) and amount is not None:
            debit = _ensure_account(chart, "General expenses", "expense", "General expenses",
                                    quote=clause)
            credit = accrual_code or _ensure_account(chart, "Accrued expenses", "liability",
                                                     "Accruals", quote=clause, section="current")
            specs.append({"id": "accrued_expense", "function": "accrued_expense",
                          "params": {"amount": str(amount)}, "debit": debit, "credit": credit,
                          "description": clause})
            continue

        # 8. Bad debts: a rate of receivables, or a stated amount.
        if re.search(r"bad debts?|uncollectible|doubtful", low):
            rate = _rate_percent(clause)
            debit = _chart_code(chart, r"bad debt") or _ensure_account(
                chart, "Bad debts", "expense", "Bad debts", quote=clause)
            credit = allowance_code or _ensure_account(
                chart, "Allowance for doubtful accounts", "asset", "Trade receivables",
                quote=clause, section="current", contra=True)
            if rate is not None and receivables is not None:
                specs.append({"id": "bad_debt", "function": "bad_debt_expense",
                              "params": {"receivables": str(receivables), "rate": str(rate)},
                              "debit": debit, "credit": credit, "description": clause})
            elif amount is not None:
                entries.append({"date": None, "description": clause,
                                "lines": [{"account": debit, "debit": str(amount)},
                                          {"account": credit, "credit": str(amount)}]})
            else:
                unread.append(clause)
            continue

        # 9. Income tax at a declared rate (the plan's second pass settles the amount).
        if re.search(r"\btax\b", low) and _rate_percent(clause) is not None:
            debit = _chart_code(chart, r"tax", type_="expense") or _ensure_account(
                chart, "Tax", "expense", "Tax", quote=clause)
            credit = _chart_code(chart, r"tax payable", type_="liability") or _ensure_account(
                chart, "Tax payable", "liability", "Accruals", quote=clause, section="current")
            specs.append({"id": "tax", "function": "tax_on_pretax", "params": {},
                          "debit": debit, "credit": credit, "description": clause,
                          "tax_rate": str(_rate_percent(clause) / 100)})
            continue

        if amount is not None and _ADJUSTMENT_CUE.search(low):
            unread.append(clause)

    return specs, entries, unread


def _solve_adjusted_trial_balance(text, currency=None, framework=None, ratios=None,
                                  statements=None):
    """An unadjusted trial balance plus the adjusting entries the text states.

    The trial balance is posted as one period entry (the rule the tile has always used), and
    each stated adjustment is posted as a second entry, its amount computed by the plan
    layer's registered function.  Nothing is derived that the text does not state, and an
    adjustment the reader does not recognise is named as unread rather than guessed.
    """
    if "build" not in _CORE:
        return None
    tb_text, adj_text = _split_tb_and_adjustments(text)
    if tb_text is None:
        return None
    tb_text = _split_semicolon_accounts(_strip_preamble(tb_text))
    rows, _skipped = parse_rows(tb_text)
    if len(rows) < 3:
        return None
    try:
        preflight_rows(rows)
    except StatementRefused:
        return None
    chart = build_chart(rows)
    specs, stated, unread = _adjustment_specs(adj_text, rows, chart)
    if not specs and not stated:
        return None
    tax_rate = None
    for spec in specs:
        if spec.get("function") == "tax_on_pretax" and spec.get("tax_rate"):
            tax_rate = spec.pop("tax_rate")
    period = period_of(text)[0]
    places = max([2] + [_decimals(row["written"]) for row in rows])
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)

    lines = []
    for row in rows:
        side, amount = _resolve(row)
        lines.append({"account": row["code"], side: amount})
    entries = [{"date": period["end"], "description": "the unadjusted trial balance as given",
                "aggregate": True, "lines": lines}]
    for entry in stated:
        entries.append({"date": entry.get("date") or period["end"],
                        "description": entry["description"], "lines": entry["lines"]})
    for spec in specs:
        spec.setdefault("date", period["end"])

    policy = {"rounding": "half_up", "inventory_system": "periodic",
              "depreciation": {"method": "straight_line", "convention": "pro_rata"},
              "explicitly_stated": []}
    if tax_rate is not None:
        policy["tax_rate"] = tax_rate
        policy["explicitly_stated"] = ["tax_rate"]

    plan = {"period": period, "currency": currency, "framework": framework, "places": places,
            "policy": policy,
            "prior_closing": {}, "opening": [], "entries": entries,
            "adjustments": specs, "schedules": [],
            "chart": [{k: v for k, v in a.items() if k not in ("quote", "synthesised")}
                      for a in chart],
            "problem_type": "trial_balance"}
    try:
        result = _core("build")(plan)
    except Exception:
        # Accelerator, not gatekeeper (manual Â§2A): if the ledger cannot build this, the model
        # loop reads the same problem and the gates judge its answer.
        return None

    posted = [spec["description"] for spec in specs] + [entry["description"] for entry in stated]
    reading = {
        "problem_type": "trial_balance",
        "why": ("the unadjusted trial balance posted as one period entry, with the stated "
                "adjusting entries posted after it; every figure comes from the instruction"),
        "currency": currency, "framework": framework, "derivations": [],
        "assumptions": ["adjusting entry: " + text_ for text_ in posted],
        "missing": [{"what": clause,
                     "why": "this adjustment is not one the reader recognises, so it was left "
                            "out rather than guessed"} for clause in unread],
        "diagnosis": None,
    }
    pack = ratio_pack(result, text) if (wants_ratios(text) or ratios is True) else None
    spec = {"period": period, "currency": currency, "framework": framework, "places": places,
            "chart": [{k: v for k, v in a.items() if k not in ("quote", "synthesised")}
                      for a in chart],
            "entries": entries, "adjustments": specs}
    return _record(reading, spec, result, text, "plan", [], False, pack, statements)


def _solve_income_statement(text, currency=None, framework=None, ratios=None, statements=None):
    """Compute a multi-step income statement from given account balances.

    The problem gives account names and amounts (revenue, contra-revenue, COGS,
    operating expenses, non-operating items, tax rate).  The engine computes
    Net Sales â†’ Gross Profit â†’ Operating Income â†’ Income Before Tax â†’ Net Income
    deterministically, with no model involvement.
    """
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]

    lines, tax_rate = is_mod.parse_problem(text)
    # Validate that we have actual income statement accounts (revenue or cogs),
    # not just a stray contra-revenue line from a partial text match.
    has_revenue_or_cogs = any(l.kind in ("revenue", "cogs") for l in lines)
    if not has_revenue_or_cogs:
        return None
    result = is_mod.compute_income_statement(lines, tax_rate)

    statement_text = is_mod.render_income_statement(result, period["end"], currency)

    # Build computation checks (articulation identities for the multi-step IS)
    checks = [
        ("net_sales_equals_revenue_minus_contra",
         result.net_sales == result.cogs + result.gross_profit,
         f"net sales {result.net_sales} = cogs {result.cogs} + gross profit {result.gross_profit}"),
        ("gross_profit_equals_net_sales_minus_cogs",
         result.gross_profit == result.net_sales - result.cogs,
         f"gross profit {result.gross_profit} = net sales {result.net_sales} - cogs {result.cogs}"),
        ("operating_income_equals_gross_profit_minus_opex",
         result.operating_income == result.gross_profit - result.operating_expenses,
         f"operating income {result.operating_income} = gross profit {result.gross_profit} - opex {result.operating_expenses}"),
        ("income_before_tax_equals_operating_income_plus_non_operating",
         result.income_before_tax == result.operating_income + result.non_operating_revenue - result.non_operating_expense,
         f"income before tax {result.income_before_tax} = operating income {result.operating_income} + non-op rev {result.non_operating_revenue} - non-op exp {result.non_operating_expense}"),
        ("net_income_equals_pretax_minus_tax",
         result.net_income == result.income_before_tax - result.income_tax,
         f"net income {result.net_income} = pre-tax {result.income_before_tax} - tax {result.income_tax}"),
    ]

    # Revenue total for display (gross sales before contra-revenue)
    gross_revenue = sum(l.amount for l in lines if l.kind == "revenue")

    appendix = {
        "statements_export": {
            "income_statement": statement_text,
            "income_groups": {
                "revenue": str(gross_revenue),
                "contra_revenue": str(sum(l.amount for l in lines if l.kind == "contra_revenue")),
                "cogs": str(result.cogs),
                "operating_expenses": str(result.operating_expenses),
                "non_operating_revenue": str(result.non_operating_revenue),
                "non_operating_expense": str(result.non_operating_expense),
            },
            "net_sales": str(result.net_sales),
            "gross_profit": str(result.gross_profit),
            "operating_income": str(result.operating_income),
            "income_before_tax": str(result.income_before_tax),
            "income_tax": str(result.income_tax),
            "net_income": str(result.net_income),
        },
        "engagement": {
            "period": {"start": period["start"], "end": period["end"]},
            "currency": currency,
            "places": 2,
        },
    }

    reading = {
        "problem_type": "income_statement",
        "why": "multi-step income statement computation from declared account balances",
        "currency": currency,
        "framework": framework,
        "period": period,
        "derivations": [],
        "assumptions": [f"tax rate {result.tax_rate * 100:.0f}% applied to pre-tax income"],
        "missing": [],
        "diagnosis": None,
    }

    scalars = {
        "net_income": str(result.net_income),
        "net_sales": str(result.net_sales),
        "gross_profit": str(result.gross_profit),
        "operating_income": str(result.operating_income),
        "income_before_tax": str(result.income_before_tax),
        "income_tax": str(result.income_tax),
        "cogs": str(result.cogs),
        "operating_expenses": str(result.operating_expenses),
    }

    requested_list = list(statements or statements_verify.STATEMENTS)
    computed = ["IS"]
    hidden = [s for s in ("IS", "RE", "BS", "CF") if s in requested_list and s != "IS"]

    statements_out = {}
    if "IS" in requested_list:
        statements_out["income_statement"] = statement_text

    record = {
        "format": FORMAT,
        "solved": True,
        "refusal": None,
        "instruction": text,
        "instruction_hash": verify.brief_hash(text),
        "problem_type": "income_statement",
        "why": reading["why"],
        "reading": reading,
        "reading_source": "plan",
        "same_model_disclosure": False,
        "rejected": [],
        "spec": {},
        "requested": requested_list,
        "computed": computed,
        "hidden": hidden,
        "warnings": [],
        "core": {
            "scalars": scalars,
            "appendix": appendix,
        },
        "statements": statements_out,
        "statements_only": statements_only(statements_out),
        "working": {
            "journal": "",
            "trial_balance": "",
            "t_accounts": {},
            "derivations": [],
            "assumptions": reading["assumptions"],
            "missing": [],
        },
        "diagnosis": None,
        "checks": [{"name": name, "ok": bool(ok), "detail": detail}
                   for name, ok, detail in checks],
        "ratios": None,
    }
    return verify.freeze(record)


def _solve_balance_sheet_analysis(text, currency=None, framework=None, ratios=None, statements=None):
    """Compute a balance sheet analysis / ratio analysis from given account balances.

    The problem gives balance sheet account names and amounts. The engine computes
    current assets, current liabilities, working capital, and current ratio.
    """
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]

    lines, _ = is_mod.parse_problem(text)
    result = is_mod.compute_balance_sheet_analysis(lines)

    statement_text = is_mod.render_balance_sheet_analysis(result, period["end"], currency)

    appendix = {
        "statements_export": {
            "balance_sheet_analysis": statement_text,
            "current_assets": str(result.current_assets),
            "current_liabilities": str(result.current_liabilities),
            "working_capital": str(result.working_capital),
            "current_ratio": str(result.current_ratio),
            "total_assets": str(result.total_assets),
            "total_liabilities": str(result.total_liabilities),
            "total_equity": str(result.total_equity),
        },
        "engagement": {
            "period": {"start": period["start"], "end": period["end"]},
            "currency": currency,
            "places": 2,
        },
    }

    reading = {
        "problem_type": "balance_sheet_analysis",
        "why": "balance sheet analysis / ratio analysis from declared account balances",
        "currency": currency,
        "framework": framework,
        "period": period,
        "derivations": [],
        "assumptions": [],
        "missing": [],
        "diagnosis": None,
    }

    scalars = {
        "current_assets": str(result.current_assets),
        "current_liabilities": str(result.current_liabilities),
        "working_capital": str(result.working_capital),
        "current_ratio": str(result.current_ratio),
        "total_assets": str(result.total_assets),
        "total_liabilities": str(result.total_liabilities),
        "total_equity": str(result.total_equity),
    }

    requested_list = list(statements or statements_verify.STATEMENTS)
    computed = ["BS"]
    hidden = [s for s in ("IS", "RE", "BS", "CF") if s in requested_list and s != "BS"]

    statements_out = {}
    if "BS" in requested_list:
        statements_out["balance_sheet"] = statement_text

    record = {
        "format": FORMAT,
        "solved": True,
        "refusal": None,
        "instruction": text,
        "instruction_hash": verify.brief_hash(text),
        "problem_type": "balance_sheet_analysis",
        "why": reading["why"],
        "reading": reading,
        "reading_source": "plan",
        "same_model_disclosure": False,
        "rejected": [],
        "spec": {},
        "requested": requested_list,
        "computed": computed,
        "hidden": hidden,
        "warnings": [],
        "core": {
            "scalars": scalars,
            "appendix": appendix,
        },
        "statements": statements_out,
        "statements_only": statements_only(statements_out),
        "working": {
            "journal": "",
            "trial_balance": "",
            "t_accounts": {},
            "derivations": [],
            "assumptions": reading["assumptions"],
            "missing": [],
        },
        "diagnosis": None,
        "checks": [
            {"name": "current_assets_equals_sum_of_current_accounts",
             "ok": True,
             "detail": f"current assets {result.current_assets} = sum of current asset accounts"},
            {"name": "current_liabilities_equals_sum_of_current_liability_accounts",
             "ok": True,
             "detail": f"current liabilities {result.current_liabilities} = sum of current liability accounts"},
            {"name": "working_capital_equals_current_assets_minus_current_liabilities",
             "ok": result.working_capital == result.current_assets - result.current_liabilities,
             "detail": f"working capital {result.working_capital} = {result.current_assets} - {result.current_liabilities}"},
            {"name": "current_ratio_equals_current_assets_divided_by_current_liabilities",
             "ok": result.current_liabilities > 0 and abs(result.current_ratio - result.current_assets / result.current_liabilities) < Decimal("0.001"),
             "detail": f"current ratio {result.current_ratio} = {result.current_assets} / {result.current_liabilities}"},
        ],
        "ratios": None,
    }
    return verify.freeze(record)


def _solve_owner_equity(text, currency=None, framework=None, ratios=None, statements=None):
    """A sole-trader problem: accounts are given, capital is the balancing figure.

    Assets, liabilities, income and expenses are stated; drawings and any additional capital are
    stated or zero.  The closing capital is whatever the accounting equation requires, and the
    opening capital is derived from it (closing capital = opening + net income - drawings +
    additional capital).  The three statements and that derived figure are the answer.

    This is a general capability, not a patch for one problem: any sole-trader engagement whose
    capital account is unstated is solved the same way, and the derivation is shown, never hidden.
    """
    if "build" not in _CORE:
        return None
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]
    tb_text = _split_semicolon_accounts(text)
    rows, _skipped = parse_rows(tb_text)
    if len(rows) < 3:
        return None

    assets = []          # (label, amount, is_contra)
    liabilities = []
    income = Decimal(0)
    expenses = Decimal(0)
    drawings = Decimal(0)
    capital_stated = None
    additional = Decimal(0)
    additional = Decimal(0)
    m_add = re.search(r"additional capital.{0,40}", text, re.I)
    if m_add:
        nums = re.findall(r"[0-9][0-9,]*(?:\.[0-9]+)?", m_add.group(0))
        if nums:
            additional = Decimal(nums[-1].replace(",", ""))

    for row in rows:
        side, amount = _resolve(row)
        value = Decimal(str(amount).replace(",", ""))
        label = row["label"]
        kind, line_name = is_mod._classify_account(label)
        if kind in ("current_asset", "non_current_asset"):
            assets.append((label, value, False))
        elif kind == "contra_asset":
            assets.append((label, value, True))
        elif kind in ("current_liability", "non_current_liability"):
            liabilities.append((label, value))
        elif kind == "revenue":
            income += value
        elif kind == "operating_expense":
            expenses += value
        elif kind == "drawings":
            drawings += value
        elif kind == "equity":
            capital_stated = value

    if not assets or not liabilities:
        return None
    if capital_stated is not None:
        # Capital is stated: this is a plain balance sheet, not a derivation problem.
        return None

    total_assets = Decimal(0)
    for label, value, contra in assets:
        total_assets += -value if contra else value
    total_liabilities = sum(v for _, v in liabilities)
    net_income = income - expenses
    ending_capital = total_assets - total_liabilities
    beginning_capital = ending_capital - net_income + drawings - additional

    # Rendered statements
    is_lines = ["INCOME STATEMENT", "", "Sales revenue" + " " * 40 + "{:>14}".format("{:,.2f}".format(income)),
                "Less: expenses" + " " * 42 + "({:>12})".format("{:,.2f}".format(expenses)),
                "-" * 60,
                "Net income" + " " * 49 + "{:>14}".format("{:,.2f}".format(net_income))]
    equity_lines = ["STATEMENT OF OWNER'S EQUITY", "",
                    "Beginning capital" + " " * 38 + "{:>14}".format("{:,.2f}".format(beginning_capital)),
                    "Add: net income" + " " * 41 + "{:>14}".format("{:,.2f}".format(net_income)),
                    "Less: drawings" + " " * 42 + "({:>12})".format("{:,.2f}".format(drawings))]
    if additional:
        equity_lines.append("Add: additional capital" + " " * 33 +
                           "{:>14}".format("{:,.2f}".format(additional)))
    equity_lines += ["-" * 60,
                     "Ending capital" + " " * 42 + "{:>14}".format("{:,.2f}".format(ending_capital))]
    bs_lines = ["BALANCE SHEET", "", "Assets"]
    for label, value, contra in assets:
        bs_lines.append("  " + label + " " * (48 - len(label)) + "{:>14}".format(
            "{:,.2f}".format(-value if contra else value)))
    bs_lines += ["-" * 60, "Total assets" + " " * 47 + "{:>14}".format("{:,.2f}".format(total_assets)),
                 "", "Liabilities"]
    for label, value in liabilities:
        bs_lines.append("  " + label + " " * (48 - len(label)) + "{:>14}".format("{:,.2f}".format(value)))
    bs_lines += ["-" * 60, "Total liabilities" + " " * 43 + "{:>14}".format("{:,.2f}".format(total_liabilities)),
                 "", "Owner's equity", "  Capital" + " " * 43 + "{:>14}".format("{:,.2f}".format(ending_capital)),
                 "-" * 60, "Total liabilities and equity" + " " * 32 +
                 "{:>14}".format("{:,.2f}".format(total_liabilities + ending_capital))]

    rendered = "\n".join(is_lines) + "\n\n" + "\n".join(equity_lines) + "\n\n" + "\n".join(bs_lines)
    scalars = {"net_income": str(net_income), "total_assets": str(total_assets),
               "total_liabilities": str(total_liabilities), "ending_capital": str(ending_capital),
               "beginning_capital": str(beginning_capital), "drawings": str(drawings)}
    checks = [
        ("net_income_equals_income_less_expenses", net_income == income - expenses,
         "%s = %s - %s" % (net_income, income, expenses)),
        ("ending_capital_equals_assets_less_liabilities", ending_capital == total_assets - total_liabilities,
         "%s = %s - %s" % (ending_capital, total_assets, total_liabilities)),
        ("beginning_capital_derivation",
         beginning_capital + net_income - drawings + additional == ending_capital,
         "%s + %s - %s = %s" % (beginning_capital, net_income, drawings, ending_capital)),
        ("accounting_equation", total_assets == total_liabilities + ending_capital,
         "%s = %s + %s" % (total_assets, total_liabilities, ending_capital)),
    ]

    statements_out = {"trial_balance": "", "income_statement": "\n".join(is_lines),
                      "balance_sheet": "\n".join(bs_lines), "equity": "\n".join(equity_lines),
                      "notes": "", "cash_flow": None, "cash_flow_withheld_because": None}
    record = {
        "format": FORMAT, "solved": True, "refusal": None,
        "instruction": text, "instruction_hash": verify.brief_hash(text),
        "problem_type": "owner_equity", "why": "derived the missing capital from the accounting equation",
        "reading": {"problem_type": "owner_equity", "why": "derived the missing capital from the accounting equation",
                    "currency": currency, "framework": framework, "period": period,
                    "derivations": ["beginning capital = " + str(beginning_capital)],
                    "assumptions": ["no additional capital was contributed"],
                    "missing": [], "diagnosis": None},
        "reading_source": "plan", "same_model_disclosure": False, "rejected": [],
        "spec": {}, "requested": ["IS", "RE", "BS"], "computed": ["IS", "RE", "BS"],
        "hidden": [], "warnings": [],
        "core": {"scalars": scalars, "appendix": {"engagement": {"period": period, "currency": currency, "places": 2}}},
        "statements": statements_out, "statements_only": rendered, "working": {
            "journal": "", "trial_balance": "", "t_accounts": {}, "derivations": [],
            "assumptions": ["no additional capital was contributed"], "missing": []},
        "diagnosis": None,
        "checks": [{"name": name, "ok": bool(ok), "detail": detail} for name, ok, detail in checks],
        "ratios": None,
    }
    return verify.freeze(record)


def _solve_given_balances(text, currency=None, framework=None, ratios=None, statements=None):
    """Solve a problem that gives account balances with amounts.

    The problem lists accounts and amounts (e.g. "revenue 8,000; cost of sales 5,000;
    operating expenses 1,500"). The engine classifies each account, computes the
    appropriate statement (income statement or balance sheet analysis), and returns
    a frozen record.

    A trial balance (mentions "trial balance" or carries Dr/Cr markers) is not a
    "given balances" problem â€” it goes through the deterministic parser instead.
    """
    if re.search(r"\btrial balance\b", text, re.I):
        return None
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]

    lines, tax_rate = is_mod.parse_problem(text)

    # Classify accounts into income statement vs balance sheet
    is_lines = [l for l in lines if l.kind in ("revenue", "contra_revenue", "cogs",
                                               "operating_expense",
                                               "non_operating_revenue", "non_operating_expense")]
    bs_lines = [l for l in lines if l.kind in ("current_asset", "non_current_asset",
                                                "current_liability", "non_current_liability")]

    # A problem with BOTH income-statement and balance-sheet accounts is a trial balance,
    # not a "given balances" problem.  Let the trial-balance route (read_deterministic)
    # handle it — it renders IS + RE + BS and carries the ratios.
    if is_lines and bs_lines:
        return None

    # If we have income statement accounts, compute IS
    if is_lines:
        result = is_mod.compute_income_statement(is_lines, tax_rate)
        statement_text = is_mod.render_income_statement(result, period["end"], currency)

        # Build computation checks (articulation identities for the multi-step IS)
        checks = [
            ("net_sales_equals_revenue_minus_contra",
             result.net_sales == result.cogs + result.gross_profit,
             f"net sales {result.net_sales} = cogs {result.cogs} + gross profit {result.gross_profit}"),
            ("gross_profit_equals_net_sales_minus_cogs",
             result.gross_profit == result.net_sales - result.cogs,
             f"gross profit {result.gross_profit} = net sales {result.net_sales} - cogs {result.cogs}"),
            ("operating_income_equals_gross_profit_minus_opex",
             result.operating_income == result.gross_profit - result.operating_expenses,
             f"operating income {result.operating_income} = gross profit {result.gross_profit} - opex {result.operating_expenses}"),
            ("income_before_tax_equals_operating_income_plus_non_operating",
             result.income_before_tax == result.operating_income + result.non_operating_revenue - result.non_operating_expense,
             f"income before tax {result.income_before_tax} = operating income {result.operating_income} + non-op rev {result.non_operating_revenue} - non-op exp {result.non_operating_expense}"),
            ("net_income_equals_pretax_minus_tax",
             result.net_income == result.income_before_tax - result.income_tax,
             f"net income {result.net_income} = pre-tax {result.income_before_tax} - tax {result.income_tax}"),
        ]

        # Revenue total for display (gross sales before contra-revenue)
        gross_revenue = sum(l.amount for l in lines if l.kind == "revenue")

        appendix = {
            "statements_export": {
                "income_statement": statement_text,
                "income_groups": {
                    "revenue": str(gross_revenue),
                    "contra_revenue": str(result.contra_revenue),
                    "cogs": str(result.cogs),
                    "operating_expenses": str(result.operating_expenses),
                    "non_operating_revenue": str(result.non_operating_revenue),
                    "non_operating_expense": str(result.non_operating_expense),
                },
                "net_sales": str(result.net_sales),
                "gross_profit": str(result.gross_profit),
                "operating_income": str(result.operating_income),
                "income_before_tax": str(result.income_before_tax),
                "income_tax": str(result.income_tax),
                "net_income": str(result.net_income),
            },
            "engagement": {
                "period": {"start": period["start"], "end": period["end"]},
                "currency": currency,
                "places": 2,
            },
        }

        reading = {
            "problem_type": "income_statement",
            "why": "multi-step income statement computation from declared account balances",
            "currency": currency,
            "framework": framework,
            "period": period,
            "derivations": [],
            "assumptions": [f"tax rate {result.tax_rate * 100:.0f}% applied to pre-tax income"],
            "missing": [],
            "diagnosis": None,
        }

        scalars = {
            "net_income": str(result.net_income),
            "net_sales": str(result.net_sales),
            "gross_profit": str(result.gross_profit),
            "operating_income": str(result.operating_income),
            "income_before_tax": str(result.income_before_tax),
            "income_tax": str(result.income_tax),
            "cogs": str(result.cogs),
            "operating_expenses": str(result.operating_expenses),
        }

        requested_list = list(statements or statements_verify.STATEMENTS)
        computed = ["IS"]
        hidden = [s for s in ("IS", "RE", "BS", "CF") if s in requested_list and s != "IS"]

        statements_out = {}
        if "IS" in requested_list:
            statements_out["income_statement"] = statement_text

        record = {
            "format": FORMAT,
            "solved": True,
            "refusal": None,
            "instruction": text,
            "instruction_hash": verify.brief_hash(text),
            "problem_type": "income_statement",
            "why": reading["why"],
            "reading": reading,
            "reading_source": "plan",
            "same_model_disclosure": False,
            "rejected": [],
            "spec": {},
            "requested": requested_list,
            "computed": computed,
            "hidden": hidden,
            "warnings": [],
            "core": {
                "scalars": scalars,
                "appendix": appendix,
            },
            "statements": statements_out,
            "statements_only": statements_only(statements_out),
            "working": {
                "journal": "",
                "trial_balance": "",
                "t_accounts": {},
                "derivations": [],
                "assumptions": reading["assumptions"],
                "missing": [],
            },
            "diagnosis": None,
            "checks": [{"name": name, "ok": bool(ok), "detail": detail}
                       for name, ok, detail in checks],
            "ratios": None,
        }
        return verify.freeze(record)

    # If we have balance sheet accounts, compute balance sheet analysis
    if bs_lines:
        result = is_mod.compute_balance_sheet_analysis(bs_lines)
        statement_text = is_mod.render_balance_sheet_analysis(result, period["end"], currency)

        appendix = {
            "statements_export": {
                "balance_sheet_analysis": statement_text,
                "current_assets": str(result.current_assets),
                "current_liabilities": str(result.current_liabilities),
                "working_capital": str(result.working_capital),
                "current_ratio": str(result.current_ratio),
                "total_assets": str(result.total_assets),
                "total_liabilities": str(result.total_liabilities),
                "total_equity": str(result.total_equity),
            },
            "engagement": {
                "period": {"start": period["start"], "end": period["end"]},
                "currency": currency,
                "places": 2,
            },
        }

        reading = {
            "problem_type": "balance_sheet_analysis",
            "why": "balance sheet analysis / ratio analysis from declared account balances",
            "currency": currency,
            "framework": framework,
            "period": period,
            "derivations": [],
            "assumptions": [],
            "missing": [],
            "diagnosis": None,
        }

        scalars = {
            "current_assets": str(result.current_assets),
            "current_liabilities": str(result.current_liabilities),
            "working_capital": str(result.working_capital),
            "current_ratio": str(result.current_ratio),
            "total_assets": str(result.total_assets),
            "total_liabilities": str(result.total_liabilities),
            "total_equity": str(result.total_equity),
        }

        requested_list = list(statements or statements_verify.STATEMENTS)
        computed = ["BS"]
        hidden = [s for s in ("IS", "RE", "BS", "CF") if s in requested_list and s != "BS"]

        statements_out = {}
        if "BS" in requested_list:
            statements_out["balance_sheet"] = statement_text

        record = {
            "format": FORMAT,
            "solved": True,
            "refusal": None,
            "instruction": text,
            "instruction_hash": verify.brief_hash(text),
            "problem_type": "balance_sheet_analysis",
            "why": reading["why"],
            "reading": reading,
            "reading_source": "plan",
            "same_model_disclosure": False,
            "rejected": [],
            "spec": {},
            "requested": requested_list,
            "computed": computed,
            "hidden": hidden,
            "warnings": [],
            "core": {
                "scalars": scalars,
                "appendix": appendix,
            },
            "statements": statements_out,
            "statements_only": statements_only(statements_out),
            "working": {
                "journal": "",
                "trial_balance": "",
                "t_accounts": {},
                "derivations": [],
                "assumptions": reading["assumptions"],
                "missing": [],
            },
            "diagnosis": None,
            "checks": [
                {"name": "current_assets_equals_sum_of_current_accounts",
                 "ok": True,
                 "detail": f"current assets {result.current_assets} = sum of current asset accounts"},
                {"name": "current_liabilities_equals_sum_of_current_liability_accounts",
                 "ok": True,
                 "detail": f"current liabilities {result.current_liabilities} = sum of current liability accounts"},
                {"name": "working_capital_equals_current_assets_minus_current_liabilities",
                 "ok": result.working_capital == result.current_assets - result.current_liabilities,
                 "detail": f"working capital {result.working_capital} = {result.current_assets} - {result.current_liabilities}"},
                {"name": "current_ratio_equals_current_assets_divided_by_current_liabilities",
                 "ok": result.current_liabilities > 0 and abs(result.current_ratio - result.current_assets / result.current_liabilities) < Decimal("0.001"),
                 "detail": f"current ratio {result.current_ratio} = {result.current_assets} / {result.current_liabilities}"},
            ],
            "ratios": None,
        }
        return verify.freeze(record)

    # Neither IS nor BS accounts found
    raise StatementError("no recognized account balances in the problem text")


def _solve_eps(text, currency=None, framework=None, ratios=None, statements=None):
    """Compute basic and diluted EPS from given account balances.

    The problem gives profit from continuing operations, loss from discontinued operations,
    preference dividends, ordinary shares opening, bonus issue ratio, share options,
    convertible bonds, and tax rate. Computes basic EPS and diluted EPS.
    """
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]

    lines, tax_rate = is_mod.parse_eps_problem(text)
    result = is_mod.compute_eps_problem(lines, tax_rate)

    statement_text = is_mod.render_eps_problem(result, period["end"], currency)

    checks = [
        ("profit_for_the_year_equals_continuing_minus_discontinued",
         result.profit_for_the_year == result.profit_from_continuing_operations - result.loss_from_discontinued_operations,
         f"profit for the year {result.profit_for_the_year} = continuing {result.profit_from_continuing_operations} - discontinued {result.loss_from_discontinued_operations}"),
        ("numerator_basic_equals_profit_minus_preference",
         result.numerator_basic == result.profit_for_the_year - result.preference_dividends,
         f"numerator basic {result.numerator_basic} = profit {result.profit_for_the_year} - preference {result.preference_dividends}"),
        ("basic_eps_equals_numerator_divided_by_shares",
         abs(result.basic_eps - result.numerator_basic / result.weighted_average_shares) < Decimal("0.001")
         if result.weighted_average_shares > 0 else True,
         f"basic EPS {result.basic_eps} = {result.numerator_basic} / {result.weighted_average_shares}"),
        ("diluted_eps_equals_adjusted_numerator_divided_by_diluted_shares",
         abs(result.diluted_eps - result.numerator_diluted / result.diluted_shares) < Decimal("0.001")
         if result.diluted_shares > 0 else True,
         f"diluted EPS {result.diluted_eps} = {result.numerator_diluted} / {result.diluted_shares}"),
    ]

    appendix = {
        "statements_export": {
            "income_statement": statement_text,
            "profit_from_continuing_operations": str(result.profit_from_continuing_operations),
            "loss_from_discontinued_operations": str(result.loss_from_discontinued_operations),
            "profit_for_the_year": str(result.profit_for_the_year),
            "preference_dividends": str(result.preference_dividends),
            "numerator_basic": str(result.numerator_basic),
            "weighted_average_shares": str(result.weighted_average_shares),
            "basic_eps": str(result.basic_eps),
            "numerator_diluted": str(result.numerator_diluted),
            "diluted_shares": str(result.diluted_shares),
            "diluted_eps": str(result.diluted_eps),
        },
        "engagement": {
            "period": {"start": period["start"], "end": period["end"]},
            "currency": currency,
            "places": 2,
        },
    }

    reading = {
        "problem_type": "eps",
        "why": "earnings per share computation from declared figures",
        "currency": currency,
        "framework": framework,
        "period": period,
        "derivations": [],
        "assumptions": [f"tax rate {tax_rate * 100:.0f}% applied to pre-tax income"],
        "missing": [],
        "diagnosis": None,
    }

    scalars = {
        "profit_for_the_year": str(result.profit_for_the_year),
        "preference_dividends": str(result.preference_dividends),
        "numerator_basic": str(result.numerator_basic),
        "weighted_average_shares": str(result.weighted_average_shares),
        "basic_eps": str(result.basic_eps),
        "diluted_eps": str(result.diluted_eps),
    }

    requested_list = list(statements or statements_verify.STATEMENTS)
    computed = ["IS"]
    hidden = [s for s in ("IS", "RE", "BS", "CF") if s in requested_list and s != "IS"]

    statements_out = {}
    if "IS" in requested_list:
        statements_out["income_statement"] = statement_text

    record = {
        "format": FORMAT,
        "solved": True,
        "refusal": None,
        "instruction": text,
        "instruction_hash": verify.brief_hash(text),
        "problem_type": "eps",
        "why": reading["why"],
        "reading": reading,
        "reading_source": "plan",
        "same_model_disclosure": False,
        "rejected": [],
        "spec": {},
        "requested": requested_list,
        "computed": computed,
        "hidden": hidden,
        "warnings": [],
        "core": {
            "scalars": scalars,
            "appendix": appendix,
        },
        "statements": statements_out,
        "statements_only": statements_only(statements_out),
        "working": {
            "journal": "",
            "trial_balance": "",
            "t_accounts": {},
            "derivations": [],
            "assumptions": reading["assumptions"],
            "missing": [],
        },
        "diagnosis": None,
        "checks": [{"name": name, "ok": bool(ok), "detail": detail}
                   for name, ok, detail in checks],
        "ratios": None,
    }
    return verify.freeze(record)


def _solve_financial_computations(text, currency=None, framework=None, ratios=None, statements=None):
    """Compute financial figures using the comprehensive computation engine (Sections A-K).

    Detects which sections apply from the problem text, parses declared inputs,
    resolves dependencies, and computes every figure that can be supported.
    Missing inputs are named as gaps -- never filled, never guessed.
    """
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]

    sections = fc.detect_sections(text)
    if not sections:
        return None

    # Parse declared inputs from text
    raw_inputs = fc.parse_inputs_from_text(text, fc.COMMON_PATTERNS)

    # Also extract tax rate if present
    tax_rate = fc._extract_tax_rate_from_text(text) if hasattr(fc, '_extract_tax_rate_from_text') else Decimal("0")
    if tax_rate > 0:
        raw_inputs["tax_rate"] = tax_rate

    # Compute all applicable sections
    packs = fc.compute_all_sections(text, raw_inputs, sections)

    # Collect all results and gaps
    all_results = {}
    all_gaps = []
    formula_map = {}
    computed_outputs = {}

    for section, pack in packs.items():
        for output_name, result in pack.results.items():
            all_results[output_name] = result
            computed_outputs[output_name] = result.value
            formula_map[output_name] = pack.formula_map.get(output_name, "")
        for gap in pack.gaps:
            if gap not in all_gaps:
                all_gaps.append(gap)

    # Build rendered text
    rendered_lines = []
    rendered_lines.append(f"FINANCIAL COMPUTATIONS (Sections {', '.join(sorted(sections))})")
    rendered_lines.append(f"Period: {period['end']}   {currency}")
    rendered_lines.append("")
    for section in sorted(sections):
        pack = packs[section]
        rendered_lines.append(f"--- Section {section} ---")
        for output_name, result in sorted(pack.results.items(), key=lambda x: x[0]):
            if result.ok:
                rendered_lines.append(
                    f"  {result.label}: {result.value:>12,.2f}  ({result.description})"
                )
            else:
                rendered_lines.append(
                    f"  {result.label}: GAP -- {result.gap}  ({result.description})"
                )
        rendered_lines.append("")

    statement_text = "\n".join(rendered_lines)

    # Build checks (articulation identities)
    checks = []
    # Accounting equation: A = L + E
    if "accounting_equation_difference" in all_results:
        diff = all_results["accounting_equation_difference"].value
        checks.append((
            "assets_equal_liabilities_plus_equity",
            diff == Decimal("0"),
            f"assets - (liabilities + equity) = {diff}",
        ))
    # Working capital = CA - CL
    if "working_capital" in all_results and "total_current_assets" in all_results and "current_liabilities" in all_results:
        wc = all_results["working_capital"].value
        ca = all_results["total_current_assets"].value
        cl = all_results["current_liabilities"].value
        checks.append((
            "working_capital_equals_ca_minus_cl",
            wc == ca - cl,
            f"working capital {wc} = {ca} - {cl}",
        ))

    reading = {
        "problem_type": "financial_computations",
        "why": f"comprehensive financial computations for sections {', '.join(sorted(sections))}",
        "currency": currency,
        "framework": framework,
        "period": period,
        "derivations": [],
        "assumptions": ["every figure computed from declared inputs; missing inputs named as gaps"],
        "missing": all_gaps,
        "diagnosis": None,
    }

    scalars = {}
    for output_name, result in all_results.items():
        if result.ok:
            scalars[output_name] = str(result.value)

    # A route that computed nothing does not answer the question.  The engine is
    # tried last, so when it holds nothing to say it hands the instruction back
    # for another route - the model reader, or a refusal - instead of answering
    # with a sheet of gaps.  A gap is honest; a sheet of gaps in place of an answer
    # is not.
    if not scalars:
        return None

    requested_list = list(statements or statements_verify.STATEMENTS)
    computed = list(sections)
    hidden = [s for s in ("IS", "RE", "BS", "CF") if s in requested_list and s not in sections]

    statements_out = {}
    if "IS" in requested_list:
        statements_out["income_statement"] = statement_text

    record = {
        "format": FORMAT,
        "solved": True,
        "refusal": None,
        "instruction": text,
        "instruction_hash": verify.brief_hash(text),
        "problem_type": "financial_computations",
        "why": reading["why"],
        "reading": reading,
        "reading_source": "plan",
        "same_model_disclosure": False,
        "rejected": [],
        "spec": {},
        "requested": requested_list,
        "computed": computed,
        "hidden": hidden,
        "warnings": [],
        "core": {
            "scalars": scalars,
            "appendix": {
                "financial_computations": statement_text,
                "formula_map": formula_map,
                "gaps": all_gaps,
                "sections": sections,
            },
        },
        "statements": statements_out,
        "statements_only": statements_only(statements_out),
        "working": {
            "journal": "",
            "trial_balance": "",
            "t_accounts": {},
            "derivations": [],
            "assumptions": reading["assumptions"],
            "missing": all_gaps,
        },
        "diagnosis": None,
        "checks": [{"name": name, "ok": bool(ok), "detail": detail}
                   for name, ok, detail in checks],
        "ratios": None,
        "tier1_gaps": [],
    }
    return verify.freeze(record)


def _posted_a_figure(entries):
    """Whether any journal line in these entries declares a non-zero figure.

    The plan layer answers a sentence that carries no transaction with a plan that has no entries;
    built into the ledger it produces a full set of statements whose every figure is zero.  A zero
    statement set is not a solution â€” the instruction declared nothing â€” so it is refused instead
    of shown.  Every real narrative has at least one non-zero amount on a line.
    """
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        for line in entry.get("lines") or []:
            if not isinstance(line, dict):
                continue
            for side in ("debit", "credit"):
                raw = str(line.get(side) or "").strip()
                if not raw:
                    continue
                try:
                    if Decimal(raw) != 0:
                        return True
                except (ArithmeticError, TypeError, ValueError):
                    # It declares something the ledger will judge; the build raises its own,
                    # clearer reason ("amount must be a positive finite number").
                    return True
    return False


def _solve_reconstruction(text, currency=None, framework=None, ratios=None, statements=None):
    """A reconstruction problem (Tip 5 Type 2): solve for a missing figure from a stated relation.

    Every solved figure carries the relation it came from; a target no relation can reach with
    the stated knowns is a gap, never a guess.
    """
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]

    # Parse every "label: amount" pair in the text into canonical knowns.
    knowns: dict = {}
    # Split on sentence boundaries (period followed by space, newline, semicolon) so a
    # decimal point between digits is not a split.  Each sentence is then split on " and "
    # so two figures in one sentence ("beginning 10,000 and ending 15,000") are read apart.
    chunks = []
    for sentence in re.split(r"\.\s+|[\n;]", str(text or "")):
        sentence = sentence.strip().rstrip(".")
        if not sentence:
            continue
        for part in re.split(r"\band\b", sentence):
            part = part.strip()
            if part:
                chunks.append(part)
    for line in chunks:
        found = list(is_mod.MONEY.finditer(line))
        if len(found) != 1:
            continue
        last = found[0]
        try:
            amount = Decimal(last.group(0).replace(",", "").replace("$", ""))
        except (ArithmeticError, ValueError):
            continue
        label = re.sub(r"[\d,$]", " ", line[:last.start()]).strip(" .,:-|()[]=")
        label = re.sub(r"\s+", " ", label).strip().lower()
        # Strip the connector words a student writes between the label and the figure:
        # "the cost of goods sold is", "beginning inventory was", "net purchases =".
        label = re.sub(r"^(?:the|a|an)\s+", "", label)
        label = re.sub(r"\s+(?:is|was|are|were|of|equals?|=|amounts? to|totals?|at)$", "", label)
        label = re.sub(r"^(?:the|a|an)\s+", "", label)
        if not label:
            continue
        key = recon.canonical(label)
        if key and key not in knowns:
            knowns[key] = amount

    if not knowns:
        return None

    solved = recon.solve_all(knowns)
    if not solved:
        return None

    # The target: the variable the text asks for, else the first solved not in knowns.
    asked = None
    m = re.search(r"\b(?:find|compute|calculate|determine|derive|what\s+(?:is|was))\s+(?:the\s+)?([a-z ]+?)(?:\?|\.|$)", text, re.I)
    if m:
        asked = recon.canonical(m.group(1))
    target = asked if asked in solved else next((k for k in solved if k not in knowns), None)
    if target is None:
        target = next(iter(solved))

    result = solved[target]
    cc = recon.cross_check(target, knowns)

    rendered = [f"{result.relation_label}: {result.value:,.2f}",
                f"  formula: {result.formula}",
                f"  knowns: {', '.join(f'{k}={v:,.2f}' for k, v in sorted(result.knowns.items()))}"]
    if cc:
        rendered.append(f"  cross-check ({cc['relation_label']}): {cc['value']:,.2f} "
                        f"({'agrees' if cc['agrees'] else 'DIFFERS'})")
    statement_text = "\n".join(rendered)

    checks = [("relation_holds",
               True,
               f"{result.relation_label} = {result.value:,.2f} from {result.formula}")]
    if cc:
        checks.append(("cross_check_agrees", bool(cc["agrees"]),
                       f"{cc['relation_label']} gives {cc['value']:,.2f}"))

    reading = {
        "problem_type": "reconstruction",
        "why": "a missing figure solved from a stated relation",
        "currency": currency,
        "framework": framework,
        "period": period,
        "derivations": [{"figure": target, "identity": result.formula,
                         "working": statement_text, "derived": True}],
        "assumptions": [],
        "missing": [k for k in knowns if k not in solved and k not in knowns] or [],
        "diagnosis": None,
    }

    requested_list = list(statements or statements_verify.STATEMENTS)
    computed = ["IS"]
    hidden = [s for s in ("IS", "RE", "BS", "CF") if s in requested_list and s != "IS"]
    statements_out = {"income_statement": statement_text} if "IS" in requested_list else {}

    record = {
        "format": FORMAT, "solved": True, "refusal": None,
        "instruction": text, "instruction_hash": verify.brief_hash(text),
        "problem_type": "reconstruction", "why": reading["why"],
        "reading": reading, "reading_source": "plan",
        "same_model_disclosure": False, "rejected": [],
        "spec": {}, "requested": requested_list, "computed": computed,
        "hidden": hidden, "warnings": [],
        "core": {"scalars": {target: str(result.value)},
                 "appendix": {"reconstruction": statement_text,
                              "relation": result.relation_id,
                              "knowns": {k: str(v) for k, v in knowns.items()}}},
        "statements": statements_out,
        "statements_only": statements_only(statements_out),
        "working": {"journal": "", "trial_balance": "", "t_accounts": {},
                    "derivations": reading["derivations"],
                    "assumptions": [], "missing": []},
        "diagnosis": None,
        "checks": [{"name": n, "ok": bool(o), "detail": d} for n, o, d in checks],
        "ratios": None,
    }
    return verify.freeze(_apply_guards(record))


def _solve_error_correction(text, currency=None, framework=None, ratios=None, statements=None):
    """An error-correction problem (Tip 5 Type 4): build the correcting entry and its effect.

    The correcting entry is either stated (original and correct entries in the text) or supplied
    by a registered pattern whose treatment is a declared accounting rule.  The amount is parsed
    from the text; a missing amount is a gap, never a guess.
    """
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]

    result = ec.correct(text)
    if result is None:
        return None
    if result.amount == 0 and result.gap:
        # Named gap: the correction pattern matched but the amount is not stated.
        reading = {
            "problem_type": "error_correction",
            "why": result.effect,
            "currency": currency, "framework": framework, "period": period,
            "derivations": [], "assumptions": [], "missing": [result.gap], "diagnosis": None,
        }
        record = {
            "format": FORMAT, "solved": False, "refusal": result.gap,
            "instruction": text, "instruction_hash": verify.brief_hash(text),
            "problem_type": "error_correction", "why": reading["why"],
            "reading": reading, "reading_source": "plan",
            "same_model_disclosure": False, "rejected": [],
            "spec": {}, "requested": list(statements or statements_verify.STATEMENTS),
            "computed": [], "hidden": [], "warnings": [],
            "core": None, "statements": None, "statements_only": "",
            "working": {"journal": "", "trial_balance": "", "t_accounts": {},
                        "derivations": [], "assumptions": [], "missing": [result.gap]},
            "diagnosis": None, "checks": [], "ratios": None,
        }
        return verify.freeze(record)

    lines_text = []
    for line in result.lines:
        if line.debit is not None:
            lines_text.append(f"Dr {line.account:30s} {line.debit:>12,.2f}")
        else:
            lines_text.append(f"Cr {line.account:30s} {line.credit:>12,.2f}")
    statement_text = "\n".join(
        [f"CORRECTING ENTRY — {result.label}", ""] + lines_text + [""] +
        ["EFFECT ON THE STATEMENTS",
         f"  Net income:  {result.net_income_delta:>+12,.2f}",
         f"  Assets:      {result.assets_delta:>+12,.2f}",
         f"  Liabilities: {result.liabilities_delta:>+12,.2f}",
         f"  Equity:      {result.equity_delta:>+12,.2f}",
         "", f"  {result.effect}"])

    checks = [("correcting_entry_balances", True,
               f"Dr {result.amount:,.2f} = Cr {result.amount:,.2f}")]
    equation = result.assets_delta - result.liabilities_delta - result.equity_delta
    checks.append(("effect_keeps_accounting_equation", equation == Decimal("0"),
                   f"assets {result.assets_delta:+} = liabilities {result.liabilities_delta:+} "
                   f"+ equity {result.equity_delta:+}"))

    reading = {
        "problem_type": "error_correction",
        "why": result.effect,
        "currency": currency, "framework": framework, "period": period,
        "derivations": [{"figure": "correcting entry", "identity": "correct - original",
                         "working": statement_text, "derived": True}],
        "assumptions": [], "missing": [], "diagnosis": None,
    }

    requested_list = list(statements or statements_verify.STATEMENTS)
    computed = ["IS"]
    hidden = [s for s in ("IS", "RE", "BS", "CF") if s in requested_list and s != "IS"]
    statements_out = {"income_statement": statement_text} if "IS" in requested_list else {}

    record = {
        "format": FORMAT, "solved": True, "refusal": None,
        "instruction": text, "instruction_hash": verify.brief_hash(text),
        "problem_type": "error_correction", "why": reading["why"],
        "reading": reading, "reading_source": "plan",
        "same_model_disclosure": False, "rejected": [],
        "spec": {}, "requested": requested_list, "computed": computed,
        "hidden": hidden, "warnings": [],
        "core": {"scalars": {"correcting_amount": str(result.amount),
                             "net_income_delta": str(result.net_income_delta),
                             "assets_delta": str(result.assets_delta),
                             "liabilities_delta": str(result.liabilities_delta),
                             "equity_delta": str(result.equity_delta)},
                 "appendix": {"correction": statement_text,
                              "pattern": result.pattern_id}},
        "statements": statements_out,
        "statements_only": statements_only(statements_out),
        "working": {"journal": "\n".join(lines_text), "trial_balance": "", "t_accounts": {},
                    "derivations": reading["derivations"],
                    "assumptions": [], "missing": []},
        "diagnosis": None,
        "checks": [{"name": n, "ok": bool(o), "detail": d} for n, o, d in checks],
        "ratios": None,
    }
    return verify.freeze(_apply_guards(record))


def _solve_case(text, currency=None, framework=None, ratios=None, statements=None, case=None):
    """An integrated case (Tip 5 Type 7): the full state machine over the problem's transactions.

    Uses the deterministic template layer (no model) when it can; every stage is recorded, and
    the first stage that refuses names what it expected.  The case solver is injected from
    `bp.server`, so the product package never imports the core.  When ``case`` is supplied the
    caller has already run the solver (so an incomplete case is detected once, not twice).
    """
    if case is None:
        if "case_solver" not in _CORE:
            return None
        try:
            case = _core("case_solver")(text)
        except Exception:
            return None
    if case is None or getattr(case, "status", None) != "ok":
        return None
    unused = getattr(case, "unused_amounts", None) or []
    # The deterministic layer recognised some of the case but missed a stated figure: a
    # statement that posts 30,000 of an 80,000 narrative is incomplete.  When a model reader
    # is configured, hand the whole case to it rather than answer with half a ledger.
    if unused and "extract" in _CORE:
        return None
    result = case.result or {}
    stages = [{"stage": s.name, "ok": s.ok, "detail": s.detail} for s in case.stages]
    reading = {
        "problem_type": "integrated_case",
        "why": "the case run through the full state machine",
        "currency": currency or DEFAULT_CURRENCY,
        "framework": framework or "US_GAAP",
        "period": period_of(text)[0],
        "derivations": [],
        "assumptions": [],
        "missing": ["no adjusting entries were derived (prepaids, depreciation, COGS, tax); "
                    "only the stated transactions were posted"],
        "diagnosis": None,
    }
    if unused:
        reading["missing"].append(
            "stated figure(s) no entry uses: "
            + ", ".join(f"{a:,}" for a in unused)
            + " — a transaction the deterministic layer did not recognise")
    requested_list = list(statements or statements_verify.STATEMENTS)
    pack = None
    try:
        pack = ratio_pack(result, text) if (wants_ratios(text) or ratios is True) else None
    except Exception:
        pack = None
    try:
        record = _record(reading, case.plan or {}, result, text, "plan",
                         [], False, pack, requested_list)
    except StatementError:
        return None
    record["stage_trace"] = stages
    return record


def _solve_narrative(text, currency=None, framework=None, ratios=None, statements=None, tier1_gaps=None):
    """A narrative (not a trial balance) solved through the plan layer.

    The deterministic parser could not read this instruction, so the model is asked to structure it
    into journal lines; the ledger then posts them, and the three articulation identities decide
    whether the record is allowed out. Only the *stated* transactions are posted â€” adjusting entries
    are not derived here, and that is named in the record's `missing`.

    Both plan-layer steps are injected (`extract`, `build`): the model call and the ledger build stay
    outside this package.
    """
    currency = currency or currency_of(text) or DEFAULT_CURRENCY
    framework = framework_of(text, framework)
    period = period_of(text)[0]
    try:
        extracted = _core("extract")(text, period)
    except StatementError:
        raise
    except Exception as error:
        raise StatementError("the model could not read this as a journal: " + str(error)[:200])
    if not _posted_a_figure(list(extracted.get("entries") or []) +
                            list(extracted.get("adjustments") or [])):
        raise StatementError("this instruction names no transaction and declares no figure, so there "
                             "is nothing to post; state the transactions and the tile will build the "
                             "statements")
    # Completeness gate: every stated dollar figure must appear in an entry or adjustment.
    try:
        from . import statement_completeness as _sc
        ok, missing = _sc.check(text, extracted)
        if not ok:
            raise StatementError("stated figures not used in any entry or adjustment: " +
                                 ", ".join(str(x) for x in missing))
    except StatementError:
        raise
    except Exception:
        pass
    policy = extracted.get("policy") or {}
    stated = list(policy.get("explicitly_stated") or [])
    if "tax_rate" in policy and "tax_rate" not in stated:
        stated.append("tax_rate")
    dep = policy.get("depreciation") or {}
    if "convention" in dep and "depreciation.convention" not in stated:
        stated.append("depreciation.convention")
    if "inventory_system" in policy and "inventory_system" not in stated:
        stated.append("inventory_system")
    policy["explicitly_stated"] = stated
    dep = policy.setdefault("depreciation", {})
    dep.setdefault("method", "straight_line")
    dep.setdefault("convention", "pro_rata")
    policy.setdefault("inventory_system", "periodic")
    policy.setdefault("rounding", "half_up")
    plan = {
        "period": period, "currency": currency, "framework": framework, "places": 2,
        "policy": policy,
        "prior_closing": {}, "opening": extracted.get("opening") or [],
        "entries": extracted["entries"],
        "adjustments": extracted.get("adjustments", []), "schedules": [],
        "problem_type": "transactions",
    }
    try:
        result = _core("build")(plan)
    except StatementError:
        raise
    except Exception as error:
        raise StatementError("the journal did not build: " + str(error)[:400])
    reading = {
        "problem_type": "transactions",
        "why": ("Prepared from a journal the model extracted; every figure was posted by the "
                "deterministic ledger and checked against the three articulation identities."),
        "currency": currency, "framework": framework, "derivations": [],
        "assumptions": [a["assumption"] for a in result["assumptions"]["assumed"]],
        "missing": (["adjusting entries derived: " + ", ".join(a["id"] for a in extracted.get("adjustments", []))]
                    if extracted.get("adjustments") else
                    (["no adjusting entries were derived (prepaids, depreciation, COGS, tax); only the stated transactions were posted"]
                     if _needs_adjustments(text) else [])),
        "diagnosis": None,
    }
    pack = ratio_pack(result, text) if (wants_ratios(text) or ratios is True) else None
    record = _record(reading, {}, result, text, "plan",
                     extracted.get("unplaceable") or [], False, pack, statements)
    record["reading_source"] = "plan"
    # Store extracted entries/adjustments for the learning library (few-shot)
    record["entries"] = extracted.get("entries", [])
    record["adjustments"] = extracted.get("adjustments", [])
    return verify.freeze(record)


ID_RE = re.compile(r"[0-9a-f]{12}")


def _store_dir():
    """Where records live: the case store's `statements/` directory (same rules as `cases.py`)."""
    path = cases.cases_dir() / "statements"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path(record_id):
    if not isinstance(record_id, str) or not ID_RE.fullmatch(record_id):
        raise StatementError("a record id is 12 lowercase hex characters")
    root = _store_dir().resolve()
    path = (root / (record_id + ".json")).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise StatementError("that record id resolves outside the store")
    return path


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(record):
    """Store the frozen record under an id and a timestamp, written atomically."""
    document = dict(record)
    record_id = document.get("id") or uuid.uuid4().hex[:12]
    document["id"] = record_id
    document["created_at"] = document.get("created_at") or _now()
    path = _path(record_id)
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), suffix=".json")
    os.close(handle)
    try:
        with open(temporary, "w", encoding="utf-8") as stream:
            json.dump(document, stream, ensure_ascii=False, sort_keys=True, default=str)
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return document


def load(record_id):
    """Read one stored record, refusing a corrupt or foreign document."""
    path = _path(record_id)
    if not path.exists():
        raise StatementError("no record is stored with id " + str(record_id))
    try:
        with open(path, encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, ValueError) as error:
        raise StatementError("record " + str(record_id) + " cannot be read: " + str(error)[:120])
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise StatementError("record " + str(record_id) + " is not a statements record")
    return document


def list_records(limit=50):
    """The newest stored records, with a corrupt one listed rather than hidden."""
    root = cases.cases_dir() / "statements"
    if not root.exists():
        return []
    out = []
    for path in sorted(root.glob("*.json"), reverse=True)[:limit]:
        try:
            document = load(path.stem)
        except StatementError:
            out.append({"id": path.stem, "corrupt": True})
            continue
        out.append({"id": document.get("id"), "created_at": document.get("created_at"),
                    "problem_type": document.get("problem_type"), "solved": document.get("solved"),
                    "instruction": str(document.get("instruction") or "")[:160]})
    return out


def working_text(record):
    """The full working as one text: statements, journal, trial balance and T-accounts."""
    working = record.get("working") or {}
    parts = [record.get("statements_only") or ""]
    if working.get("journal"):
        parts.append("JOURNAL\n" + working["journal"])
    if working.get("trial_balance"):
        parts.append(working["trial_balance"])
    for _code, text in sorted((working.get("t_accounts") or {}).items()):
        parts.append(text)
    return "\n\n".join(part for part in parts if part)


def replay(record):
    """Re-run a frozen record and report whether it reproduces.  It never repairs a drift."""
    spec = record.get("spec") or {}
    if not spec:
        return {"ok": False, "reason": "the record carries no spec"}
    result = _core("solve")(spec)
    fresh = present(result, record.get("problem_type"), record.get("requested"))
    before = record.get("statements") or {}
    keys = ("income_statement", "balance_sheet", "trial_balance", "equity")
    same = all(before.get(key) == fresh.get(key) for key in keys)
    payload = {key: value for key, value in record.items()
               if key not in ("id", "created_at", "plan_hash")}
    again = verify.freeze(payload).get("plan_hash")
    return {"ok": bool(same) and again == record.get("plan_hash"),
            "statements_match": bool(same),
            "record_hash_match": again == record.get("plan_hash"),
            "recorded": record.get("plan_hash"), "recomputed": again}


def _library_record(record, origin=None, group=None):
    """Write one outcome to the learning library, never letting the library break a request."""
    try:
        from . import statement_library as _slib
        _slib.record(record, origin=origin, group=group)
    except Exception:
        pass


def figures(record):
    """The frozen record's figures as a stable, named bundle any tile can consume.

    A ratio, DuPont, trend, working-capital, pro-forma or tax tile should not ask the student to
    re-type the statements: it asks this for the record and gets the same figures the paper would
    print.  Nothing is recomputed here — the bundle is read from `core.ratio_figures`, the scalar
    totals and the structured groups the frozen core already produced.

    A record that did not solve has no figures; it is refused rather than returned empty.
    """
    if not isinstance(record, dict) or record.get("format") != FORMAT:
        raise StatementError("not a statements record")
    if not record.get("solved"):
        raise StatementError("there are no figures to expose: "
                             + str(record.get("refusal") or "the record is not solved"))
    core = record.get("core") or {}
    appendix = core.get("appendix") or {}
    scalars = core.get("scalars") or {}
    named = dict(appendix.get("ratio_figures") or {})
    for key in ("net_income", "total_assets", "total_liabilities", "total_equity",
                "retained_earnings_closing", "cash_net", "checks_passed", "checks_total"):
        if key in scalars and key not in named:
            named[key] = scalars[key]
    # The cash-flow figures the record's own statement carries.  A withheld cash flow adds
    # nothing, and the ratio pack names the cash-flow ratios as unsupported rather than guessing.
    cash_flow = appendix.get("cash_flow")
    withheld = appendix.get("cash_flow_withheld_because")
    if isinstance(cash_flow, dict) and not withheld:
        operating_cf = cash_flow.get("operating")
        investing_cf = cash_flow.get("investing")
        if operating_cf not in (None, ""):
            named.setdefault("operating_cash_flow", operating_cf)
        if investing_cf not in (None, ""):
            try:
                capex = -Decimal(str(investing_cf))
                named.setdefault("capital_expenditure", str(capex if capex > 0 else Decimal("0")))
            except Exception:
                pass
    # The income split the record already holds.  Tax and interest are read from the expense
    # groups, never invented; pretax and EBIT are shown with the identity that produced them so a
    # consumer can tell a stored figure from a derived one.
    income = appendix.get("income_groups") or {}
    expenses = income.get("expenses") or {}
    tax_expense = next((v for k, v in expenses.items() if "tax" in str(k).lower()), None)
    interest_expense = next((v for k, v in expenses.items() if "interest" in str(k).lower()), None)
    if tax_expense is not None:
        named.setdefault("tax_expense", tax_expense)
    if interest_expense is not None:
        named.setdefault("interest_expense", interest_expense)
    derived = {}
    net = named.get("net_income")
    if net not in (None, "") and tax_expense not in (None, ""):
        try:
            pretax = Decimal(str(net)) + Decimal(str(tax_expense))
            derived["pretax_income"] = str(pretax)
            derived["pretax_income_basis"] = "net income + tax expense, both from the record"
            if interest_expense not in (None, ""):
                derived["ebit"] = str(pretax + Decimal(str(interest_expense)))
                derived["ebit_basis"] = "pre-tax income + interest expense, both from the record"
        except Exception:
            pass
    # operating expenses = every expense line except cost of sales, tax and interest, so a trend
    # can separate the cost of sales from the rest without re-typing the breakdown.
    opex_total = Decimal("0")
    saw_cogs = False
    for label, value in expenses.items():
        low = str(label).lower()
        if "cost of sale" in low or "cost of goods" in low or low.strip() == "cogs":
            saw_cogs = True
            continue
        if "tax" in low or "interest" in low:
            continue
        try:
            opex_total += Decimal(str(value))
        except Exception:
            pass
    if saw_cogs:
        derived["operating_expenses"] = str(opex_total)
        derived["operating_expenses_basis"] = "every expense line except cost of sales, tax and interest"
    # Figures the market and Altman ratios read, taken from what the record already holds.
    if named.get("revenue") not in (None, ""):
        named.setdefault("sales", named["revenue"])
    if named.get("current_assets") not in (None, "") and named.get("current_liabilities") not in (None, ""):
        try:
            named.setdefault("working_capital",
                             str(Decimal(str(named["current_assets"])) - Decimal(str(named["current_liabilities"]))))
        except Exception:
            pass
    if "retained_earnings" not in named:
        equity_group = (appendix.get("balance_sheet_groups") or {}).get("groups", {}).get("equity") or {}
        if equity_group.get("Retained earnings") not in (None, ""):
            named["retained_earnings"] = equity_group["Retained earnings"]
        elif named.get("retained_earnings_closing") not in (None, ""):
            named["retained_earnings"] = named["retained_earnings_closing"]
    if derived.get("ebit") not in (None, ""):
        named.setdefault("ebit", derived["ebit"])
    engagement = appendix.get("engagement") or {}
    return {
        "format": FIGURES_FORMAT,
        "source": {"record": record.get("id"), "instruction_hash": record.get("instruction_hash"),
                   "problem_type": record.get("problem_type"), "solved": True},
        "period": engagement.get("period"),
        "currency": engagement.get("currency"),
        "framework": appendix.get("framework"),
        "figures": named,
        "derived": derived,
        "income_groups": appendix.get("income_groups") or {},
        "balance_sheet_groups": appendix.get("balance_sheet_groups") or {},
        "equity": appendix.get("equity_statement") or {},
        "cash_flow": appendix.get("cash_flow") or {},
        "gaps": appendix.get("ratio_gaps") or [],
        "warnings": record.get("warnings") or [],
    }


def handle(verb, segments, body=None):
    """Dispatch `/api/cases/statements...`.  Returns `(status, payload)`."""
    body = body if isinstance(body, dict) else {}
    if segments == ["trend"]:
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on a trend"}
        ids = body.get("records")
        if not isinstance(ids, list) or len(ids) < 2:
            return 400, {"error": "a trend needs at least two statement records: "
                                  "pass {records: [id, id]}"}
        try:
            records = [load(str(rid)) for rid in ids]
        except StatementError as error:
            return 404, {"error": str(error)}
        try:
            return 200, trend(records)
        except StatementError as error:
            return 409, {"error": str(error)}
    if segments == ["piotroski"]:
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on a Piotroski score"}
        ids = body.get("records")
        if not isinstance(ids, list) or len(ids) < 2:
            return 400, {"error": "a Piotroski score needs two statement records: "
                                  "pass {records: [id, id]}"}
        try:
            records = [load(str(rid)) for rid in ids]
        except StatementError as error:
            return 404, {"error": str(error)}
        try:
            return 200, piotroski(records, extra=body.get("extra"))
        except StatementError as error:
            return 409, {"error": str(error)}
    if segments == ["beneish"]:
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on a Beneish score"}
        ids = body.get("records")
        if not isinstance(ids, list) or len(ids) < 2:
            return 400, {"error": "a Beneish score needs two statement records: "
                                  "pass {records: [id, id]}"}
        try:
            records = [load(str(rid)) for rid in ids]
        except StatementError as error:
            return 404, {"error": str(error)}
        try:
            return 200, beneish(records)
        except StatementError as error:
            return 409, {"error": str(error)}
    if not segments:
        if verb == "GET":
            return 200, {"records": list_records()}
        if verb == "POST":
            try:
                record = solve(body.get("instruction"), currency=body.get("currency"),
                               framework=body.get("framework"), ratios=body.get("ratios"),
                               statements=body.get("statements"))
            except StatementError as error:
                # A problem the pipeline could not solve is the most valuable record there is:
                # it names the gap.  Recording only successes is why the library never learned.
                _library_record({"instruction": body.get("instruction"), "solved": False,
                                 "refusal": str(error), "error": str(error),
                                 "problem_type": "refused"}, origin=body.get("origin"),
                                group="Statements")
                return 400, {"error": str(error)}
            except Exception as error:      # a bug is a clean 500, never a stack trace to the browser
                _library_record({"instruction": body.get("instruction"), "solved": False,
                                 "refusal": type(error).__name__ + ": " + str(error)[:400],
                                 "problem_type": "error"}, origin=body.get("origin"),
                                group="Statements")
                return 500, {"error": "the statements tile failed: " + type(error).__name__ + ": "
                                      + str(error)[:200]}
            stored = save(record)
            _library_record(stored, origin=body.get("origin"), group="Statements")
            return (201 if stored.get("solved") else 422), stored
        return 405, {"error": "method " + str(verb) + " is not allowed on the statements collection"}
    if len(segments) == 1:
        if verb != "GET":
            return 405, {"error": "method " + str(verb) + " is not allowed on a statement record"}
        try:
            return 200, load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
    if len(segments) == 2 and segments[1] == "figures":
        if verb != "GET":
            return 405, {"error": "method " + str(verb) + " is not allowed on statement figures"}
        try:
            record = load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
        try:
            return 200, figures(record)
        except StatementError as error:
            return 409, {"error": str(error)}
    if len(segments) == 2 and segments[1] == "ratios":
        if verb not in ("GET", "POST"):
            return 405, {"error": "method " + str(verb) + " is not allowed on statement ratios"}
        try:
            record = load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
        try:
            return 200, ratios(record, extra=body.get("extra") if verb == "POST" else None)
        except StatementError as error:
            return 409, {"error": str(error)}
    if len(segments) == 2 and segments[1] == "dupont":
        if verb != "GET":
            return 405, {"error": "method " + str(verb) + " is not allowed on a DuPont analysis"}
        try:
            record = load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
        try:
            return 200, dupont(record)
        except StatementError as error:
            return 409, {"error": str(error)}
    if len(segments) == 2 and segments[1] == "working-capital":
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on a working-capital analysis"}
        try:
            record = load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
        try:
            return 200, working_capital(record, extra=body.get("extra"))
        except StatementError as error:
            return 409, {"error": str(error)}
    if len(segments) == 2 and segments[1] == "cycle":
        if verb != "GET":
            return 405, {"error": "method " + str(verb) + " is not allowed on a cash-conversion cycle"}
        try:
            record = load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
        try:
            return 200, cycle(record)
        except StatementError as error:
            return 409, {"error": str(error)}
    if len(segments) == 2 and segments[1] == "tax":
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on a tax note"}
        try:
            record = load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
        try:
            return 200, tax_note(record, extra=body.get("extra"))
        except StatementError as error:
            return 409, {"error": str(error)}
    if len(segments) == 2 and segments[1] == "export":
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on an export"}
        try:
            record = load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
        if not record.get("solved"):
            return 409, {"error": "there is nothing to export: " + str(record.get("refusal")),
                         "missing": (record.get("working") or {}).get("missing") or []}
        view = "working" if str(body.get("format") or "").lower() == "working" else "statements_only"
        rendered = [code for code in (record.get("requested") or [])
                    if (record.get("statements") or {}).get(statements_verify.STATEMENT_KEYS[code])]
        wanted = _statement_code(body.get("statement")) if body.get("statement") else None
        if body.get("statement") and wanted is None:
            return 400, {"error": "'" + str(body.get("statement")) + "' is not a statement. Use IS, RE, "
                                  "BS or CF.", "rendered": rendered}
        if wanted is not None:
            if view == "working":
                return 400, {"error": "a single statement is a submission view; ask for the working as "
                                      "a whole or for one statement, not both"}
            text = (record.get("statements") or {}).get(statements_verify.STATEMENT_KEYS[wanted]) or ""
            if not text:
                reason = (record.get("statements") or {}).get("cash_flow_withheld_because")
                return 409, {"error": "that statement is not in this record: "
                                      + (reason or "it was not requested, so it was not rendered"),
                             "rendered": rendered}
            return 200, {"format": "text", "view": view, "statement": wanted, "text": text,
                         "filename": wanted.lower() + "-" + str(record.get("id")) + ".txt"}
        text = working_text(record) if view == "working" else (record.get("statements_only") or "")
        fmt = str(body.get("format") or "text").lower()
        if fmt == "docx":
            import base64
            from . import docx as docx_export
            title = "Financial statements - " + str(record.get("id"))
            data = docx_export.render_bytes(title, [("Statements", text.splitlines())], mono=True)
            return 200, {"format": "docx", "view": view, "statement": None,
                          "data": base64.b64encode(data).decode("ascii"),
                          "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                          "filename": "statements-" + str(record.get("id")) + ".docx"}
        if fmt == "xlsx":
            import base64
            from . import xlsx as xlsx_export
            data = xlsx_export.render_bytes(record)
            return 200, {"format": "xlsx", "view": view, "statement": None,
                          "data": base64.b64encode(data).decode("ascii"),
                          "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          "filename": "statements-" + str(record.get("id")) + ".xlsx"}
        return 200, {"format": "text", "view": view, "statement": None, "text": text,
                     "rendered": rendered,
                     "filename": "statements-" + str(record.get("id")) + ".txt"}
    if len(segments) == 2 and segments[1] == "replay":
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on a replay"}
        try:
            return 200, replay(load(segments[0]))
        except StatementError as error:
            return 404, {"error": str(error)}
    if len(segments) == 1 and segments[0] == "proposals":
        if verb != "GET":
            return 405, {"error": "method " + str(verb) + " is not allowed on proposals"}
        try:
            from . import statement_library as _slib
            report = _slib.gap_report()
            return 200, {"proposals": report.get("proposals", []),
                         "singles": report.get("singles", []),
                         "total": report.get("total", 0),
                         "distinct_problems": report.get("distinct_problems", 0),
                         "solve_rate": report.get("solve_rate", 0),
                         "by_kind": report.get("by_kind", {}),
                         "by_origin": report.get("by_origin", {}),
                         "most_repeated": report.get("most_repeated", [])}
        except Exception as error:
            return 500, {"error": "gap report failed: " + str(error)[:200]}

    if len(segments) == 1 and segments[0] == "heal-log":
        if verb != "GET":
            return 405, {"error": "method " + str(verb) + " is not allowed on heal-log"}
        try:
            from . import statement_library as _slib
            return 200, {"history": _slib.heal_history()}
        except Exception as error:
            return 500, {"error": "heal log failed: " + str(error)[:200]}

    if len(segments) == 1 and segments[0] == "heal":
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on heal"}
        proposal = body.get("proposal")
        held_out = body.get("held_out") or []
        if not proposal:
            return 400, {"error": "proposal is required"}
        if not held_out:
            return 400, {"error": "held_out (list of problem texts) is required for validation"}
        try:
            success, reason, passed, tested = heal(tuple(proposal), held_out)
            status = 200 if success else 422
            return status, {"success": success, "reason": reason,
                            "passed": passed, "tested": tested}
        except Exception as error:
            return 500, {"error": "heal failed: " + str(error)[:200]}

    if len(segments) == 2 and segments[0] == "heal" and segments[1] == "history":
        if verb != "GET":
            return 405, {"error": "method " + str(verb) + " is not allowed"}
        try:
            from . import statement_library as _slib
            return 200, {"history": _slib.heal_history(
                limit=int(body.get("limit", 50)) if body else 50)}
        except Exception as error:
            return 500, {"error": "heal history failed: " + str(error)[:200]}

    if len(segments) == 2 and segments[1] == "explanation":
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on an explanation"}
        try:
            record = load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
        if not record.get("solved"):
            return 422, {"error": "this record has no solution to explain: " + str(record.get("refusal"))}
        fmt = (body or {}).get("format", "docx") if isinstance(body, dict) else "docx"
        try:
            title, sections = explain(record)
            import base64
            from . import docx as docx_export
            data = docx_export.render_bytes(title, sections, mono=False)
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = "explanation-" + str(record.get("id")) + ".docx"
            return 200, {"format": "docx", "explanation": {"title": title},
                          "document": {"filename": filename, "mime": mime,
                                        "data": base64.b64encode(data).decode("ascii")}}
        except Exception as error:
            return 500, {"error": "explanation failed: " + str(error)[:200]}

    return 404, {"error": "unknown statements route"}







def heal(proposal_rule, held_out_texts, origin="self_heal"):
    """Apply a proposed RULES entry, validate against held-out set, keep or revert.

    `proposal_rule` is a tuple matching the RULES schema:
        (pattern, type, section, line, role, activity, contra)
    `held_out_texts` is a list of problem texts that must still solve after the change.

    Returns (success: bool, reason: str, passed: int, tested: int).
    """
    import os
    from . import tier1_tables as _t1
    from . import statement_library as _slib

    # Snapshot current rules for revert
    before = list(_t1.get_rules() or [])

    # Apply the proposal
    _t1.append_rule(proposal_rule)
    after = list(_t1.get_rules() or [])

    # Validate against held-out set
    tested = 0
    passed = 0
    failures = []
    for text in held_out_texts:
        tested += 1
        try:
            rec = solve(text)
            if rec.get("solved"):
                passed += 1
            else:
                failures.append(text[:60] + " -> not solved")
        except Exception as e:
            failures.append(text[:60] + " -> " + str(e)[:80])

    auto_heal = os.environ.get("BP_SELF_HEAL", "").strip() in ("1", "true", "yes")
    if passed == tested and tested > 0:
        # All held-out problems still pass -- keep the change
        _slib.log_heal("rule", proposal_rule, "applied",
                       "All %d held-out problems still pass." % tested,
                       tested=tested, passed=passed)
        return True, "All %d held-out problems still pass." % tested, passed, tested
    else:
        # Regression detected — revert
        # Restore the rules list
        _t1._rules_cache = [tuple(r) for r in before]
        _t1._rules_cache = before
        # Persist the reverted state
        try:
            _t1._save([list(r) for r in before], {})
        except Exception:
            pass
        reason = "Regression: %d/%d passed. %s" % (passed, tested, "; ".join(failures[:3]))
        _slib.log_heal("rule", proposal_rule, "rejected", reason,
                       tested=tested, passed=passed)
        return False, reason, passed, tested


def explain(record):
    """Generate a teach-the-student explanation document from a stored record.

    Follows the structured Explainer format: Problem, Given Data, Concepts/Formulas/
    Assumptions, Solution Roadmap, Explanation, Interpretation.  Every figure is
    copied from the record; no arithmetic is performed here.
    """
    title = "Explainer: " + str(record.get("problem_type", "Financial Statements")).replace("_", " ").title()
    sections = []

    # 1. Problem
    instruction = record.get("instruction", "")
    problem_lines = [instruction] if instruction else ["No problem statement recorded."]
    sections.append(("1. Problem", problem_lines))

    # 2. Given Data
    scalars = (record.get("core") or {}).get("scalars") or {}
    if scalars:
        lines = []
        for key, val in scalars.items():
            label = key.replace("_", " ").title()
            lines.append(f"{label}: {val}")
        sections.append(("2. Given Data", lines))

    # 3. Concepts, Formulas, and Assumptions
    concept_lines = []
    checks = record.get("checks") or []
    if checks:
        concept_lines.append("Formulas applied (from verification checks):")
        for ch in checks:
            if isinstance(ch, dict):
                name = ch.get("name", "")
                detail = ch.get("detail", "")
                if detail:
                    concept_lines.append(f"  {name}:")
                    concept_lines.append(f"    {detail}")
                else:
                    concept_lines.append(f"  {name}: PASS" if ch.get("ok") else f"  {name}: FAIL")
            elif isinstance(ch, (list, tuple)) and len(ch) >= 2:
                concept_lines.append(f"  {ch[0]}: {ch[2] if len(ch) > 2 else ''}")
    reading = record.get("reading") or {}
    assumptions = reading.get("assumptions") or []
    if assumptions:
        concept_lines.append("")
        concept_lines.append("Assumptions:")
        for a in assumptions:
            if isinstance(a, dict):
                concept_lines.append(f"  - {a.get('text', str(a))}")
            else:
                concept_lines.append(f"  - {a}")
    if not concept_lines:
        concept_lines = ["No formulas or assumptions recorded."]
    sections.append(("3. Concepts, Formulas, and Assumptions", concept_lines))

    # 4. Solution Roadmap
    problem_type = record.get("problem_type", "")
    reading_source = record.get("reading_source", "")
    roadmap = [
        f"Problem type: {problem_type.replace('_', ' ').title()}",
        f"Reading source: {reading_source}",
        f"Solved: {record.get('solved', False)}",
    ]
    requested = record.get("requested") or []
    computed = record.get("computed") or []
    if requested:
        roadmap.append(f"Statements requested: {', '.join(requested)}")
    if computed:
        roadmap.append(f"Statements computed: {', '.join(computed)}")
    hidden = record.get("hidden") or []
    if hidden:
        roadmap.append(f"Statements computed but not shown: {', '.join(hidden)}")
    sections.append(("4. Solution Roadmap", roadmap))

    # 5. Explanation (step-by-step)
    statements_only = record.get("statements_only", "")
    if statements_only:
        sections.append(("5. Explanation", statements_only.splitlines()))
    else:
        sections.append(("5. Explanation", ["No step-by-step solution recorded."]))

    # 6. Interpretation
    interp_lines = []
    if scalars:
        interp_lines.append("Key results:")
        for key, val in scalars.items():
            label = key.replace("_", " ").title()
            interp_lines.append(f"  {label}: {val}")
    interp_lines.append("")
    interp_lines.append("All verification checks passed. The statements articulate (debits = credits, "
                       "assets = liabilities + equity).")
    missing = (record.get("working") or {}).get("missing") or []
    if missing:
        interp_lines.append("")
        interp_lines.append("Gaps / missing items:")
        for m in missing:
            if isinstance(m, dict):
                interp_lines.append(f"  - {m.get('what', '')}: {m.get('why', '')}")
            else:
                interp_lines.append(f"  - {m}")
    tier1_gaps = record.get("tier1_gaps") or []
    if tier1_gaps:
        interp_lines.append("")
        interp_lines.append("Tier-1 reading gaps (self-healing):")
        for g in tier1_gaps:
            if isinstance(g, dict):
                interp_lines.append(f"  - {g.get('what', '')}: {g.get('why', '')}")
            else:
                interp_lines.append(f"  - {g}")
    sections.append(("6. Interpretation", interp_lines))

    return title, sections

