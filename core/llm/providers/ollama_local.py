from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, Iterable, List

import httpx

from core.llm.messages import flatten_content
from core.llm.rate_limits import capture_rate_limit_headers


def _headers_endpoint(endpoint: str) -> tuple[Dict[str, str], str]:
    return {}, str(endpoint).rstrip("/")


async def complete_chat(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float,
    ollama_endpoint: str,
    tools: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    headers, endpoint = _headers_endpoint(ollama_endpoint)
    if not endpoint:
        raise RuntimeError(f"missing_endpoint:{provider}")

    payload: Dict[str, Any] = {
        "model": str(model or "").strip(),
        "messages": list(messages or []),
        "stream": False,
        "keep_alive": "5m",
    }
    if tools:
        payload["tools"] = tools
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(f"{endpoint}/api/chat", json=payload, headers=headers or None)
        capture_rate_limit_headers(provider, response.headers, response.status_code)
        response.raise_for_status()
        data = response.json()

    msg = data.get("message", {}) if isinstance(data.get("message"), dict) else {}
    return {
        "content": flatten_content(msg.get("content")).strip(),
        "tool_calls": msg.get("tool_calls", []) if isinstance(msg.get("tool_calls"), list) else [],
    }


async def stream_chat_events(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float,
    ollama_endpoint: str,
) -> AsyncGenerator[Dict[str, str], None]:
    headers, endpoint = _headers_endpoint(ollama_endpoint)
    if not endpoint:
        raise RuntimeError(f"missing_endpoint:{provider}")

    payload = {
        "model": str(model or "").strip(),
        "messages": list(messages or []),
        "stream": True,
        "keep_alive": "5m",
    }
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        async with client.stream("POST", f"{endpoint}/api/chat", json=payload, headers=headers or None) as response:
            capture_rate_limit_headers(provider, response.headers, response.status_code)
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                msg = data.get("message", {}) if isinstance(data.get("message"), dict) else {}
                thinking = flatten_content(msg.get("thinking"))
                if thinking:
                    yield {"type": "thinking", "chunk": thinking}
                chunk = flatten_content(msg.get("content"))
                if chunk:
                    yield {"type": "content", "chunk": chunk}
                if data.get("done"):
                    break


async def complete_prompt(
    *,
    provider: str,
    model: str,
    prompt: str,
    timeout_s: float,
    ollama_endpoint: str,
    json_mode: bool = False,
) -> str:
    headers, endpoint = _headers_endpoint(ollama_endpoint)
    if not endpoint:
        raise RuntimeError(f"missing_endpoint:{provider}")

    payload: Dict[str, Any] = {
        "model": str(model or "").strip(),
        "prompt": prompt,
        "stream": False,
        "keep_alive": "2m",
    }
    if json_mode:
        payload["format"] = "json"
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(f"{endpoint}/api/generate", json=payload, headers=headers or None)
        capture_rate_limit_headers(provider, response.headers, response.status_code)
        response.raise_for_status()
        data = response.json()
    return str(data.get("response", "") or data.get("thinking", "")).strip()


async def stream_prompt(
    *,
    provider: str,
    model: str,
    prompt: str,
    timeout_s: float,
    ollama_endpoint: str,
) -> AsyncGenerator[str, None]:
    headers, endpoint = _headers_endpoint(ollama_endpoint)
    if not endpoint:
        raise RuntimeError(f"missing_endpoint:{provider}")

    payload = {
        "model": str(model or "").strip(),
        "prompt": prompt,
        "stream": True,
        "keep_alive": "2m",
    }
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        async with client.stream("POST", f"{endpoint}/api/generate", json=payload, headers=headers or None) as response:
            capture_rate_limit_headers(provider, response.headers, response.status_code)
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                chunk = str(data.get("response", "") or "")
                if chunk:
                    yield chunk
                if data.get("done"):
                    break
