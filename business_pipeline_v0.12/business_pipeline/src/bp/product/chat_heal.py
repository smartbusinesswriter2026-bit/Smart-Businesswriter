"""Self-improvement chat box backend (product layer, stdlib only).

Three-model loop:
  1. Problem generator — creates N test problems from an instruction
  2. Solver — solves each problem through the pipeline
  3. Improvement writer — reviews failures, proposes improvements
  4. Code proposer — writes a diff + test for a validation finding
     (never applied; owner approval only)

Uses the existing llm module. Model selection follows the same env-var
pattern as the rest of the product (BP_LLM_PROVIDER, BP_LLM_MODEL,
PROSE_MODEL). Each role can be overridden independently:

    BP_HEAL_GEN_PROVIDER / BP_HEAL_GEN_MODEL   (problem generator)
    BP_HEAL_SOLVER_PROVIDER / BP_HEAL_SOLVER_MODEL (solver)
    BP_HEAL_IMPROVE_PROVIDER / BP_HEAL_IMPROVE_MODEL (improvement writer)
    BP_HEAL_CODE_PROVIDER / BP_HEAL_CODE_MODEL (code proposer)
    (BP_HEAL_CODE_MODEL default is set in Backend/.env; an easy override
     is kimi-k2.7-code for tricky files)

Falls back to the default model for any role not configured.
"""
import json
import os
import re
from pathlib import Path

from . import ops_log as _ops_log

# ── Model helpers ──────────────────────────────────────────────────────────

def _models_for(role):
    """Return llm.Models for a role, or None if not configured.

    Role overrides replace (never setdefault) the global provider/model pair
    and are applied only for the life of this call, so the process env is not
    permanently mutated. There is no DeepSeek fallback: with no provider
    configured, the role is simply unavailable.
    """
    from .. import llm
    provider_var = "BP_HEAL_%s_PROVIDER" % role.upper()
    model_var = "BP_HEAL_%s_MODEL" % role.upper()
    override_provider = os.environ.get(provider_var)
    override_model = os.environ.get(model_var)
    saved = (os.environ.get("BP_LLM_PROVIDER"), os.environ.get("BP_LLM_MODEL"))
    try:
        if override_provider or override_model:
            if override_provider:
                os.environ["BP_LLM_PROVIDER"] = override_provider
            if override_model:
                os.environ["BP_LLM_MODEL"] = override_model
        models = llm.from_env()
        if models is not None:
            models.config.max_output_tokens = 4000
            models.config.max_input_chars = 30000
        return models
    finally:
        for name, value in zip(("BP_LLM_PROVIDER", "BP_LLM_MODEL"), saved):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


#: Backup model when the free model fails (rate limit, bad response shape, error).
#: Same OpenCode Go provider/key — the paid deepseek flash. Override with BP_LLM_FALLBACK_MODEL.
FALLBACK_MODEL = "deepseek-v4.1-flash"


def _call_model(models, system, user):
    """Call a model and return the raw text, or None on failure.

    Order of use: beam (free) first, retried up to 3 times on transient
    failures; when beam is exhausted (rate limit, error, bad shape), switch
    to the backup model (deepseek flash, same OpenCode Go key).
    """
    if models is None:
        return None
    import time
    for attempt in range(3):
        try:
            result = models.call("builder", "chat_heal", "v1", system, user, consent=True)
            if isinstance(result, tuple) and len(result) >= 1:
                return result[0]
            return str(result)
        except Exception:
            if attempt < 2:
                time.sleep(1)
            continue
    return _call_fallback(system, user)


def _call_fallback(system, user, task_label="chat_heal"):
    """Backup call on the fallback model (deepseek flash on OpenCode Go)."""
    import os
    from .. import llm
    fallback = os.environ.get("BP_LLM_FALLBACK_MODEL", FALLBACK_MODEL)
    if not fallback or fallback == os.environ.get("BP_LLM_MODEL"):
        return None
    saved = os.environ.get("BP_LLM_MODEL")
    try:
        os.environ["BP_LLM_MODEL"] = fallback
        backup = llm.from_env()
    finally:
        if saved is None:
            os.environ.pop("BP_LLM_MODEL", None)
        else:
            os.environ["BP_LLM_MODEL"] = saved
    if backup is None:
        return None
    backup.config.max_output_tokens = 4000
    backup.config.max_input_chars = 30000
    for attempt in range(2):
        try:
            result = backup.call("builder", task_label, "v1", system, user, consent=True)
            if isinstance(result, tuple) and len(result) >= 1:
                return result[0]
            return str(result)
        except Exception:
            if attempt < 1:
                time.sleep(1)
            continue
    return None


