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

from . import cases
from . import verify

FORMAT = "bp-statements/1"
PROBLEM_TYPES = ("trial_balance", "transactions", "adjustments", "incomplete_records")
FRAMEWORKS = ("US_GAAP", "IFRS", "local")
DEFAULT_CURRENCY = "USD"

#: A currency or a place this product does not use.  Refused with the reason, never normalised
#: silently: the product is global and its examples are neutral (CONTRIBUTORS section 1 item 11).
BLOCKED = re.compile(r"\b(PHP|PSE|PSEi|Philippines?|Filipino|Manila)\b|\u20b1", re.I)


class StatementError(ValueError):
    """The tile cannot solve this instruction; the message is what the student is shown."""


class CoreNotAttached(StatementError):
    """`server.py` did not inject the frozen core, so the tile refuses instead of guessing."""


class StatementRefused(StatementError):
    """A reading the tile refuses outright.

    Distinct from a plain `StatementError` because no model reading can rescue it: two sets of
    balances, two periods, or a consolidation are **not one entity's one trial balance**, and asking
    a model about them would only produce a merged statement that looks right and is not.
    """


_CORE = {}


def attach_core(solve=None, diagnose=None, ratio_analysis=None, dupont=None, reader=None):
    """Attach the frozen-core callables and the optional model reader (called from `bp.server`)."""
    for name, fn in (("solve", solve), ("diagnose", diagnose), ("ratio_analysis", ratio_analysis),
                     ("dupont", dupont), ("reader", reader)):
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
    ("transactions", (r"\bstarted (with|business)\b", r"\bbought\b", r"\bsold\b", r"\bpaid\b",
                      r"\breceived\b", r"\bon credit\b", r"\bpurchased\b")),
)

#: The chart vocabulary: (label pattern, type, section, statement line, role, activity, contra).
#: Order is the ranking when a label matches more than once: the earlier rule is the literal
#: standard reading (a loan is a liability before it is capital).  A label that matches nothing is
#: reported, never guessed.
RULES = (
    (r"^(cash|bank|cash at bank|bank account|bank current account)$", "asset", "current", "Cash", "cash", "operating", False),
    (r"^(trade receivables?|receivables?|debtors?|accounts? receivable|sundry debtors)$", "asset", "current", "Trade receivables", "", "operating", False),
    (r"^(inventor(y|ies)|stock|closing stock)$", "asset", "current", "Inventory", "", "operating", False),
    (r"^(prepayments?|prepaid\b.*)$", "asset", "current", "Prepayments", "", "operating", False),
    (r"^(equipment|vehicles?|machinery|furniture|land|buildings?|plant|motor vehicles?|office equipment|freehold property)$",
     "asset", "non_current", "Property, plant and equipment", "", "investing", False),
    (r"^(accumulated depreciation\b.*|provision for depreciation\b.*)$",
     "asset", "non_current", "Property, plant and equipment", "", "investing", True),
    (r"\bloan\b", "liability", "non_current", "Borrowings", "", "financing", False),
    (r"^(trade payables?|payables?|creditors?|accounts? payable|sundry creditors)$", "liability", "current", "Trade payables", "", "operating", False),
    (r"^(accrued expenses?|accruals?|accrued\b.*)$", "liability", "current", "Accruals", "", "operating", False),
    (r"\bowner'?s?\b", "equity", "", "Capital", "capital", "financing", False),
    (r"^(capital|share capital|equity|owner'?s? capital)$", "equity", "", "Capital", "capital", "financing", False),
    (r"^(retained earnings?|accumulated (profit|earnings)|revenue reserve)$", "equity", "", "Retained earnings", "retained_earnings", "", False),
    (r"^(drawings?|dividends?)$", "equity", "", "Dividends", "dividends", "financing", False),
    (r"^(sales|revenue|turnover|fees earned|service revenue)$", "income", "", "Revenue", "", "operating", False),
    (r"\bincom(e|es)\b|\bgains?\b", "income", "", "Other income", "", "operating", False),
    (r"^(purchases?|cost of (sales|goods sold)|cogs)$", "expense", "", "Cost of sales", "", "operating", False),
    (r"^(interest (expense|paid)|finance costs?)$", "expense", "", "Finance costs", "", "operating", False),
    (r"^(rent|salaries|salary|wages|utilities|insurance|advertising|marketing|depreciation|bad debts?|general expenses|operating expenses|telephone|transport|repairs|stationery|fuel|travel)$",
     "expense", "", "Operating expenses", "", "operating", False),
    (r"\bexpenses?\b|\bcosts?\b", "expense", "", "Other expenses", "", "operating", False),
)

