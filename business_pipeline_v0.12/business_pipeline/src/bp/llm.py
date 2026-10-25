"""Model-provider boundary (Build Charter 3.3). Domain logic never imports a vendor SDK: it talks to a Provider.
Calls happen in the server process (the sandbox has no network by design). Keys come from the environment only and are never logged,
returned by the API, or placed in client code. Every call is budgeted, logged by hash, and its output treated as untrusted text."""
import hashlib, json, os, time
from dataclasses import dataclass, field

class ProviderError(Exception): pass
class BudgetExceeded(Exception): pass
class ConsentRequired(Exception): pass

@dataclass
class LLMResult:
    text: str; model: str; provider: str; input_tokens: int | None = None; output_tokens: int | None = None

class Provider:
    name = "base"
    def __init__(self, model): self.model = model
    def complete(self, system: str, user: str, max_tokens: int = 1500) -> LLMResult: raise NotImplementedError

class MockProvider(Provider):
    """Scripted provider for tests: `script(role_hint, system, user)` returns the text to 'generate'. Records every call."""
    name = "mock"
    def __init__(self, script, model="mock-model"): super().__init__(model); self.script, self.calls = script, []
    def complete(self, system, user, max_tokens=1500):
        self.calls.append({"system": system, "user": user, "max_tokens": max_tokens}); out = self.script(system, user)
        if isinstance(out, Exception): raise out
        return LLMResult(out, self.model, self.name, len(system + user) // 4, len(out) // 4)

class AnthropicProvider(Provider):
    """Messages API over HTTPS using only the standard library. UNTESTED against the live service in this build: request construction
    and error handling are unit-tested with an injected opener; the owner must run a first live call."""
    name = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"; VERSION = "2023-06-01"
    def __init__(self, model, api_key=None, timeout=60, opener=None):
        super().__init__(model); self._key = api_key or os.environ.get("ANTHROPIC_API_KEY"); self.timeout = timeout; self._open = opener
        if not self._key: raise ProviderError("no API key: set the ANTHROPIC_API_KEY environment variable on the server")
    def complete(self, system, user, max_tokens=1500):
        import urllib.request, urllib.error
        body = json.dumps({"model": self.model, "max_tokens": int(max_tokens), "temperature": 0, "system": system, "messages": [{"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(self.URL, data=body, method="POST", headers={"content-type": "application/json", "x-api-key": self._key, "anthropic-version": self.VERSION})
        try:
            with (self._open or urllib.request.urlopen)(req, timeout=self.timeout) as r: data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e: raise ProviderError(f"provider returned HTTP {e.code}")          # never include headers or the key
        except (urllib.error.URLError, TimeoutError, OSError) as e: raise ProviderError(f"could not reach the provider: {type(e).__name__}")
        except ValueError: raise ProviderError("provider returned a response that is not JSON")
        try: text = "".join(b["text"] for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError): raise ProviderError("unexpected response shape from the provider")
        u = data.get("usage", {}); return LLMResult(text, data.get("model", self.model), self.name, u.get("input_tokens"), u.get("output_tokens"))

class OpenAICompatProvider(Provider):
    """OpenAI-compatible Chat Completions API over HTTPS using only the standard library. Covers OpenAI and any compatible
    endpoint (DeepSeek, a local vLLM/Ollama server, or another vendor), so additional models for graphs, spreadsheets,
    research and writing can be added without touching domain logic. UNTESTED against a live service in this build:
    request construction and error handling are unit-tested with an injected opener; the owner must run a first live call."""
    name = "openai"
    URL = "https://api.openai.com/v1/chat/completions"; KEY_ENV = "OPENAI_API_KEY"
    def __init__(self, model, api_key=None, base_url=None, timeout=60, opener=None):
        super().__init__(model); self._key = api_key or os.environ.get(self.KEY_ENV); self.timeout = timeout; self._open = opener
        self.base_url = base_url or self.URL
        if not self._key: raise ProviderError(f"no API key: set the {self.KEY_ENV} environment variable on the server")
    def complete(self, system, user, max_tokens=1500):
        import urllib.request, urllib.error
        body = json.dumps({"model": self.model, "temperature": 0, "max_tokens": int(max_tokens),
                           "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(self.base_url, data=body, method="POST", headers={"content-type": "application/json", "authorization": f"Bearer {self._key}"})
        try:
            with (self._open or urllib.request.urlopen)(req, timeout=self.timeout) as r: data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e: raise ProviderError(f"provider returned HTTP {e.code}")          # never include headers or the key
        except (urllib.error.URLError, TimeoutError, OSError) as e: raise ProviderError(f"could not reach the provider: {type(e).__name__}")
        except ValueError: raise ProviderError("provider returned a response that is not JSON")
        try:
            text = data["choices"][0]["message"]["content"]
            if not isinstance(text, str): raise KeyError
        except (KeyError, IndexError, TypeError): raise ProviderError("unexpected response shape from the provider")
        u = data.get("usage", {}); return LLMResult(text, data.get("model", self.model), self.name, u.get("prompt_tokens"), u.get("completion_tokens"))

class DeepSeekProvider(OpenAICompatProvider):
    """DeepSeek (OpenAI-compatible). Note: the DeepSeek API is billed separately from the 'DeepSeek Pro' chat-app subscription;
    a programmatic API key comes from platform.deepseek.com. Recommended model ids: deepseek-chat (V3) for the builder, and
    deepseek-reasoner (R1) for the independent reviewer to decorrelate errors."""
    name = "deepseek"
    URL = "https://api.deepseek.com/chat/completions"; KEY_ENV = "DEEPSEEK_API_KEY"

@dataclass
class LLMConfig:
    enabled: bool = False
    max_calls_total: int = 50            # per server run
    max_input_chars: int = 20000
    max_output_tokens: int = 1500
    privacy_notice: str = ("Text you submit is sent to the model provider you configured. Do not submit personal, confidential or regulated data unless your agreement with that provider "
                           "allows it. Model output is a proposal only: code validates it and you confirm it. The model produces no numbers.")

class Models:
    """Builder and reviewer roles. Using different models for the two roles is recommended (manual 10: decorrelate errors)."""
    def __init__(self, builder: Provider, reviewer: Provider | None = None, config: LLMConfig | None = None):
        self.builder, self.reviewer, self.config = builder, reviewer or builder, config or LLMConfig(enabled=True)
        self.calls = 0; self.log = []
    @property
    def same_model(self): return (self.builder.name, self.builder.model) == (self.reviewer.name, self.reviewer.model)
    def call(self, role, task, template_version, system, user, consent):
        if not consent: raise ConsentRequired("you must consent to sending this text to the model provider")
        if not self.config.enabled: raise ProviderError("model assistance is disabled on this server")
        if len(system) + len(user) > self.config.max_input_chars: raise BudgetExceeded(f"input exceeds {self.config.max_input_chars} characters")
        if self.calls >= self.config.max_calls_total: raise BudgetExceeded("this server has used its model-call budget")
        prov = self.builder if role == "builder" else self.reviewer; self.calls += 1; t0 = time.time()
        res = prov.complete(system, user, self.config.max_output_tokens)
        rec = {"task": task, "role": role, "provider": res.provider, "model": res.model, "template_version": template_version, "prompt_sha256": hashlib.sha256((system + "\n" + user).encode()).hexdigest(),
               "output_sha256": hashlib.sha256(res.text.encode()).hexdigest(), "input_chars": len(system) + len(user), "input_tokens": res.input_tokens, "output_tokens": res.output_tokens, "seconds": round(time.time() - t0, 2)}
        self.log.append(rec); return res.text, rec

PROVIDERS = {"anthropic": AnthropicProvider, "openai": OpenAICompatProvider, "deepseek": DeepSeekProvider}

def from_env(env=None):
    """BP_LLM_PROVIDER in {anthropic, openai, deepseek}; BP_LLM_MODEL=<model id> (never defaulted); optional BP_LLM_REVIEWER_MODEL.
    Optional BP_LLM_BASE_URL overrides the endpoint for openai/deepseek (e.g. a local or alternate OpenAI-compatible server).
    Returns None when BP_LLM_PROVIDER is not set. The reviewer uses the same provider class, which keeps the boundary small;
    per-role or per-task provider routing (graphs, spreadsheets, research, writing) is a future extension."""
    env = env if env is not None else os.environ; prov = env.get("BP_LLM_PROVIDER"); model = env.get("BP_LLM_MODEL")
    if not prov: return None
    if prov not in PROVIDERS: raise ProviderError(f"unknown provider {prov!r}; supported: {', '.join(sorted(PROVIDERS))}")
    if not model: raise ProviderError("BP_LLM_MODEL is required (the model identifier is your choice and is never defaulted)")
    cls = PROVIDERS[prov]; kw = {"base_url": env["BP_LLM_BASE_URL"]} if env.get("BP_LLM_BASE_URL") and cls is not AnthropicProvider else {}
    b = cls(model, **kw); r = cls(env["BP_LLM_REVIEWER_MODEL"], **kw) if env.get("BP_LLM_REVIEWER_MODEL") else None
    return Models(b, r, LLMConfig(enabled=True))
