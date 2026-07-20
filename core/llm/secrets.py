from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Tuple

import httpx

from config import get_secret_resolve_miss_ttl_s, get_secret_resolve_not_found_ttl_s
from core.llm.provider_registry import normalize_provider, provider_secret_names
from core.secret_resolve_runtime import (
    clear_provider_miss,
    mark_provider_miss,
    mark_secret_not_found,
    mark_secret_success,
    order_candidates,
    provider_miss_active,
    secret_not_found_active,
)
from utils.provider_keys_store import resolve_provider_key


API_KEY_CACHE: Dict[str, Tuple[float, str]] = {}
API_KEY_TTL_S = 20.0
_ROOT = Path(__file__).resolve().parents[2]


def clear_api_key_cache(provider: str | None = None) -> None:
    if provider:
        API_KEY_CACHE.pop(normalize_provider(provider), None)
        return
    API_KEY_CACHE.clear()


def _env_or_dotenv(name: str, default: str = "") -> str:
    value = str(os.getenv(name, "")).strip()
    if value:
        return value

    env_path = _ROOT / ".env"
    if not env_path.exists():
        return default
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, raw_value = line.partition("=")
            if key.strip() != name:
                continue
            value = raw_value.strip().strip("'\"")
            return value or default
    except Exception:
        return default
    return default

def _secret_resolve_base() -> str:
    explicit = str(os.getenv("SECRETS_API_URL", "")).strip()
    if explicit:
        return explicit.rstrip("/")
    admin_api = str(os.getenv("ADMIN_API_URL", "http://trion-admin-api:8200")).strip().rstrip("/")
    return f"{admin_api}/api/secrets/resolve"


async def resolve_cloud_api_key(provider: str) -> str:
    provider_norm = normalize_provider(provider)
    if provider_norm == "ollama":
        return ""

    now = time.monotonic()
    miss_ttl = max(0, int(get_secret_resolve_miss_ttl_s() or 0))
    not_found_ttl = max(0, int(get_secret_resolve_not_found_ttl_s() or 0))

    cached = API_KEY_CACHE.get(provider_norm)
    if cached and (now - float(cached[0])) < API_KEY_TTL_S and cached[1]:
        return cached[1]
    if provider_miss_active(provider_norm, now, miss_ttl):
        return ""

    secret_candidates = provider_secret_names(provider_norm)
    for secret_name in secret_candidates:
        value = resolve_provider_key(secret_name)
        if value:
            API_KEY_CACHE[provider_norm] = (now, value)
            mark_secret_success(provider_norm, secret_name)
            return value

    token = _env_or_dotenv("INTERNAL_SECRET_RESOLVE_TOKEN", "")
    base = _secret_resolve_base()
    if not token or not base:
        mark_provider_miss(provider_norm, now)
        return ""

    headers = {"Authorization": f"Bearer {token}"}
    attempted_remote = False
    saw_not_found = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name in order_candidates(provider_norm, secret_candidates):
                if secret_not_found_active(provider_norm, name, now, not_found_ttl):
                    continue
                try:
                    attempted_remote = True
                    resp = await client.get(f"{base}/{name}", headers=headers)
                    if resp.status_code == 404:
                        saw_not_found = True
                        mark_secret_not_found(provider_norm, name, now)
                        continue
                    if resp.status_code != 200:
                        continue
                    data = resp.json() if resp.content else {}
                    value = str((data or {}).get("value") or "").strip()
                    if value:
                        API_KEY_CACHE[provider_norm] = (now, value)
                        mark_secret_success(provider_norm, name)
                        clear_provider_miss(provider_norm)
                        return value
                    saw_not_found = True
                    mark_secret_not_found(provider_norm, name, now)
                except Exception:
                    continue
    except Exception:
        return ""

    if saw_not_found or not attempted_remote:
        mark_provider_miss(provider_norm, now)
    return ""
