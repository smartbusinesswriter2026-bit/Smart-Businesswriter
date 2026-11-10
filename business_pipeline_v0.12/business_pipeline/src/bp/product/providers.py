"""A provider-agnostic model gateway for the optional lanes (product layer).

No vendor is assumed.  The gateway is resolved from the environment, or from a
callable registered at runtime (tests and embedders use that), and two wire
formats are implemented with the standard library only:

* **OpenAI-compatible** ``chat/completions`` — OpenAI, DeepSeek, OpenCode Go,
  Ollama, vLLM, LM Studio, LiteLLM and any proxy that speaks the same shape;
* **Anthropic** ``messages``.

When nothing is configured the gateway is absent, ``available()`` is false, and
every caller keeps its deterministic text.  A missing key, a missing model id or
an unknown provider is reported by ``explain()`` — never guessed, and never a
reason to invent a model that a gateway may not serve.
"""

import json
import os
import urllib.error
import urllib.request

#: A call is bounded by this many seconds unless the caller says otherwise.
DEFAULT_TIMEOUT = 120

#: The model OpenCode Go served before a model id was required to be named.
DEFAULT_MODEL_OPENCODE = "beam-free"

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
OPENCODE_URL = "https://opencode.ai/inference/go/openai/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OLLAMA_URL = "http://localhost:11434/v1"


class GatewayError(ValueError):
    """The model gateway is absent, misconfigured or answered unreadably."""


def _first(env, *names):
    for name in names:
        value = env.get(name)
        if value and str(value).strip():
            return str(value).strip()
    return ""


