"""Ledger kernel, custom arm of the Stage 8 spike (manual 9.1-9.3, 9.5; decision D-006).
The journal entry is the only way money moves. An unbalanced entry cannot be constructed. Statements are pure derived views.
Management accounts and analysis only: not GAAP/IFRS-compliant statements, not assurance (manual 9.5). Nothing here is wired into the pipeline yet."""
import hashlib, json, re
from dataclasses import dataclass, field
from decimal import Decimal as D

class LedgerError(ValueError): pass
class UnbalancedEntry(LedgerError): pass
class BadAmount(LedgerError): pass
class UnknownAccount(LedgerError): pass
class OutOfPeriod(LedgerError): pass
class ChartError(LedgerError): pass

NORMAL = {"asset": "D", "expense": "D", "liability": "C", "equity": "C", "income": "C"}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
FRAMEWORKS = ("IFRS", "US_GAAP", "local")        # required input, never a default (D-010)

@dataclass(frozen=True)
class Account:
    code: str; name: str; type: str; line: str; contra: bool = False
    role: str = ""                 # "retained_earnings" | "capital" | "dividends" | "cash" | ""
    activity: str = ""             # "operating" | "investing" | "financing" | "" (cash-flow classification override; empty falls back to the type default)
    def __post_init__(self):
        if self.type not in NORMAL: raise ChartError(f"{self.code}: type must be one of {sorted(NORMAL)}")
        if not re.fullmatch(r"[A-Za-z0-9_.\-]{1,20}", self.code): raise ChartError(f"bad account code {self.code!r}")
        if self.activity not in ("", "operating", "investing", "financing"): raise ChartError(f"{self.code}: activity must be operating, investing or financing (or empty)")
        if self.role == "dividends" and self.type == "equity" and not self.contra: object.__setattr__(self, "contra", True)    # dividends normally carry a debit balance and reduce equity
    @property
    def normal(self): return ({"D": "C", "C": "D"}[NORMAL[self.type]]) if self.contra else NORMAL[self.type]

class Chart:
    def __init__(self, accounts=()):
        self.accounts = {}
        for a in accounts: self.add(a)
    def add(self, a):
        if a.code in self.accounts: raise ChartError(f"duplicate account code {a.code}")
        self.accounts[a.code] = a
    def get(self, code):
        try: return self.accounts[code]
        except KeyError: raise UnknownAccount(f"unknown account {code!r}")

@dataclass(frozen=True)
class Line:
    account: str; side: str; amount: D

def _amount(x, places):
    if isinstance(x, (float, bool)): raise BadAmount("amounts must be strings, integers or Decimals, never binary floats")
    d = D(str(x))
    if not d.is_finite() or d <= 0: raise BadAmount(f"amount must be a positive finite number, got {x!r}")
    if d != d.quantize(D(1).scaleb(-places)): raise BadAmount(f"amount {x!r} has more than {places} decimal places; the ledger never rounds silently")
    return d

@dataclass(frozen=True)
class Entry:
    date: str; description: str; lines: tuple; opening: bool = False; closing: bool = False
    def __post_init__(self):
        if not DATE.fullmatch(self.date or ""): raise LedgerError(f"date must be YYYY-MM-DD, got {self.date!r}")
        if len(self.lines) < 2: raise UnbalancedEntry("an entry needs at least two lines")
        if {l.side for l in self.lines} != {"D", "C"}: raise UnbalancedEntry("an entry needs at least one debit and one credit")
        dr = sum((l.amount for l in self.lines if l.side == "D"), D(0)); cr = sum((l.amount for l in self.lines if l.side == "C"), D(0))
        if dr != cr: raise UnbalancedEntry(f"entry '{self.description}' on {self.date} does not balance: debits {dr}, credits {cr}")
    @staticmethod
    def make(date, description, lines, places=2, opening=False, closing=False):
        """lines: [{"account": code, "debit": x} or {"credit": x}]"""
        out = []
        for l in lines:
            if ("debit" in l) == ("credit" in l): raise UnbalancedEntry("each line needs exactly one of debit or credit")
            side, x = ("D", l["debit"]) if "debit" in l else ("C", l["credit"])
            out.append(Line(l["account"], side, _amount(x, places)))
        return Entry(date, description, tuple(out), opening, closing)

def _canon(e): return json.dumps([e.date, e.description, e.opening, e.closing, [[l.account, l.side, str(l.amount)] for l in e.lines]])

