"""Schedule engines for the Stage 8 ledger increment (manual 9.2, 9.3): declarative specs that generate balanced journal
lines for straight-line depreciation, loan amortization and accruals. All amounts are Decimal with explicit places; the
ledger never rounds silently, so each schedule declares how a non-divisible remainder is absorbed:
- depreciation: the final period absorbs the rounding remainder, so the schedule sums exactly to cost minus residual;
- amortization: interest rounds half-even to the currency places, and a payment never exceeds the balance due — the
  final payment absorbs the remainder and the schedule ends early if a fixed payment clears the loan sooner;
  without a payment the level annuity is rounded UP so the loan pays off within the term;
- accrual: a constant amount per period.
The generated lines are posted through the ledger kernel (ledger.py), which enforces balancing, account existence, period
bounds and the hash chain. Management accounts and analysis only: not GAAP/IFRS-compliant statements (manual 9.5)."""
import calendar, re
from decimal import Decimal as D, ROUND_HALF_EVEN, ROUND_CEILING

class ScheduleError(ValueError): pass

MONTH = re.compile(r"\d{4}-\d{2}")
ACCT = re.compile(r"[A-Za-z0-9_.\-]{1,20}")

def _dec(x, what="amount"):
    if isinstance(x, (float, bool)): raise ScheduleError(f"{what} must be a string, integer or Decimal, never a binary float")
    d = D(str(x))
    if not d.is_finite(): raise ScheduleError(f"{what} must be finite, got {x!r}")
    return d

def _places(n):
    if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= 6: raise ScheduleError("places must be a whole number from 0 to 6")
    return n

def _check_places(d, places, what):
    if d != d.quantize(D(1).scaleb(-places)): raise ScheduleError(f"{what} {d} has more than {places} decimal places; the ledger never rounds silently")

def _month_end(ym, i):
    """Last day of the month i periods after 'YYYY-MM'."""
    y, m = map(int, ym.split("-")); m += i
    y += (m - 1) // 12; m = (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"

def _codes(spec, names):
    for name in names:
        code = spec.get(name)
        if not (isinstance(code, str) and ACCT.fullmatch(code)): raise ScheduleError(f"{name} must be a valid account code")

def _common(spec):
    places = _places(spec.get("places", 2)); start = spec.get("start")
    if not (MONTH.fullmatch(start or "")): raise ScheduleError("start must be YYYY-MM")
    return places, start

_DEPRECIATION_METHODS = ("straight_line", "reducing_balance", "units_of_production")

def depreciation(spec):
    """Depreciation by the method the owner declares: `straight_line` (default), `reducing_balance`
    or `units_of_production`.

    Every method produces the same shape - one Dr expense / Cr accumulated-depreciation entry per
    period - and every method guarantees the same two things: the charge never takes the carrying
    amount below the declared residual, and the schedule sums exactly to cost minus residual (the
    final charge absorbs the rounding remainder).

    Only `straight_line` supports `changes` (a prospective revision of life and/or residual): the
    other two methods have no defined meaning for a revised life, so they refuse it rather than
    silently ignore it.
    """
    method = spec.get("method", "straight_line")
    if method not in _DEPRECIATION_METHODS:
        raise ScheduleError(f"depreciation method must be one of {list(_DEPRECIATION_METHODS)}")
    if method == "straight_line":
        return _depreciation_straight_line(spec)
    if spec.get("changes"):
        raise ScheduleError("policy changes are only supported by the straight_line method")
    if method == "reducing_balance":
        return _depreciation_reducing_balance(spec)
    return _depreciation_units(spec)

def _depreciation_reducing_balance(spec):
    """Reducing-balance depreciation: each period charges a declared rate against the carrying
    amount, never pushing it below the residual, and the final period takes the remainder.

    The rate is a per-period proportion (0 < rate < 1); it is declared, never derived, because the
    choice of rate is the owner's estimate and not a fact the engine can discover.
    """
    cost = _dec(spec.get("cost"), "cost"); residual = _dec(spec.get("residual"), "residual")
    rate = _dec(spec.get("rate"), "rate"); life = spec.get("life")
    places, start = _common(spec)
    if isinstance(life, bool) or not isinstance(life, int) or life < 1: raise ScheduleError("life must be a whole number of at least one period")
    if cost <= 0: raise ScheduleError("cost must be positive")
    if residual < 0 or residual >= cost: raise ScheduleError("residual must be between zero and the cost")
    if not (0 < rate < 1): raise ScheduleError("rate must be a per-period proportion between zero and one")
    _check_places(cost, places, "cost"); _check_places(residual, places, "residual")
    _codes(spec, ("dep_account", "accum_account"))
    q = D(1).scaleb(-places); out = []; carrying = cost
    for period in range(1, life + 1):
        if period == life:
            amount = carrying - residual
        else:
            amount = (carrying * rate).quantize(q, rounding=ROUND_HALF_EVEN)
            if carrying - amount < residual: amount = carrying - residual
        if amount < 0: amount = D(0)
        if amount == 0 and carrying > residual:
            raise ScheduleError("the depreciation per period rounds to zero; the amount is too small for the declared places")
        out.append({"date": _month_end(start, period - 1), "description": spec.get("description", "depreciation"),
                    "lines": [{"account": spec["dep_account"], "debit": str(amount)}, {"account": spec["accum_account"], "credit": str(amount)}]})
        carrying -= amount
    return out

