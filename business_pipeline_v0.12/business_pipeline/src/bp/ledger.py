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
    date: str; description: str; lines: tuple; opening: bool = False
    def __post_init__(self):
        if not DATE.fullmatch(self.date or ""): raise LedgerError(f"date must be YYYY-MM-DD, got {self.date!r}")
        if len(self.lines) < 2: raise UnbalancedEntry("an entry needs at least two lines")
        if {l.side for l in self.lines} != {"D", "C"}: raise UnbalancedEntry("an entry needs at least one debit and one credit")
        dr = sum((l.amount for l in self.lines if l.side == "D"), D(0)); cr = sum((l.amount for l in self.lines if l.side == "C"), D(0))
        if dr != cr: raise UnbalancedEntry(f"entry '{self.description}' on {self.date} does not balance: debits {dr}, credits {cr}")
    @staticmethod
    def make(date, description, lines, places=2, opening=False):
        """lines: [{"account": code, "debit": x} or {"credit": x}]"""
        out = []
        for l in lines:
            if ("debit" in l) == ("credit" in l): raise UnbalancedEntry("each line needs exactly one of debit or credit")
            side, x = ("D", l["debit"]) if "debit" in l else ("C", l["credit"])
            out.append(Line(l["account"], side, _amount(x, places)))
        return Entry(date, description, tuple(out), opening)

def _canon(e): return json.dumps([e.date, e.description, e.opening, [[l.account, l.side, str(l.amount)] for l in e.lines]])

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
        if net == 0 and d == 0: continue
        rows.append((code, j.chart.get(code).name, net if net > 0 else D(0), -net if net < 0 else D(0))); td += rows[-1][2]; tc += rows[-1][3]
    return {"rows": rows, "total_debits": td, "total_credits": tc}

def _signed(chart, code, d, c):
    """Contribution of an account to its statement section: contra accounts reduce the section they sit in."""
    a = chart.get(code); n = natural(chart, code, d, c); return -n if a.contra else n

def statements(j):
    ch = j.chart; sect = {"income": {}, "expense": {}, "asset": {}, "liability": {}, "equity": {}}
    for code, (d, c) in j.balances().items():
        if d == 0 and c == 0: continue
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
    op = inv = fin = D(0); fl = []
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
        if "operating" in acts: op += net
        elif "investing" in acts: inv += net
        else: fin += net
    d_cash = _sum_type(j, ("asset",), include_opening=False, role="cash")
    d_nca = _sum_type(j, ("asset",), include_opening=False) - d_cash
    indirect = st["net_income"] + _sum_type(j, ("equity",), include_opening=False) + _sum_type(j, ("liability",), include_opening=False) - d_nca
    direct = op + inv + fin
    return {"operating": op, "investing": inv, "financing": fin, "net_direct": direct, "net_indirect": indirect,
            "checks": [("cash_flow_agrees_across_routes", direct == indirect, f"direct {direct}, indirect {indirect}")], "flags": fl}

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
