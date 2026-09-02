import time
import requests
from typing import Optional

from .config import (
    ADMIN_API_URL,
    MODELS_EFFECTIVE_ROUTE,
    _CACHE_TTL,
    _EMBED_DEFAULT,
    _memory_read_headers,
)

_cache: dict = {"value": None, "ts": 0.0}


def _resolve_embedding_model() -> str:
    """
    Precedence: Settings API → EMBEDDING_MODEL env var → default.
    TTL-cached. Fails open — never blocks embeddings.
    """
    now = time.time()
    if _cache["value"] is not None and (now - _cache["ts"]) < _CACHE_TTL:
        return _cache["value"]

    if ADMIN_API_URL:
        try:
            resp = requests.get(
                f"{ADMIN_API_URL}{MODELS_EFFECTIVE_ROUTE}",
                headers=_memory_read_headers(),
                timeout=2,
            )
            resp.raise_for_status()
            data = resp.json()
            val = data.get("effective", {}).get("EMBEDDING_MODEL", {}).get("value", "")
            if val:
                _cache["value"] = val
                _cache["ts"] = now
                return val
        except Exception:
            pass

    _cache["value"] = _EMBED_DEFAULT
    _cache["ts"] = now
    return _EMBED_DEFAULT
