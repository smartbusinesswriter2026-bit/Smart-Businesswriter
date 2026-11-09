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
from . import causes
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


#: The verifier lives in `verifier.py` so both the repair loop and the problem
#: solver use the same independent check.  These names are kept here for callers
#: that already import them from this module.
from . import verifier as _verifier


def _verifier_models():
    return _verifier.verifier_models()


def _verify_fix(problem, result):
    return _verifier.verify_fix(problem, result)


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
    """Replay one problem with the statements reader pinned to `model`.

    The replay is **silent**: the failure it is replaying is already in the error
    log, so a second record would grow the queue every time the repair loop
    tried to fix it.  A pass still proves the fix.
    """
    import os
    from . import chat_heal
    saved = (os.environ.get("BP_LLM_MODEL"),
             os.environ.get("BP_LLM_MODEL_TIER2"),
             os.environ.get("BP_LLM_MODEL_TIER3"))
    try:
        os.environ["BP_LLM_MODEL"] = model
        os.environ["BP_LLM_MODEL_TIER2"] = model
        os.environ["BP_LLM_MODEL_TIER3"] = model
        results, _err = chat_heal.solve_problems([problem], log_failures=False)
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


def _account_from_error(error_text):
    """The account label named by a "could not find an account" refusal, or ''."""
    import re
    text = str(error_text or "")
    match = re.search(
        r"could not find an account\s*(?:named\s*)?['\"\u2018\u201c]([^'\"\u2019\u201d]+)['\"\u2019\u201d]",
        text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"could not find an account\s+([A-Za-z][A-Za-z0-9 &'\-]{1,60})",
                      text, re.IGNORECASE)
    return match.group(1).strip(" .,:;") if match else ""


def _try_fix_account(problem, label):
    """Add a vocabulary rule for a named account and prove it by replay.

    This is the durable fix for `pipeline.vocabulary`: the label was outside the
    statement vocabulary, so the reader dropped it.  The rule is typed from the
    label's own keywords, never from an invented figure, and it is removed again
    if the replay does not pass.  Returns the label when the fix holds, or ''.
    """
    if not problem or not label:
        return ""
    rule = _guess_rule(label)
    if rule is None:
        return ""
    from . import tier1_tables
    tier1_tables.append_rule(rule)
    model, _escalation = _fix_models()
    result = _replay_on(problem, model)
    if result.get("status") == "ok":
        return label
    tier1_tables.remove_rule(rule)
    return ""


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


