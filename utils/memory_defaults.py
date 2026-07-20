import os
from typing import Any

from utils.settings import settings

MEMORY_DEFAULT_MODE_KEY = "MEMORY_DEFAULT_MODE"
MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY = "MEMORY_DEFAULT_DO_NOT_REMEMBER"
MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY = "MEMORY_DEFAULT_MAX_MEMORY_HITS"

HARDCODED_DEFAULT_MEMORY_MODE = "global_enabled"
HARDCODED_DEFAULT_DO_NOT_REMEMBER = False
HARDCODED_DEFAULT_MAX_MEMORY_HITS = 5


def raw_memory_default(key: str, fallback: Any) -> Any:
    if key in settings.settings:
        return settings.settings[key]
    env_value = os.getenv(key)
    if env_value is not None and str(env_value).strip():
        return env_value
    return fallback


def parse_bool(raw: Any, fallback: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return fallback
    lowered = str(raw).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return fallback


def get_default_memory_mode_value() -> str:
    raw = raw_memory_default(MEMORY_DEFAULT_MODE_KEY, HARDCODED_DEFAULT_MEMORY_MODE)
    value = str(raw or "").strip()
    if value in {"global_enabled", "conversation_only", "disabled"}:
        return value
    return HARDCODED_DEFAULT_MEMORY_MODE


def get_default_do_not_remember_value() -> bool:
    raw = raw_memory_default(
        MEMORY_DEFAULT_DO_NOT_REMEMBER_KEY,
        HARDCODED_DEFAULT_DO_NOT_REMEMBER,
    )
    return parse_bool(raw, HARDCODED_DEFAULT_DO_NOT_REMEMBER)


def get_default_max_memory_hits_value() -> int:
    raw = raw_memory_default(
        MEMORY_DEFAULT_MAX_MEMORY_HITS_KEY,
        HARDCODED_DEFAULT_MAX_MEMORY_HITS,
    )
    try:
        value = int(raw)
    except (ValueError, TypeError):
        return HARDCODED_DEFAULT_MAX_MEMORY_HITS
    return max(1, min(value, 50))