class Journal:
    def __init__(self, chart, start, end, currency):
        if not (DATE.fullmatch(start) and DATE.fullmatch(end) and start <= end): raise LedgerError("period needs start <= end as YYYY-MM-DD")
        self.chart, self.start, self.end, self.currency = chart, start, end, currency; self.entries, self.hashes = [], []
    def post(self, e):
        for l in e.lines: self.chart.get(l.account)
        if not (self.start <= e.date <= self.end): raise OutOfPeriod(f"{e.date} is outside the period {self.start} to {self.end}")
        prev = self.hashes[-1] if self.hashes else ""; self.entries.append(e); self.hashes.append(hashlib.sha256((prev + _canon(e)).encode()).hexdigest())
    def verify_chain(self):
        prev = ""
        for e, h in zip(self.entries, self.hashes):
            if hashlib.sha256((prev + _canon(e)).encode()).hexdigest() != h: return False
            prev = h
        return True
    def balances(self, upto=None, include_opening=True):
        b = {c: [D(0), D(0)] for c in self.chart.accounts}
        for e in self.entries:
            if (upto and e.date > upto) or (e.opening and not include_opening): continue
            for l in e.lines: b[l.account][0 if l.side == "D" else 1] += l.amount
        return {c: (v[0], v[1]) for c, v in b.items()}
    def export_text(self):
        out = [f"; ledger {self.start} to {self.end} {self.currency}"]
        for e in self.entries:
            out.append(f"{e.date} {'(opening) ' if e.opening else ''}{e.description}")
            out += [f"  {l.account:<10} {'Dr' if l.side == 'D' else 'Cr'} {l.amount}" for l in e.lines]
        return "\n".join(out)

def natural(chart, code, d, c):
    """Signed balance on the account's normal side (negative = abnormal)."""
    a = chart.get(code); return (d - c) if a.normal == "D" else (c - d)

def trial_balance(j):
    rows, td, tc = [], D(0), D(0)
    for code, (d, c) in j.balances().items():
        net = d - c
        if net == 0: continue                                          # closed accounts and fully settled balances carry no line
        rows.append((code, j.chart.get(code).name, net if net > 0 else D(0), -net if net < 0 else D(0))); td += rows[-1][2]; tc += rows[-1][3]
    return {"rows": rows, "total_debits": td, "total_credits": tc}

def account_ledger(j, code):
    """One account as a T-account: its opening balance, every posting in date order with the
    running balance on the account's normal side, and its closing balance.

    The running balance is a *reading of the account*, not a presentation choice, so it is
    produced here rather than assembled in the page.  Closing entries are included and marked:
    a T-account that silently dropped the close would not foot to the trial balance, which is
    the whole point of being able to look at one account.

    Postings are ordered by date, keeping the journal's own order for same-date entries, so the
    running balance reads chronologically even when opening or closing entries were posted last.
    """
    a = j.chart.get(code)
    ordered = sorted(enumerate(j.entries), key=lambda t: (t[1].date, t[0]))

    # Pass 1: the opening balance, so the running balance can start from it.
    od = oc = D(0)
    for _, e in ordered:
        if not e.opening:
            continue
        for l in e.lines:
            if l.account != code:
                continue
            if l.side == "D": od += l.amount
            else: oc += l.amount
    opening = natural(j.chart, code, od, oc)

    # Pass 2: the period movements, running on from the opening balance.
    dr = cr = D(0)
    running = opening
    rows = []
    for _, e in ordered:
        if e.opening:
            continue
        for l in e.lines:
            if l.account != code:
                continue
            if l.side == "D": dr += l.amount
            else: cr += l.amount
            running += l.amount if l.side == a.normal else -l.amount
            rows.append({"date": e.date, "entry": e.description, "closing": bool(e.closing),
                         "debit": l.amount if l.side == "D" else D(0),
                         "credit": l.amount if l.side == "C" else D(0),
                         "balance": running})
    return {"code": code, "name": a.name, "type": a.type, "normal": a.normal, "contra": bool(a.contra),
            "opening_debit": od, "opening_credit": oc, "opening_balance": opening,
            "movements": rows, "movement_debits": dr, "movement_credits": cr,
            "closing_balance": running,
            "closing_debits": od + dr, "closing_credits": oc + cr}

def account_ledgers(j):
    """Every account's T-account, in chart order."""
    return [account_ledger(j, code) for code in j.chart.accounts]