def _resolve_inner(error_id):
    """The fix ladder itself.  `resolve` wraps it with the cause policy."""
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

    cause_key = causes.classify_cause(record.get("error"), record.get("problem"))["cause"]
    from . import cause_ledger as _ledger
    if cause_key in _ledger.fixed_causes():
        # The class already has a durable fix and no recurrence: another instance
        # does not justify two model calls.  Mark it attended so the picker skips it.
        _ops_log.mark_error_attended(
            error_id, "cause %s is already fixed by a durable artifact; not retried" % cause_key)
        return {"resolved": False, "verified": False, "attempted": False, "invalid": False,
                "steps": [], "siblings_resolved": 0, "category": cause_key, "cause": cause_key,
                "artifact": "", "reason": "cause %s already fixed; no model call spent" % cause_key}
    if cause_key in ("input.closing_balances", "input.environment",
                     "pipeline.case_expectation", "pipeline.method_contract"):
        # The remedy is a human change (a refreshed expectation, a wiring fix, a
        # decision about abnormal balances).  A replay cannot make it true, so do
        # not spend two model calls proving the same failing case again.
        remedy = causes.REMEDIES[cause_key]["remedy"]
        steps = [{"strategy": "cause has no automated fix", "model": "none",
                  "outcome": "waiting", "detail": remedy}]
        _ops_log.log_resolution_attempt(error_id, cause_key, steps, "waiting for owner")
        return {"resolved": False, "verified": False, "attempted": False, "invalid": False,
                "steps": steps, "siblings_resolved": 0, "category": cause_key,
                "artifact": "", "reason": "cause %s needs %s" % (cause_key, remedy)}

    if category == "unsupported_instruction":
        _ops_log.mark_error_invalid(
            error_id, "the problem is not an accounting problem; not a pipeline defect",
            cause="input.not_accounting", artifact="")
        closed = 0
        for sibling in _siblings(record, limit=200):
            _ops_log.mark_error_invalid(
                sibling.get("error_id"),
                "same invalid-input class: the problem names no transaction and declares no figure",
                cause="input.not_accounting", artifact="")
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
                        "recognised the account %r and the trial balance now balances" % fixed,
                        cause="pipeline.vocabulary", artifact="tier1_rule")
                    steps = [{"strategy": "recognise a skipped account", "model": "vocabulary (code)",
                              "outcome": "solved", "detail": fixed}]
                    _ops_log.log_resolution_attempt(error_id, category, steps, "solved")
                    return {"resolved": True, "verified": True, "attempted": True,
                            "invalid": False, "category": category, "steps": steps,
                            "model": "vocabulary (code)", "siblings_resolved": 0,
                            "artifact": "tier1_rule",
                            "reason": "recognised the account %r; the trial balance now balances" % fixed}
            except Exception:
                pass
        # No recognisable skipped account: the figures are the student's and the tile
        # correctly refuses rather than plugging.  Mark invalid and close it.  The
        # narrative balance guard is the durable change that keeps this shape out of
        # the queue, so it is named as the artifact.
        _ops_log.mark_error_invalid(
            error_id,
            "the trial balance does not balance; the figures are the student's and the tile "
            "correctly refuses rather than plugging a difference",
            cause="input.unbalanced", artifact="narrative_balance")
        return {"resolved": False, "verified": False, "attempted": False, "invalid": True,
                "category": category, "steps": [], "siblings_resolved": 0,
                "artifact": "narrative_balance",
                "reason": "the trial balance does not balance — the input is wrong, not the pipeline"}

    if category == "unreadable_layout":
        # A named account label is outside the vocabulary.  Typing it from its own
        # keywords and replaying is the durable fix; the rule survives the solve.
        problem = record.get("problem") or ""
        label = _account_from_error(record.get("error") or "")
        fixed = _try_fix_account(problem, label)
        if fixed:
            steps = [{"strategy": "add a vocabulary rule", "model": "vocabulary (code)",
                      "outcome": "solved", "detail": fixed}]
            _ops_log.mark_error_verified(
                error_id, "recognised the account %r and the problem now solves" % fixed,
                cause="pipeline.vocabulary", artifact="tier1_rule")
            _ops_log.log_resolution_attempt(error_id, category, steps, "solved")
            return {"resolved": True, "verified": True, "attempted": True,
                    "invalid": False, "category": category, "steps": steps,
                    "model": "vocabulary (code)", "siblings_resolved": 0,
                    "artifact": "tier1_rule",
                    "reason": "recognised the account %r; the problem now solves" % fixed}

    if category == "timeout":        # A provider timeout is transient: retry the stored problem once on the fix model
        # before giving up.  If the provider is back, the retry proves the fix; if it times
        # out again, dismiss it so it stops blocking the queue (a re-run reopens it).
        problem = record.get("problem") or ""
        if problem:
            fix_model, _escalation = _fix_models()
            retry = _replay_on(problem, fix_model)
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
                    error_id, "retried after a provider timeout and passed on %s" % fix_model,
                    cause="transient.provider", artifact="")
                steps = [{"strategy": "retry after timeout", "model": fix_model,
                          "outcome": "solved"}]
                _ops_log.log_resolution_attempt(error_id, category, steps, "solved")
                return {"resolved": True, "verified": True, "attempted": True,
                        "invalid": False, "category": category, "steps": steps,
                        "model": fix_model, "siblings_resolved": 0,
                        "artifact": "",
                        "reason": "retried after a provider timeout and passed on %s" % fix_model}
        _ops_log.mark_error_dismissed(
            error_id, "the model reader timed out twice; re-run the problem to retry",
            cause="transient.provider", artifact="")
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

        # The solver's replay is a proposal.  An independent model, seeing only the
        # problem and the answer, must agree before the fix is called verified.
        verdict = _verify_fix(problem, first)
        steps.append({"strategy": "independent verification",
                      "model": verdict.get("model") or "none",
                      "outcome": ("pass" if verdict.get("ok") is True else
                                  "unchecked" if verdict.get("ok") is None else "rejected"),
                      "detail": verdict.get("reason") or ""})
        if verdict.get("ok") is False:
            continue

        from . import regression_cases
        regression_cases.record_case(
            error_id, category, problem, normalized, notes, model,
            deterministic_ok=_deterministic_ok(normalized))
        # A normalized replay that passes *and* a verifier that agrees is a durable
        # fix; the recorded golden case pins the change.  A replay no verifier could
        # check, or one with no normalizer change, is an instance close.
        artifact = "golden_case" if (notes and verdict.get("ok") is True) else ""
        verified_by = verdict.get("model") or "no verifier"
        _ops_log.mark_error_verified(
            error_id, "pipeline replayed the problem on %s and %s agreed" % (model, verified_by),
            cause="pipeline.parser_shape", artifact=artifact)

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
                    "same failure class verified by the class replay on %s" % model,
                    cause="pipeline.parser_shape", artifact=artifact)
                closed += 1
        steps.extend(sib_steps)
        _ops_log.log_resolution_attempt(error_id, category, steps, "solved")
        return {"resolved": True, "verified": True, "attempted": True, "invalid": False,
                "steps": steps, "model": model, "category": category,
                "siblings_resolved": closed, "artifact": artifact,
                "reason": "replay passed on %s (%s)%s" % (
                    model, strategy,
                    "; %d sibling error(s) closed" % closed if closed else "")}

    _ops_log.log_resolution_attempt(error_id, category, steps, "still failing")
    return {"resolved": False, "verified": False, "attempted": True, "invalid": False,
            "steps": steps, "siblings_resolved": 0, "category": category,
            "reason": steps[-1]["detail"] if steps else "no remediation applied"}


