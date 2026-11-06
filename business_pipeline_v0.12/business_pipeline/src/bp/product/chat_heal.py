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


def _call_model(models, system, user):
    """Call a model and return the raw text, or None on failure.

    Retries up to 3 times on transient failures (rate limits, bad response shape).
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
    return None


# ── Problem generator ───────────────────────────────────────────────────────

def generate_problems_from_error(error_text, count=5, difficulty="medium"):
    """Reframe an error into an instruction and generate problems.

    Returns (problems: list[str], instruction: str, error: str or None).
    """
    instruction = (
        "The pipeline failed with this error: " + str(error_text)[:300] + ". "
        "Create " + str(count) + " realistic test problems that exercise the "
        "scenario described by this error. Include edge cases and variations."
    )
    problems, err = generate_problems(instruction, count, difficulty=difficulty)
    return problems, instruction, err


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
        "Return ONLY a JSON object: {\"problems\": [\"problem 1\", \"problem 2\", ...]}. "
        "No markdown, no extra text. Do not include reasoning or thinking. Output only the JSON."
    )
    user = json.dumps({"instruction": instruction, "count": count, "difficulty": difficulty}, ensure_ascii=False)
    raw = _call_model(models, system, user)
    if raw is None:
        return [], "model call failed"
    try:
        data = json.loads(raw.strip().strip("`").strip())
        if isinstance(data, dict) and isinstance(data.get("problems"), list):
            problems = [str(p).strip() for p in data["problems"] if str(p).strip()]
            return problems[:count], None
    except (json.JSONDecodeError, AttributeError):
        pass
    # Fallback: try to extract lines
    lines = [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith("{") and not line.startswith("}")]
    if lines:
        return lines[:count], None
    return [], "could not parse model response"


# ── Solver ──────────────────────────────────────────────────────────────────

def solve_problems(problems):
    """Solve a list of problems through the pipeline.

    Returns (results: list[dict], error: str or None).
    Each result: {problem, status, answer, error, gaps}.
    """
    from .. import methods
    results = []
    for problem in problems:
        result = {"problem": problem, "status": "unknown", "answer": None, "error": None, "gaps": []}
        try:
            # Try to detect the method from the problem text
            # For now, log the problem and mark as "needs manual solve"
            result["status"] = "logged"
            result["answer"] = "Problem logged for pipeline solve (manual step required)"
            _ops_log.log_run("chat", "solve", "logged", problem_text=problem)
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)[:200]
            _ops_log.log_error("chat", str(e), problem_text=problem)
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