def _chat_url(base):
    """The chat-completions URL for a base, a version root or a full endpoint."""
    base = str(base or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/chat/completions") or base.endswith("/messages"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def _ollama_url(base):
    base = str(base or "").strip().rstrip("/")
    if base and "://" not in base:
        base = "http://" + base
    return _chat_url(base or OLLAMA_URL)


def _anthropic_url(base):
    base = str(base or "").strip().rstrip("/")
    if not base:
        return ANTHROPIC_URL
    if base.endswith("/messages"):
        return base
    if base.endswith("/v1"):
        return base + "/messages"
    return base + "/v1/messages"


class Gateway:
    """One model, one endpoint, one ``complete`` method."""

    name = "base"

    def __init__(self, model, url, key="", headers=None, opener=None, timeout=None):
        self.model = model
        self.url = url
        self._key = key
        self.headers = dict(headers or {})
        self._opener = opener
        try:
            self.timeout = int(timeout or os.environ.get("BP_LLM_TIMEOUT", DEFAULT_TIMEOUT)
                               or DEFAULT_TIMEOUT)
        except (TypeError, ValueError):
            self.timeout = DEFAULT_TIMEOUT

    def describe(self):
        """What would answer, in words a record may carry — never the key."""
        return {"provider": getattr(self, "label", self.name),
                "model": self.model, "url": self.url}

    def _open(self, request, timeout):
        return (self._opener or urllib.request.urlopen)(request, timeout=timeout)

    def complete(self, messages, max_tokens=1500, timeout=None, temperature=0.0):
        raise NotImplementedError


class OpenAICompatible(Gateway):
    """Any endpoint that speaks the OpenAI chat-completions shape."""

    name = "openai-compatible"

    def complete(self, messages, max_tokens=1500, timeout=None, temperature=0.0):
        payload = {"model": self.model, "messages": messages,
                   "temperature": float(temperature), "max_tokens": int(max_tokens)}
        headers = {"Content-Type": "application/json",
                   "User-Agent": "smart-business-writer/1.0"}
        if self._key:
            headers["Authorization"] = "Bearer " + self._key
        headers.update(self.headers)
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"),
                                         headers=headers)
        try:
            with self._open(request, timeout or self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise GatewayError("the model gateway answered HTTP %s" % error.code)
        except ValueError:
            raise GatewayError("the model gateway returned a response that is not JSON")
        except Exception as error:
            raise GatewayError("the model gateway could not be reached: " + str(error)[:160])
        try:
            message = data["choices"][0]["message"]
            text = message.get("content") or message.get("reasoning_content")
        except (KeyError, IndexError, TypeError, AttributeError):
            raise GatewayError("the model gateway returned an unreadable response")
        if not isinstance(text, str) or not text.strip():
            raise GatewayError("the model gateway returned no text")
        return text


class Anthropic(Gateway):
    """Anthropic's messages API."""

    name = "anthropic"

    def complete(self, messages, max_tokens=1500, timeout=None, temperature=0.0):
        system = "\n".join(str(item.get("content") or "") for item in messages
                           if item.get("role") == "system")
        turns = [{"role": item.get("role"), "content": item.get("content")}
                 for item in messages if item.get("role") in ("user", "assistant")]
        payload = {"model": self.model, "max_tokens": int(max_tokens),
                   "temperature": float(temperature), "messages": turns}
        if system:
            payload["system"] = system
        headers = {"content-type": "application/json", "x-api-key": self._key,
                   "anthropic-version": "2023-06-01",
                   "User-Agent": "smart-business-writer/1.0"}
        headers.update(self.headers)
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"),
                                         headers=headers)
        try:
            with self._open(request, timeout or self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise GatewayError("the model gateway answered HTTP %s" % error.code)
        except ValueError:
            raise GatewayError("the model gateway returned a response that is not JSON")
        except Exception as error:
            raise GatewayError("the model gateway could not be reached: " + str(error)[:160])
        try:
            text = "".join(block.get("text") or "" for block in data.get("content") or []
                           if block.get("type") == "text")
        except (AttributeError, TypeError):
            raise GatewayError("the model gateway returned an unreadable response")
        if not text.strip():
            raise GatewayError("the model gateway returned no text")
        return text


class CallableGateway(Gateway):
    """A function supplied by the caller: ``complete(messages) -> text``."""

    name = "callable"

    def __init__(self, function, model="callable"):
        super().__init__(model, "", "")
        self._function = function

    def complete(self, messages, max_tokens=1500, timeout=None, temperature=0.0):
        try:
            text = self._function(messages)
        except Exception as error:
            raise GatewayError("the registered model function failed: " + str(error)[:160])
        if not isinstance(text, str) or not text.strip():
            raise GatewayError("the registered model function returned no text")
        return text


#: One process-wide registration.  Tests and embedders set it; production uses the env.
_REGISTERED = None


def register(function, model="callable"):
    """Use ``function(messages) -> text`` for every call.  ``None`` clears it."""
    global _REGISTERED
    if function is not None and not callable(function):
        raise GatewayError("a registered model must be callable")
    _REGISTERED = CallableGateway(function, model) if function is not None else None
    return _REGISTERED


def registered():
    return _REGISTERED


def _selection(env):
    """Read the environment into a provider choice, or None when nothing is set."""
    explicit = (env.get("BP_LLM_PROVIDER") or "").strip().lower()
    model = _first(env, "BP_LLM_MODEL", "BP_PROSE_MODEL")
    opencode_key = _first(env, "BP_OPENGO_API_KEY", "OPENCODE_API_KEY")
    prose_url = _first(env, "BP_PROSE_URL")
    base_url = _first(env, "BP_LLM_BASE_URL", "BP_LLM_URL")

    if not explicit:
        if opencode_key:
            explicit = "opencode"
        elif prose_url:
            explicit = "openai-compatible"
        elif _first(env, "BP_OLLAMA_URL", "BP_OLLAMA_HOST"):
            explicit = "ollama"
        elif _first(env, "BP_LLM_KEY") and base_url:
            explicit = "openai-compatible"
        else:
            return None

    if explicit in ("openai", "openai-compatible", "openai_compatible", "compatible"):
        url = _chat_url(base_url or prose_url or OPENAI_URL)
        key = _first(env, "BP_LLM_KEY", "OPENAI_API_KEY", "BP_OPENGO_API_KEY",
                     "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY")
        if not model:
            return {"error": "BP_LLM_MODEL is required for an OpenAI-compatible gateway"}
        return {"kind": "openai", "name": "openai-compatible", "model": model,
                "url": url, "key": key}

    if explicit == "deepseek":
        key = _first(env, "BP_LLM_KEY", "DEEPSEEK_API_KEY")
        if not key:
            return {"error": "DEEPSEEK_API_KEY (or BP_LLM_KEY) is not set"}
        if not model:
            return {"error": "BP_LLM_MODEL is required for DeepSeek"}
        return {"kind": "openai", "name": "deepseek", "model": model,
                "url": _chat_url(base_url or DEEPSEEK_URL), "key": key}

    if explicit in ("opencode", "opencode-go", "opencode_go"):
        key = _first(env, "BP_LLM_KEY", "BP_OPENGO_API_KEY", "OPENCODE_API_KEY")
        if not key:
            return {"error": "BP_OPENGO_API_KEY (or BP_LLM_KEY) is not set"}
        return {"kind": "openai", "name": "opencode",
                "model": model or DEFAULT_MODEL_OPENCODE,
                "url": _chat_url(prose_url or base_url or OPENCODE_URL), "key": key,
                "headers": {"x-opencode-session": "bp-prose"}}

    if explicit in ("ollama", "local"):
        base = _first(env, "BP_LLM_BASE_URL", "BP_LLM_URL", "BP_OLLAMA_URL", "BP_OLLAMA_HOST")
        if not model:
            return {"error": "BP_LLM_MODEL is required for a local Ollama gateway"}
        return {"kind": "openai", "name": "ollama", "model": model,
                "url": _ollama_url(base), "key": _first(env, "BP_LLM_KEY")}

    if explicit == "anthropic":
        key = _first(env, "BP_LLM_KEY", "ANTHROPIC_API_KEY")
        if not key:
            return {"error": "ANTHROPIC_API_KEY (or BP_LLM_KEY) is not set"}
        if not model:
            return {"error": "BP_LLM_MODEL is required for Anthropic"}
        return {"kind": "anthropic", "name": "anthropic", "model": model,
                "url": _anthropic_url(_first(env, "BP_LLM_BASE_URL", "BP_LLM_URL")),
                "key": key}

    return {"error": "unknown BP_LLM_PROVIDER %r; supported: openai, deepseek, opencode, "
                     "anthropic, ollama, openai-compatible" % explicit}


def resolve(env=None, opener=None):
    """The configured gateway, or None when nothing is configured.

    Raises :class:`GatewayError` when a provider was chosen but cannot be used
    (an unknown name, a missing key or a missing model id).
    """
    if _REGISTERED is not None:
        return _REGISTERED
    selected = _selection(env if env is not None else os.environ)
    if selected is None:
        return None
    if selected.get("error"):
        raise GatewayError(selected["error"])
    cls = Anthropic if selected["kind"] == "anthropic" else OpenAICompatible
    gateway = cls(selected["model"], selected["url"], selected.get("key", ""),
                  headers=selected.get("headers"), opener=opener)
    gateway.label = selected["name"]
    return gateway


def available(env=None):
    try:
        return resolve(env) is not None
    except GatewayError:
        return False


def model_id(env=None):
    try:
        gateway = resolve(env)
    except GatewayError:
        return ""
    return gateway.model if gateway is not None else ""


def describe(env=None):
    """What would answer, including the reason nothing would."""
    try:
        gateway = resolve(env)
    except GatewayError as error:
        return {"provider": "", "model": "", "url": "", "problem": str(error)}
    if gateway is None:
        return {"provider": "", "model": "", "url": "", "problem": explain(env)}
    return gateway.describe()


def explain(env=None):
    if _REGISTERED is not None:
        return "a registered model function"
    try:
        selected = _selection(env if env is not None else os.environ)
    except Exception as error:  # a broken environment must not raise from a status read
        return str(error)[:160]
    if selected is None:
        return ("no model is configured; set BP_LLM_PROVIDER and BP_LLM_MODEL "
                "(and the provider's key), or BP_OPENGO_API_KEY for the OpenCode Go gateway")
    if selected.get("error"):
        return selected["error"]
    return "%s model %s" % (selected["name"], selected["model"])


def complete(messages, **options):
    """One completion through the configured gateway."""
    gateway = resolve()
    if gateway is None:
        raise GatewayError("model assistance is not configured: " + explain())
    return gateway.complete(messages, **options)
