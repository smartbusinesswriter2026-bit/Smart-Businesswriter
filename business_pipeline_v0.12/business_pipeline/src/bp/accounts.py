"""Declarative layer for the Stage 8 ledger (manual 9.1-9.3): a JSON-serializable engagement spec that builds a chart,
posts the declared opening balances, entries and schedules into the ledger kernel, closes the period, and returns the
statements, trial balance, two-route cash flow, every check and the human-review flags. The spec is data; the kernel
never posts anything the owner did not declare. Declared policy changes (a change in an accounting estimate) apply
prospectively from their date and are disclosed in the appendix. Management accounts only: not GAAP/IFRS statements
(manual 9.5)."""
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
_POLICY_KINDS = ("useful_life_revision", "residual_value_revision", "disclosure")

def _at_period(start, date):
    """1-based period index of `date` within a schedule starting at `start` (YYYY-MM)."""
    y1, m1 = map(int, start.split("-")); y2, m2 = map(int, date[:7].split("-"))
    return (y2 - y1) * 12 + (m2 - m1) + 1

def _schedule_changes(spec):
    """Map the declared policy changes onto their schedules as prospective schedule revisions (life and/or residual)."""
    out = {}
    for c in spec.get("policy_changes") or []:
        if not isinstance(c, dict) or c.get("kind") not in ("useful_life_revision", "residual_value_revision"): continue
        s = spec["schedules"][c["schedule"]]
        rec = {"at_period": _at_period(s["start"], c["date"]),
               "life": c["life"] if c["kind"] == "useful_life_revision" else s["life"],
               "residual": c.get("residual", s.get("residual", "0"))}
        out.setdefault(c["schedule"], []).append(rec)
    return out

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
        try: s2["changes"] = _schedule_changes(spec).get(i, [])
        except (KeyError, IndexError, TypeError, ValueError): s2["changes"] = []
        try: es = getattr(schedules, kind)(s2)
        except schedules.ScheduleError as e: errs.append(f"schedules[{i}]: {e}"); continue
        for j, e in enumerate(es):
            for l in e["lines"]:
                if l["account"] not in codes: errs.append(f"schedules[{i}] uses unknown account {l['account']}")
    pcs = spec.get("policy_changes")
    if pcs is not None:
        if not isinstance(pcs, list): errs.append("policy_changes must be a list")
        else:
            sched_list = spec.get("schedules") or []
            end = (p or {}).get("end") if isinstance(p, dict) else None
            for i, c in enumerate(pcs):
                tag = f"policy_changes[{i}]"
                if not isinstance(c, dict): errs.append(f"{tag} must be an object"); continue
                if not ledger.DATE.fullmatch(str(c.get("date", "")) or ""): errs.append(f"{tag} date must be YYYY-MM-DD")
                elif start and end and not (start <= c["date"] <= end): errs.append(f"{tag} date is outside the period")
                if c.get("treatment") != "prospective": errs.append(f"{tag} treatment must be 'prospective' (retrospective restatement is not implemented)")
                if not isinstance(c.get("description"), str) or not c["description"].strip(): errs.append(f"{tag} description is required")
                kind = c.get("kind")
                if kind not in _POLICY_KINDS: errs.append(f"{tag} kind must be one of {list(_POLICY_KINDS)}"); continue
                if kind == "disclosure": continue
                idx = c.get("schedule")
                if isinstance(idx, bool) or not isinstance(idx, int) or not (0 <= idx < len(sched_list)): errs.append(f"{tag} schedule must be the index of a schedules entry"); continue
                if not isinstance(sched_list[idx], dict) or sched_list[idx].get("kind") != "depreciation": errs.append(f"{tag} only a depreciation schedule can carry this change"); continue
                if kind == "useful_life_revision" and not (isinstance(c.get("life"), int) and not isinstance(c.get("life"), bool) and c["life"] > 0): errs.append(f"{tag} life must be a positive whole number")
                if kind == "residual_value_revision":
                    try: r = D(str(c.get("residual")))
                    except Exception: errs.append(f"{tag} residual is required"); continue
                    if not r.is_finite() or r < 0: errs.append(f"{tag} residual must not be negative")
    rec = spec.get("reconciliation")
    if rec is not None:
        if not isinstance(rec, dict): errs.append("reconciliation must be an object with an account and a statement")
        else:
            if rec.get("account") not in codes: errs.append(f"reconciliation account {rec.get('account')!r} is not in the chart")
            errs += [f"reconciliation: {e}" for e in reconcile.validate_statement(rec.get("statement"))]
    return errs

def account_mapping(spec):
    """The account-mapping table for the second mandatory checkpoint (manual 9.3): every chart account with its type,
    statement line, role, activity tag and contra flag, plus the mapping checks the owner confirms before anything is
    posted. Raises EngagementError when the spec does not validate."""
    errs = validate_spec(spec)
    if errs: raise EngagementError("; ".join(errs))
    chart = ledger.Chart([ledger.Account(**a) for a in spec["chart"]])
    rows = [{"code": a.code, "name": a.name, "type": a.type, "line": a.line, "role": a.role, "activity": a.activity, "contra": a.contra} for a in chart.accounts.values()]
    unmapped = [a.code for a in chart.accounts.values() if not str(a.line).strip()]
    cash = [a.code for a in chart.accounts.values() if a.role == "cash"]
    re_acc = [a.code for a in chart.accounts.values() if a.type == "equity" and a.role == "retained_earnings"]
    checks = [("every_account_maps_to_a_statement_line", not unmapped, "unmapped: " + ", ".join(unmapped) if unmapped else "all accounts map to a statement line"),
              ("at_least_one_cash_account", bool(cash), "cash accounts: " + ", ".join(cash) if cash else "no account is tagged role cash"),
              ("exactly_one_retained_earnings_account", len(re_acc) == 1, "retained earnings accounts: " + ", ".join(re_acc) if re_acc else "no retained earnings account")]
    return {"rows": rows, "checks": checks, "framework": spec["framework"]}

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
    by_sched = _schedule_changes(spec)
    for i, s in enumerate(spec.get("schedules", [])):
        s2 = dict(s); kind = s2.pop("kind"); s2["changes"] = by_sched.get(i, [])
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
    notes = [{"date": c["date"], "kind": c["kind"], "description": c["description"], "treatment": c["treatment"],
              "applied_prospectively": c["kind"] != "disclosure"} for c in (spec.get("policy_changes") or [])]
    if notes: extra["policy_changes"] = notes
    return {**scalars, "_appendix": extra, "_checks": checks}
