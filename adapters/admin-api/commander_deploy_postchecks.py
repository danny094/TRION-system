from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from commander_host_companion_runtime import run_package_postchecks
from commander_host_runtime_discovery import run_package_host_runtime_checks

logger = logging.getLogger(__name__)


def run_post_start_checks(
    *,
    blueprint_id: str,
    bp: Any,
    package_manifest: Optional[Dict[str, Any]],
    runtime: Dict[str, Any],
    derive_readiness_timeout_seconds: Callable,
    wait_for_container_health: Callable,
    cleanup_failed_container_start: Callable,
    emit_ws_activity: Callable,
    log_action: Callable,
    logger: Any,
) -> List[dict]:
    container = runtime["container"]
    client = runtime["client"]
    volume_name = runtime["volume_name"]
    created_workspace_volume = bool(runtime["created_workspace_volume"])
    healthcheck = runtime["healthcheck"]

    if healthcheck:
        ready_timeout = derive_readiness_timeout_seconds(bp.healthcheck)
        ready, ready_error_code, ready_reason = wait_for_container_health(
            container,
            timeout_seconds=ready_timeout,
            poll_interval_seconds=2.0,
        )
        if not ready:
            try:
                tail_logs = container.logs(tail=80, timestamps=True).decode("utf-8", errors="replace")
                logger.error("[Engine] Container '%s' (%s) failed — last logs:\n%s", blueprint_id, container.short_id, tail_logs)
            except Exception as log_err:
                logger.warning("[Engine] Could not capture logs before cleanup: %s", log_err)
            cleanup_failed_container_start(
                client=client,
                container=container,
                volume_name=volume_name,
                remove_workspace_volume=created_workspace_volume,
            )
            log_action("", blueprint_id, "deploy_failed", ready_reason)
            emit_ws_activity(
                "deploy_failed",
                level="error",
                message=ready_reason,
                blueprint_id=blueprint_id,
                container_id=container.id,
                error_code=ready_error_code,
            )
            raise RuntimeError(ready_reason)

    postcheck_warnings: List[dict] = []

    if isinstance(package_manifest, dict):
        from commander_package_runtime_post_start import run_package_runtime_post_start

        try:
            postcheck_warnings.extend(list(run_package_runtime_post_start(blueprint_id, bp, package_manifest, container) or []))
        except Exception as exc:
            reason = f"package_runtime_post_start_failed: {exc}"
            try:
                logger.error(
                    "[Engine] Container '%s' (%s) failed post-start config — last logs:\n%s",
                    blueprint_id,
                    container.short_id,
                    container.logs(tail=80, timestamps=True).decode("utf-8", errors="replace"),
                )
            except Exception:
                pass
            cleanup_failed_container_start(
                client=client,
                container=container,
                volume_name=volume_name,
                remove_workspace_volume=created_workspace_volume,
            )
            log_action("", blueprint_id, "deploy_failed", reason)
            emit_ws_activity(
                "deploy_failed",
                level="error",
                message=reason,
                blueprint_id=blueprint_id,
                error_code="package_runtime_post_start_failed",
            )
            raise RuntimeError(reason)

    if isinstance(package_manifest, dict) and list(package_manifest.get("postchecks") or []):
        postcheck_result = run_package_postchecks(blueprint_id, blueprint=bp, container=container, manifest=package_manifest)
        postcheck_warnings = list(postcheck_result.get("warnings") or [])
        if not bool(postcheck_result.get("ok")):
            failed = [item for item in list(postcheck_result.get("checks") or []) if not bool(item.get("ok"))]
            failed_names = ", ".join(str(item.get("name", "?")) for item in failed[:3]) or "package_postchecks_failed"
            reason = f"package_postchecks_failed: {failed_names}"
            try:
                logger.error(
                    "[Engine] Container '%s' (%s) failed postchecks — last logs:\n%s",
                    blueprint_id,
                    container.short_id,
                    container.logs(tail=80, timestamps=True).decode("utf-8", errors="replace"),
                )
            except Exception:
                pass
            cleanup_failed_container_start(
                client=client,
                container=container,
                volume_name=volume_name,
                remove_workspace_volume=created_workspace_volume,
            )
            log_action("", blueprint_id, "deploy_failed", reason)
            emit_ws_activity(
                "deploy_failed",
                level="error",
                message=reason,
                blueprint_id=blueprint_id,
                error_code="package_postchecks_failed",
            )
            raise RuntimeError(reason)
        if postcheck_warnings:
            warning_names = ", ".join(str(item.get("name", "?")) for item in postcheck_warnings)
            logger.warning("[Engine] Container '%s' deployed with advisory warnings: %s", blueprint_id, warning_names)
            emit_ws_activity(
                "deploy_warning",
                level="warning",
                message=f"Deploy erfolgreich, aber: {warning_names}",
                blueprint_id=blueprint_id,
                warnings=postcheck_warnings,
            )

    if isinstance(package_manifest, dict) and isinstance(package_manifest.get("host_runtime_requirements"), dict):
        runtime_result = run_package_host_runtime_checks(blueprint_id, manifest=package_manifest)
        host_runtime_infos = list(runtime_result.get("infos") or [])
        runtime_warnings = list(runtime_result.get("warnings") or [])
        postcheck_warnings.extend(runtime_warnings)
        if not bool(runtime_result.get("ok")):
            failed = [item for item in list(runtime_result.get("checks") or []) if not bool(item.get("ok"))]
            failed_names = ", ".join(str(item.get("name", "?")) for item in failed[:3]) or "host_runtime_requirements_failed"
            reason = f"host_runtime_requirements_failed: {failed_names}"
            try:
                logger.error(
                    "[Engine] Container '%s' (%s) failed host runtime requirements — last logs:\n%s",
                    blueprint_id,
                    container.short_id,
                    container.logs(tail=80, timestamps=True).decode("utf-8", errors="replace"),
                )
            except Exception:
                pass
            cleanup_failed_container_start(
                client=client,
                container=container,
                volume_name=volume_name,
                remove_workspace_volume=created_workspace_volume,
            )
            log_action("", blueprint_id, "deploy_failed", reason)
            emit_ws_activity(
                "deploy_failed",
                level="error",
                message=reason,
                blueprint_id=blueprint_id,
                error_code="host_runtime_requirements_failed",
            )
            raise RuntimeError(reason)
        if host_runtime_infos:
            info_messages = [
                str((item.get("detail") or {}).get("message") or item.get("name", "")).strip()
                for item in host_runtime_infos
                if str((item.get("detail") or {}).get("message") or item.get("name", "")).strip()
            ]
            if info_messages:
                emit_ws_activity(
                    "deploy_info",
                    level="info",
                    message="; ".join(info_messages),
                    blueprint_id=blueprint_id,
                    host_runtime=host_runtime_infos,
                )
        if runtime_warnings:
            warning_names = ", ".join(str(item.get("name", "?")) for item in runtime_warnings)
            logger.warning("[Engine] Container '%s' deployed with host runtime warnings: %s", blueprint_id, warning_names)
            emit_ws_activity(
                "deploy_warning",
                level="warning",
                message="; ".join(
                    str((item.get("detail") or {}).get("message") or item.get("name", "")).strip()
                    for item in runtime_warnings
                    if str((item.get("detail") or {}).get("message") or item.get("name", "")).strip()
                )
                or f"Deploy erfolgreich, aber: {warning_names}",
                blueprint_id=blueprint_id,
                warnings=runtime_warnings,
            )

    return postcheck_warnings
