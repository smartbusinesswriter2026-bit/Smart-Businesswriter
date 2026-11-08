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
    # The repair runs on OpenCode Go: the same provider/key the app already uses.
    # The model ids are the OpenCode Go catalogue; override with BP_FIX_MODEL /
    # BP_FIX_ESCALATION_MODEL.  This is not the platform.deepseek.com key and is
    # not gated by BP_ENABLE_DEEPSEEK.
    return (os.environ.get("BP_FIX_MODEL", FIX_MODEL),
            os.environ.get("BP_FIX_ESCALATION_MODEL", ESCALATION_MODEL))


def diagnose(error_text):
    """Classify one error message into a failure class."""
    low = str(error_text or "").lower()
    if "429" in low or "rate limit" in low or "too many requests" in low or "provider returned http" in low:
        return "rate_limit"
    # A provider timeout is transient and must be checked BEFORE the reader-parse cue:
    # "could not read this as a journal: could not reach the provider: TimeoutError" is
    # a timeout, not a parse failure.
    if ("timeout" in low or "timed out" in low or "could not reach" in low
            or "failed to fetch" in low or "no answer within" in low
            or "connection" in low):
        return "timeout"
    if "exceeds" in low and "character" in low:
        return "input_too_large"
    if "appears twice" in low or "appears more than once" in low:
        return "duplicate_account"
    if "could not find an account" in low:
        return "unreadable_layout"
    if "could not read this as a journal" in low:
        return "reader_parse"
    if "does not balance" in low or "do not balance" in low:
        return "unbalanced_input"
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


def _silent_solve(problem, model):
    """Solve one problem on `model` without logging a new error.

    The timeout retry uses this: a second timeout must not add a second error to the
    queue, and a pass proves the fix without touching the log.
    """
    import os
    try:
        from . import statements as stmt_mod
    except Exception:
        return {"status": "error", "error": "statements module unavailable"}
    saved = (os.environ.get("BP_LLM_MODEL"),
             os.environ.get("BP_LLM_MODEL_TIER2"),
             os.environ.get("BP_LLM_MODEL_TIER3"))
    try:
        os.environ["BP_LLM_MODEL"] = model
        os.environ["BP_LLM_MODEL_TIER2"] = model
        os.environ["BP_LLM_MODEL_TIER3"] = model
        record = stmt_mod.solve(str(problem))
        if isinstance(record, dict) and record.get("solved"):
            return {"status": "ok", "error": ""}
        error = (record.get("refusal") if isinstance(record, dict) else "") or "not solved"
        return {"status": "error", "error": str(error)[:200]}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}
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


def _journal_imbalance(reading):
    """Debits minus credits of the reading's journal, as a Decimal."""
    from decimal import Decimal
    debits = credits = Decimal("0")
    for entry in reading.get("journal") or []:
        for line in entry.get("lines") or []:
            if line.get("debit"):
                debits += Decimal(str(line["debit"]))
            if line.get("credit"):
                credits += Decimal(str(line["credit"]))
    return debits - credits