def _depreciation_units(spec):
    """Units-of-production depreciation: the depreciable amount is spread over declared total units
    and each period charges its own usage.

    `units_per_period` is one entry per period. Charges are rounded to the declared places, and the
    last period **that uses any units** absorbs the rounding remainder, so the schedule still sums
    exactly to cost minus residual without dumping the remainder into a period with no production.
    """
    cost = _dec(spec.get("cost"), "cost"); residual = _dec(spec.get("residual"), "residual")
    total_units = _dec(spec.get("total_units"), "total_units"); units = spec.get("units_per_period")
    places, start = _common(spec)
    if cost <= 0: raise ScheduleError("cost must be positive")
    if residual < 0 or residual >= cost: raise ScheduleError("residual must be between zero and the cost")
    if total_units <= 0: raise ScheduleError("total_units must be positive")
    if not isinstance(units, list) or not units: raise ScheduleError("units_per_period must be a non-empty list, one entry per period")
    per = []
    for i, u in enumerate(units):
        v = _dec(u, f"units_per_period[{i}]")
        if v < 0: raise ScheduleError(f"units_per_period[{i}] must not be negative")
        per.append(v)
    used = sum(per, D(0))
    if used > total_units: raise ScheduleError("units_per_period sums to more than total_units")
    last_used = max((i for i, u in enumerate(per) if u > 0), default=None)
    if last_used is None: raise ScheduleError("at least one period must declare units above zero")
    _check_places(cost, places, "cost"); _check_places(residual, places, "residual")
    _codes(spec, ("dep_account", "accum_account"))
    depreciable = cost - residual; q = D(1).scaleb(-places); out = []; charged = D(0)
    for i, u in enumerate(per):
        if i == last_used:
            amount = depreciable - charged
        else:
            amount = (depreciable * u / total_units).quantize(q, rounding=ROUND_HALF_EVEN)
        out.append({"date": _month_end(start, i), "description": spec.get("description", "depreciation"),
                    "lines": [{"account": spec["dep_account"], "debit": str(amount)}, {"account": spec["accum_account"], "credit": str(amount)}]})
        charged += amount
    return out