def journal_view(j):
    """The journal as data: every entry in posting order, with each line named and sided.

    This is the audit trail the statements, the trial balance and the T-accounts are all derived
    from.  Each entry carries its hash so a reader can see the chain that `verify_chain` checks,
    and each entry carries its own debit and credit totals so a line that did not balance could
    never be shown as though it had.
    """
    if len(j.entries) != len(j.hashes):
        raise LedgerError("journal and hash chain are different lengths")
    out = []
    for e, h in zip(j.entries, j.hashes):
        lines = []
        for l in e.lines:
            a = j.chart.get(l.account)
            lines.append({"account": l.account, "name": a.name, "side": l.side,
                          "debit": l.amount if l.side == "D" else D(0),
                          "credit": l.amount if l.side == "C" else D(0)})
        out.append({"date": e.date, "description": e.description,
                    "opening": bool(e.opening), "closing": bool(e.closing),
                    "lines": lines,
                    "debits": sum((x["debit"] for x in lines), D(0)),
                    "credits": sum((x["credit"] for x in lines), D(0)),
                    "hash": h})
    return out

def _signed(chart, code, d, c):
    """Contribution of an account to its statement section: contra accounts reduce the section they sit in."""
    a = chart.get(code); n = natural(chart, code, d, c); return -n if a.contra else n

def statements(j):
    ch = j.chart; sect = {"income": {}, "expense": {}, "asset": {}, "liability": {}, "equity": {}}
    for code, (d, c) in j.balances().items():
        if _signed(ch, code, d, c) == 0: continue                      # zero net contribution (includes closed accounts)
        a = ch.get(code); sect[a.type][a.line] = sect[a.type].get(a.line, D(0)) + _signed(ch, code, d, c)
    tot = lambda k: sum(sect[k].values(), D(0)); ni = tot("income") - tot("expense")
    return {"income": sect["income"], "expenses": sect["expense"], "net_income": ni, "assets": sect["asset"], "liabilities": sect["liability"], "equity": sect["equity"],
            "total_assets": tot("asset"), "total_liabilities": tot("liability"), "total_equity": tot("equity"), "equity_with_current_earnings": tot("equity") + ni}

def _sum_type(j, types, include_opening=True, role=None, only_opening=False):
    t = D(0)
    for e in j.entries:
        if (e.opening and not include_opening) or (only_opening and not e.opening): continue
        for l in e.lines:
            a = j.chart.get(l.account)
            if a.type in types and (role is None or a.role == role):
                signed = l.amount if l.side == a.normal else -l.amount      # movement on the account's normal side
                t += -signed if a.contra else signed
    return t

# ---------- Cash flow statement by two routes (manual 9.2, 9.3; PROVISIONAL pending the manual) ----------
TYPE_ACTIVITY = {"income": "operating", "expense": "operating", "asset": "investing", "liability": "financing", "equity": "financing"}
PRIORITY = ("operating", "investing", "financing")

def cash_flow(j, st=None):
    """Two independent computations of the period's cash movement, which must agree:
    route A (direct) classifies each entry's cash delta by its non-cash counterpart activity; route B (indirect) derives
    the same total from net income and the changes in non-cash assets, liabilities and non-earnings equity.
    Cash accounts are identified by role 'cash'. Opening entries are excluded (they are prior-period balances).
    Classification rule (declared): a counterpart account's explicit `activity` tag wins; otherwise its type defaults
    (income/expense operating, asset investing, liability/equity financing). Entries whose counterparts mix activities are
    classified operating-first and flagged; cash-to-cash transfers are flagged and carry no activity."""
    st = st or statements(j)
    op = inv = fin = D(0); fl = []; detail = []
    def is_cash(l): return j.chart.get(l.account).role == "cash"
    for e in j.entries:
        if e.opening: continue
        dr = sum((l.amount for l in e.lines if l.side == "D" and is_cash(l)), D(0))
        cr = sum((l.amount for l in e.lines if l.side == "C" and is_cash(l)), D(0))
        if dr == 0 and cr == 0: continue
        acts = {j.chart.get(l.account).activity or TYPE_ACTIVITY[j.chart.get(l.account).type] for l in e.lines if not is_cash(l)}
        if len(acts) > 1: fl.append({"kind": "mixed_classification", "entry": e.description, "detail": f"counterpart activities {sorted(acts)}; classified by the operating-first priority rule"})
        if not acts: fl.append({"kind": "cash_to_cash_transfer", "entry": e.description, "detail": "cash moved between cash accounts; no activity recorded"})
        net = dr - cr
        if "operating" in acts: kind, op = "operating", op + net
        elif "investing" in acts: kind, inv = "investing", inv + net
        else: kind, fin = "financing", fin + net
        if net != 0: detail.append({"date": e.date, "description": e.description, "activity": kind, "amount": net})
    d_cash = _sum_type(j, ("asset",), include_opening=False, role="cash")
    d_nca = _sum_type(j, ("asset",), include_opening=False) - d_cash
    indirect = st["net_income"] + _sum_type(j, ("equity",), include_opening=False) + _sum_type(j, ("liability",), include_opening=False) - d_nca
    direct = op + inv + fin
    return {"operating": op, "investing": inv, "financing": fin, "net_direct": direct, "net_indirect": indirect, "detail": detail,
            "checks": [("cash_flow_agrees_across_routes", direct == indirect, f"direct {direct}, indirect {indirect}")], "flags": fl}