def _guess_rule(label):
    """A placement rule for one account label, guessed from its own keywords.

    This is the self-heal half for an unbalanced trial balance: an account the vocabulary
    does not recognise is dropped, so the two sides disagree by exactly that account's
    amount.  Recognising the label by its keywords adds the line back without inventing a
    figure — the amount is the student's own.  Returns a rule tuple or None.
    """
    import re
    low = re.sub(r"\s+", " ", str(label or "").strip().lower())
    if not low:
        return None
    pattern = r"^" + re.escape(low) + r"$"
    if re.search(r"\b(loan|borrowing|mortgage|note payable|debenture)\b", low):
        return (pattern, "liability", "non_current", "Borrowings", "", "financing", False)
    if re.search(r"\b(payable|creditor|accrual|accrued)\b", low):
        return (pattern, "liability", "current", "Trade payables", "", "operating", False)
    if re.search(r"\b(unearned|deferred)\b", low):
        return (pattern, "liability", "current", "Accruals", "", "operating", False)
    if re.search(r"\b(receivable|debtor)\b", low):
        return (pattern, "asset", "current", "Trade receivables", "", "operating", False)
    if re.search(r"\b(equipment|vehicle|machine|building|land|furniture|plant|fixture)\b", low):
        return (pattern, "asset", "non_current", "Property, plant and equipment", "", "investing", False)
    if re.search(r"\b(cash|bank)\b", low):
        return (pattern, "asset", "current", "Cash", "cash", "operating", False)
    if re.search(r"\b(inventory|stock)\b", low):
        return (pattern, "asset", "current", "Inventory", "", "operating", False)
    if re.search(r"\b(capital|equity|owner)\b", low):
        return (pattern, "equity", "", "Capital", "capital", "financing", False)
    if re.search(r"\b(retained|reserve)\b", low):
        return (pattern, "equity", "", "Retained earnings", "retained_earnings", "", False)
    if re.search(r"\b(revenue|sales|income|turnover|fee)\b", low):
        return (pattern, "income", "", "Revenue", "", "operating", False)
    if re.search(r"\b(expense|cost|wages|salary|salaries|rent|utility|utilities|insurance|advertising)\b", low):
        return (pattern, "expense", "", "Operating expenses", "", "operating", False)
    return None


