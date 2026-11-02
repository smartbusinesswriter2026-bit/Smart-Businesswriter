"""Trial-balance check: compare what a student submitted with what their own journal rebuilds to.

The point of this module is to be useful without ever claiming more than it can prove. It reports:

- every submitted figure that matched, differed, or had no counterpart;
- the net and absolute differences;
- a small set of **candidate causes** whose evidence is stated, with a confidence word;
- and what the check **cannot** establish - starting with the fact that a balanced trial balance is not
  proof of correct entries.

Matching is declared rather than guessed: by account code when both sides carry one, otherwise by name,
and an ambiguous name is refused instead of being resolved arbitrarily. Numbers are Decimal throughout and
nothing is rounded silently.
"""

from decimal import Decimal as D

from . import ledger

CONFIDENCE = ("likely", "possible", "no-conclusion")


class CheckError(ValueError):
    """The check cannot run on what was supplied (ambiguous name, malformed figure, no input at all)."""


def _places(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 6:
        raise CheckError("places must be a whole number from 0 to 6")
    return value


def _amount(x, what, places):
    if isinstance(x, bool):
        raise CheckError(f"{what} must be a number, not a boolean")
    try:
        d = D(str(x))
    except Exception:
        raise CheckError(f"{what} must be a number, got {x!r}")
    if not d.is_finite():
        raise CheckError(f"{what} must be finite")
    if d < 0:
        raise CheckError(f"{what} must not be negative; put the figure on the debit or credit side instead")
    if d != d.quantize(D(1).scaleb(-places)):
        raise CheckError(f"{what} has more than {places} decimal places")
    return d


def _norm(name):
    return " ".join(str(name or "").strip().lower().split())


def submitted_rows(rows, places):
    """The student's own trial balance, as {code?, name?, debit, credit, net}."""
    if not isinstance(rows, list) or not rows:
        raise CheckError("trial_balance must be a non-empty list of rows")
    out = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            raise CheckError(f"trial_balance[{i}] must be an object with a code or a name and a debit or credit")
        code = str(r.get("code") or "").strip()
        name = str(r.get("name") or "").strip()
        if not code and not name:
            raise CheckError(f"trial_balance[{i}] needs a code or a name")
        debit = _amount(r.get("debit", 0), f"trial_balance[{i}].debit", places)
        credit = _amount(r.get("credit", 0), f"trial_balance[{i}].credit", places)
        out.append({"index": i, "code": code, "name": name, "debit": debit, "credit": credit,
                    "net": debit - credit})
    seen = set()
    for r in out:
        key = r["code"] or _norm(r["name"])
        if key in seen:
            raise CheckError(f"{r['name'] or r['code']!r} is listed more than once; "
                             "combine the figures or use the account code to tell them apart")
        seen.add(key)
    return out


def rebuilt_rows(journal_spec, places):
    """The trial balance the student's own journal produces, via the ledger kernel."""
    from . import accounts
    built = accounts.build(journal_spec)
    tb = built["_appendix"]["trial_balance"]
    rows = []
    for code, name, debit, credit in tb["rows"]:
        d, c = D(str(debit)), D(str(credit))
        rows.append({"code": code, "name": name, "debit": d, "credit": c, "net": d - c})
    return rows, D(str(tb["total_debits"])), D(str(tb["total_credits"])), built


def _index(rows):
    by_code, by_name = {}, {}
    for r in rows:
        if r["code"]:
            by_code[r["code"]] = r
        if r["name"]:
            by_name.setdefault(_norm(r["name"]), []).append(r)
    return by_code, by_name


def _resolve(row, by_code, by_name):
    """The rebuilt row a submitted row refers to, or None. An ambiguous name is refused."""
    if row["code"]:
        return by_code.get(row["code"])
    candidates = by_name.get(_norm(row["name"]), [])
    if len(candidates) > 1:
        raise CheckError(f"the name {row['name']!r} matches more than one account; use the account code")
    return candidates[0] if candidates else None


def _divisible_by_nine(value):
    v = abs(value)
    return v != 0 and v == v.to_integral_value() and int(v) % 9 == 0


def _fmt(v, places):
    return f"{v:,.{places}f}"


def compare(journal_spec, trial_balance, places=2):
    """Compare a submitted trial balance with the one the submitted journal rebuilds to.

    Either input may be omitted; the verdict says what that costs the reader. Returns counts, per-line
    rows, findings and a verdict sentence - never a correction.
    """
    places = _places(places)
    if journal_spec is None and trial_balance is None:
        raise CheckError("supply a journal, a trial balance, or both")
    submitted = submitted_rows(trial_balance, places) if trial_balance is not None else None
    rebuilt = None
    rebuilt_totals = None
    if journal_spec is not None:
        rebuilt, dr, cr, built = rebuilt_rows(journal_spec, places)
        rebuilt_totals = (dr, cr)
    sub_dr = sum((r["debit"] for r in submitted), D(0)) if submitted else D(0)
    sub_cr = sum((r["credit"] for r in submitted), D(0)) if submitted else D(0)
    sub_diff = sub_dr - sub_cr

    rows, findings = [], []
    matched = differing = missing_submitted = missing_rebuilt = 0

    if submitted is not None and rebuilt is not None:
        by_code, by_name = _index(rebuilt)
        claimed = set()
        for r in submitted:
            other = _resolve(r, by_code, by_name)
            if other is None:
                missing_rebuilt += 1
                rows.append({"code": r["code"], "name": r["name"], "status": "only-in-yours",
                             "submitted": r["net"], "rebuilt": None,
                             "difference": None})
                findings.append({"kind": "only-in-yours", "confidence": "likely",
                                 "account": r["name"] or r["code"],
                                 "detail": "Your trial balance has this account; your journal does not "
                                           "produce it. Either the account is not in your chart, or no "
                                           "entry posts to it."})
                continue
            claimed.add(id(other))
            diff = r["net"] - other["net"]
            if diff == 0:
                matched += 1
                rows.append({"code": other["code"], "name": other["name"], "status": "agrees",
                             "submitted": r["net"], "rebuilt": other["net"], "difference": D(0)})
            else:
                differing += 1
                rows.append({"code": other["code"], "name": other["name"], "status": "differs",
                             "submitted": r["net"], "rebuilt": other["net"], "difference": diff})
                findings.append(_difference_finding(other, r, diff, places))
        for other in rebuilt:
            if id(other) in claimed:
                continue
            missing_submitted += 1
            rows.append({"code": other["code"], "name": other["name"], "status": "only-in-journal",
                         "submitted": None, "rebuilt": other["net"], "difference": None})
            findings.append({"kind": "only-in-journal", "confidence": "likely",
                             "account": other["name"] or other["code"],
                             "detail": "Your journal produces this account; your trial balance leaves it "
                                       "out. That is either an omission or a different account used."})
    elif submitted is not None:
        for r in submitted:
            rows.append({"code": r["code"], "name": r["name"], "status": "unchecked",
                         "submitted": r["net"], "rebuilt": None, "difference": None})
    else:
        for other in rebuilt:
            rows.append({"code": other["code"], "name": other["name"], "status": "unchecked",
                         "submitted": None, "rebuilt": other["net"], "difference": None})

    diffs = [D(r["difference"]) for r in rows if r["difference"] is not None]
    total_abs = sum((abs(d) for d in diffs), D(0))
    net_diff = sum(diffs, D(0))

    if sub_diff != 0:
        hint = ""
        if _divisible_by_nine(sub_diff):
            hint = (f" It is divisible by 9, which is the signature of a transposition (54 written as 45) "
                    f"or a slide (a misplaced decimal). Treat that as a hint about where to look, not a "
                    f"finding.")
        findings.insert(0, {"kind": "submitted-does-not-balance", "confidence": "likely",
                            "account": None,
                            "detail": f"Your trial balance does not balance: debits {_fmt(sub_dr, places)}, "
                                      f"credits {_fmt(sub_cr, places)}, a difference of "
                                      f"{_fmt(abs(sub_diff), places)}.{hint}"})

    state = {
        "has_journal": journal_spec is not None,
        "has_trial_balance": submitted is not None,
        "n_matched": matched, "n_differing": differing,
        "n_missing_submitted": missing_submitted, "n_missing_rebuilt": missing_rebuilt,
        "total_abs": total_abs, "net_diff": net_diff, "submitted_diff": sub_diff,
        "places": places,
    }
    return {
        "counts": {
            "n_submitted": len(submitted) if submitted is not None else 0,
            "n_rebuilt": len(rebuilt) if rebuilt is not None else 0,
            "n_matched": matched,
            "n_differing": differing,
            "n_missing_submitted": missing_submitted,
            "n_missing_rebuilt": missing_rebuilt,
            "n_findings": len(findings),
        },
        "amounts": {
            "total_absolute_difference": total_abs,
            "difference_net": net_diff,
            "submitted_balance_difference": sub_diff,
        },
        "rows": rows,
        "findings": findings,
        "verdict": verdict(state),
        "cannot_prove": [
            "It cannot tell you which of the two figures is right when both are declared.",
            "It cannot catch an error of principle if the journal itself encodes the wrong treatment.",
            "It cannot check amounts against source documents.",
            "It corrects nothing.",
        ],
    }


def _difference_finding(other, submitted_row, diff, places):
    """A candidate cause for one account that differs, with the evidence that suggests it."""
    if submitted_row["net"] == 0 and other["net"] != 0:
        return {"kind": "unposted", "confidence": "possible", "account": other["name"] or other["code"],
                "detail": f"Your trial balance shows nothing for this account while your journal posts "
                          f"{_fmt(abs(other['net']), places)} to it. That is what an unposted entry looks like."}
    if submitted_row["net"] == 0 - other["net"]:
        return {"kind": "wrong-side", "confidence": "possible", "account": other["name"] or other["code"],
                "detail": f"The two figures are equal and opposite ({_fmt(submitted_row['net'], places)} "
                          f"against {_fmt(other['net'], places)}). That is what a posting to the wrong side "
                          f"looks like."}
    return {"kind": "amount-differs", "confidence": "no-conclusion", "account": other["name"] or other["code"],
            "detail": f"Your figure is {_fmt(submitted_row['net'], places)} and the journal produces "
                      f"{_fmt(other['net'], places)}, a difference of {_fmt(diff, places)}. No single "
                      f"pattern explains it, so the comparison is the evidence."}


def recount(journal_spec, trial_balance, places=2):
    """Independent second route: a linear scan instead of an index.

    The main path builds code and name indexes and tracks claimed rows with identity. This one walks both
    lists naively. It is slower and plainer on purpose - agreement between the two is evidence that the
    indexing is not dropping or double-counting rows.
    """
    places = _places(places)
    submitted = submitted_rows(trial_balance, places) if trial_balance is not None else None
    rebuilt = rebuilt_rows(journal_spec, places)[0] if journal_spec is not None else None
    if submitted is None or rebuilt is None:
        return {"n_matched": 0, "n_differing": 0, "n_missing_submitted": 0, "n_missing_rebuilt": 0,
                "total_absolute_difference": D(0), "difference_net": D(0)}
    seen = [False] * len(rebuilt)
    matched = differing = missing_submitted = 0
    total, net = D(0), D(0)
    for r in submitted:
        hit = None
        for i, o in enumerate(rebuilt):
            if seen[i]:
                continue
            if r["code"]:
                if o["code"] == r["code"]:
                    hit = i
                    break
            elif _norm(o["name"]) == _norm(r["name"]):
                hit = i
                break
        if hit is None:
            missing_submitted += 1
            continue
        seen[hit] = True
        d = r["net"] - rebuilt[hit]["net"]
        if d == 0:
            matched += 1
        else:
            differing += 1
            total += abs(d)
            net += d
    return {"n_matched": matched, "n_differing": differing,
            "n_missing_submitted": missing_submitted,
            "n_missing_rebuilt": sum(1 for s in seen if not s),
            "total_absolute_difference": total, "difference_net": net}


def verdict(state):
    """The sentence a student reads. It says what was checked and what that check is worth."""
    p = state["places"]
    if not state["has_journal"]:
        return ("I can check that your trial balance balances, and that is all. Errors of principle, "
                "commission, original entry, omission, reversal and compensating errors all leave a trial "
                "balance balanced. Paste your journal and I can check the entries themselves.")
    if not state["has_trial_balance"]:
        return ("Your journal has been rebuilt and balances. There is nothing to compare it against - "
                "paste your trial balance and I will check your summary of it.")
    if state["submitted_diff"] != 0:
        return (f"Your trial balance does not balance, so it cannot be compared meaningfully yet. The "
                f"imbalance must be found first; everything else on this screen is secondary to it.")
    if state["n_differing"] == 0 and state["n_missing_submitted"] == 0 and state["n_missing_rebuilt"] == 0:
        return ("Your trial balance agrees with your own journal, line for line. This is the strongest check "
                "available here. It does not prove your entries are right - only that your trial balance is a "
                "faithful summary of them.")
    return (f"Your trial balance does not agree with your journal in "
            f"{state['n_differing'] + state['n_missing_submitted'] + state['n_missing_rebuilt']} place(s). "
            f"The net difference is {_fmt(state['net_diff'], p)}. I can tell you where the two disagree; I "
            f"cannot tell you which one is wrong - that depends on the entries you intended.")
