"""Reconciliation engine for the Stage 8 ledger (manual 9.3, 9.4): compare an external statement (for example a bank
statement) with the ledger balance of one account, classify every movement exactly once, and list what must be booked.
Matching is a declared heuristic: a book movement is paired with a statement line of the same signed amount; when more
than one candidate exists the pairing is flagged, never guessed silently. The reconciliation must tie: the adjusted
statement balance equals the adjusted ledger balance once in-transit book items and unrecorded statement items are shown.
Management accounts only: not GAAP/IFRS statements and not assurance (manual 9.5)."""
from decimal import Decimal as D
from . import ledger

class ReconcileError(ValueError): pass
DIRECTIONS = ("in", "out")

def _dec(x, what):
    if isinstance(x, (float, bool)): raise ReconcileError(f"{what} must be a string, integer or Decimal, never a binary float")
    try: d = D(str(x))
    except Exception: raise ReconcileError(f"{what} must be a number, got {x!r}")
    if not d.is_finite(): raise ReconcileError(f"{what} must be finite")
    return d

def validate_statement(statement):
    """Actionable errors for a statement object; empty means it can reconcile."""
    if not isinstance(statement, dict): return ["the statement must be an object with opening_balance, closing_balance and lines"]
    errs = []
    for k in ("opening_balance", "closing_balance"):
        try: _dec(statement.get(k), k)
        except ReconcileError as e: errs.append(str(e))
    lines = statement.get("lines")
    if not isinstance(lines, list): errs.append("lines must be a list")
    else:
        for i, l in enumerate(lines):
            if not isinstance(l, dict): errs.append(f"lines[{i}] must be an object"); continue
            if l.get("direction") not in DIRECTIONS: errs.append(f"lines[{i}] direction must be 'in' or 'out'")
            try:
                if _dec(l.get("amount"), f"lines[{i}] amount") <= 0: errs.append(f"lines[{i}] amount must be positive")
            except ReconcileError as e: errs.append(str(e))
    return errs

def reconcile(j, account, statement):
    """Reconcile `account` against `statement` on the journal's period. Returns the adjustment lines, the classified
    movements, the disclosed report and its checks. Signed amounts are increases (+) and decreases (-) of the balance."""
    errs = validate_statement(statement)
    if errs: raise ReconcileError("; ".join(errs))
    a = j.chart.get(account)
    ob, book = D(0), []
    for e in j.entries:
        for l in e.lines:
            if l.account != account: continue
            s = l.amount if l.side == a.normal else -l.amount          # signed increase of the reconciled balance
            if e.opening: ob += s
            else: book.append({"date": e.date, "description": e.description, "signed": s})
    st = [{"date": str(l.get("date") or ""), "description": str(l.get("description") or ""),
           "signed": _dec(l["amount"], "amount") * (1 if l["direction"] == "in" else -1), "used": False} for l in statement["lines"]]
    so = _dec(statement["opening_balance"], "opening_balance"); sc = _dec(statement["closing_balance"], "closing_balance")
    flags = []
    for s in st:
        if s["date"] and not (j.start <= s["date"] <= j.end): flags.append({"kind": "statement_line_outside_period", "date": s["date"], "description": s["description"]})
    matched, books_only = [], []
    for b in book:
        cands = [s for s in st if not s["used"] and s["signed"] == b["signed"]]
        if len(cands) > 1: flags.append({"kind": "ambiguous_match", "amount": b["signed"], "description": b["description"], "detail": f"several statement lines have the same amount; the first unused one was paired"})
        if cands: cands[0]["used"] = True; matched.append(b)
        else: books_only.append(b)
    stmt_only = [s for s in st if not s["used"]]
    b_d = sum((b["signed"] for b in books_only if b["signed"] > 0), D(0)); b_c = -sum((b["signed"] for b in books_only if b["signed"] < 0), D(0))
    s_d = sum((s["signed"] for s in stmt_only if s["signed"] > 0), D(0)); s_c = -sum((s["signed"] for s in stmt_only if s["signed"] < 0), D(0))
    book_sum = sum((b["signed"] for b in book), D(0)); stmt_sum = sum((s["signed"] for s in st), D(0))
    ledger_balance = ob + book_sum
    adj_stmt = sc + b_d - b_c; adj_ledger = ledger_balance + s_d - s_c
    checks = [("statement_internally_consistent", sc == so + stmt_sum, f"closing {sc}, opening plus lines {so + stmt_sum}"),
              ("opening_balances_agree", ob == so, f"ledger opening {ob}, statement opening {so}")]
    report = {"account": account, "account_name": j.chart.get(account).name,
              "ledger_opening": ob, "ledger_balance": ledger_balance, "statement_opening": so, "statement_closing": sc,
              "receipts_in_transit": b_d, "payments_outstanding": b_c, "unrecorded_receipts": s_d, "unrecorded_payments": s_c,
              "adjusted_statement": adj_stmt, "adjusted_ledger": adj_ledger, "difference": adj_stmt - adj_ledger,
              "matched": matched, "books_only": books_only, "statement_only": stmt_only}
    return {"report": report, "checks": checks, "flags": flags}
