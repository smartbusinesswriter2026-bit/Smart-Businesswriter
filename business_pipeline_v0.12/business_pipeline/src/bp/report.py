"""Accountant-facing statement exports for the Stage 8 ledger (manual 9.5): plain-text trial balance, income statement,
balance sheet, cash flow statement, reconciliation and notes, rendered from the journal and its derived statements.
The text is deterministic (fixed-width columns, thousands separators, parentheses for negative values, the accounting
convention) and can be downloaded from the workbench. Management accounts only: not GAAP/IFRS statements and not
assurance (manual 9.5)."""
from decimal import Decimal as D
from . import ledger

def _num(v, places=2):
    s = f"{abs(v):,.{places}f}"
    return f"({s})" if v < 0 else s

def _row(label, value, places=2, width=46):
    return f"{label[:width]:<{width}}{_num(value, places):>20}"

def t_account(lg, places=2):
    """One account as a readable T-account: opening balance, dated postings with a running
    balance, the movement, and the closing balance.

    The numbers are rendered exactly as `ledger.account_ledger` computed them; nothing is
    recalculated here. A closing entry is marked, because a reader who sees the income and
    expense accounts go to zero deserves to know why.
    """
    out = [f"ACCOUNT {lg['code']} {lg['name']}", f"  {lg['type']}, normal side {'debit' if lg['normal'] == 'D' else 'credit'}"
                                                 + (", contra" if lg.get("contra") else "")]
    out.append(_row("  Opening balance", lg["opening_balance"], places))
    if not lg["movements"]:
        out.append("  no movement in the period")
    for r in lg["movements"]:
        mark = " (closing)" if r.get("closing") else ""
        out.append(f"  {r['date']}  Dr {_num(r['debit'], places):>16}  Cr {_num(r['credit'], places):>16}"
                   f"  balance {_num(r['balance'], places):>16}{mark}  {r['entry'][:40]}")
    out.append(_row("  Movement, debits less credits", lg["movement_debits"] - lg["movement_credits"], places))
    out.append(_row("  Closing balance", lg["closing_balance"], places))
    return "\n".join(out)

def t_accounts(ledgers, places=2):
    """Every account's T-account, separated by a blank line."""
    return "\n\n".join(t_account(lg, places) for lg in ledgers)

def statement_of_equity(eq, places=2):
    """The statement of changes in equity as text: per account, opening, each movement with its kind,
    and closing, then the totals.

    Nothing is recalculated here. The per-account identity (opening + movements = closing) is the point
    of the statement, so it is printed in a form a reader can check line by line.
    """
    out = ["STATEMENT OF CHANGES IN EQUITY"]
    for row in eq["accounts"]:
        out.append(f"{row['code']} {row['name']}")
        out.append(_row("  Opening balance", row["opening"], places))
        if not row["movements"]:
            out.append("  no movement in the period")
        for m in row["movements"]:
            mark = " (closing)" if m.get("closing_entry") else ""
            out.append(f"  {m['date']}  {m['kind'][:22]:<22}{_num(m['amount'], places):>16}  {m['description'][:34]}{mark}")
        out.append(_row("  Closing balance", row["closing"], places))
        out.append("")
    out.append(_row("Total opening", eq["total_opening"], places))
    out.append(_row("Total movement", eq["total_movement"], places))
    out.append(_row("Total closing", eq["total_closing"], places))
    return "\n".join(out)

def journal(j, places=2):
    """The journal as text: each entry with its lines, and the entry's own debit and credit totals.

    Opening and closing entries are marked. The totals are printed so an entry that did not
    balance could not be read as though it had, even though the kernel refuses to post one.
    """
    out = [f"JOURNAL  {j.start} to {j.end}  {j.currency}"]
    for row in ledger.journal_view(j):
        tag = " (opening)" if row["opening"] else (" (closing)" if row["closing"] else "")
        out.append(f"{row['date']}  {row['description']}{tag}")
        for l in row["lines"]:
            side = "Dr" if l["side"] == "D" else "Cr"
            amount = l["debit"] if l["side"] == "D" else l["credit"]
            out.append(f"    {l['account']:<8} {l['name'][:34]:<34} {side} {_num(amount, places):>16}")
        out.append(f"    {'':<8} {'entry totals':<34} Dr {_num(row['debits'], places):>13}"
                   f"  Cr {_num(row['credits'], places):>13}")
    return "\n".join(out)