#: Internal chart codes.  The statements print the `line`, never the code, so these are
#: house-keeping rather than a numbering convention the student has to match.
CODE_FOR_LINE = {"Cash": "1000", "Trade receivables": "1100", "Inventory": "1200", "Prepayments": "1300",
                 "Property, plant and equipment": "1500", "Trade payables": "2000", "Accruals": "2100",
                 "Borrowings": "2200", "Capital": "3000", "Retained earnings": "3100", "Dividends": "3200",
                 "Revenue": "4000", "Other income": "4100", "Cost of sales": "5000",
                 "Operating expenses": "5100", "Finance costs": "5200", "Other expenses": "5300"}

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
    """(problem_type, cue, sentence) — the first group that fires wins, and the cue is recorded."""
    for kind, patterns in CUES:
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return kind, match.group(0), _sentence(text, match.start())
    raise StatementError("this does not read as an accounting problem I can solve: name the problem "
                         "(a trial balance, transactions, adjustments, or incomplete records) and give "
                         "the figures, and I will do the rest")


def period_of(text):
    """(period, source, quote).  A date is derived from the text; with none, the year is assumed."""
    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso:
        year = iso.group(1)
        return {"start": year + "-01-01", "end": iso.group(0)}, "derived", _sentence(text, iso.start())
    named = re.search(r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|"
                      r"october|november|december)\.?\s+(\d{4})\b", text, re.I)
    if named:
        day, month, year = int(named.group(1)), MONTHS[named.group(2).lower()], named.group(3)
        end = "%s-%02d-%02d" % (year, month, day)
        return {"start": year + "-01-01", "end": end}, "derived", _sentence(text, named.start())
    year_only = re.search(r"\b(?:year (?:ended|to)|for the year|financial year)\D{0,12}((?:19|20)\d{2})\b",
                          text, re.I)
    if year_only:
        year = year_only.group(1)
        return {"start": year + "-01-01", "end": year + "-12-31"}, "derived", _sentence(text, year_only.start())
    return {"start": "2026-01-01", "end": "2026-12-31"}, "assumed", ""


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
    for index, rule in enumerate(RULES):
        if re.search(rule[0], normalised):
            hits.append({"rule": index, "type": rule[1], "section": rule[2], "line": rule[3],
                         "role": rule[4], "activity": rule[5], "contra": rule[6]})
    return {"label": label, "normalised": normalised, "candidates": hits,
            "contested": len(hits) > 1, "placement": hits[0] if hits else None}


def parse_rows(text):
    """Every 'label ... amount' line whose label the vocabulary knows.

    The amount is the **last** numeric token on the line, so 'Loan 2026 5,000' reads as 5,000.  A
    line whose label matches no rule is returned as `skipped` with its text: it is shown in the
    working, never silently dropped.
    """
    rows, skipped = [], []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        found = list(MONEY.finditer(line))
        if not found:
            skipped.append(line)
            continue
        last = found[-1]
        amount = last.group(0)
        label = re.sub(r"\b(dr|cr)\.?\b", " ", re.sub(r"\.{2,}", " ", line[:last.start()]), flags=re.I)
        label = re.sub(r"\b(dr|cr)\.?\b", " ", label, flags=re.I).strip(" .,:-|()[]")
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
    """(key, amount) — the side a row is posted on: its marker, else its nature, then its sign."""
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
    """Every distinct period the text names: full dates, written dates, or a stated year."""
    source = str(text or "")
    ends = set()
    for match in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", source):
        ends.add(match.group(0))
    for match in re.finditer(r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|"
                             r"september|october|november|december)\.?\s+((?:19|20)\d{2})\b", source, re.I):
        ends.add("%s-%02d-%02d" % (match.group(3), MONTHS[match.group(2).lower()], int(match.group(1))))
    if not ends:
        ends = set(re.findall(r"\b(?:year (?:ended|to)|for the year|financial year)\D{0,12}((?:19|20)\d{2})\b",
                              source, re.I))
    return ends