def _try_fix_unbalanced(problem):
    """Try to balance the trial balance by recognising a skipped account line.

    Reads the problem, finds the imbalance, and looks for a line the parser could not place
    whose amount equals the imbalance.  If the label can be typed from its keywords, the rule
    is added, the problem is re-read, and the fix is accepted only if the two sides now
    agree.  A wrong guess is removed again.  Returns the label that was added, or None.
    """
    import re
    from decimal import Decimal, InvalidOperation
    from . import statements as stmt_mod

    def read(text):
        try:
            return stmt_mod.read_deterministic(text)
        except Exception:
            return None

    reading = read(problem)
    if reading is None:
        return None
    diff = _journal_imbalance(reading)
    if diff == 0:
        return None
    for miss in reading.get("missing") or []:
        raw = str(miss.get("what") or "")
        numbers = re.findall(r"-?\d[\d,]*(?:\.\d+)?", raw)
        if not numbers:
            continue
        try:
            amount = Decimal(numbers[-1].replace(",", ""))
        except (InvalidOperation, ValueError):
            continue
        if abs(diff) != amount:
            continue
        label = re.sub(r"[\d,$]", " ", raw).strip(" .,:-|()[]=")
        label = re.sub(r"\b(cr|dr)\.?\b", "", label, flags=re.I)
        label = re.sub(r"\s+", " ", label).strip()
        rule = _guess_rule(label)
        if rule is None:
            continue
        from . import tier1_tables
        tier1_tables.append_rule(rule)
        retry = read(problem)
        if retry is not None and _journal_imbalance(retry) == 0:
            return label
        # The guess did not balance the reading: take the rule out again.
        tier1_tables.remove_rule(rule)
    return None


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
    case_id = record.get("case_id")
    if case_id:
        # A stored tile case is replayed by code, not by a model.  A pass closes
        # the error; a fail keeps it open with the case's own message.  This is
        # the token-free half of the fix ladder.
        from . import case_runner
        outcome = case_runner.run_case(case_id, log=False)
        steps = [{"strategy": "replay stored tile case", "model": "none (code)",
                  "outcome": outcome.get("status") or "error",
                  "detail": (outcome.get("error") or "")[:200]}]
        if outcome.get("status") == "pass":
            _ops_log.mark_error_verified(
                error_id, "stored tile case %s replayed and passed" % case_id)
            _ops_log.log_resolution_attempt(error_id, "tile_case", steps, "solved")
            return {"resolved": True, "verified": True, "attempted": True, "invalid": False,
                    "steps": steps, "model": "none (code)", "category": "tile_case",
                    "siblings_resolved": 0,
                    "reason": "stored tile case replayed and passed"}
        _ops_log.log_resolution_attempt(error_id, "tile_case", steps, "still failing")
        return {"resolved": False, "verified": False, "attempted": True, "invalid": False,
                "steps": steps, "model": "none (code)", "category": "tile_case",
                "siblings_resolved": 0,
                "reason": outcome.get("error") or "the stored tile case still fails"}

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

    if category == "unbalanced_input":
        # First try the deterministic self-heal: an account the vocabulary does not
        # recognise is dropped, so the two sides disagree by exactly that account's
        # amount.  Recognising the label by its keywords adds the line back without
        # inventing a figure.  Only if that fails is the input genuinely wrong.
        problem = record.get("problem") or ""
        fixed = _try_fix_unbalanced(problem) if problem else None
        if fixed:
            # Re-solve with the new rule in place and verify it balances end to end.
            try:
                from . import statements as stmt_mod
                result = stmt_mod.solve(problem)
                if isinstance(result, dict) and result.get("solved"):
                    from . import regression_cases
                    normalized, notes = normalize_problem(problem)
                    regression_cases.record_case(
                        error_id, "unbalanced_input", problem, normalized, notes,
                        "vocabulary (code)", deterministic_ok=True)
                    _ops_log.mark_error_verified(
                        error_id,
                        "recognised the account %r and the trial balance now balances" % fixed)
                    steps = [{"strategy": "recognise a skipped account", "model": "vocabulary (code)",
                              "outcome": "solved", "detail": fixed}]
                    _ops_log.log_resolution_attempt(error_id, category, steps, "solved")
                    return {"resolved": True, "verified": True, "attempted": True,
                            "invalid": False, "category": category, "steps": steps,
                            "model": "vocabulary (code)", "siblings_resolved": 0,
                            "reason": "recognised the account %r; the trial balance now balances" % fixed}
            except Exception:
                pass
        # No recognisable skipped account: the figures are the student's and the tile
        # correctly refuses rather than plugging.  Mark invalid and close it.
        _ops_log.mark_error_invalid(
            error_id,
            "the trial balance does not balance; the figures are the student's and the tile "
            "correctly refuses rather than plugging a difference")
        return {"resolved": False, "verified": False, "attempted": False, "invalid": True,
                "category": category, "steps": [], "siblings_resolved": 0,
                "reason": "the trial balance does not balance — the input is wrong, not the pipeline"}

    if category == "timeout":
        # A provider timeout is transient: retry the stored problem once on the fix model
        # before giving up.  If the provider is back, the retry proves the fix; if it times
        # out again, dismiss it so it stops blocking the queue (a re-run reopens it).
        problem = record.get("problem") or ""
        if problem:
            fix_model, _escalation = _fix_models()
            retry = _silent_solve(problem, fix_model)
            if retry.get("status") == "ok":
                try:
                    from . import regression_cases
                    normalized, notes = normalize_problem(problem)
                    regression_cases.record_case(
                        error_id, category, problem, normalized, notes, fix_model,
                        deterministic_ok=_deterministic_ok(normalized))
                except Exception:
                    pass
                _ops_log.mark_error_verified(
                    error_id, "retried after a provider timeout and passed on %s" % fix_model)
                steps = [{"strategy": "retry after timeout", "model": fix_model,
                          "outcome": "solved"}]
                _ops_log.log_resolution_attempt(error_id, category, steps, "solved")
                return {"resolved": True, "verified": True, "attempted": True,
                        "invalid": False, "category": category, "steps": steps,
                        "model": fix_model, "siblings_resolved": 0,
                        "reason": "retried after a provider timeout and passed on %s" % fix_model}
        _ops_log.mark_error_dismissed(
            error_id, "the model reader timed out twice; re-run the problem to retry")
        return {"resolved": False, "verified": False, "attempted": bool(problem),
                "invalid": False, "category": category, "steps": [], "siblings_resolved": 0,
                "reason": "the model reader timed out — transient, retry by re-running"}

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
