from __future__ import annotations

from typing import Any

import runtime_views
from container_reference import ContainerReferenceError, resolve_container_reference


def _client():
    return runtime_views._client()


def _action_result(container: Any, action: str) -> dict[str, Any]:
    return runtime_views._action_result(container, action)


def _guard_managed_action(container: Any) -> dict[str, Any] | None:
    return runtime_views._guard_managed_action(container)


def _is_not_found(error: Exception) -> bool:
    return runtime_views._is_not_found(error)


def _managed_flags(labels: dict[str, str]) -> tuple[bool, bool, bool]:
    return runtime_views._managed_flags(labels)


def _summary(container: Any):
    return runtime_views._summary(container)


def error_result(code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return runtime_views.error_result(code, message, retryable=retryable)


def start_stopped_container(container_id: str = "", container_name: str = "") -> dict[str, Any]:
    try:
        container = resolve_container_reference(_client(), container_id=container_id, container_name=container_name)
        blocked = _guard_managed_action(container)
        if blocked:
            return blocked
        container.reload()
        if str(container.status or "").strip().lower() == "running":
            return _action_result(container, "already_running")
        container.start()
        container.reload()
        return _action_result(container, "started")
    except ContainerReferenceError as exc:
        return error_result("INVALID_CONTAINER_REFERENCE", str(exc))
    except Exception as exc:
        if _is_not_found(exc):
            container_ref = container_id or container_name
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def stop_container(container_id: str = "", container_name: str = "") -> dict[str, Any]:
    try:
        container = resolve_container_reference(_client(), container_id=container_id, container_name=container_name)
        blocked = _guard_managed_action(container)
        if blocked:
            return blocked
        container.reload()
        if str(container.status or "").strip().lower() != "running":
            return _action_result(container, "already_stopped")
        container.stop(timeout=10)
        container.reload()
        return _action_result(container, "stopped")
    except ContainerReferenceError as exc:
        return error_result("INVALID_CONTAINER_REFERENCE", str(exc))
    except Exception as exc:
        if _is_not_found(exc):
            container_ref = container_id or container_name
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def remove_stopped_container(container_id: str = "", container_name: str = "") -> dict[str, Any]:
    try:
        container = resolve_container_reference(_client(), container_id=container_id, container_name=container_name)
        resolved_container_id = str(getattr(container, "id", "") or container_id or container_name)
        labels = dict(container.labels or {})
        summary = _summary(container)
        if not summary.managed_by_trion:
            return {"removed": False, "container_id": resolved_container_id, "reason": "not_managed"}
        container.reload()
        if bool(((container.attrs or {}).get("State") or {}).get("Running")):
            return {"removed": False, "container_id": resolved_container_id, "reason": "running"}
        blueprint_id = str(labels.get("trion.blueprint") or "unknown")
        container.remove(force=True)
        return {"removed": True, "container_id": resolved_container_id, "blueprint_id": blueprint_id}
    except ContainerReferenceError as exc:
        return {"removed": False, "container_id": container_id, "reason": "invalid_reference", "error": str(exc)}
    except Exception as exc:
        if _is_not_found(exc):
            return {"removed": False, "container_id": container_id, "reason": "not_found"}
        return {"removed": False, "container_id": container_id, "reason": "error", "error": str(exc)}


def cleanup_all() -> dict[str, Any]:
    try:
        client = _client()
        removed: list[str] = []
        errors: list[dict[str, str]] = []
        for container in client.containers.list(all=True):
            labels = dict(container.labels or {})
            managed, _, _ = _managed_flags(labels)
            if not managed:
                continue
            container_id = str(getattr(container, "id", "") or "")
            try:
                container.stop(timeout=5)
            except Exception:
                pass
            try:
                container.remove(force=True)
                removed.append(container_id)
            except Exception as exc:
                errors.append({"container_id": container_id, "error": str(exc)})
        return {"cleaned": True, "removed": removed, "errors": errors}
    except Exception as exc:
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)