def _money(v, currency, places=2):
    s = f"{abs(v):,.{places}f}"
    return f"{currency} ({s})" if v < 0 else f"{currency} {s}"

def trial_balance(j, places=2):
    tb = ledger.trial_balance(j)
    out = ["TRIAL BALANCE", f"{j.start} to {j.end}   {j.currency}", f"{'Code':<6}{'Account':<40}{'Debit':>20}{'Credit':>20}"]
    for code, name, d, c in tb["rows"]:
        out.append(f"{code:<6}{name[:40]:<40}{_num(d, places) if d else '':>20}{_num(c, places) if c else '':>20}")
    out.append(f"{'':<46}{_num(tb['total_debits'], places):>20}{_num(tb['total_credits'], places):>20}")
    return "\n".join(out)

def income_statement(pre, j, places=2):
    inc, exp = pre["income"], pre["expenses"]
    out = ["INCOME STATEMENT", f"{j.start} to {j.end}   {j.currency}", "Revenue"]
    out += [_row("  " + k, inc[k], places) for k in sorted(inc)]
    out.append(_row("Total revenue", sum(inc.values(), D(0)), places))
    out.append("Expenses")
    out += [_row("  " + k, exp[k], places) for k in sorted(exp)]
    out.append(_row("Total expenses", sum(exp.values(), D(0)), places))
    out.append(_row("Net income", pre["net_income"], places))
    oci = pre.get("oci") or {}
    if oci:
        out.append("Other comprehensive income")
        out += [_row("  " + k, oci[k], places) for k in sorted(oci)]
        out.append(_row("Total other comprehensive income", pre["total_oci"], places))
        out.append(_row("Total comprehensive income", pre["total_comprehensive_income"], places))
    return "\n".join(out)

def balance_sheet(j, st, places=2):
    """The balance sheet. When the chart declares current/non-current sections it is presented in those
    sections with subtotals; otherwise the flat layout is kept, so a specification that has not adopted
    the split produces exactly the statement it produced before."""
    bs = ledger.balance_sheet_groups(j)
    if not bs["classified"]:
        return _balance_sheet_flat(j, st, places)
    out = ["BALANCE SHEET", f"As at {j.end}   {j.currency}"]
    t = bs["totals"]
    for key, title, total_label in (
            ("current_assets", "Current assets", "Total current assets"),
            ("non_current_assets", "Non-current assets", "Total non-current assets"),
            ("unclassified_assets", "Assets (no section declared)", "Total unclassified assets")):
        group = bs["groups"][key]
        if not group: continue
        out.append(title)
        for label, v in group.items():
            out.append(_row(f"  {label}", v, places))
        out.append(_row(total_label, t[key], places))
    out.append(_row("Total assets", t["current_assets"] + t["non_current_assets"] + t["unclassified_assets"], places))
    for key, title, total_label in (
            ("current_liabilities", "Current liabilities", "Total current liabilities"),
            ("non_current_liabilities", "Non-current liabilities", "Total non-current liabilities"),
            ("unclassified_liabilities", "Liabilities (no section declared)", "Total unclassified liabilities")):
        group = bs["groups"][key]
        if not group: continue
        out.append(title)
        for label, v in group.items():
            out.append(_row(f"  {label}", v, places))
        out.append(_row(total_label, t[key], places))
    out.append(_row("Total liabilities",
                    t["current_liabilities"] + t["non_current_liabilities"] + t["unclassified_liabilities"], places))
    out.append("Equity")
    for label, v in bs["groups"]["equity"].items():
        out.append(_row(f"  {label}", v, places))
    out.append(_row("Total equity", t["equity"], places))
    out.append(_row("Total liabilities and equity", st["total_liabilities"] + st["equity_with_current_earnings"], places))
    return "\n".join(out)

