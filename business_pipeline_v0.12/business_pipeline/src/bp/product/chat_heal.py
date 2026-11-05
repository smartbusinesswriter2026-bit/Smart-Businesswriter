"""Self-improvement chat box backend (product layer, stdlib only).

Three-model loop:
  1. Problem generator — creates N test problems from an instruction
  2. Solver — solves each problem through the pipeline
  3. Improvement writer — reviews failures, proposes improvements

Uses the existing llm module. Model selection follows the same env-var
pattern as the rest of the product (BP_LLM_PROVIDER, BP_LLM_MODEL,
PROSE_MODEL). Each role can be overridden independently:

    BP_HEAL_GEN_PROVIDER / BP_HEAL_GEN_MODEL   (problem generator)
    BP_HEAL_SOLVER_PROVIDER / BP_HEAL_SOLVER_MODEL (solver)
    BP_HEAL_IMPROVE_PROVIDER / BP_HEAL_IMPROVE_MODEL (improvement writer)

Falls back to the default model for any role not configured.
"""
import json
import os
from pathlib import Path

from . import ops_log as _ops_log

# ── Model helpers ──────────────────────────────────────────────────────────

def _models_for(role):
    """Return llm.Models for a role, or None if not configured."""
    from .. import llm
    # Role-specific overrides
    provider_var = "BP_HEAL_%s_PROVIDER" % role.upper()
    model_var = "BP_HEAL_%s_MODEL" % role.upper()
    if os.environ.get(provider_var) or os.environ.get(model_var):
        os.environ.setdefault("BP_LLM_PROVIDER", os.environ.get(provider_var, "deepseek"))
        os.environ.setdefault("BP_LLM_MODEL", os.environ.get(model_var, "deepseek-chat"))
    # Fall back to DeepSeek if key is available but provider not set
    if not os.environ.get("BP_LLM_PROVIDER") and os.environ.get("DEEPSEEK_API_KEY"):
        os.environ["BP_LLM_PROVIDER"] = "deepseek"
        os.environ.setdefault("BP_LLM_MODEL", "deepseek-chat")
    return llm.from_env()


def _call_model(models, system, user):
    """Call a model and return the raw text, or None on failure."""
    if models is None:
        return None
    try:
        result = models.call("builder", "chat_heal", "v1", system, user, consent=True)
        if isinstance(result, tuple) and len(result) >= 1:
            return result[0]
        return str(result)
    except Exception:
        return None


# ── Problem generator ───────────────────────────────────────────────────────

def generate_problems_from_error(error_text, count=5):
    """Reframe an error into an instruction and generate problems.

    Returns (problems: list[str], instruction: str, error: str or None).
    """
    instruction = (
        "The pipeline failed with this error: " + str(error_text)[:300] + ". "
        "Create " + str(count) + " realistic test problems that exercise the "
        "scenario described by this error. Include edge cases and variations."
    )
    problems, err = generate_problems(instruction, count)
    return problems, instruction, err


def generate_problems(instruction, count=5):
    """Generate N test problems from an instruction.

    Returns (problems: list[str], error: str or None).
    """
    models = _models_for("gen")
    if models is None:
        return [], "no model configured (set BP_LLM_PROVIDER / BP_LLM_MODEL)"
    system = (
        "You are a test-problem generator for a business analysis pipeline. "
        "Given an instruction and a count, create that many distinct test problems "
        "that exercise the pipeline. Each problem should be a realistic business "
        "analysis question or scenario. "
        "Return ONLY a JSON object: {\"problems\": [\"problem 1\", \"problem 2\", ...]}. "
        "No markdown, no extra text."
    )
    user = json.dumps({"instruction": instruction, "count": count}, ensure_ascii=False)
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