# ── Problem generator ───────────────────────────────────────────────────────

#: Reasoning prefixes that leak from a reasoning model into problem text.
_REASONING_PREFIXES = (
    "we need", "we must", "we should", "we can", "we'll", "need ", "need craft",
    "let's", "let me", "okay", "ok,", "i need", "i will", "i'll", "thinking",
    "plan:", "so ", "now ", "first,", "the user wants", "the instruction asks",
    "output only", "answer only", "here's", "here is",
)


def _clean_problem(text):
    """Strip reasoning noise from one generated problem; '' when nothing usable."""
    s = str(text).strip().strip('"').strip()
    s = re.sub(r'^(?:\d+[.)]\s*|[-*]\s*)', '', s)
    changed = True
    while changed:
        changed = False
        low = s.lower()
        for prefix in _REASONING_PREFIXES:
            if low.startswith(prefix):
                m = re.search(r'[.!?:]\s+', s)
                if m:
                    s = s[m.end():].strip()
                    changed = True
                else:
                    return ""
                break
    if len(s) < 20:
        return ""
    return s


def _parse_problems(raw, count):
    """Parse model output into clean problems (JSON first, then numbered lines)."""
    text = str(raw).strip().strip("`").strip()
    data = None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, AttributeError):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                data = None
    if not isinstance(data, dict):
        # retry with a loose brace scan
        m = re.search(r'\{.*\}', text, re.S)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                data = None
    candidates = []
    if isinstance(data, dict) and isinstance(data.get("problems"), list):
        candidates = [str(p) for p in data["problems"]]
    else:
        candidates = [line for line in text.splitlines()
                      if line.strip() and not line.strip().startswith(("{", "}", "[", "]"))]
    problems, seen = [], set()
    for item in candidates:
        clean = _clean_problem(item)
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            problems.append(clean)
    return problems[:count]


def generate_problems_from_error(error_text, count=5, difficulty="medium"):
    """Reframe an error into an instruction and generate problems.

    The error is a **defect report**, not a problem to solve.  The generated
    problems exercise the same failure class but must themselves be valid and
    fully declared: a trial balance must balance, and every figure the reader
    needs must be written next to its label.  An unbalanced trial balance in the
    error text must never be copied into a generated problem.

    Returns (problems: list[str], instruction: str, error: str or None).
    """
    instruction = (
        "The pipeline refused an input with this error: " + str(error_text)[:300] + ". "
        "That error is a defect report, not a problem to solve. Create " + str(count) + " "
        "realistic test problems that exercise the same failure class, but every problem "
        "you write must be VALID and fully declared: state the period, name the "
        "transaction or the accounts, and write every figure next to its label. A trial "
        "balance MUST balance (total debits equal total credits). Do not copy the "
        "unbalanced totals or the numbers from the error; write fresh, consistent "
        "figures. Include edge cases and variations, but never a problem that cannot be "
        "answered from the figures it states."
    )
    problems, err = generate_problems(instruction, count, difficulty=difficulty)
    return problems, instruction, err


