from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, Iterable

import httpx

from core.llm.messages import normalize_anthropic_messages
from core.llm.provider_registry import anthropic_base
from core.llm.rate_limits import capture_rate_limit_headers
from core.llm.secrets import resolve_cloud_api_key


async def _headers(provider: str) -> Dict[str, str]:
    api_key = await resolve_cloud_api_key(provider)
    if not api_key:
        raise RuntimeError(f"missing_api_key:{provider}")
    return {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


def _content_text(data: Dict[str, Any]) -> str:
    out: list[str] = []
    for item in data.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            txt = str(item.get("text") or "")
            if txt:
                out.append(txt)
    return "".join(out).strip()


async def complete_chat(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float,
) -> Dict[str, Any]:
    system, norm_messages = normalize_anthropic_messages(messages)
    body: Dict[str, Any] = {"model": str(model or "").strip(), "max_tokens": 4096, "messages": norm_messages}
    if system:
        body["system"] = system
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(f"{anthropic_base()}/messages", json=body, headers=await _headers(provider))
        capture_rate_limit_headers(provider, response.headers, response.status_code)
        response.raise_for_status()
        data = response.json()
    return {"content": _content_text(data), "tool_calls": []}


async def stream_chat_events(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float,
) -> AsyncGenerator[Dict[str, str], None]:
    system, norm_messages = normalize_anthropic_messages(messages)
    body: Dict[str, Any] = {
        "model": str(model or "").strip(),
        "max_tokens": 4096,
        "messages": norm_messages,
        "stream": True,
    }
    if system:
        body["system"] = system
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        async with client.stream("POST", f"{anthropic_base()}/messages", json=body, headers=await _headers(provider)) as response:
            capture_rate_limit_headers(provider, response.headers, response.status_code)
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    data = json.loads(payload)
                except Exception:
                    continue
                if str(data.get("type") or "") != "content_block_delta":
                    continue
                delta = data.get("delta", {}) if isinstance(data.get("delta"), dict) else {}
                chunk = str(delta.get("text") or "")
                if chunk:
                    yield {"type": "content", "chunk": chunk}


async def complete_prompt(*, provider: str, model: str, prompt: str, timeout_s: float) -> str:
    body = {"model": str(model or "").strip(), "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]}
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(f"{anthropic_base()}/messages", json=body, headers=await _headers(provider))
        capture_rate_limit_headers(provider, response.headers, response.status_code)
        response.raise_for_status()
        data = response.json()
    return _content_text(data)


async def stream_prompt(*, provider: str, model: str, prompt: str, timeout_s: float) -> AsyncGenerator[str, None]:
    async for event in stream_chat_events(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": prompt}],
        timeout_s=timeout_s,
    ):
        yield str(event.get("chunk") or "")
