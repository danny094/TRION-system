from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Iterable

from core.llm.providers import normalize_provider, provider_runtime_module
from core.llm.reasoning_sanitizer import StreamingReasoningSanitizer


async def stream_chat_events(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float = 90.0,
    ollama_endpoint: str = "",
) -> AsyncGenerator[Dict[str, str], None]:
    provider_norm = normalize_provider(provider)
    model_name = str(model or "").strip()
    impl = provider_runtime_module(provider_norm)
    kwargs: Dict[str, Any] = {
        "provider": provider_norm,
        "model": model_name,
        "messages": messages,
        "timeout_s": timeout_s,
    }
    if provider_norm in {"ollama", "ollama_cloud"}:
        kwargs["ollama_endpoint"] = ollama_endpoint
    sanitizer = StreamingReasoningSanitizer()
    async for event in impl.stream_chat_events(**kwargs):
        event_type = str(event.get("type") or "")
        if event_type == "thinking":
            continue
        if event_type != "content":
            yield event
            continue
        for chunk in sanitizer.feed(str(event.get("chunk") or "")):
            if chunk:
                yield {"type": "content", "chunk": chunk}
    for chunk in sanitizer.flush():
        if chunk:
            yield {"type": "content", "chunk": chunk}


async def stream_chat(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float = 90.0,
    ollama_endpoint: str = "",
) -> AsyncGenerator[str, None]:
    async for event in stream_chat_events(
        provider=provider,
        model=model,
        messages=messages,
        timeout_s=timeout_s,
        ollama_endpoint=ollama_endpoint,
    ):
        if str(event.get("type") or "") != "content":
            continue
        chunk = str(event.get("chunk") or "")
        if chunk:
            yield chunk