def _valid_problems(problems):
    """Drop a generated problem that cannot be answered as written.

    Two failure classes are fixtures, not pipeline defects: a trial balance whose
    two sides do not agree, and a problem that declares no figure at all (the
    reader then says "names no transaction and declares no figure").  Either is
    dropped before it reaches the solver and the pass rate.
    """
    from .problem_norm import trial_balance_imbalance
    import re as _re
    kept = []
    for problem in problems or []:
        text = str(problem or "")
        if not any(ch.isdigit() for ch in text):
            continue
        if not any(cue in text.lower() for cue in (
                "debit", "credit", "balance", "journal", "trial balance", "revenue",
                "expense", "cash", "receivable", "payable", "equity", "entry")):
            continue
        # A problem that states its own totals must state equal ones.  The
        # balance parser reads the account lines; this catches the case where
        # only the summary totals are written.
        debits = _re.search(r"debits?\s*(?:of|are|total(?:led)?|:)?\s*([0-9][0-9,.]*)", text, _re.I)
        credits = _re.search(r"credits?\s*(?:of|are|total(?:led)?|:)?\s*([0-9][0-9,.]*)", text, _re.I)
        if debits and credits:
            try:
                left = float(debits.group(1).replace(",", ""))
                right = float(credits.group(1).replace(",", ""))
                if abs(left - right) > 0.005:
                    continue
            except ValueError:
                pass
        imbalance = trial_balance_imbalance(text)
        if imbalance is not None and imbalance != 0:
            continue
        kept.append(text)
    return kept


def generate_problems(instruction, count=5, difficulty="medium"):
    """Generate N test problems from an instruction.

    difficulty: easy, medium, hard, expert (stress test)

    Returns (problems: list[str], error: str or None).
    """
    models = _models_for("gen")
    if models is None:
        return [], "no model configured (set BP_LLM_PROVIDER / BP_LLM_MODEL)"

    diff_instructions = {
        "easy": "Make problems simple and clear with all values given explicitly.",
        "medium": "Make problems moderately complex, combining 2-3 concepts.",
        "hard": "Make problems complex with missing information, edge cases, and multi-step reasoning.",
        "expert": "Make problems expert-level stress tests: contradictory data, multiple periods, unusual account placements, tricky adjustments, boundary values, and scenarios designed to break the pipeline. Include malformed inputs, ambiguous wording, and edge cases.",
    }
    diff_note = diff_instructions.get(difficulty, diff_instructions["medium"])

    system = (
        "You are a test-problem generator for a business analysis pipeline. "
        "Given an instruction and a count, create that many distinct test problems "
        "that exercise the pipeline. Each problem should be a realistic business "
        "analysis question or scenario. " + diff_note + " "
        "Vary the format: some as word problems, some as trial balances, some as journal entries, "
        "some as narrative instructions. "
        "A trial balance you write MUST balance: the total debits must equal the total credits. "
        "Check that before you return it. "
        "Return ONLY a JSON object: {\"problems\": [\"problem 1\", \"problem 2\", ...]}. "
        "No markdown, no extra text. Do not include reasoning or thinking. Output only the JSON."
    )
    user = json.dumps({"instruction": instruction, "count": count, "difficulty": difficulty}, ensure_ascii=False)
    raw = _call_model(models, system, user)
    problems = _valid_problems(_parse_problems(raw, count)) if raw else []
    if problems:
        return problems[:count], None
    # One strict retry: reasoning leaked out and no usable problems came back
    raw2 = _call_model(
        models,
        "You generate test problems. Output ONLY compact JSON like "
        '{"problems": ["...", "..."]}. No reasoning, no markdown, no commentary. '
        "Every trial balance must balance: total debits must equal total credits.",
        user)
    if raw2 is None:
        return [], "model call failed"
    problems = _valid_problems(_parse_problems(raw2, count))
    if problems:
        return problems[:count], None
    return [], "could not parse model response (or every generated trial balance was out of balance)"


# ── Solver ──────────────────────────────────────────────────────────────────

def _looks_rate_limited(text):
    """Whether an error message looks like a rate limit / transient provider failure."""
    low = str(text).lower()
    return ("429" in low or "rate limit" in low or "too many requests" in low
            or "provider returned http" in low or "could not reach the provider" in low
            or "unexpected response shape" in low)


