"""The model gateway is provider-agnostic: any key, any endpoint, or none."""

import io
import json
import os
import sys
import unittest
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from bp.product import providers  # noqa: E402


class Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _opener(payload, capture=None):
    def open_request(request, timeout=None):
        if capture is not None:
            capture.append(request)
        return Reply(json.dumps(payload).encode("utf-8"))
    return open_request


class ProviderSelectionTest(unittest.TestCase):
    def tearDown(self):
        providers.register(None)

    def test_nothing_configured_is_available_but_says_why_not(self):
        self.assertFalse(providers.available({}))
        self.assertIsNone(providers.resolve({}))
        self.assertIn("no model is configured", providers.explain({}))

    def test_a_registered_callable_is_the_gateway(self):
        providers.register(lambda messages: "hello")
        self.assertTrue(providers.available({}))
        self.assertEqual(providers.complete([{"role": "user", "content": "x"}]), "hello")
        self.assertEqual(providers.describe({})["provider"], "callable")

    def test_an_explicit_openai_compatible_provider(self):
        env = {"BP_LLM_PROVIDER": "openai", "BP_LLM_MODEL": "gpt-x",
               "BP_LLM_KEY": "secret", "BP_LLM_BASE_URL": "http://localhost:1234"}
        described = providers.describe(env)
        self.assertEqual(described["provider"], "openai-compatible")
        self.assertEqual(described["model"], "gpt-x")
        self.assertEqual(described["url"], "http://localhost:1234/v1/chat/completions")
        self.assertNotIn("secret", json.dumps(described))

    def test_the_opencode_key_is_auto_detected(self):
        described = providers.describe({"BP_OPENGO_API_KEY": "k"})
        self.assertEqual(described["provider"], "opencode")
        self.assertEqual(described["model"], providers.DEFAULT_MODEL_OPENCODE)

    def test_a_legacy_prose_url_keeps_the_opencode_gateway(self):
        env = {"BP_OPENGO_API_KEY": "k",
               "BP_PROSE_URL": "https://proxy.example/v1/chat/completions"}
        described = providers.describe(env)
        self.assertEqual(described["provider"], "opencode")
        self.assertEqual(described["url"], "https://proxy.example/v1/chat/completions")

    def test_an_unknown_provider_is_reported_not_guessed(self):
        self.assertFalse(providers.available({"BP_LLM_PROVIDER": "mystery"}))
        self.assertIn("unknown BP_LLM_PROVIDER", providers.explain({"BP_LLM_PROVIDER": "mystery"}))

    def test_a_missing_key_is_reported(self):
        env = {"BP_LLM_PROVIDER": "deepseek", "BP_LLM_MODEL": "deepseek-chat"}
        self.assertFalse(providers.available(env))
        self.assertIn("DEEPSEEK_API_KEY", providers.explain(env))

    def test_ollama_needs_no_key(self):
        env = {"BP_LLM_PROVIDER": "ollama", "BP_LLM_MODEL": "llama3",
               "BP_OLLAMA_HOST": "127.0.0.1:11434"}
        self.assertTrue(providers.available(env))
        self.assertEqual(providers.describe(env)["url"],
                         "http://127.0.0.1:11434/v1/chat/completions")


class ProviderCallTest(unittest.TestCase):
    def tearDown(self):
        providers.register(None)

    def test_an_openai_compatible_reply_is_read(self):
        gateway = providers.OpenAICompatible(
            "m", "http://x/v1/chat/completions", "k",
            opener=_opener({"choices": [{"message": {"content": "plain"}}]}))
        self.assertEqual(gateway.complete([{"role": "user", "content": "x"}]), "plain")

    def test_a_reasoning_model_reply_is_read(self):
        gateway = providers.OpenAICompatible(
            "m", "http://x/v1/chat/completions", "k",
            opener=_opener({"choices": [{"message": {"reasoning_content": "thought"}}]}))
        self.assertEqual(gateway.complete([{"role": "user", "content": "x"}]), "thought")

    def test_anthropic_splits_the_system_message(self):
        captured = []
        gateway = providers.Anthropic(
            "claude", providers.ANTHROPIC_URL, "akey",
            opener=_opener({"content": [{"type": "text", "text": "answer"}]}, captured))
        text = gateway.complete([{"role": "system", "content": "be terse"},
                                 {"role": "user", "content": "question"}])
        self.assertEqual(text, "answer")
        body = json.loads(captured[0].data.decode("utf-8"))
        self.assertEqual(body["system"], "be terse")
        self.assertEqual([turn["role"] for turn in body["messages"]], ["user"])
        headers = {key.lower(): value for key, value in captured[0].headers.items()}
        self.assertEqual(headers["x-api-key"], "akey")
        self.assertEqual(headers["anthropic-version"], "2023-06-01")

    def test_a_http_error_is_named_without_the_key(self):
        def opener(request, timeout=None):
            raise urllib.error.HTTPError(request.full_url, 401, "no", {}, None)
        gateway = providers.OpenAICompatible("m", "http://x/v1/chat/completions", "secret",
                                             opener=opener)
        with self.assertRaises(providers.GatewayError) as caught:
            gateway.complete([{"role": "user", "content": "x"}])
        self.assertIn("HTTP 401", str(caught.exception))
        self.assertNotIn("secret", str(caught.exception))

    def test_an_unreadable_reply_is_refused(self):
        gateway = providers.OpenAICompatible("m", "http://x/v1/chat/completions", "k",
                                             opener=_opener({"unexpected": True}))
        with self.assertRaises(providers.GatewayError):
            gateway.complete([{"role": "user", "content": "x"}])

    def test_a_registered_function_that_raises_is_named(self):
        def broken(messages):
            raise RuntimeError("boom")
        providers.register(broken)
        with self.assertRaises(providers.GatewayError) as caught:
            providers.complete([])
        self.assertIn("boom", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