def _depreciation_straight_line(spec):
    """Straight-line depreciation: one Dr expense / Cr accumulated-depreciation entry per period. An optional `changes`
    list applies a declared PROSPECTIVE revision of useful life and/or residual value from a period onward (a change in
    accounting estimate): earlier periods keep the old amount, and the remaining carrying amount is spread over the
    revised remaining life. The final period absorbs the rounding remainder so the schedule sums exactly to
    cost minus the final residual. Retrospective restatement is not implemented."""
    cost = _dec(spec.get("cost"), "cost"); residual = _dec(spec.get("residual"), "residual"); life = spec.get("life")
    places, start = _common(spec)
    if isinstance(life, bool) or not isinstance(life, int) or life < 1: raise ScheduleError("life must be a whole number of at least one period")
    if cost <= 0: raise ScheduleError("cost must be positive")
    if residual < 0 or residual >= cost: raise ScheduleError("residual must be between zero and the cost")
    _check_places(cost, places, "cost"); _check_places(residual, places, "residual")
    _codes(spec, ("dep_account", "accum_account"))
    chs = []
    for c in spec.get("changes") or []:
        at, new_life = c.get("at_period"), c.get("life")
        if isinstance(at, bool) or not isinstance(at, int) or at < 1: raise ScheduleError("a policy change needs a whole at_period of at least one")
        if isinstance(new_life, bool) or not isinstance(new_life, int) or new_life < 1: raise ScheduleError("a policy change needs a whole new life of at least one")
        r2 = _dec(c.get("residual", residual), "change residual"); _check_places(r2, places, "change residual")
        if r2 < 0 or r2 >= cost: raise ScheduleError("a change residual must be between zero and the cost")
        chs.append({"at_period": at, "life": new_life, "residual": r2})
    chs.sort(key=lambda c: c["at_period"])
    segs = []; life_cur, resid_cur, seg_start, ci = life, residual, 1, 0
    while True:
        seg_end = (chs[ci]["at_period"] - 1) if ci < len(chs) else life_cur
        if seg_end > life_cur: raise ScheduleError("a policy change falls after the current useful life ends")
        if seg_end < seg_start: raise ScheduleError("a policy change leaves no periods to depreciate before it")
        segs.append((seg_start, seg_end, life_cur, resid_cur))
        if ci >= len(chs): break
        c = chs[ci]
        if c["at_period"] < 2: raise ScheduleError("a policy change must take effect after at least one period")
        life_cur, resid_cur, seg_start = c["life"], c["residual"], c["at_period"]
        if life_cur < seg_start: raise ScheduleError("a policy change leaves no periods to depreciate after it")
        ci += 1
    out = []; charged = D(0); last_k = len(segs) - 1; resid_final = segs[-1][3]
    for k, (s, e, life_k, resid_k) in enumerate(segs):
        if cost - charged - resid_k <= 0: raise ScheduleError("a policy change leaves nothing to depreciate")
        rem = life_k - (s - 1); per = ((cost - charged - resid_k) / rem).quantize(D(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
        if per == 0 and e > s: raise ScheduleError("the depreciation per period rounds to zero; the amount is too small for the declared places")
        for period in range(s, e + 1):
            amount = (cost - charged - resid_final) if (k == last_k and period == e) else per
            out.append({"date": _month_end(start, period - 1), "description": spec.get("description", "depreciation"),
                        "lines": [{"account": spec["dep_account"], "debit": str(amount)}, {"account": spec["accum_account"], "credit": str(amount)}]})
            charged += amount
    return out

def amortization(spec):
    """Loan amortization: one Dr interest / Dr loan / Cr cash entry per period; the final payment absorbs the balance."""
    principal = _dec(spec.get("principal"), "principal"); rate = _dec(spec.get("rate"), "rate"); term = spec.get("term")
    ppy = spec.get("periods_per_year", 12); places, start = _common(spec)
    if isinstance(term, bool) or not isinstance(term, int) or term < 1: raise ScheduleError("term must be a whole number of at least one period")
    if isinstance(ppy, bool) or not isinstance(ppy, int) or ppy < 1: raise ScheduleError("periods_per_year must be a positive whole number")
    if principal <= 0: raise ScheduleError("principal must be positive")
    if not 0 <= rate <= 1: raise ScheduleError("rate must be between zero and one")
    _check_places(principal, places, "principal")
    _codes(spec, ("cash_account", "loan_account", "interest_account"))
    r = rate / ppy; payment = spec.get("payment")
    if payment is not None:
        P = _dec(payment, "payment"); _check_places(P, places, "payment")
    else:
        P = (principal / term) if r == 0 else principal * r / (1 - (1 + r) ** (-term))
        P = P.quantize(D(1).scaleb(-places), rounding=ROUND_CEILING)    # declared rule: the level annuity rounds up
    out, bal = [], principal
    for i in range(term):
        interest_i = (bal * r).quantize(D(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
        pay = min(P, bal + interest_i)                     # a payment never exceeds the balance due: the final payment absorbs the remainder, and the schedule ends early if the fixed payment clears the loan sooner
        if pay < interest_i: raise ScheduleError("the payment does not cover the interest in a period")
        principal_i = pay - interest_i
        if principal_i <= 0 and bal > 0: raise ScheduleError("the payment does not reduce the principal")
        out.append({"date": _month_end(start, i), "description": spec.get("description", "loan payment"),
                    "lines": [{"account": spec["interest_account"], "debit": str(interest_i)}, {"account": spec["loan_account"], "debit": str(principal_i)}, {"account": spec["cash_account"], "credit": str(pay)}]})
        bal -= principal_i
        if bal == 0: break
    if bal != 0: raise ScheduleError(f"the loan is not fully repaid after {term} periods (remaining {bal}); increase the payment")
    return out

def accrual(spec):
    """Straight accrual: one Dr expense / Cr accrued-liability entry per period."""
    amount = _dec(spec.get("amount"), "amount"); periods = spec.get("periods"); places, start = _common(spec)
    if isinstance(periods, bool) or not isinstance(periods, int) or periods < 1: raise ScheduleError("periods must be a whole number of at least one")
    if amount <= 0: raise ScheduleError("amount must be positive")
    _check_places(amount, places, "amount")
    _codes(spec, ("expense_account", "accrual_account"))
    return [{"date": _month_end(start, i), "description": spec.get("description", "accrual"),
             "lines": [{"account": spec["expense_account"], "debit": str(amount)}, {"account": spec["accrual_account"], "credit": str(amount)}]} for i in range(periods)]