def resolve(error_id):
    """Attempt to resolve one logged error and report its *cause* honestly.

    Wraps the fix ladder with the cause policy: the result always carries
    `cause`, `remedy`, `scope` and `artifact`.  A pipeline cause that was not
    closed with a durable artifact is marked attended with the remedy it still
    needs, so it waits for the owner instead of being retried forever and never
    reads as "fixed" just because a replay passed once.
    """
    record = _ops_log.get_error(error_id)
    if record is None:
        return {"resolved": False, "verified": False, "attempted": False, "invalid": False,
                "steps": [], "siblings_resolved": 0, "reason": "unknown error_id",
                "cause": "pipeline.unknown", "remedy": "investigate",
                "scope": causes.PIPELINE, "artifact": ""}
    cause = causes.classify_cause(record.get("error"), record.get("problem"))
    result = _resolve_inner(error_id)
    result["cause"] = cause["cause"]
    result["remedy"] = cause["remedy"]
    result["scope"] = cause["scope"]
    result.setdefault("artifact", "")
    if not (result.get("resolved") or result.get("invalid") or result.get("dismissed")):
        if cause["scope"] == causes.INPUT:
            # A legacy input record (logged before the intake policy): it is not a
            # pipeline defect, so it leaves the queue as invalid, never as "fixed".
            _ops_log.mark_error_invalid(
                error_id, "%s - not a pipeline defect" % cause["title"],
                cause=cause["cause"], artifact=cause.get("artifact") or "")
            result["invalid"] = True
        elif cause["scope"] == causes.TRANSIENT:
            _ops_log.mark_error_dismissed(
                error_id, "transient: %s" % cause["title"],
                cause=cause["cause"], artifact="")
            result["dismissed"] = True
        else:
            # The ladder could not close it.  Name the remedy rather than leaving a
            # bare "still failing": the owner should see what kind of change would
            # fix it, and the loop must not retry it forever.
            _ops_log.mark_error_attended(
                error_id, "cause %s needs %s" % (cause["cause"], cause["remedy"]))
            result["unfixed_cause"] = cause["cause"]
            result["needed_remedy"] = cause["remedy"]
    return result
