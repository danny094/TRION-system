from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Iterable, List

from core.llm.providers import ollama_cloud, ollama_local


def _impl(provider: str):
    return ollama_cloud if str(provider or "").strip().lower() == "ollama_cloud" else ollama_local


async def complete_chat(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float,
    ollama_endpoint: str,
    tools: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    return await _impl(provider).complete_chat(
        provider=provider,
        model=model,
        messages=messages,
        timeout_s=timeout_s,
        ollama_endpoint=ollama_endpoint,
        tools=tools,
    )


async def stream_chat_events(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float,
    ollama_endpoint: str,
) -> AsyncGenerator[Dict[str, str], None]:
    async for event in _impl(provider).stream_chat_events(
        provider=provider,
        model=model,
        messages=messages,
        timeout_s=timeout_s,
        ollama_endpoint=ollama_endpoint,
    ):
        yield event


async def complete_prompt(
    *,
    provider: str,
    model: str,
    prompt: str,
    timeout_s: float,
    ollama_endpoint: str,
    json_mode: bool = False,
) -> str:
    return await _impl(provider).complete_prompt(
        provider=provider,
        model=model,
        prompt=prompt,
        timeout_s=timeout_s,
        ollama_endpoint=ollama_endpoint,
        json_mode=json_mode,
    )


async def stream_prompt(**kwargs: Any) -> AsyncGenerator[str, None]:
    async for chunk in _impl(str(kwargs["provider"])).stream_prompt(**kwargs):
        yield chunk
