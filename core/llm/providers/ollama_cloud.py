from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, Iterable, List

import httpx

from core.llm.messages import flatten_content
from core.llm.provider_registry import ollama_cloud_base, ollama_cloud_model_candidates
from core.llm.rate_limits import capture_rate_limit_headers
from core.llm.secrets import resolve_cloud_api_key


async def _headers_endpoint(provider: str) -> tuple[Dict[str, str], str]:
    api_key = await resolve_cloud_api_key(provider)
    if not api_key:
        raise RuntimeError(f"missing_api_key:{provider}")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, ollama_cloud_base()


async def complete_chat(
    *,
    provider: str,
    model: str,
    messages: Iterable[Dict[str, Any]],
    timeout_s: float,
    ollama_endpoint: str,
    tools: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    headers, endpoint = await _headers_endpoint(provider)
    if not endpoint:
        raise RuntimeError(f"missing_endpoint:{provider}")

    last_exc: Exception | None = None
    data: Dict[str, Any] = {}
    for candidate_model in ollama_cloud_model_candidates(str(model or "").strip()):
        payload: Dict[str, Any] = {
            "model": candidate_model,
            "messages": list(messages or []),
            "stream": False,
            "keep_alive": "5m",
        }
        if tools:
            payload["tools"] = tools
        try:
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                response = await client.post(f"{endpoint}/api/chat", json=payload, headers=headers or None)
                capture_rate_limit_headers(provider, response.headers, response.status_code)
                response.raise_for_status()
                data = response.json()
            break
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            code = int(getattr(getattr(exc, "response", None), "status_code", 0) or 0)
            if code == 404:
                continue
            raise
    else:
        if last_exc:
            raise last_exc
        raise RuntimeError(f"{provider}_complete_chat_failed_no_candidate")

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
    headers, endpoint = await _headers_endpoint(provider)
    if not endpoint:
        raise RuntimeError(f"missing_endpoint:{provider}")

    last_exc: Exception | None = None
    for candidate_model in ollama_cloud_model_candidates(str(model or "").strip()):
        payload = {"model": candidate_model, "messages": list(messages or []), "stream": True, "keep_alive": "5m"}
        try:
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
            return
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            code = int(getattr(getattr(exc, "response", None), "status_code", 0) or 0)
            if code == 404:
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError(f"{provider}_stream_chat_failed_no_candidate")


async def complete_prompt(
    *,
    provider: str,
    model: str,
    prompt: str,
    timeout_s: float,
    ollama_endpoint: str,
    json_mode: bool = False,
) -> str:
    result = await complete_chat(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": prompt}],
        timeout_s=timeout_s,
        ollama_endpoint=ollama_endpoint,
    )
    return str(result.get("content") or "")


async def stream_prompt(
    *,
    provider: str,
    model: str,
    prompt: str,
    timeout_s: float,
    ollama_endpoint: str,
) -> AsyncGenerator[str, None]:
    async for event in stream_chat_events(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": prompt}],
        timeout_s=timeout_s,
        ollama_endpoint=ollama_endpoint,
    ):
        if event.get("type") == "content":
            yield str(event.get("chunk") or "")