def column_lines(text):
    """Lines that carry two figures for one account: a comparative, which this tile does not support.

    A year inside a label ("Loan 2026 5,000") is not a second figure, so year-like tokens are removed
    before the figures are counted; what remains is a label plus two amounts.
    """
    out = []
    for raw in str(text or "").splitlines():
        without_years = re.sub(r"\b(?:19|20)\d{2}\b", " ", raw)
        if len(MONEY.findall(without_years)) < 2:
            continue
        label = MONEY.sub(" ", without_years).strip(" .,:-|()[]")
        if place(label)["candidates"]:
            out.append(raw.strip())
    return out


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
    kind, cue, sentence = classify(text)
    if kind not in ("trial_balance", "adjustments", "incomplete_records"):
        raise StatementError("this reads as a " + kind.replace("_", " ") + " problem; that needs the "
                             "model reading, and none is configured")
    rows, skipped = parse_rows(text)
    if not rows:
        raise StatementError("I could not find an account with a balance in this text. Write one "
                             "account per line, as 'Cash 5,000' or 'Capital 5,000 Cr'.")
    preflight_rows(rows)
    chart = build_chart(rows)
    period, period_source, _quote = period_of(text)
    places = max([2] + [_decimals(row["written"]) for row in rows])
    reading = {
        "problem_type": kind,
        "why": "cue '" + cue + "' in: " + (sentence or cue),
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
    accounts may share a line — "Cash" and "Bank" both report as Cash — and that is a legitimate
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


def wants_ratios(text):
    """Whether the instruction asks for ratios (any cue)."""
    return any(re.search(pattern, str(text or ""), re.I) for pattern in RATIO_CUES)


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


def present(result, problem_type):
    """The statements a reader is shown, from the core's rendered text, with the cash-flow rule."""
    appendix = result.get("_appendix") or {}
    export = appendix.get("statements_export") or {}
    out = {"trial_balance": export.get("trial_balance", ""),
           "income_statement": export.get("income_statement", ""),
           "balance_sheet": export.get("balance_sheet", ""),
           "equity": appendix.get("equity_statement_export", ""),
           "notes": export.get("notes", ""),
           "cash_flow": None, "cash_flow_withheld_because": None}
    if problem_type == "transactions":
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
    rather than a silent zero — a diagnosis that quietly reads "balanced" is worse than no diagnosis.
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
    capital line — i.e. when the instruction asks for the capital.  Any other unknown is left alone,
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

def ratio_pack(result, text):
    """The ratio pack the instruction asked for: computed rows, plus every ratio named unsupported."""
    appendix = result.get("_appendix") or {}
    figures = appendix.get("ratio_figures") or {}
    if not figures or "ratio_analysis" not in _CORE:
        return None
    pack = _core("ratio_analysis")(figures)
    computed = list((pack.get("_appendix") or {}).get("ratios") or [])
    named = [{"ratio": row.get("ratio"), "reason": row.get("reason"), "needs": []}
             for row in (pack.get("_appendix") or {}).get("not_computed") or []]
    for gap in appendix.get("ratio_gaps") or []:
        if _mentioned(gap, text):
            named.append({"ratio": gap.get("ratio"), "reason": gap.get("why"),
                          "needs": gap.get("needs") or []})
    return {"requested": True, "computed": computed, "named_unsupported": named, "figures": figures}


def _record(reading, spec, result, text, source, rejected, same_model, ratios):
    """The frozen record of a solved problem: the reading, the spec, the core's output, both views."""
    appendix = result.get("_appendix") or {}
    export = appendix.get("statements_export") or {}
    statements = present(result, reading["problem_type"])
    record = {
        "format": FORMAT, "solved": True, "refusal": None,
        "instruction": text, "instruction_hash": verify.brief_hash(text),
        "problem_type": reading["problem_type"], "why": reading.get("why", ""),
        "reading": reading, "reading_source": source,
        "same_model_disclosure": bool(same_model), "rejected": rejected,
        "spec": spec,
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
    return verify.freeze(record)


def _refusal(text, reading, spec, message, source, rejected, same_model):
    """A record that says what is wrong instead of showing a number that would be wrong."""
    reading = reading or {}
    record = {
        "format": FORMAT, "solved": False, "refusal": message,
        "instruction": text, "instruction_hash": verify.brief_hash(text),
        "problem_type": reading.get("problem_type"), "why": reading.get("why", ""),
        "reading": reading, "reading_source": source,
        "same_model_disclosure": bool(same_model), "rejected": rejected,
        "spec": spec or {},
        "core": None, "statements": None, "statements_only": "",
        "working": {"journal": "", "trial_balance": "", "t_accounts": {},
                    "derivations": reading.get("derivations") or [],
                    "assumptions": reading.get("assumptions") or [],
                    "missing": reading.get("missing") or []},
        "diagnosis": reading.get("diagnosis"),
        "checks": [], "ratios": None,
    }
    return verify.freeze(record)


def solve(instruction, currency=None, framework=None, ratios=None, reader=None):
    """Solve one instruction and return a frozen record.

    The deterministic reader goes first because it is exact on a trial balance; the model reader is
    used when it cannot read the problem (a transaction list, an adjusting-entry narrative), and
    every reading — either source — passes the verifier before the core is called.
    """
    text = str(instruction or "").strip()
    if len(text) < 10:
        raise StatementError("describe the problem in at least a sentence, with its figures")
    blocked = blocked_cue(text)
    if blocked:
        raise StatementError("'" + blocked + "' is a currency or a place this product does not use. It "
                             "works in USD with neutral places: restate the figures in USD and it will "
                             "solve them.")
    reading, rows, source, rejected, same_model = None, [], "parser", [], False
    parser_error = None
    try:
        reading = read_deterministic(text, currency=currency, framework=framework)
        rows = reading.pop("_rows", []) or []
    except StatementRefused:
        raise                      # no model can rescue two sets of balances or two periods
    except StatementError as error:
        parser_error = error
        reading = None
    if reading is None:
        used = reader if reader is not None else _CORE.get("reader")
        if used is None:
            raise StatementError(str(parser_error))
        try:
            answer = used(text)
        except Exception as error:
            raise StatementError("the model reading failed (" + str(error)[:160] + "), and the "
                                 "deterministic reader could not read this either: " + str(parser_error))
        reading = answer.get("reading") if isinstance(answer, dict) else None
        if not isinstance(reading, dict):
            raise StatementError("the model returned no reading")
        source = answer.get("source") or "council"
        rejected = answer.get("rejected") or []
        same_model = bool(answer.get("same_model"))
    from . import statements_verify
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
                        source, rejected, same_model)
    pack = ratio_pack(result, text) if (wants_ratios(text) or ratios is True) else None
    return _record(reading, spec, result, text, source, rejected, same_model, pack)


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
    fresh = present(result, record.get("problem_type"))
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


def handle(verb, segments, body=None):
    """Dispatch `/api/cases/statements...`.  Returns `(status, payload)`."""
    body = body if isinstance(body, dict) else {}
    if not segments:
        if verb == "GET":
            return 200, {"records": list_records()}
        if verb == "POST":
            try:
                record = solve(body.get("instruction"), currency=body.get("currency"),
                               framework=body.get("framework"), ratios=body.get("ratios"))
            except StatementError as error:
                return 400, {"error": str(error)}
            except Exception as error:      # a bug is a clean 500, never a stack trace to the browser
                return 500, {"error": "the statements tile failed: " + type(error).__name__ + ": "
                                      + str(error)[:200]}
            stored = save(record)
            return (201 if stored.get("solved") else 422), stored
        return 405, {"error": "method " + str(verb) + " is not allowed on the statements collection"}
    if len(segments) == 1:
        if verb != "GET":
            return 405, {"error": "method " + str(verb) + " is not allowed on a statement record"}
        try:
            return 200, load(segments[0])
        except StatementError as error:
            return 404, {"error": str(error)}
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
        text = working_text(record) if view == "working" else (record.get("statements_only") or "")
        return 200, {"format": "text", "view": view, "text": text,
                     "filename": "statements-" + str(record.get("id")) + ".txt"}
    if len(segments) == 2 and segments[1] == "replay":
        if verb != "POST":
            return 405, {"error": "method " + str(verb) + " is not allowed on a replay"}
        try:
            return 200, replay(load(segments[0]))
        except StatementError as error:
            return 404, {"error": str(error)}
    return 404, {"error": "unknown statements route"}




