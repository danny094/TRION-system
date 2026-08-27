import asyncio
import json

from config.models import providers as config_providers
from config.models.providers import _normalize_provider as normalize_config_provider
from core.llm import chat, prompts
from core.llm.provider_registry import PROVIDER_VALUES, get_provider_spec, normalize_provider, provider_base
from core.llm.providers import openai, provider_runtime_module
from core.llm.rate_limits import capture_rate_limit_headers, get_rate_limit_snapshot


def test_deepseek_registry_uses_openai_compatible_runtime(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_BASE", raising=False)

    spec = get_provider_spec("deepseek")

    assert normalize_provider("DeepSeek") == "deepseek"
    assert normalize_config_provider("DeepSeek") == "deepseek"
    assert normalize_config_provider("FutureProvider") == "futureprovider"
    assert normalize_provider("FutureProvider") == "ollama"
    assert not hasattr(config_providers, "_VALID_PROVIDERS")
    assert "deepseek" in PROVIDER_VALUES
    assert spec.api_style == "openai"
    assert spec.secret_names == ("DEEPSEEK_API_KEY", "DEEPSEEK_KEY", "DEEPSEEK")
    assert spec.preset_models == ("deepseek-v4-flash", "deepseek-v4-pro")
    assert provider_base("deepseek") == "https://api.deepseek.com"
    assert provider_runtime_module("deepseek") is openai


def test_deepseek_chat_uses_provider_base(monkeypatch):
    seen = {}

    class Response:
        headers = {}
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    class Client:
        def __init__(self, timeout):
            seen["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **kwargs):
            seen.update(url=url, request=kwargs)
            return Response()

    async def headers(provider):
        assert provider == "deepseek"
        return {"Authorization": "Bearer hidden"}

    monkeypatch.setattr(openai.httpx, "AsyncClient", Client)
    monkeypatch.setattr(openai, "_headers", headers)

    result = asyncio.run(openai.complete_chat(
        provider="deepseek",
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": "Hallo"}],
        timeout_s=9.0,
    ))

    assert result == {"content": "ok", "tool_calls": []}
    assert seen["url"] == "https://api.deepseek.com/chat/completions"
    assert seen["request"]["json"]["model"] == "deepseek-v4-flash"


def test_deepseek_openai_capabilities_reach_runtime(monkeypatch):
    chat_seen = {}
    prompt_seen = {}

    class Runtime:
        async def complete_chat(self, **kwargs):
            chat_seen.update(kwargs)
            return {"content": "ok"}

        async def complete_prompt(self, **kwargs):
            prompt_seen.update(kwargs)
            return "{}"

    runtime = Runtime()
    monkeypatch.setattr(chat, "provider_runtime_module", lambda _provider: runtime)
    monkeypatch.setattr(prompts, "provider_runtime_module", lambda _provider: runtime)

    tools = [{"type": "function", "function": {"name": "ping"}}]
    asyncio.run(chat.complete_chat(
        provider="deepseek",
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": "ping"}],
        tools=tools,
    ))
    asyncio.run(prompts.complete_prompt(
        provider="deepseek",
        model="deepseek-v4-pro",
        prompt="return json",
        json_mode=True,
    ))

    assert chat_seen["tools"] == tools
    assert prompt_seen["json_mode"] is True


def test_deepseek_prompt_and_stream_use_provider_base(monkeypatch):
    seen = {"post": [], "stream": []}

    class Response:
        headers = {}
        status_code = 200

        def __init__(self, *, payload=None, lines=()):
            self._payload = payload or {}
            self._lines = tuple(lines)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

        async def aiter_lines(self):
            for line in self._lines:
                yield line

    class Client:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **kwargs):
            seen["post"].append({"url": url, **kwargs})
            return Response(payload={"choices": [{"message": {"content": "{}"}}]})

        def stream(self, method, url, **kwargs):
            seen["stream"].append({"method": method, "url": url, **kwargs})
            reasoning = json.dumps({"choices": [{"delta": {"reasoning_content": "hidden"}}]})
            content = json.dumps({"choices": [{"delta": {"content": "Hallo"}}]})
            return Response(lines=(f"data: {reasoning}", f"data: {content}", "data: [DONE]"))

    async def headers(provider):
        assert provider == "deepseek"
        return {"Authorization": "Bearer hidden"}

    async def collect_stream():
        return [event async for event in openai.stream_chat_events(
            provider="deepseek",
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "Hallo"}],
            timeout_s=8.0,
        )]

    monkeypatch.setattr(openai.httpx, "AsyncClient", Client)
    monkeypatch.setattr(openai, "_headers", headers)

    prompt = asyncio.run(openai.complete_prompt(
        provider="deepseek",
        model="deepseek-v4-flash",
        prompt="json",
        timeout_s=7.0,
        json_mode=True,
    ))
    events = asyncio.run(collect_stream())

    assert prompt == "{}"
    assert seen["post"][0]["url"] == "https://api.deepseek.com/chat/completions"
    assert seen["post"][0]["json"]["response_format"] == {"type": "json_object"}
    assert seen["stream"][0]["url"] == "https://api.deepseek.com/chat/completions"
    assert events == [{"type": "content", "chunk": "Hallo"}]


def test_deepseek_rate_limits_are_captured():
    capture_rate_limit_headers("deepseek", {"x-ratelimit-remaining-requests": "7"}, 200)

    assert get_rate_limit_snapshot()["deepseek"]["request_remaining"] == 7
