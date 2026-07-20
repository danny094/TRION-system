"""
Shared Commander secret store backed by the existing memory secret tools.

This module is the single truth for Commander-scoped secret persistence and
lookup. Global and blueprint-local secrets are mapped onto the underlying
flat secret store via explicit key prefixes.
"""

from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from commander_secret_models import SecretEntry, SecretScope


MEMORY_URL = os.getenv("MEMORY_URL", "http://mcp-sql-memory:8081")
_ACCESS_LOG: deque[dict[str, Any]] = deque(maxlen=500)
_GLOBAL_PREFIX = "CC_GLOBAL::"
_BLUEPRINT_PREFIX = "CC_BLUEPRINT::"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mcp_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": args},
    }
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{MEMORY_URL}/mcp",
            json=payload,
            headers={"Accept": "application/json, text/event-stream"},
        )
    for line in resp.text.splitlines():
        if not line.startswith("data:"):
            continue
        envelope = json.loads(line[5:].strip())
        result = envelope.get("result", {})
        content = result.get("content", [])
        if content:
            return json.loads(content[0].get("text", "{}"))
        return result
    return {}


def _normalize_name(name: str) -> str:
    normalized = str(name or "").upper().strip()
    if not normalized:
        raise ValueError("secret name is required")
    return normalized


def _encoded_name(name: str, scope: SecretScope, blueprint_id: str | None = None) -> str:
    normalized = _normalize_name(name)
    if scope == SecretScope.GLOBAL:
        return f"{_GLOBAL_PREFIX}{normalized}"
    blueprint = str(blueprint_id or "").strip()
    if not blueprint:
        raise ValueError("blueprint_id is required for blueprint-scoped secrets")
    return f"{_BLUEPRINT_PREFIX}{blueprint}::{normalized}"


def _decode_name(raw: str) -> tuple[SecretScope, str, str | None] | None:
    value = str(raw or "").strip()
    if value.startswith(_GLOBAL_PREFIX):
        return SecretScope.GLOBAL, value[len(_GLOBAL_PREFIX) :], None
    if value.startswith(_BLUEPRINT_PREFIX):
        rest = value[len(_BLUEPRINT_PREFIX) :]
        blueprint_id, sep, secret_name = rest.partition("::")
        if sep and blueprint_id and secret_name:
            return SecretScope.BLUEPRINT, secret_name, blueprint_id
    return None


def _iter_entries(names: Iterable[str]) -> list[SecretEntry]:
    entries: list[SecretEntry] = []
    for raw_name in names:
        decoded = _decode_name(raw_name)
        if not decoded:
            continue
        scope, name, blueprint_id = decoded
        entries.append(
            SecretEntry(
                name=name,
                scope=scope,
                blueprint_id=blueprint_id,
                created_at=None,
                expires_at=None,
            )
        )
    return entries


def list_secrets(scope: SecretScope | None = None, blueprint_id: str | None = None) -> list[SecretEntry]:
    result = _mcp_call("secret_list", {})
    raw_names = result.get("secrets")
    names = raw_names if isinstance(raw_names, list) else []
    entries = _iter_entries(str(item or "") for item in names)
    if scope is not None:
        entries = [entry for entry in entries if entry.scope == scope]
    if blueprint_id is not None:
        target = str(blueprint_id or "").strip()
        entries = [entry for entry in entries if str(entry.blueprint_id or "") == target]
    return entries


def store_secret(
    name: str,
    value: str,
    scope: SecretScope = SecretScope.GLOBAL,
    blueprint_id: str | None = None,
    expires_at: str | None = None,
) -> SecretEntry:
    encoded = _encoded_name(name, scope, blueprint_id)
    result = _mcp_call("secret_save", {"name": encoded, "value": value})
    if not result.get("success"):
        raise RuntimeError(str(result.get("error") or "secret_save_failed"))
    return SecretEntry(
        name=_normalize_name(name),
        scope=scope,
        blueprint_id=str(blueprint_id or "").strip() or None,
        created_at=None,
        expires_at=str(expires_at or "").strip() or None,
    )


def delete_secret(name: str, scope: SecretScope = SecretScope.GLOBAL, blueprint_id: str | None = None) -> bool:
    encoded = _encoded_name(name, scope, blueprint_id)
    result = _mcp_call("secret_delete", {"name": encoded})
    return bool(result.get("success"))


def get_secret_value(name: str, scope: SecretScope = SecretScope.GLOBAL, blueprint_id: str | None = None) -> str | None:
    encoded = _encoded_name(name, scope, blueprint_id)
    result = _mcp_call("secret_get", {"name": encoded})
    value = result.get("value")
    return str(value) if value is not None else None


def get_secrets_for_blueprint(blueprint_id: str, requirements: list[dict[str, Any]]) -> dict[str, str]:
    env: dict[str, str] = {}
    for requirement in list(requirements or []):
        name = _normalize_name(str((requirement or {}).get("name") or ""))
        optional = bool((requirement or {}).get("optional"))
        value = get_secret_value(name, SecretScope.BLUEPRINT, blueprint_id)
        if value is None:
            value = get_secret_value(name, SecretScope.GLOBAL)
        if value is None:
            if optional:
                continue
            raise RuntimeError(f"missing_required_secret: {name}")
        env[name] = value
    return env


def log_secret_access(name: str, action: str, actor: str = "", blueprint_id: str | None = None) -> None:
    _ACCESS_LOG.appendleft(
        {
            "name": _normalize_name(name),
            "action": str(action or "").strip() or "access",
            "actor": str(actor or "").strip(),
            "blueprint_id": str(blueprint_id or "").strip() or None,
            "ts": _now_iso(),
        }
    )


def get_access_log(limit: int = 50) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), len(_ACCESS_LOG) or 1))
    return list(list(_ACCESS_LOG)[:safe_limit])