# ---------- Period-end closing and the retained-earnings rollforward (manual 9.3; B-034, B-046) ----------
def closing_entries(j, st=None):
    """Generate the period-end closing entries (dated j.end): income balances close to retained earnings, expense balances
    close against it, and declared dividends close against it. The caller posts them; the kernel never posts silently.
    Accounts with an abnormal balance among the closed types block (a human decision is required)."""
    st = st or statements(j)
    re_codes = [c for c, a in j.chart.accounts.items() if a.type == "equity" and a.role == "retained_earnings"]
    if not re_codes: raise LedgerError("closing needs a retained earnings account (role 'retained_earnings')")
    re_code = re_codes[0]
    inc, exp, divs, bad = [], [], [], []
    for code, (d, c) in j.balances().items():
        a = j.chart.get(code); n = natural(j.chart, code, d, c)
        if n == 0: continue
        if n < 0: bad.append(f"{code} ({a.name})")
        if a.type == "income": inc.append({"account": code, "debit": str(n)})
        elif a.type == "expense": exp.append({"account": code, "credit": str(n)})
        elif a.role == "dividends": divs.append({"account": code, "credit": str(n)})   # dividends carry a debit balance and reduce equity
    if bad: raise LedgerError("closing with abnormal balances needs a human decision (flags(j) reports them): " + ", ".join(bad))
    out = []
    if inc: out.append({"date": j.end, "description": "closing: income to retained earnings", "closing": True,
                        "lines": inc + [{"account": re_code, "credit": str(sum((D(l["debit"]) for l in inc), D(0)))}]})
    if exp: out.append({"date": j.end, "description": "closing: expenses to retained earnings", "closing": True,
                        "lines": [{"account": re_code, "debit": str(sum((D(l["credit"]) for l in exp), D(0)))}] + exp})
    if divs: out.append({"date": j.end, "description": "closing: dividends to retained earnings", "closing": True,
                         "lines": [{"account": re_code, "debit": str(sum((D(l["credit"]) for l in divs), D(0)))}] + divs})
    return out

def retained_earnings_rollforward(j, st_pre=None):
    """The manual 9.3 rollforward, meaningful now that closing entries exist: closing retained earnings must equal opening
    retained earnings plus the pre-closing net income, minus declared dividends, plus any direct (non-opening, non-closing)
    postings to retained earnings. Also checks that closing zeroed the income, expense and dividend accounts."""
    st_pre = st_pre or statements(j)
    def re_natural(entries):
        t = D(0)
        for e in entries:
            for l in e.lines:
                a = j.chart.get(l.account)
                if a.type == "equity" and a.role == "retained_earnings":
                    t += l.amount if l.side == a.normal else -l.amount
        return t
    opening_re = re_natural([e for e in j.entries if e.opening])
    direct_re = re_natural([e for e in j.entries if not e.opening and not e.closing])
    closing_re = re_natural(j.entries)
    divs = D(0)
    for e in j.entries:
        if e.opening or e.closing: continue
        for l in e.lines:
            a = j.chart.get(l.account)
            if a.role == "dividends": divs += l.amount if l.side == a.normal else -l.amount
    expect = opening_re + st_pre["net_income"] - divs + direct_re
    res = [("retained_earnings_rollforward", closing_re == expect, f"closing {closing_re}, expected {expect}")]
    open_after = []
    for code, (d, c) in j.balances().items():
        a = j.chart.get(code)
        if (a.type in ("income", "expense") or a.role == "dividends") and natural(j.chart, code, d, c) != 0: open_after.append(code)
    res.append(("income_expense_and_dividends_zero_after_closing", not open_after, f"still open: {open_after}" if open_after else "all closed"))
    return res

def closing_balances(j):
    """Natural closing balance of every account, for the next period's prior_closing argument."""
    return {c: natural(j.chart, c, d, cr) for c, (d, cr) in j.balances().items() if d or cr}

