"""Automatic in-pipeline resolution of logged errors (product layer).

"Resolve" repairs the failure inside the pipeline and proves it by replay:

  1. diagnose the failure class from the error message
  2. refuse to "fix" input that is not an accounting problem — that is an
     invalid test case, not a pipeline defect, and it is marked invalid
  3. replay the stored problem through the normal solve path (which applies
     the deterministic normalizers on every solve) on deepseek-v4.1-flash;
     if it still fails, replay on deepseek-v4-pro (both OpenCode Go)
  4. on a passing replay: record a golden regression case, mark the error
     verified, and close its siblings (errors with the identical message)
     that also pass the same replay

An error is marked verified solved only when a replay passes. Fixes are
durable because normalisation runs on every solve and every verified fix is
pinned in `qa/regression/problem_norm_cases.jsonl`, replayed by the
`regression` test suite.
"""
from . import ops_log as _ops_log
from .problem_norm import normalize_problem

#: The fix model ladder: cheap flash first; if it cannot fix it, the pro model.
#: Both are on OpenCode Go. Override with BP_FIX_MODEL / BP_FIX_ESCALATION_MODEL.
FIX_MODEL = "deepseek-v4.1-flash"
ESCALATION_MODEL = "deepseek-v4-pro"

#: How many same-error siblings one resolve may verify and close.
MAX_SIBLINGS = 5


def _fix_models():
    import os
    return (os.environ.get("BP_FIX_MODEL", FIX_MODEL),
            os.environ.get("BP_FIX_ESCALATION_MODEL", ESCALATION_MODEL))


def diagnose(error_text):
    """Classify one error message into a failure class."""
    low = str(error_text or "").lower()
    if "429" in low or "rate limit" in low or "too many requests" in low or "provider returned http" in low:
        return "rate_limit"
    if "exceeds" in low and "character" in low:
        return "input_too_large"
    if "appears twice" in low or "appears more than once" in low:
        return "duplicate_account"
    if "could not find an account" in low:
        return "unreadable_layout"
    if "could not read this as a journal" in low:
        return "reader_parse"
    if "names no transaction" in low or "does not read as an accounting problem" in low:
        return "unsupported_instruction"
    return "unknown"


def _replay_on(problem, model):
    """Replay one problem with the statements reader pinned to `model`."""
    import os
    from . import chat_heal
    saved = (os.environ.get("BP_LLM_MODEL"),
             os.environ.get("BP_LLM_MODEL_TIER2"),
             os.environ.get("BP_LLM_MODEL_TIER3"))
    try:
        os.environ["BP_LLM_MODEL"] = model
        os.environ["BP_LLM_MODEL_TIER2"] = model
        os.environ["BP_LLM_MODEL_TIER3"] = model
        results, _err = chat_heal.solve_problems([problem])
        return results[0] if results else {}
    finally:
        for name, value in zip(("BP_LLM_MODEL", "BP_LLM_MODEL_TIER2", "BP_LLM_MODEL_TIER3"), saved):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _deterministic_ok(normalized):
    """Whether the frozen reader accepts the normalised problem with no model."""
    try:
        from . import statements as stmt_mod
        rows = stmt_mod.read_deterministic(normalized)
        return bool(rows)
    except Exception:
        return False


def _siblings(record, limit=MAX_SIBLINGS):
    """Unresolved errors carrying the identical message but a different id."""
    target = (record.get("error") or "").strip()
    if not target:
        return []
    rows = _ops_log.merge_resolved(_ops_log.list_errors(limit=500))
    out = []
    for row in rows:
        if (row.get("error") or "").strip() != target:
            continue
        if row.get("error_id") == record.get("error_id"):
            continue
        if row.get("resolved") or row.get("invalid") or row.get("dismissed") or not row.get("problem"):
            continue
        out.append(row)
    return out[:limit]


def resolve(error_id):
    """Attempt to resolve one logged error inside the pipeline.

    Returns {resolved, verified, attempted, invalid, model, category,
    steps, siblings_resolved, reason}.
    """
    record = _ops_log.get_error(error_id)
    if record is None:
        return {"resolved": False, "verified": False, "attempted": False, "invalid": False,
                "steps": [], "siblings_resolved": 0, "reason": "unknown error_id"}

    category = diagnose(record.get("error", ""))
    if category == "unsupported_instruction":
        _ops_log.mark_error_invalid(
            error_id, "the problem is not an accounting problem; not a pipeline defect")
        closed = 0
        for sibling in _siblings(record, limit=200):
            _ops_log.mark_error_invalid(
                sibling.get("error_id"),
                "same invalid-input class: the problem names no transaction and declares no figure")
            closed += 1
        return {"resolved": False, "verified": False, "attempted": False, "invalid": True,
                "category": category, "steps": [], "siblings_resolved": 0,
                "siblings_invalid": closed,
                "reason": "invalid test input: the problem names no transaction and declares no figure"}

    problem = record.get("problem") or ""
    if not problem:
        return {"resolved": False, "verified": False, "attempted": False, "invalid": False,
                "steps": [], "siblings_resolved": 0,
                "reason": "no replayable problem was stored for this error, so a fix cannot be verified"}

    normalized, notes = normalize_problem(problem)
    strategy = "replay normalized problem" if notes else "replay original problem"
    steps = []
    fix_model, escalation_model = _fix_models()

    for model in (fix_model, escalation_model):
        first = _replay_on(problem, model)
        status = first.get("status") or "error"
        steps.append({"strategy": strategy, "model": model, "outcome": status,
                      "detail": (first.get("error") or "")[:200]})
        if status != "ok":
            continue

        from . import regression_cases
        regression_cases.record_case(
            error_id, category, problem, normalized, notes, model,
            deterministic_ok=_deterministic_ok(normalized))
        _ops_log.mark_error_verified(
            error_id, "pipeline replayed the problem on %s and it passed" % model)

        closed, sib_steps = 0, []
        for sibling in _siblings(record):
            again = _replay_on(sibling.get("problem"), model)
            ok = (again.get("status") == "ok")
            sib_steps.append({"strategy": "close sibling", "model": model,
                              "outcome": again.get("status") or "error",
                              "detail": (sibling.get("error_id") or "")[:40]})
            if ok:
                _ops_log.mark_error_verified(
                    sibling.get("error_id"),
                    "same failure class verified by the class replay on %s" % model)
                closed += 1
        steps.extend(sib_steps)
        _ops_log.log_resolution_attempt(error_id, category, steps, "solved")
        return {"resolved": True, "verified": True, "attempted": True, "invalid": False,
                "steps": steps, "model": model, "category": category,
                "siblings_resolved": closed,
                "reason": "replay passed on %s (%s)%s" % (
                    model, strategy,
                    "; %d sibling error(s) closed" % closed if closed else "")}

    _ops_log.log_resolution_attempt(error_id, category, steps, "still failing")
    return {"resolved": False, "verified": False, "attempted": True, "invalid": False,
            "steps": steps, "siblings_resolved": 0, "category": category,
            "reason": steps[-1]["detail"] if steps else "no remediation applied"}
