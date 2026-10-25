"""Runs the neutral trap cases against the custom kernel (bp.ledger) and prints/returns a results table."""
import copy, sys, os
from decimal import Decimal as D
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bp import ledger as L
from trap_cases import CASES, CHART, PERIOD

def run_case(case):
    chart = copy.deepcopy(CHART)
    for code, ch in case.get("chart_change", {}).items():
        next(a for a in chart if a["code"] == code).update(ch)
    ch = L.Chart([L.Account(a["code"], a["name"], a["type"], a["line"], a.get("contra", False), a.get("role", "")) for a in chart]); j = L.Journal(ch, *PERIOD, "USD")
    try:
        for en in case["entries"]: j.post(L.Entry.make(en["date"], en["description"], en["lines"], opening=en.get("opening", False)))
    except L.LedgerError as err: return "rejected_at_entry", f"{type(err).__name__}: {err}"
    if case.get("tamper"):
        e0 = j.entries[-1]; j.entries[-1] = L.Entry(e0.date, e0.description + " (edited)", e0.lines, e0.opening)
    inv = L.check_invariants(j, L.statements(j), case.get("prior_closing")); bad = [n for n, ok, _ in inv if not ok]
    if bad: return "invariant", ", ".join(bad)
    fl = L.flags(j)
    if fl: return "flag", "; ".join(f"{f['kind']}({f['account']})" for f in fl)
    return "nothing", ""

def run_all(): return [(c["id"], c["expect"], *run_case(c)) for c in CASES]

if __name__ == "__main__":
    rows = run_all(); w = max(len(r[0]) for r in rows)
    for cid, exp, got, detail in rows: print(f"{cid:<{w}}  expected {exp:<26} got {got:<18} {'OK ' if got == exp or exp == 'not_detectable_from_data' and got == 'nothing' else 'DIFF'}  {detail[:70]}")
    print("kernel size:", sum(1 for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "bp", "ledger.py")) if l.strip()), "non-blank lines")
