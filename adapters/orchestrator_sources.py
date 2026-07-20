"""Default orchestrator context sources for the admin-api chat path.

Each source is a ``Callable[[user_text, conversation_id], Any]`` consumed by
``core/orchestrator/context.py::build_context``. Sources are intentionally
robust: failures inside a source surface as ``{"available": False, ...}`` via
the orchestrator (it wraps every call in try/except).

Currently wired sources:
- ``memory``           — multi-channel memory search via adapters.memory_broker
- ``conversation_meta``— persisted conversation policy via mcp.client
- ``runtime``          — minimal host/runtime fingerprint (stdlib only)
- ``active_containers``— live container/home summary via Docker runtime
"""

from __future__ import annotations

import platform
import socket
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from adapters.memory_broker import retrieve_memory
from mcp.client import get_conversation_meta
from utils.trion_home_contract import (
    MANIFEST_PATH,
    build_home_scope,
    is_verified_home_scope,
    parse_home_manifest,
)

ContextSource = Callable[[str, str], Any]


def build_context_sources() -> Dict[str, ContextSource]:
    return {
        "memory": _memory_source,
        "conversation_meta": _conversation_meta_source,
        "runtime": _runtime_source,
        "active_containers": _active_containers_source,
    }


def _memory_source(user_text: str, conversation_id: str) -> Dict[str, Any]:
    return retrieve_memory(conversation_id or "global", (user_text or "").strip())


def _conversation_meta_source(user_text: str, conversation_id: str) -> Optional[Dict[str, Any]]:
    return get_conversation_meta(conversation_id or "global")


def _runtime_source(user_text: str, conversation_id: str) -> Dict[str, Any]:
    return {
        "hostname": _safe(socket.gethostname),
        "platform": _safe(platform.platform),
        "python": _safe(platform.python_version),
        "now_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _active_containers_source(user_text: str, conversation_id: str) -> Dict[str, Any]:
    try:
        from docker import from_env
    except Exception as exc:
        return {"containers": [], "available": False, "error": str(exc)}
    try:
        client = from_env()
        containers = client.containers.list(all=True)
    except Exception as exc:
        return {"containers": [], "available": False, "error": str(exc)}
    rows: list[Dict[str, Any]] = []
    for container in containers:
        labels = dict(getattr(container, "labels", {}) or {})
        manifest = _read_home_manifest(container)
        scope = build_home_scope(
            labels=labels,
            manifest=manifest,
            available_capability_classes=[],
            verification_sources=["container_inventory"] + (["home_manifest"] if manifest else []),
        )
        rows.append(
            {
                "container_id": str(getattr(container, "id", "")),
                "name": str(getattr(container, "name", "")),
                "status": str(getattr(container, "status", "")),
                "labels": labels,
                "home_scope": scope,
            }
        )
    active_home = next((row for row in rows if is_verified_home_scope(row.get("home_scope") or {})), None)
    return {"containers": rows, "active_home": active_home}


def _read_home_manifest(container: Any) -> Dict[str, Any]:
    try:
        result = container.exec_run(["cat", MANIFEST_PATH])
    except Exception:
        return {}
    output = getattr(result, "output", b"")
    exit_code = getattr(result, "exit_code", None)
    if exit_code is None or int(exit_code) != 0:
        return {}
    try:
        raw = output.decode("utf-8", errors="replace")
    except Exception:
        return {}
    return parse_home_manifest(raw)


def _safe(fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except Exception:
        return None