def opening_lines(j):
    """Lines for the next period's opening entry: each account's closing balance on its natural side. An abnormal balance
    (negative natural) is carried on the opposite side with a positive amount; flags(j) reports it separately."""
    lines = []
    for code, (d, c) in j.balances().items():
        a = j.chart.get(code); n = natural(j.chart, code, d, c)
        if n == 0: continue
        if n > 0: lines.append({"account": code, ("debit" if a.normal == "D" else "credit"): str(n)})
        else: lines.append({"account": code, ("credit" if a.normal == "D" else "debit"): str(-n)})
    return lines

def check_invariants(j, st, prior_closing=None):
    """Independent recomputation from the journal lines, compared with the derived statements (manual 9.3). Returns [(name, ok, detail)].
    Retained-earnings rollforward is deliberately absent: with one period and no closing entries it would be a tautology."""
    tb = trial_balance(j); res = []
    res.append(("trial_balance_debits_equal_credits", tb["total_debits"] == tb["total_credits"], f"{tb['total_debits']} vs {tb['total_credits']}"))
    res.append(("assets_equal_liabilities_plus_equity", st["total_assets"] == st["total_liabilities"] + st["equity_with_current_earnings"], f"{st['total_assets']} vs {st['total_liabilities'] + st['equity_with_current_earnings']}"))
    ni_a = _sum_type(j, ("income",)) - _sum_type(j, ("expense",))                                    # route A: income and expense movements in the journal
    ni_b = None
    if any(e.opening for e in j.entries):                                                             # route B: change in net assets less all equity movements other than earnings
        d_na = (_sum_type(j, ("asset",)) - _sum_type(j, ("liability",))) - (_sum_type(j, ("asset",), only_opening=True) - _sum_type(j, ("liability",), only_opening=True))
        eq_moves = _sum_type(j, ("equity",), include_opening=False)       # every non-earnings equity movement: capital, dividends, direct postings to retained earnings
        ni_b = d_na - eq_moves
    res.append(("net_income_agrees_across_routes", st["net_income"] == ni_a and (ni_b is None or ni_b == st["net_income"]),
                f"statements {st['net_income']}, journal {ni_a}" + (f", balance-sheet route {ni_b}" if ni_b is not None else "; no opening balances, so the second route is unavailable")))
    if prior_closing is not None:
        ob = {}
        for e in j.entries:
            if e.opening:
                for l in e.lines: ob[l.account] = ob.get(l.account, D(0)) + (l.amount if l.side == j.chart.get(l.account).normal else -l.amount)
        bad = sorted(c for c, v in prior_closing.items() if ob.get(c, D(0)) != D(str(v)))
        res.append(("opening_balances_equal_prior_closing", not bad, f"differences in {bad}" if bad else "all agree"))
    foot = (sum(st["assets"].values(), D(0)) == st["total_assets"] and sum(st["liabilities"].values(), D(0)) == st["total_liabilities"]
            and sum(st["income"].values(), D(0)) - sum(st["expenses"].values(), D(0)) == st["net_income"])
    res.append(("statement_lines_foot_to_totals", foot, "ok" if foot else "a statement total differs from its lines"))
    res.append(("journal_hash_chain_intact", j.verify_chain(), "ok"))
    return res

CONTRA_WORDS = re.compile(r"accumulated|allowance|provision|less:", re.I)

def flags(j):
    """Judgment items no invariant can catch (manual 9, 9.4): listed for confirmation, never silently fixed."""
    out = []; ch = j.chart
    for code, (d, c) in j.balances().items():
        a = ch.get(code); n = natural(ch, code, d, c)
        if n < 0: out.append({"kind": "abnormal_balance", "account": code, "detail": f"{a.name} has a {'credit' if a.normal == 'D' else 'debit'} balance, opposite to its normal side; check the sign of the entries or the account type"})
        if CONTRA_WORDS.search(a.name) and not a.contra: out.append({"kind": "possible_misclassified_contra", "account": code, "detail": f"{a.name} looks like a contra or valuation account but is not marked contra"})
    months = sorted({e.date[:7] for e in j.entries if not e.opening}); seen = {}
    for e in j.entries:
        if e.opening: continue
        for l in e.lines:
            if l.side == "D" and ch.get(l.account).type == "expense": seen.setdefault(l.account, set()).add(e.date[:7])
    if len(months) >= 3:
        last = months[-1]
        for code, ms in seen.items():
            if last not in ms and len([m for m in months[:-1][-3:] if m in ms]) >= 2: out.append({"kind": "possible_missing_accrual", "account": code, "detail": f"{ch.get(code).name} appears in earlier months but not in {last}; check for an unrecorded accrual"})
    return out

def require_framework(f):
    if f not in FRAMEWORKS: raise LedgerError(f"reporting framework is a required input and has no default; choose one of {list(FRAMEWORKS)}")
    return f