def _solve_with_fallback(problem):
    """Re-solve after a rate-limit failure, using the backup model (deepseek flash).

    The statements core reads BP_LLM_MODEL per call, so swapping the env for the
    retry sends the model reader to the paid fallback on the same provider.
    """
    import os as _os
    from .. import llm as _llm
    from . import statements as stmt_mod
    fallback = _os.environ.get("BP_LLM_FALLBACK_MODEL", FALLBACK_MODEL)
    if not fallback or fallback == _os.environ.get("BP_LLM_MODEL"):
        return None
    saved = (_os.environ.get("BP_LLM_MODEL"), _os.environ.get("BP_LLM_MODEL_TIER2"))
    try:
        _os.environ["BP_LLM_MODEL"] = fallback
        _os.environ["BP_LLM_MODEL_TIER2"] = fallback
        _llm.from_env(tier=1)  # validates the fallback model is configured
        return stmt_mod.solve(str(problem))
    except Exception:
        return None
    finally:
        for name, value in zip(("BP_LLM_MODEL", "BP_LLM_MODEL_TIER2"), saved):
            if value is None:
                _os.environ.pop(name, None)
            else:
                _os.environ[name] = value


def solve_problems(problems, log_failures=True):
    """Solve a list of problems through the pipeline.

    Every problem passes through the deterministic normalizers first (one-line
    account lists, duplicate lines, oversized input), so the frozen parser
    always sees input in the shape it accepts — not only when Resolve is used.

    ``log_failures=False`` is for a **replay of a known failure** inside the
    repair loop: the error is already in the log, so logging the same failure
    again would grow the queue every time the loop tried to fix it.

    Returns (results: list[dict], error: str or None).
    Each result: {problem, status, answer, error, gaps, normalization}.
    """
    from .problem_norm import normalize_problem, trial_balance_imbalance
    results = []
    for problem in problems:
        result = {"problem": problem, "status": "unknown", "answer": None, "error": None, "gaps": []}
        normalized, norm_notes = normalize_problem(problem)
        if norm_notes:
            result["normalization"] = norm_notes
        # A generated trial balance that does not balance is an invalid test fixture,
        # not a pipeline failure: no pipeline change can make two figures the generator
        # wrote agree.  Mark it invalid before solving, so it is not counted against
        # the pipeline and does not reach the fixer as a defect.
        imbalance = trial_balance_imbalance(normalized)
        if imbalance is not None and imbalance != 0:
            result["status"] = "invalid"
            result["invalid"] = True
            result["error"] = ("the generated trial balance does not balance (out by %s); "
                               "it is an invalid test fixture, not a pipeline defect" % imbalance)
            results.append(result)
            continue
        try:
            from . import statements as stmt_mod
            try:
                record = stmt_mod.solve(str(normalized))
            except Exception as first_err:
                if _looks_rate_limited(first_err):
                    # Rate limit on beam -> retry once on the backup model (deepseek flash)
                    record = _solve_with_fallback(normalized)
                    if record is None:
                        raise first_err
                else:
                    raise
            if isinstance(record, dict):
                if record.get("solved"):
                    result["status"] = "ok"
                    result["answer"] = "Solved"
                    result["gaps"] = record.get("working", {}).get("missing", []) or []
                else:
                    refusal = str(record.get("refusal") or record.get("error") or "not solved")
                    result["error"] = refusal[:200]
                    if "does not balance" in refusal.lower():
                        # The figures the problem declared do not balance.  That is an
                        # invalid test fixture (the generator wrote them), not a pipeline
                        # defect: no pipeline change can make two figures agree.  Mark it
                        # invalid instead of logging it as a pipeline error.
                        result["status"] = "invalid"
                        result["invalid"] = True
                        result["error"] = ("the trial balance in the problem does not balance; "
                                           "it is an invalid test fixture, not a pipeline defect")
                    else:
                        result["status"] = "error"
                        if _looks_rate_limited(rl_error := (record.get("error") or result["error"])):
                            retry = _solve_with_fallback(problem)
                            if isinstance(retry, dict) and retry.get("solved"):
                                result["status"] = "ok"
                                result["answer"] = "Solved"
                                result["gaps"] = retry.get("working", {}).get("missing", []) or []
                        result["gaps"] = result["gaps"] or record.get("working", {}).get("missing", []) or []
                        # Log to error log so it appears in Self-Healing panel
                        if log_failures:
                            _ops_log.log_error("statements", result["error"], problem_text=problem,
                                               gap_label=result["error"][:80])
            else:
                result["status"] = "error"
                result["error"] = "unexpected result type"
                if log_failures:
                    _ops_log.log_error("statements", "unexpected result type", problem_text=problem)
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)[:200]
            if log_failures:
                _ops_log.log_error("statements", str(e)[:200], problem_text=problem)
        results.append(result)
    return results, None


