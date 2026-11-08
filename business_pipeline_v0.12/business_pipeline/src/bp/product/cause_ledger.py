"""Cause ledger: what broke, what was actually fixed, and what came back.

The admin panel used to report "errors closed %", which counted dismissals and
one-off replay passes as fixes.  A cause is a class of failure; it is **fixed**
only when a durable artifact was written (a vocabulary rule, a golden case, a
refreshed case expectation, a reviewed code change) and **recurring** when the
same class appears after that fix.  This module turns the append-only error log
into that view without a second store to keep in sync.

Nothing here guesses: a record whose cause cannot be classified is reported as
`pipeline.unknown`, and an instance close with no artifact never counts as a fix.
"""
from . import causes, ops_log


def _row_template(cause, meta):
    return {
        "cause": cause,
        "title": meta.get("title", cause),
        "scope": meta.get("scope", causes.PIPELINE),
        "remedy": meta.get("remedy", "investigate"),
        "required_artifact": meta.get("artifact", ""),
        "occurrences": 0,
        "instances_closed": 0,
        "artifacts": [],
        "first_seen": "",
        "last_seen": "",
        "fixed_at": "",
        "recurrences": 0,
        "status": "open",
    }


def summary(limit=100000):
    """Return the per-cause ledger and its totals.

    Every pipeline failure is counted once per logged record.  `fixed_at` is the
    earliest close that carried an artifact; a later record of the same cause is
    a recurrence, because the fix did not hold.
    """
    rows = ops_log.list_errors(limit=limit, status="all")
    ledger = {}
    for record in rows:
        error_text = record.get("error") or ""
        cause = record.get("cause")
        if not cause:
            cause = causes.classify_cause(error_text, record.get("problem"))["cause"]
        meta = causes.REMEDIES.get(cause) or causes.REMEDIES["pipeline.unknown"]
        if meta.get("scope") != causes.PIPELINE:
            # Input and transient classes are refused before they reach the log;
            # a legacy record of one is not a cause the loop can fix.
            continue
        entry = ledger.setdefault(cause, _row_template(cause, meta))
        entry["occurrences"] += 1
        ts = str(record.get("ts") or "")
        if ts and (not entry["first_seen"] or ts < entry["first_seen"]):
            entry["first_seen"] = ts
        if ts and ts > entry["last_seen"]:
            entry["last_seen"] = ts
        if record.get("resolved") or record.get("invalid") or record.get("dismissed"):
            entry["instances_closed"] += 1
        artifact = record.get("artifact") or ""
        closed_at = record.get("closed_at") or ""
        if artifact:
            if artifact not in entry["artifacts"]:
                entry["artifacts"].append(artifact)
            if closed_at and (not entry["fixed_at"] or closed_at < entry["fixed_at"]):
                entry["fixed_at"] = closed_at

    # A cause fix is recorded explicitly (the change lives in the repository), not
    # inferred from an instance close.  Date the class from that record.
    for fix in ops_log.list_cause_fixes():
        entry = ledger.get(fix.get("cause"))
        if entry is None:
            continue
        artifact = fix.get("artifact") or ""
        ts = fix.get("ts") or ""
        if artifact and artifact not in entry["artifacts"]:
            entry["artifacts"].append(artifact)
        if ts and (not entry["fixed_at"] or ts < entry["fixed_at"]):
            entry["fixed_at"] = ts

    for entry in ledger.values():
        if entry["fixed_at"]:
            entry["recurrences"] = sum(
                1 for r in rows
                if (r.get("cause") or causes.classify_cause(
                        r.get("error") or "", r.get("problem"))["cause"]) == entry["cause"]
                and str(r.get("ts") or "") > entry["fixed_at"])
            entry["status"] = "recurring" if entry["recurrences"] else "fixed"
        elif entry["instances_closed"] >= entry["occurrences"]:
            entry["status"] = "closed_instance"
        else:
            entry["status"] = "unfixed"

    ordered = sorted(ledger.values(),
                     key=lambda e: ({"recurring": 0, "unfixed": 1, "closed_instance": 2,
                                     "fixed": 3}.get(e["status"], 4),
                                    -e["occurrences"]))
    fixed = sum(1 for e in ordered if e["status"] == "fixed")
    recurring = sum(1 for e in ordered if e["status"] == "recurring")
    unfixed = sum(1 for e in ordered if e["status"] == "unfixed")
    totals = {
        "causes": len(ordered),
        "fixed": fixed,
        "recurring": recurring,
        "unfixed": unfixed,
        "closed_instance_only": sum(1 for e in ordered if e["status"] == "closed_instance"),
        # The only percentage that says the pipeline learned something.
        "fixed_pct": round(100.0 * fixed / len(ordered), 1) if ordered else 100.0,
    }
    return {"causes": ordered, "summary": totals}


#: Artifacts that change the reader for every instance of the cause, so the class
#: is fixed and the loop must not spend a model call on another instance of it.
WHOLE_CLASS_ARTIFACTS = ("golden_case", "narrative_balance", "code")


def fixed_causes(limit=100000):
    """Causes with a durable artifact and no recurrence since that fix."""
    return {row["cause"] for row in summary(limit)["causes"]
            if row["status"] == "fixed"}


def covered_causes(limit=100000):
    """Fixed causes whose artifact applies to every instance of the class."""
    out = set()
    for row in summary(limit)["causes"]:
        if row["status"] != "fixed":
            continue
        if any(artifact in WHOLE_CLASS_ARTIFACTS for artifact in row["artifacts"]):
            out.add(row["cause"])
    return out


def attended_causes():
    """Pipeline causes whose remedy is a human change (no automated artifact).

    `pipeline.unknown` is excluded: an unclassified failure still deserves one
    investigation, which is what the loop is for.  A cause already fixed is
    skipped separately by `fixed_causes`.
    """
    return {key for key, meta in causes.REMEDIES.items()
            if meta.get("scope") == causes.PIPELINE and not meta.get("artifact")
            and key != "pipeline.unknown"}

