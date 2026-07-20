from __future__ import annotations

from typing import Any, List, Optional

import httpx

from utils.logger import log_debug


def embed_payload_v1(model: str, text: str) -> dict[str, str]:
    return {"model": model, "input": str(text or "")}


def embed_payload_legacy(model: str, text: str) -> dict[str, str]:
    return {"model": model, "prompt": str(text or "")}


def extract_embedding(data: Any) -> Optional[List[float]]:
    if not isinstance(data, dict):
        return None
    vector = data.get("embedding")
    if isinstance(vector, list) and vector:
        return [float(v) for v in vector]
    batch = data.get("embeddings")
    if isinstance(batch, list) and batch and isinstance(batch[0], list) and batch[0]:
        return [float(v) for v in batch[0]]
    return None


async def request_embedding_async(
    *,
    endpoint: str,
    model: str,
    text: str,
    timeout_s: float,
    headers: dict[str, str] | None = None,
    label: str = "local",
) -> Optional[List[float]]:
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        try:
            response = await client.post(
                f"{endpoint.rstrip('/')}/api/embed",
                json=embed_payload_v1(model, text),
                headers=headers,
            )
            response.raise_for_status()
            return extract_embedding(response.json())
        except httpx.HTTPStatusError as exc:
            if int(getattr(getattr(exc, "response", None), "status_code", 0) or 0) != 404:
                log_debug(f"[EmbeddingClient] {label} unavailable: {type(exc).__name__}: {exc}")
                return None
        except Exception as exc:
            log_debug(f"[EmbeddingClient] {label} unavailable: {type(exc).__name__}: {exc}")
            return None
        try:
            response = await client.post(
                f"{endpoint.rstrip('/')}/api/embeddings",
                json=embed_payload_legacy(model, text),
                headers=headers,
            )
            response.raise_for_status()
            return extract_embedding(response.json())
        except Exception as exc:
            log_debug(f"[EmbeddingClient] {label} legacy unavailable: {type(exc).__name__}: {exc}")
            return None


def request_embedding_sync(
    *,
    endpoint: str,
    model: str,
    text: str,
    timeout_s: float,
    headers: dict[str, str] | None = None,
    label: str = "local",
) -> Optional[List[float]]:
    with httpx.Client(timeout=timeout_s) as client:
        try:
            response = client.post(
                f"{endpoint.rstrip('/')}/api/embed",
                json=embed_payload_v1(model, text),
                headers=headers,
            )
            response.raise_for_status()
            return extract_embedding(response.json())
        except httpx.HTTPStatusError as exc:
            if int(getattr(getattr(exc, "response", None), "status_code", 0) or 0) != 404:
                log_debug(f"[EmbeddingClient] sync {label} unavailable: {type(exc).__name__}: {exc}")
                return None
        except Exception as exc:
            log_debug(f"[EmbeddingClient] sync {label} unavailable: {type(exc).__name__}: {exc}")
            return None
        try:
            response = client.post(
                f"{endpoint.rstrip('/')}/api/embeddings",
                json=embed_payload_legacy(model, text),
                headers=headers,
            )
            response.raise_for_status()
            return extract_embedding(response.json())
        except Exception as exc:
            log_debug(f"[EmbeddingClient] sync {label} legacy unavailable: {type(exc).__name__}: {exc}")
            return None