def _balance_sheet_flat(j, st, places=2):
    out = ["BALANCE SHEET", f"As at {j.end}   {j.currency}"]
    for sect, title in (("asset", "Assets"), ("liability", "Liabilities"), ("equity", "Equity")):
        out.append(title); total = D(0)
        for code, (d, c) in j.balances().items():
            a = j.chart.get(code)
            if a.type != sect: continue
            n = ledger.natural(j.chart, code, d, c)
            if n == 0: continue
            v = -n if a.contra else n                      # contra accounts reduce the section they sit in
            out.append(_row(f"  {a.name}", v, places)); total += v
        out.append(_row(f"Total {title.lower()}", total, places))
    out.append(_row("Total liabilities and equity", st["total_liabilities"] + st["equity_with_current_earnings"], places))
    return "\n".join(out)

def cash_flow_statement(j, cf, places=2):
    cash_open = D(0)
    for e in j.entries:
        if not e.opening: continue
        for l in e.lines:
            a = j.chart.get(l.account)
            if a.role == "cash": cash_open += l.amount if l.side == a.normal else -l.amount
    out = ["CASH FLOW STATEMENT", f"{j.start} to {j.end}   {j.currency}"]
    for key, title in (("operating", "Operating activities"), ("investing", "Investing activities"), ("financing", "Financing activities")):
        out.append(title)
        for d in cf["detail"]:
            if d["activity"] == key: out.append(_row(f"  {d['date']}  {d['description']}", d["amount"], places))
        out.append(_row(f"Total {title.lower()}", cf[key], places))
    out.append(_row("Net change in cash", cf["net_direct"], places))
    out.append(_row("Cash at start of period", cash_open, places))
    out.append(_row("Cash at end of period", cash_open + cf["net_direct"], places))
    return "\n".join(out)

def reconciliation_statement(rec_report, places=2):
    r = rec_report
    out = [f"RECONCILIATION (account {r['account']})", "Balance per statement"]
    out += [_row("Balance per statement", r["statement_closing"], places),
            _row("Add: receipts in transit", r["receipts_in_transit"], places),
            _row("Less: outstanding payments", -r["payments_outstanding"], places),
            _row("Adjusted statement balance", r["adjusted_statement"], places),
            "Balance per ledger",
            _row("Balance per ledger", r["ledger_balance"], places),
            _row("Add: unrecorded receipts", r["unrecorded_receipts"], places),
            _row("Less: unrecorded payments", -r["unrecorded_payments"], places),
            _row("Adjusted ledger balance", r["adjusted_ledger"], places),
            _row("Difference", r["difference"], places),
            f"Matched lines: {len(r['matched'])}; in transit: {len(r['books_only'])}; unrecorded: {len(r['statement_only'])}"]
    return "\n".join(out)

def notes(j, framework, pre, policy_changes=(), rec_report=None, places=2):
    out = ["NOTES", f"Reporting framework: {framework}",
           "Basis: management accounts prepared from the entries you declared; not GAAP or IFRS statements and not assurance.",
           f"Net income for the period: {_num(pre['net_income'], places)}"]
    if policy_changes:
        out.append("Declared policy changes:")
        out += [f"  {c['date']}  {c['description']}  ({c['kind']}, {c['treatment']})" for c in policy_changes]
    else:
        out.append("Declared policy changes: none")
    if rec_report is not None:
        out.append(f"Reconciliation of account {rec_report['account']}: adjusted statement {_num(rec_report['adjusted_statement'], places)}, "
                   f"adjusted ledger {_num(rec_report['adjusted_ledger'], places)}, difference {_num(rec_report['difference'], places)}")
    return "\n".join(out)

def financial_statements(j, pre, cf, framework, policy_changes=(), rec_report=None, places=2):
    """Render every accountant-facing statement and a combined document. `pre` is the pre-closing statement set
    (so the income statement still has its lines); the balance sheet uses the post-closing journal."""
    st = ledger.statements(j)
    parts = {"trial_balance": trial_balance(j, places), "income_statement": income_statement(pre, j, places),
             "balance_sheet": balance_sheet(j, st, places), "cash_flow": cash_flow_statement(j, cf, places)}
    if rec_report is not None: parts["reconciliation"] = reconciliation_statement(rec_report, places)
    parts["notes"] = notes(j, framework, pre, policy_changes, rec_report, places)
    order = ("trial_balance", "income_statement", "balance_sheet", "cash_flow", "reconciliation", "notes")
    parts["combined"] = "\n\n".join(parts[k] for k in order if k in parts)
    return parts
