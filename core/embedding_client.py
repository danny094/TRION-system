"""Shared embedding helper for lightweight runtime checks."""

from __future__ import annotations

import math
import os
from typing import List, Optional

from config import (
    OLLAMA_BASE,
    get_embedding_cloud_fallback_enable,
    get_embedding_cloud_fallback_model,
    get_embedding_model,
)
from core.embedding_transport import request_embedding_async, request_embedding_sync
from core.llm.provider_registry import ollama_cloud_base
from utils.provider_keys_store import resolve_provider_key
from utils.role_endpoint_resolver import resolve_role_endpoint


async def embed_text(
    text: str,
    *,
    timeout_s: float = 2.8,
) -> Optional[List[float]]:
    route = resolve_role_endpoint("embedding", default_endpoint=OLLAMA_BASE)
    if route.get("hard_error"):
        return await _cloud_embedding_async(text, timeout_s=timeout_s)
    endpoint = route.get("endpoint") or OLLAMA_BASE
    vector = await request_embedding_async(
        endpoint=endpoint,
        model=get_embedding_model(),
        text=text,
        timeout_s=timeout_s,
    )
    if vector:
        return vector
    return await _cloud_embedding_async(text, timeout_s=timeout_s)


def embed_text_sync(
    text: str,
    *,
    timeout_s: float = 0.8,
) -> Optional[List[float]]:
    route = resolve_role_endpoint("embedding", default_endpoint=OLLAMA_BASE)
    if route.get("hard_error"):
        return _cloud_embedding_sync(text, timeout_s=timeout_s)
    endpoint = route.get("endpoint") or OLLAMA_BASE
    vector = request_embedding_sync(
        endpoint=endpoint,
        model=get_embedding_model(),
        text=text,
        timeout_s=timeout_s,
    )
    if vector:
        return vector
    return _cloud_embedding_sync(text, timeout_s=timeout_s)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


async def _cloud_embedding_async(text: str, *, timeout_s: float) -> Optional[List[float]]:
    if not get_embedding_cloud_fallback_enable():
        return None
    headers = _cloud_headers()
    if not headers:
        return None
    endpoint = ollama_cloud_base().rstrip("/")
    if not endpoint:
        return None
    return await request_embedding_async(
        endpoint=endpoint,
        model=get_embedding_cloud_fallback_model(),
        text=text,
        timeout_s=max(1.0, timeout_s),
        headers=headers,
        label="cloud",
    )


def _cloud_embedding_sync(text: str, *, timeout_s: float) -> Optional[List[float]]:
    if not get_embedding_cloud_fallback_enable():
        return None
    headers = _cloud_headers()
    if not headers:
        return None
    endpoint = ollama_cloud_base().rstrip("/")
    if not endpoint:
        return None
    return request_embedding_sync(
        endpoint=endpoint,
        model=get_embedding_cloud_fallback_model(),
        text=text,
        timeout_s=max(1.0, timeout_s),
        headers=headers,
        label="cloud",
    )


def _cloud_headers() -> dict[str, str]:
    api_key = (
        str(os.getenv("OLLAMA_API_KEY", "")).strip()
        or str(os.getenv("OLLAMA_CLOUD_API_KEY", "")).strip()
        or _safe_resolve_provider_key("OLLAMA_API_KEY")
        or _safe_resolve_provider_key("OLLAMA_CLOUD_API_KEY")
        or _safe_resolve_provider_key("OLLAMA_KEY")
        or _safe_resolve_provider_key("OLLAMA")
    )
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _safe_resolve_provider_key(name: str) -> str:
    try:
        return resolve_provider_key(name)
    except Exception:
        return ""