# ── Improvement writer ──────────────────────────────────────────────────────

def write_improvements(failures):
    """Review failures and propose improvements.

    Returns (improvements: list[dict], error: str or None).
    Each improvement: {problem, suggestion, type}.
    """
    models = _models_for("improve")
    if models is None:
        return [], "no model configured (set BP_LLM_PROVIDER / BP_LLM_MODEL)"
    if not failures:
        return [], "no failures to review"
    system = (
        "You are an improvement writer for a business analysis pipeline. "
        "Given a list of failures (problems the pipeline could not solve), "
        "propose improvements: what data table entry, rule, or schedule schema "
        "should be added or changed to fix each failure. "
        "Each improvement must be a data-only change (no code changes). "
        "Return ONLY a JSON object: {\"improvements\": [{\"problem\": \"...\", "
        "\"suggestion\": \"...\", \"type\": \"rule|schema|synonym\"}]}. "
        "No markdown, no extra text."
    )
    user = json.dumps({"failures": failures}, ensure_ascii=False)
    raw = _call_model(models, system, user)
    if raw is None:
        return [], "model call failed"
    try:
        data = json.loads(raw.strip().strip("`").strip())
        if isinstance(data, dict) and isinstance(data.get("improvements"), list):
            improvements = []
            for imp in data["improvements"]:
                if isinstance(imp, dict):
                    improvements.append({
                        "problem": str(imp.get("problem", ""))[:200],
                        "suggestion": str(imp.get("suggestion", ""))[:500],
                        "type": str(imp.get("type", "rule"))[:50],
                    })
            return improvements, None
    except (json.JSONDecodeError, AttributeError):
        pass
    return [], "could not parse model response"


def propose_code_fix(finding, source_files=None):
    """Propose a code fix for a validation finding.

    `finding` is a finding dict (rule, subject, feature, section, message, ...).
    `source_files` is a list of {path, content} dicts (or paths) the model
    may read.  Returns (proposal: dict, error: str or None).  The proposal
    has keys: summary, diff, test, files.  It is NEVER applied automatically.
    """
    source_files = source_files or []
    # resolve paths to contents if strings were passed
    resolved = []
    for sf in source_files:
        if isinstance(sf, str):
            try:
                with open(sf, encoding="utf-8") as fh:
                    resolved.append({"path": sf, "content": fh.read()[:8000]})
            except OSError:
                continue
        elif isinstance(sf, dict):
            resolved.append({"path": sf.get("path", ""), "content": str(sf.get("content", ""))[:8000]})
    models = _models_for("code")
    if models is None:
        return None, "no model configured (set BP_HEAL_CODE_PROVIDER / BP_HEAL_CODE_MODEL)"
    system = (
        "You are a code proposer for a business analysis pipeline. "
        "Given a validation finding and the relevant source files, propose a "
        "minimal patch that addresses the finding. You may ONLY suggest changes "
        "to source files shown to you; never invent files. "
        "Return ONLY a JSON object with keys: "
        "\"summary\" (one sentence), "
        "\"diff\" (unified diff text), "
        "\"test\" (a pytest test that would fail before and pass after), "
        "\"files\" (list of paths touched). "
        "No markdown, no extra text."
    )
    user = json.dumps({"finding": finding, "source_files": resolved}, ensure_ascii=False)
    raw = _call_model(models, system, user)
    if raw is None:
        return None, "model call failed"
    try:
        data = json.loads(raw.strip().strip("`").strip())
        if isinstance(data, dict):
            return {
                "summary": str(data.get("summary", ""))[:300],
                "diff": str(data.get("diff", ""))[:8000],
                "test": str(data.get("test", ""))[:8000],
                "files": [str(p) for p in (data.get("files") or [])],
            }, None
    except (json.JSONDecodeError, AttributeError):
        pass
    return None, "could not parse model response"
