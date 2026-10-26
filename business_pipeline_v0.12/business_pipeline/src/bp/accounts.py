"""Declarative layer for the Stage 8 ledger (manual 9.1-9.3): a JSON-serializable engagement spec that builds a chart,
posts the declared opening balances, entries and schedules into the ledger kernel, closes the period, and returns the
statements, trial balance, two-route cash flow, every check and the human-review flags. The spec is data; the kernel
never posts anything the owner did not declare. Management accounts only: not GAAP/IFRS-compliant statements (manual 9.5)."""
from decimal import Decimal as D
from . import ledger, schedules, reconcile

class EngagementError(ValueError): pass

EXAMPLE_SPEC = {
    "period": {"start": "2026-01-01", "end": "2026-03-31"}, "currency": "USD", "framework": "local", "places": 2,
    "chart": [{"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash"},
              {"code": "3000", "name": "Owner capital", "type": "equity", "line": "Capital", "role": "capital"},
              {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"},
              {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"},
              {"code": "5000", "name": "Rent", "type": "expense", "line": "Rent"}],
    "prior_closing": {"1000": "5000", "3000": "5000"},
    "opening": [{"lines": [{"account": "1000", "debit": "5000"}, {"account": "3000", "credit": "5000"}]}],
    "entries": [{"date": "2026-01-15", "description": "sale", "lines": [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}]},
                {"date": "2026-02-28", "description": "rent", "lines": [{"account": "5000", "debit": "500"}, {"account": "1000", "credit": "500"}]},
                {"date": "2026-03-31", "description": "deposit in transit", "lines": [{"account": "1000", "debit": "150"}, {"account": "4000", "credit": "150"}]}],
    "schedules": [],
    "reconciliation": {"account": "1000", "statement": {"opening_balance": "5000", "closing_balance": "6475", "lines": [
        {"date": "2026-01-15", "description": "sale deposit", "amount": "2000", "direction": "in"},
        {"date": "2026-02-28", "description": "rent cheque", "amount": "500", "direction": "out"},
        {"date": "2026-03-31", "description": "bank charge", "amount": "25", "direction": "out"}]}},
}

_KINDS = ("depreciation", "amortization", "accrual")

def _s(x):
    if isinstance(x, D): return str(x)
    if isinstance(x, dict): return {k: _s(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [_s(v) for v in x]
    return x

def _line_errs(tag, line, codes):
    errs = []
    if not isinstance(line, dict) or not isinstance(line.get("account"), str): errs.append(f"{tag} line must be an object with an account code")
    elif line["account"] not in codes: errs.append(f"{tag} uses unknown account {line['account']}")
    if not (("debit" in line) ^ ("credit" in line)): errs.append(f"{tag} line needs exactly one of debit or credit")
    return errs

def _entry_errs(tag, e, places, codes, default_date=None):
    if not isinstance(e, dict): return [f"{tag} must be an object with date, description and lines"]
    errs = []; date = e.get("date") or default_date
    if not ledger.DATE.fullmatch(str(date or "")): errs.append(f"{tag} date must be YYYY-MM-DD")
    lines = e.get("lines")
    if not isinstance(lines, list) or not lines: errs.append(f"{tag} needs at least two lines")
    else:
        for i, l in enumerate(lines): errs += _line_errs(f"{tag} lines[{i}]", l, codes)
        try: ledger.Entry.make(str(date or "2026-01-01"), str(e.get("description", "")), lines, places)
        except ledger.LedgerError as ex: errs.append(f"{tag}: {ex}")
    return errs

def validate_spec(spec):
    """Return a list of actionable errors; empty means the spec can build. """
    if not isinstance(spec, dict): return ["spec must be an object"]
    errs = []
    p = spec.get("period")
    if not isinstance(p, dict) or not ledger.DATE.fullmatch(str(p.get("start", "") or "")) or not ledger.DATE.fullmatch(str(p.get("end", "") or "")) or str(p.get("start", "")) > str(p.get("end", "")):
        errs.append("period must have start <= end as YYYY-MM-DD")
    if not isinstance(spec.get("currency"), str) or not spec["currency"].strip(): errs.append("currency is required")
    try: ledger.require_framework(spec.get("framework"))
    except ledger.LedgerError as e: errs.append(str(e))
    places = spec.get("places", 2)
    if isinstance(places, bool) or not isinstance(places, int) or not 0 <= places <= 6: errs.append("places must be a whole number from 0 to 6")
    chart, codes = spec.get("chart"), set()
    if not isinstance(chart, list) or not chart: errs.append("chart must be a non-empty list of accounts")
    else:
        for i, a in enumerate(chart):
            if not isinstance(a, dict): errs.append(f"chart[{i}] must be an object"); continue
            try: acc = ledger.Account(**a)
            except (ledger.ChartError, TypeError) as e: errs.append(f"chart[{i}]: {e}"); continue
            if acc.code in codes: errs.append(f"chart[{i}]: duplicate account code {acc.code}")
            codes.add(acc.code)
        if not any(isinstance(a, dict) and a.get("type") == "equity" and a.get("role") == "retained_earnings" for a in chart):
            errs.append("the chart needs a retained earnings account (equity with role 'retained_earnings')")
    pc = spec.get("prior_closing")
    if not isinstance(pc, dict): errs.append("prior_closing must be an object of account code -> natural closing balance ({} for a first period)")
    for tag, lst in (("opening", spec.get("opening")), ("entries", spec.get("entries")), ("schedules", spec.get("schedules"))):
        if not isinstance(lst, list): errs.append(f"{tag} must be a list")
    start = (p or {}).get("start") if isinstance(p, dict) else None
    for i, e in enumerate(spec.get("opening") or []): errs += _entry_errs(f"opening[{i}]", e, places, codes, default_date=start)
    for i, e in enumerate(spec.get("entries") or []): errs += _entry_errs(f"entries[{i}]", e, places, codes)
    for i, s in enumerate(spec.get("schedules") or []):
        if not isinstance(s, dict) or s.get("kind") not in _KINDS: errs.append(f"schedules[{i}] needs a kind in {list(_KINDS)}"); continue
        s2 = dict(s); kind = s2.pop("kind")
        try: es = getattr(schedules, kind)(s2)
        except schedules.ScheduleError as e: errs.append(f"schedules[{i}]: {e}"); continue
        for j, e in enumerate(es):
            for l in e["lines"]:
                if l["account"] not in codes: errs.append(f"schedules[{i}] uses unknown account {l['account']}")
    rec = spec.get("reconciliation")
    if rec is not None:
        if not isinstance(rec, dict): errs.append("reconciliation must be an object with an account and a statement")
        else:
            if rec.get("account") not in codes: errs.append(f"reconciliation account {rec.get('account')!r} is not in the chart")
            errs += [f"reconciliation: {e}" for e in reconcile.validate_statement(rec.get("statement"))]
    return errs

def build(spec):
    """Run the engagement: validate, build the chart and journal, post opening + entries + schedules, close the period,
    and return scalar outputs plus a serialized appendix (statements, trial balance, cash flow, checks, flags, export)."""
    errs = validate_spec(spec)
    if errs: raise EngagementError("; ".join(errs))
    p, places, cur = spec["period"], spec.get("places", 2), spec["currency"]
    chart = ledger.Chart([ledger.Account(**a) for a in spec["chart"]])
    j = ledger.Journal(chart, p["start"], p["end"], cur); n_posted = 0
    for e in spec.get("opening", []):
        j.post(ledger.Entry.make(p["start"], e.get("description", "opening"), e["lines"], places, opening=True)); n_posted += 1
    for e in spec.get("entries", []):
        j.post(ledger.Entry.make(e["date"], e["description"], e["lines"], places)); n_posted += 1
    for s in spec.get("schedules", []):
        s2 = dict(s); kind = s2.pop("kind")
        for e in getattr(schedules, kind)(s2):
            j.post(ledger.Entry.make(e["date"], e["description"], e["lines"], places)); n_posted += 1
    pre = ledger.statements(j)
    for e in ledger.closing_entries(j, pre):
        j.post(ledger.Entry.make(e["date"], e["description"], e["lines"], places, closing=e["closing"])); n_posted += 1
    st = ledger.statements(j); cf = ledger.cash_flow(j, st)
    checks = ledger.check_invariants(j, st, spec.get("prior_closing")) + cf["checks"] + ledger.retained_earnings_rollforward(j, pre)
    re_code = next(c for c, a in chart.accounts.items() if a.type == "equity" and a.role == "retained_earnings")
    flags = ledger.flags(j) + cf["flags"]
    rec = spec.get("reconciliation")
    if rec:
        r = reconcile.reconcile(j, rec["account"], rec["statement"])
        checks = checks + r["checks"]; flags = flags + r["flags"]; rec_report = _s(r["report"])
    else:
        checks = checks + [("statement_internally_consistent", True, "no reconciliation was supplied"),
                           ("opening_balances_agree", True, "no reconciliation was supplied")]
        rec_report = None
    na = 0 if rec else 2     # checks that were not applicable rather than passed
    scalars = {"net_income": pre["net_income"], "total_assets": st["total_assets"], "total_liabilities": st["total_liabilities"], "total_equity": st["equity_with_current_earnings"],
               "retained_earnings_closing": ledger.closing_balances(j).get(re_code, D(0)), "cash_net": cf["net_direct"],
               "checks_passed": D(sum(1 for _, ok, _ in checks if ok) - na), "checks_total": D(len(checks)), "checks_na": D(na),
               "n_entries": D(n_posted), "n_flags": D(len(flags))}
    extra = {"framework": spec["framework"], "statements": _s(st), "trial_balance": _s(ledger.trial_balance(j)), "cash_flow": _s(cf),
             "checks": _s(checks), "flags": flags, "closing_balances": _s(ledger.closing_balances(j)), "export": j.export_text()}
    if rec_report is not None: extra["reconciliation"] = rec_report
    return {**scalars, "_appendix": extra, "_checks": checks}
