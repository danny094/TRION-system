#!/usr/bin/env python3
import bundle_docker
from bundle_common import action_result, container_summary, error_result, guard_managed_action, is_not_found, resolve_container_reference


def runtime_cleanup_all():
    try:
        client = bundle_docker.get_docker_client()
        removed = []
        errors = []
        for container in client.containers.list(all=True):
            summary = container_summary(container)
            if not bool(summary.get("managed_by_trion")):
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


def remove_stopped_container(container_id="", container_name=""):
    container_ref = container_id
    try:
        client = bundle_docker.get_docker_client()
        container = resolve_container_reference(client, container_ref)
        labels = dict(container.labels or {})
        summary = container_summary(container)
        if not bool(summary.get("managed_by_trion")):
            return {"removed": False, "container_id": container_ref, "reason": "not_managed"}
        container.reload()
        if bool(((container.attrs or {}).get("State") or {}).get("Running")):
            return {"removed": False, "container_id": container_ref, "reason": "running"}
        blueprint_id = str(labels.get("trion.blueprint") or "unknown")
        container.remove(force=True)
        return {"removed": True, "container_id": str(getattr(container, "id", "") or container_ref), "blueprint_id": blueprint_id}
    except Exception as exc:
        if is_not_found(exc):
            return {"removed": False, "container_id": container_ref, "reason": "not_found"}
        return {"removed": False, "container_id": container_ref, "reason": "error", "error": str(exc)}


def start_stopped_container(container_id="", container_name=""):
    container_ref = container_id
    try:
        client = bundle_docker.get_docker_client()
        container = resolve_container_reference(client, container_ref)
        blocked = guard_managed_action(container)
        if blocked:
            return blocked
        container.reload()
        if str(container.status or "").strip().lower() == "running":
            return action_result(container, "already_running")
        container.start()
        container.reload()
        return action_result(container, "started")
    except Exception as exc:
        if is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)


def stop_container(container_id="", container_name=""):
    container_ref = container_id
    try:
        client = bundle_docker.get_docker_client()
        container = resolve_container_reference(client, container_ref)
        blocked = guard_managed_action(container)
        if blocked:
            return blocked
        container.reload()
        if str(container.status or "").strip().lower() != "running":
            return action_result(container, "already_stopped")
        container.stop(timeout=10)
        container.reload()
        return action_result(container, "stopped")
    except Exception as exc:
        if is_not_found(exc):
            return error_result("CONTAINER_NOT_FOUND", f"Container '{container_ref}' not found")
        return error_result("RUNTIME_UNAVAILABLE", str(exc), retryable=True)
