"""Credits for exports: an append-only ledger, a derived balance, and idempotent charges.

Product-layer storage (additive; the frozen core is not touched). The design choices are deliberate:

* **The balance is derived, never stored.** It is the sum of the ledger. A stored balance can drift from the
  ledger that explains it, and then nobody can answer a student asking "why was I charged twice?".
* **Charge on success, never on request.** The renderer runs first; the deduction is appended only if a file
  was actually produced. A failed export costs nothing.
* **Charges are idempotent.** The key is `account|report|kind`, so a retry after a dropped connection returns
  the same receipt and does not charge again.
* **Prices are configuration.** They live in `PRICE_TABLE` and are meant to be replaced by the owner's
  numbers; nothing in the code assumes a particular amount.
* **The first export of a report is free, whatever its format** (owner decision, 2026-10-28), so a student who
  only ever needs a PDF is not penalised for not choosing Word.

Standard library only; one JSON line per movement; a lock so the threaded server cannot interleave appends.
"""

import json
import os
import threading
import time
import uuid
from hashlib import sha256

LOCK = threading.Lock()

#: Credits per export kind. Replace with the owner's numbers; nothing here is a computed fact.
PRICE_TABLE = {"html": 0, "csv": 0, "docx": 1, "spreadsheetml": 1, "pptx": 3}

#: A brand-new wallet is granted this many credits (free tier). Set BP_CREDITS_GRANT to change it.
DEFAULT_GRANT = 100

#: The first export of any report is free, regardless of kind (owner decision).
INCLUDED_FIRST = True


class CreditError(ValueError):
    """The charge cannot be made: unknown kind, or not enough credits."""


class InsufficientCredits(CreditError):
    def __init__(self, needed, available, kind):
        super().__init__(f"{kind} costs {needed} credit(s); the balance is {available}")
        self.needed, self.available, self.kind = needed, available, kind


def _state_dir():
    from . import ops
    return str(ops.state_dir())


def _path():
    return os.path.join(_state_dir(), "credits.jsonl")


def _read():
    path = _path()
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue          # a torn line is skipped rather than crashing the wallet
    return out


def _append(entry):
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def _grant_if_new(account):
    if any(e.get("account") == account for e in _read()):
        return
    amount = int(os.environ.get("BP_CREDITS_GRANT", DEFAULT_GRANT))
    _append({"id": uuid.uuid4().hex[:12], "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "account": account, "kind": "grant", "amount": amount, "reason": "opening free tier",
             "report": None, "format": None, "idem": None, "balance_after": amount})


def entries(account="local"):
    _grant_if_new(account)
    return [e for e in _read() if e.get("account") == account]


def balance(account="local"):
    """The wallet balance: the sum of the ledger, never a stored figure."""
    return sum(int(e["amount"]) for e in entries(account))


def exported_reports(account="local"):
    return {e["report"] for e in entries(account) if e.get("kind") == "deduct" and e.get("report")}


def idem_key(account, report, kind):
    return sha256(f"{account}|{report}|{kind}".encode()).hexdigest()[:32]


def quote(report, kind, account="local"):
    """What one export would cost, and why. Never raises for affordability - only for an unknown kind."""
    if kind not in PRICE_TABLE:
        raise CreditError(f"unknown export kind {kind!r}; known: {sorted(PRICE_TABLE)}")
    already = exported_reports(account)
    free = INCLUDED_FIRST and report not in already
    cost = 0 if free else int(PRICE_TABLE[kind])
    return {"report": report, "kind": kind, "cost": cost, "free": free,
            "price": int(PRICE_TABLE[kind]), "balance": balance(account)}


def charge(report, kind, account="local", idem=None):
    """Append a deduction for a completed export.

    Deduplication happens only when the caller supplies an `idem` key, which is what a retry carries. Without
    one, each call is a genuine new export and is charged: keying on report and format alone would make every
    second export of the same file look like a retry and silently free.
    """
    with LOCK:
        if idem:
            for e in entries(account):
                if e.get("idem") == idem and e.get("kind") == "deduct":
                    return {"charged": False, "reused": True, "entry": e, "balance": balance(account)}
        q = quote(report, kind, account)
        if q["cost"] > q["balance"]:
            raise InsufficientCredits(q["cost"], q["balance"], kind)
        entry = {"id": uuid.uuid4().hex[:12], "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "account": account, "kind": "deduct", "amount": -q["cost"], "reason": "export",
                 "report": report, "format": kind, "idem": idem,
                 "balance_after": q["balance"] - q["cost"]}
        _append(entry)
        return {"charged": q["cost"] > 0, "reused": False, "entry": entry,
                "balance": q["balance"] - q["cost"], "free": q["free"]}


def refund(report, kind, account="local", reason="export failed"):
    """Give back the most recent charge for that report and format. Appended, never edited."""
    with LOCK:
        prior = [e for e in entries(account)
                 if e.get("kind") == "deduct" and e.get("report") == report and e.get("format") == kind]
        if not prior:
            return {"refunded": False, "reason": "nothing was charged for that export"}
        amount = -int(prior[-1]["amount"])
        if amount == 0:
            return {"refunded": False, "reason": "that export was free"}
        entry = {"id": uuid.uuid4().hex[:12], "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "account": account, "kind": "refund", "amount": amount, "reason": reason,
                 "report": report, "format": kind, "idem": prior[-1].get("idem"),
                 "balance_after": balance(account) + amount}
        _append(entry)
        return {"refunded": True, "amount": amount, "entry": entry, "balance": balance(account)}


def receipt(account="local", limit=20):
    return {"account": account, "balance": balance(account),
            "prices": dict(PRICE_TABLE), "included_first": INCLUDED_FIRST,
            "entries": entries(account)[-limit:]}
