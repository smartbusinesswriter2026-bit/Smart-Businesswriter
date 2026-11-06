"""Automatic in-pipeline resolution of logged errors (product layer).

"Resolve" is not bookkeeping: given a logged error, this module diagnoses the
failure class, applies the deterministic remediations the pipeline can make on
its own, replays the failing problem after each, and reports every step. An
error is marked *verified solved* only when a replay passes.

What it can fix by itself (no invented content, no core edits):
  - rate limited / provider failure  -> replay (solve path swaps to the backup
    model automatically) and retry
  - input too large                  -> shorten the problem deterministically
    (normalise whitespace, drop separator lines, truncate at a line boundary)
    and replay
  - duplicated account line          -> drop exact duplicate lines (same account
    and same amount); differing amounts are never merged or invented
  - everything else                  -> replayed unchanged; an honest failure
    reason is returned and the error stays open
"""
import re

from . import ops_log as _ops_log

#: The statements model reader refuses inputs above 20000 characters.
MAX_INPUT = 18000


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


def _split_inline_accounts(text):
    """Split a one-line 'Cash 5000, Capital 5000' problem into account lines.

    Deterministic, no new figures: only commas/semicolons between segments that
    each carry a number become line breaks, and a leading cue ("Trial balance:")
    is removed from the first account.
    """
    text = str(text).strip()
    if not text or "\n" in text:
        return text
    parts = [p.strip() for p in re.split(r"[;,]", text) if p.strip()]
    if len(parts) < 2 or not all(re.search(r"\d", p) for p in parts):
        return text
    parts[0] = re.sub(r"^(?:the following balances?|trial balance|balances?)[^:]*:\s*", "", parts[0], flags=re.I)
    return "\n".join(p for p in parts if p)


def _shorten(text):
    """Deterministically shorten an over-long problem without inventing anything."""
    text = re.sub(r"[ \t]+", " ", str(text))
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line and not re.fullmatch(r"[-=_*~]{3,}", line)]
    text = "\n".join(lines)
    if len(text) <= MAX_INPUT:
        return text
    cut = text[:MAX_INPUT]
    boundary = cut.rfind("\n")
    if boundary < MAX_INPUT * 0.6:
        boundary = max(cut.rfind(". "), cut.rfind("; "))
    if boundary > 0:
        cut = cut[:boundary + 1]
    return cut.rstrip()


def _drop_duplicate_lines(text):
    """Drop exact duplicate account lines (same normalised content); keep the first."""
    seen, kept = set(), []
    for line in str(text).splitlines():
        key = re.sub(r"\s+", " ", line.strip().lower())
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        kept.append(line)
    return "\n".join(kept)


def _remediations(problem, category):
    """Ordered (strategy label, rewritten problem) pairs to replay."""
    attempts = []
    if category == "input_too_large":
        fixed = _shorten(problem)
        if fixed and fixed != problem:
            attempts.append(("shorten oversized input", fixed))
    if category == "duplicate_account":
        fixed = _drop_duplicate_lines(problem)
        if fixed and fixed != problem:
            attempts.append(("drop duplicate account lines", fixed))
    if category == "unreadable_layout":
        fixed = _split_inline_accounts(problem)
        if fixed and fixed != problem:
            attempts.append(("split inline account list into lines", fixed))
    attempts.append(("replay original problem", problem))
    return attempts


#: The fix model ladder: cheap flash first; if it cannot fix it, the pro model.
#: Both are on OpenCode Go. Override with BP_FIX_MODEL / BP_FIX_ESCALATION_MODEL.
FIX_MODEL = "deepseek-v4.1-flash"
ESCALATION_MODEL = "deepseek-v4-pro"


def _fix_models():
    import os
    return (os.environ.get("BP_FIX_MODEL", FIX_MODEL),
            os.environ.get("BP_FIX_ESCALATION_MODEL", ESCALATION_MODEL))


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


def resolve(error_id):
    """Attempt to resolve one logged error inside the pipeline.

    Ladder: deterministic remediations replayed on the fix model
    (deepseek-v4.1-flash); if none passes, the same attempts are replayed on the
    escalation model (deepseek-v4-pro). Returns a dict:
    {resolved, verified, attempted, steps, reason}.
    """
    record = _ops_log.get_error(error_id)
    if record is None:
        return {"resolved": False, "verified": False, "attempted": False,
                "steps": [], "reason": "unknown error_id"}
    problem = record.get("problem") or ""
    if not problem:
        return {"resolved": False, "verified": False, "attempted": False, "steps": [],
                "reason": "no replayable problem was stored for this error, so a fix cannot be verified"}

    category = diagnose(record.get("error", ""))
    attempts = _remediations(problem, category)
    steps = []
    fix_model, escalation_model = _fix_models()
    ladder = [(fix_model, attempts), (escalation_model, attempts)]
    for model, candidates in ladder:
        for label, candidate in candidates:
            first = _replay_on(candidate, model)
            status = first.get("status") or "error"
            steps.append({"strategy": label, "model": model, "outcome": status,
                          "detail": (first.get("error") or "")[:200]})
            if status == "ok":
                _ops_log.mark_error_verified(
                    error_id, "pipeline replayed the problem on %s and it passed" % model)
                _ops_log.log_resolution_attempt(error_id, category, steps, "solved")
                return {"resolved": True, "verified": True, "attempted": True,
                        "steps": steps, "model": model, "category": category,
                        "reason": "replay passed on %s after: %s" % (model, label)}

    _ops_log.log_resolution_attempt(error_id, category, steps, "still failing")
    return {"resolved": False, "verified": False, "attempted": True, "steps": steps,
            "reason": steps[-1]["detail"] if steps else "no remediation applied",
            "category": category}
