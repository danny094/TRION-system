from __future__ import annotations

from typing import Any, AsyncGenerator

from core.llm.provider_registry import get_provider_spec
from core.llm.providers import normalize_provider, provider_runtime_module
from core.llm.reasoning_sanitizer import StreamingReasoningSanitizer, sanitize_reasoning_text


async def complete_prompt(
    *,
    provider: str,
    model: str,
    prompt: str,
    timeout_s: float = 90.0,
    ollama_endpoint: str = "",
    json_mode: bool = False,
) -> str:
    provider_norm = normalize_provider(provider)
    impl = provider_runtime_module(provider_norm)
    kwargs: dict[str, Any] = {
        "provider": provider_norm,
        "model": model,
        "prompt": prompt,
        "timeout_s": timeout_s,
    }
    if provider_norm in {"ollama", "ollama_cloud"}:
        kwargs["ollama_endpoint"] = ollama_endpoint
        kwargs["json_mode"] = json_mode
    elif get_provider_spec(provider_norm).api_style == "openai":
        kwargs["json_mode"] = json_mode
    return sanitize_reasoning_text(await impl.complete_prompt(**kwargs))


async def stream_prompt(
    *,
    provider: str,
    model: str,
    prompt: str,
    timeout_s: float = 90.0,
    ollama_endpoint: str = "",
) -> AsyncGenerator[str, None]:
    provider_norm = normalize_provider(provider)
    impl = provider_runtime_module(provider_norm)
    kwargs: dict[str, Any] = {
        "provider": provider_norm,
        "model": model,
        "prompt": prompt,
        "timeout_s": timeout_s,
    }
    if provider_norm in {"ollama", "ollama_cloud"}:
        kwargs["ollama_endpoint"] = ollama_endpoint
    sanitizer = StreamingReasoningSanitizer()
    async for chunk in impl.stream_prompt(**kwargs):
        for safe in sanitizer.feed(chunk):
            if safe:
                yield safe
    for safe in sanitizer.flush():
        if safe:
            yield safe
