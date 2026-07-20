from __future__ import annotations

import re
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from core.llm.providers import normalize_provider


_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMIT_SNAPSHOT: Dict[str, Dict[str, Any]] = {}


def _to_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        match = re.search(r"-?\d+(?:\.\d+)?", str(value).strip())
        return int(float(match.group(0))) if match else None
    except Exception:
        return None


def _pick_header(headers: Dict[str, str], keys: Iterable[str]) -> str:
    for key in keys:
        val = str(headers.get(str(key).lower(), "")).strip()
        if val:
            return val
    return ""


def capture_rate_limit_headers(provider: str, headers_obj: Any, status_code: int = 0) -> None:
    provider_norm = normalize_provider(provider)
    if provider_norm not in {"openai", "anthropic", "ollama_cloud", "openrouter", "minimax"}:
        return

    lower_headers: Dict[str, str] = {}
    try:
        if hasattr(headers_obj, "items"):
            lower_headers = {str(k).lower(): str(v) for k, v in headers_obj.items()}
    except Exception:
        lower_headers = {}

    raw = {
        key: value
        for key, value in lower_headers.items()
        if "ratelimit" in key or key in {"retry-after", "x-request-id", "request-id", "anthropic-request-id"}
    }
    payload: Dict[str, Any] = {
        "provider": provider_norm,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status_code": int(status_code or 0),
        "request_id": _pick_header(lower_headers, ("x-request-id", "request-id", "anthropic-request-id")),
        "request_limit": _to_int(_pick_header(lower_headers, (
            "x-ratelimit-limit-requests", "x-ratelimit-requests-limit",
            "ratelimit-limit-requests", "anthropic-ratelimit-requests-limit",
            "x-ratelimit-limit",
        ))),
        "request_remaining": _to_int(_pick_header(lower_headers, (
            "x-ratelimit-remaining-requests", "x-ratelimit-requests-remaining",
            "ratelimit-remaining-requests", "anthropic-ratelimit-requests-remaining",
            "x-ratelimit-remaining",
        ))),
        "request_reset": _pick_header(lower_headers, (
            "x-ratelimit-reset-requests", "x-ratelimit-requests-reset",
            "ratelimit-reset-requests", "anthropic-ratelimit-requests-reset",
            "x-ratelimit-reset", "retry-after",
        )),
        "token_limit": _to_int(_pick_header(lower_headers, (
            "x-ratelimit-limit-tokens", "x-ratelimit-tokens-limit",
            "ratelimit-limit-tokens", "anthropic-ratelimit-tokens-limit",
        ))),
        "token_remaining": _to_int(_pick_header(lower_headers, (
            "x-ratelimit-remaining-tokens", "x-ratelimit-tokens-remaining",
            "ratelimit-remaining-tokens", "anthropic-ratelimit-tokens-remaining",
        ))),
        "token_reset": _pick_header(lower_headers, (
            "x-ratelimit-reset-tokens", "x-ratelimit-tokens-reset",
            "ratelimit-reset-tokens", "anthropic-ratelimit-tokens-reset",
        )),
        "raw": raw,
    }

    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_SNAPSHOT[provider_norm] = payload


def get_rate_limit_snapshot() -> Dict[str, Dict[str, Any]]:
    with _RATE_LIMIT_LOCK:
        return {key: dict(value) for key, value in _RATE_LIMIT_SNAPSHOT.items()}
