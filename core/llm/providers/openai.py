from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, Iterable, List

import httpx

from core.llm.messages import flatten_content, normalize_openai_messages
from core.llm.provider_registry import openai_base
from core.llm.rate_limits import capture_rate_limit_headers
from core.llm.secrets import resolve_cloud_api_key


async def _headers(provider: str) -> Dict[str, str]:
    api_key = await resolve_cloud_api_key(provider)
    if not api_key:
        raise RuntimeError(f"missing_api_key:{provider}")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


async def complete_chat(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float,
    tools: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "model": str(model or "").strip(),
        "messages": normalize_openai_messages(messages),
        "temperature": 0,
        "stream": False,
    }
    if tools:
        body["tools"] = tools
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(f"{openai_base()}/chat/completions", json=body, headers=await _headers(provider))
        capture_rate_limit_headers(provider, response.headers, response.status_code)
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices") or []
    msg = choices[0].get("message", {}) if choices else {}
    tool_calls = msg.get("tool_calls", []) if isinstance(msg.get("tool_calls"), list) else []
    return {"content": flatten_content(msg.get("content")).strip(), "tool_calls": tool_calls}


async def stream_chat_events(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float,
) -> AsyncGenerator[Dict[str, str], None]:
    body = {
        "model": str(model or "").strip(),
        "messages": normalize_openai_messages(messages),
        "temperature": 0,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        async with client.stream("POST", f"{openai_base()}/chat/completions", json=body, headers=await _headers(provider)) as response:
            capture_rate_limit_headers(provider, response.headers, response.status_code)
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                except Exception:
                    continue
                choices = data.get("choices") or []
                delta = choices[0].get("delta", {}) if choices else {}
                chunk = flatten_content(delta.get("content"))
                if chunk:
                    yield {"type": "content", "chunk": chunk}


async def complete_prompt(*, provider: str, model: str, prompt: str, timeout_s: float, json_mode: bool = False) -> str:
    body: Dict[str, Any] = {
        "model": str(model or "").strip(),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "stream": False,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(f"{openai_base()}/chat/completions", json=body, headers=await _headers(provider))
        capture_rate_limit_headers(provider, response.headers, response.status_code)
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices") or []
    msg = choices[0].get("message", {}) if choices else {}
    return flatten_content(msg.get("content")).strip()


async def stream_prompt(*, provider: str, model: str, prompt: str, timeout_s: float) -> AsyncGenerator[str, None]:
    async for event in stream_chat_events(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": prompt}],
        timeout_s=timeout_s,
    ):
        yield str(event.get("chunk") or "")
