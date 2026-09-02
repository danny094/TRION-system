"""Non-secret filesystem and browser-auth settings for local Admin security."""
from __future__ import annotations

import os
from pathlib import Path


_ADMIN_SECURITY_DIR = "/app/data/security"
_RESOLVE_TOKEN_FILE = "/run/trion-security/secret-resolve/token"
_MEMORY_TOKEN_FILE = "/run/trion-security/memory-read/token"
SECRET_RESOLVE_ROUTE_PREFIX = "/api/secrets/resolve"
ADMIN_CSRF_HEADER_NAME = "x-csrf-token"


def _path_from_env(name: str, default: str) -> Path:
    value = os.getenv(name, default).strip()
    if not value:
        raise ValueError(f"{name} must name a file path")
    return Path(value)


def get_admin_security_dir() -> Path:
    return _path_from_env("TRION_ADMIN_SECURITY_DIR", _ADMIN_SECURITY_DIR)


def get_admin_credential_hash_path() -> Path:
    return get_admin_security_dir() / "credential.hash"


def get_admin_session_key_path() -> Path:
    return get_admin_security_dir() / "session.key"


def get_secret_resolve_token_path() -> Path:
    return _path_from_env("TRION_SECRET_RESOLVE_TOKEN_FILE", _RESOLVE_TOKEN_FILE)


def get_memory_read_token_path() -> Path:
    return _path_from_env("TRION_MEMORY_READ_TOKEN_FILE", _MEMORY_TOKEN_FILE)


def get_admin_session_ttl_seconds() -> int:
    raw = os.getenv("TRION_ADMIN_SESSION_TTL_SECONDS", "28800")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("TRION_ADMIN_SESSION_TTL_SECONDS must be an integer") from exc
    return max(300, min(value, 86400))


def get_admin_cookie_name() -> str:
    return "trion_session"


def get_admin_csrf_header_name() -> str:
    return ADMIN_CSRF_HEADER_NAME


def get_admin_cookie_secure() -> bool:
    return os.getenv("TRION_ADMIN_COOKIE_SECURE", "false").strip().lower() == "true"
