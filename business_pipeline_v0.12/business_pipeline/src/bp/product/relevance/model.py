"""RRA model helper.

One place that resolves the RRA's model and makes the call, so every
model-driven stage (S1 discovery, S2 extraction, S5 drafting) uses the same
provider, the same consent rule and the same budget.

Configuration (mirrors autoresearch):
    BP_RELEVANCE_PROVIDER  provider id (default: whatever BP_LLM_PROVIDER says)
    BP_RELEVANCE_MODEL     model id (default: BP_LLM_MODEL)
    BP_RELEVANCE_EXTRACT_MODEL   model for S2 (the passage that matters)
    BP_RELEVANCE_DESIGN_MODEL    model for S5 (the gap spec)
    BP_RELEVANCE_DISCOVERY_MODEL model for S1b (the search query)
    BP_RELEVANCE_MAX_TOKENS  per-call output cap (default 2000)
    BP_RELEVANCE_MAX_INPUT   per-call input cap (default 30000)
    BP_RELEVANCE_BUDGET_TOKENS  total token budget per run (default 200000)
    BP_RELEVANCE_ENABLED   set to 0 to forbid every model call (default 1)

**Per-stage models (decision D-4).**  Two stages read the outside world and
one writes the spec; if all three use the same model, a mis-reading in one is
mirrored in the other.  Set the per-stage variables to different models and
the stages decorrelate.  The stage that *decides* is still code: S4 (the
skeptic) and S6 (the evaluator) are deterministic and never call a model.

No model call is made without the owner's consent flag being on; the caller
passes consent=True because the owner configured the provider deliberately.
Stdlib only.  No new runtime dependency.
"""
import json
import os

#: The default model ladder's task names, and the variable that overrides the
#: model for that stage.  A stage with no override uses BP_RELEVANCE_MODEL.
STAGE_MODELS = {
    "relevance-discovery-query": "BP_RELEVANCE_DISCOVERY_MODEL",
    "relevance-extract": "BP_RELEVANCE_EXTRACT_MODEL",
    "relevance-design": "BP_RELEVANCE_DESIGN_MODEL",
}

#: The RRA never calls a model when this is 0.
DEFAULT_ENABLED = "1"
DEFAULT_MAX_TOKENS = 2000
DEFAULT_MAX_INPUT = 30000
DEFAULT_BUDGET_TOKENS = 200000


def enabled():
    from . import config as _config
    return _config.model_enabled()


def budget_tokens():
    from . import config as _config
    return _config.budget_tokens()


def max_tokens():
    from . import config as _config
    return _config.max_tokens()


def max_input_chars():
    from . import config as _config
    return _config.max_input()


def model_names(task=""):
    """Return (provider, model) the RRA would use for a task.

    A per-stage variable wins over BP_RELEVANCE_MODEL, so two stages can read
    and write with different models (decision D-4).
    """
    provider = os.environ.get("BP_RELEVANCE_PROVIDER") or os.environ.get("BP_LLM_PROVIDER") or ""
    variable = STAGE_MODELS.get(task or "")
    model = ""
    if variable:
        model = os.environ.get(variable) or ""
    if not model:
        model = os.environ.get("BP_RELEVANCE_MODEL") or os.environ.get("BP_LLM_MODEL") or ""
    return provider.strip(), model.strip()


def _models(task=""):
    """Build an llm.Models with the RRA's provider/model applied for one call.

    Returns (models, error).  The process env is restored before returning, so
    one stage never changes another stage's model.
    """
    if not enabled():
        return None, "model assistance is disabled for the RRA (BP_RELEVANCE_ENABLED=0)"
    provider, model = model_names(task)
    if not provider:
        return None, ("no provider configured for the RRA "
                      "(set BP_RELEVANCE_PROVIDER / BP_RELEVANCE_MODEL)")
    if not model:
        return None, ("no model configured for the RRA "
                      "(set BP_RELEVANCE_MODEL, or BP_LLM_MODEL)")

    from ... import llm   # bp.llm — three levels up from bp.product.relevance
    saved = (os.environ.get("BP_LLM_PROVIDER"), os.environ.get("BP_LLM_MODEL"),
             os.environ.get("BP_LLM_BASE_URL"))
    try:
        os.environ["BP_LLM_PROVIDER"] = provider
        os.environ["BP_LLM_MODEL"] = model
        models = llm.from_env()
        if models is None:
            return None, "no model gateway could be built for the RRA"
        models.config.max_output_tokens = max_tokens()
        models.config.max_input_chars = max_input_chars()
        return models, ""
    except Exception as error:
        return None, str(error)[:200]
    finally:
        for name, value in zip(("BP_LLM_PROVIDER", "BP_LLM_MODEL", "BP_LLM_BASE_URL"), saved):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def call(system, user, task="relevance"):
    """Make one model call.  Returns (text, record, error).

    text is "" on failure.  The record carries the prompt/output hashes the
    rest of the system uses for an audit trail.
    """
    models, err = _models(task)
    if models is None:
        return "", None, err
    if len(system) + len(user) > max_input_chars():
        return "", None, "input exceeds the RRA input cap (%d chars)" % max_input_chars()
    try:
        result = models.call("builder", task, "v1", system, user, consent=True)
    except Exception as error:
        return "", None, str(error)[:200]
    if isinstance(result, tuple) and result:
        text = result[0]
        record = result[1] if len(result) > 1 else None
    else:
        text, record = str(result), None
    if not isinstance(text, str) or not text.strip():
        return "", record, "the model returned no text"
    return text, record, ""


def call_json(system, user, task="relevance"):
    """Make one model call and parse the answer as JSON.

    Returns (parsed, record, error).  The answer must be a JSON object or a
    JSON array; a fenced code block is accepted because models add one.
    """
    text, record, err = call(system, user, task=task)
    if err:
        return None, record, err
    parsed = parse_json(text)
    if parsed is None:
        return None, record, "the model did not return parseable JSON"
    return parsed, record, ""


def parse_json(text):
    """Parse a model answer as JSON.  Returns None when it is not JSON.

    Tolerates a fenced code block and leading prose before the first brace or
    bracket, but never guesses: a bad answer is a bad answer.
    """
    raw = str(text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        # strip the fence
        parts = raw.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") or candidate.startswith("["):
                raw = candidate
                break
    # The outermost bracket decides: an array stays an array, an object stays
    # an object.  Trying both in order would turn `[{"a": 1}]` into `{"a": 1}`.
    first = raw[0]
    if first == "[":
        pairs = [("[", "]"), ("{", "}")]
    elif first == "{":
        pairs = [("{", "}"), ("[", "]")]
    else:
        pairs = [("{", "}"), ("[", "]")]
    for opener, closer in pairs:
        start = raw.find(opener)
        end = raw.rfind(closer)
        if start >= 0 and end > start:
            candidate = raw[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def describe():
    """What would answer, for the admin panel.  Never exposes a key."""
    provider, model = model_names()
    stages = {}
    for task, variable in sorted(STAGE_MODELS.items()):
        stage_provider, stage_model = model_names(task)
        stages[task.replace("relevance-", "")] = {
            "variable": variable,
            "provider": stage_provider,
            "model": stage_model,
            "overridden": bool(stage_model and stage_model != model),
        }
    return {
        "enabled": enabled(),
        "provider": provider,
        "model": model,
        "stages": stages,
        "max_tokens": max_tokens(),
        "max_input_chars": max_input_chars(),
        "budget_tokens": budget_tokens(),
        "problem": "" if (provider and model) else (
            "no provider/model configured for the RRA"),
    }
