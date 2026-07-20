from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from commander_runtime_errors import PendingApprovalError
from commander_audit_store import log_action
from commander_deploy_blueprint_runtime import (
    compose_runtime_blueprint,
    normalize_runtime_device_overrides,
    normalize_runtime_mount_overrides,
    run_pre_start_exec,
    runtime_mount_asset_ids,
    runtime_mount_payloads,
)
from commander_deploy_blueprints import resolve_blueprint
from commander_deploy_container_run import start_runtime_container
from commander_deploy_hardware import (
    build_warning_entries,
    merge_device_overrides,
    merge_mount_overrides,
    resolve_for_deploy as resolve_hardware,
    select_block_engine_handoffs,
)
from commander_deploy_image import build_image
from commander_deploy_postchecks import run_post_start_checks
from commander_deploy_runtime_client import emit_ws_activity, get_runtime_client, validate_runtime_preflight
from commander_deploy_runtime_state import (
    apply_refs,
    build_refs,
    commit_quota_reservation,
    release_quota_reservation,
    reserve_quota,
    set_ttl_timer,
    sync_from_docker,
)
from commander_deploy_start_env import build_env_vars, prepare_runtime_blueprint, setup_host_companion
from commander_deploy_support import (
    build_healthcheck_config,
    build_port_bindings,
    cleanup_failed_container_start,
    derive_readiness_timeout_seconds,
    wait_for_container_health,
)
from commander_deploy_trust import enforce_trust_gates, request_deploy_approval_if_needed
from commander_hardware_resolution import build_hardware_resolution_preview_payload
from commander_mount_utils import ensure_bind_mount_host_dirs
from commander_storage_scope_store import validate_blueprint_mounts

if TYPE_CHECKING:
    from models import ContainerInstance, ResourceLimits

logger = logging.getLogger(__name__)


def _unique_runtime_suffix() -> str:
    return f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"


def start_container(
    blueprint_id: str,
    override_resources: Optional[ResourceLimits] = None,
    extra_env: Optional[Dict[str, str]] = None,
    resume_volume: Optional[str] = None,
    mount_overrides: Optional[List[Dict[str, Any]]] = None,
    storage_scope_override: Optional[str] = None,
    device_overrides: Optional[List[str]] = None,
    block_apply_handoff_resource_ids: Optional[List[str]] = None,
    skip_approval: bool = False,
    session_id: str = "",
    conversation_id: str = "",
) -> "ContainerInstance":
    from models import ContainerInstance, ContainerStatus
    bp = resolve_blueprint(blueprint_id)
    if not bp:
        raise ValueError(f"Blueprint '{blueprint_id}' not found")

    hardware_resolution = resolve_hardware(blueprint_id=bp.id, intents=list(getattr(bp, "hardware_intents", []) or []))
    deploy_warnings = build_warning_entries(hardware_resolution)
    block_engine_opt_in = select_block_engine_handoffs(
        list(hardware_resolution.block_apply_engine_handoffs or []),
        block_apply_handoff_resource_ids,
    )
    for raw in list(block_engine_opt_in.warnings or []):
        msg = str(raw or "").strip()
        if msg:
            deploy_warnings.append(
                {
                    "name": "hardware_block_engine_opt_in",
                    "detail": {
                        "message": msg,
                        "connector": hardware_resolution.connector,
                        "target_type": hardware_resolution.target_type,
                        "target_id": hardware_resolution.target_id,
                    },
                }
            )
    effective_mounts = merge_mount_overrides(mount_overrides, hardware_resolution.mount_overrides)
    effective_devices = merge_device_overrides(device_overrides, hardware_resolution.device_overrides)
    effective_devices = merge_device_overrides(effective_devices, block_engine_opt_in.device_overrides)

    package_manifest = setup_host_companion(blueprint_id, bp)
    bp, pkg_mount_overrides = apply_package_runtime_views(blueprint_id, bp, package_manifest)
    effective_mounts = merge_mount_overrides(effective_mounts, pkg_mount_overrides)

    bp, runtime_mounts, runtime_devices, mount_payloads, asset_ids, effective_scope = prepare_runtime_blueprint(
        bp,
        effective_mounts,
        effective_devices,
        storage_scope_override,
        normalize_mounts=normalize_runtime_mount_overrides,
        normalize_devices=normalize_runtime_device_overrides,
        compose_runtime_blueprint=compose_runtime_blueprint,
        validate_blueprint_mounts=validate_blueprint_mounts,
        ensure_bind_mount_host_dirs=ensure_bind_mount_host_dirs,
        runtime_mount_payloads=runtime_mount_payloads,
        runtime_mount_asset_ids=runtime_mount_asset_ids,
    )

    emit_ws_activity(
        "deploy_start",
        level="info",
        message=f"Deploy requested for {blueprint_id}",
        blueprint_id=blueprint_id,
        network_mode=bp.network.value,
        storage_scope=effective_scope,
        storage_asset_ids=asset_ids,
        mount_overrides=mount_payloads,
        session_id=session_id or "",
        conversation_id=conversation_id or "",
    )

    request_deploy_approval_if_needed(
        blueprint_id=blueprint_id,
        bp=bp,
        skip_approval=skip_approval,
        override_resources=override_resources,
        extra_env=extra_env,
        resume_volume=resume_volume,
        runtime_mount_payloads=mount_payloads,
        raw_mount_overrides=effective_mounts,
        effective_scope_name=effective_scope,
        runtime_device_overrides=runtime_devices,
        raw_device_overrides=effective_devices,
        block_apply_handoff_resource_ids=block_apply_handoff_resource_ids,
        session_id=session_id,
        conversation_id=conversation_id,
        pending_error_cls=PendingApprovalError,
    )

    resources = override_resources or bp.resources
    enforce_trust_gates(blueprint_id, bp, emit_ws_activity=emit_ws_activity, logger=logger)

    sync_from_docker()
    state = build_refs()
    reserved_mem_mb, reserved_cpu = reserve_quota(resources, state)
    apply_refs(state)
    reservation_active = True

    try:
        image_tag = build_image(bp)
        env_vars = build_env_vars(bp, blueprint_id, extra_env)
        run_pre_start_exec(
            bp,
            image_tag,
            env_vars,
            get_client=get_runtime_client,
        )

        runtime_ok, runtime_reason = validate_runtime_preflight(get_runtime_client(), bp.runtime)
        if not runtime_ok:
            raise RuntimeError(runtime_reason)

        runtime = start_runtime_container(
            blueprint_id=blueprint_id,
            bp=bp,
            resources=resources,
            image_tag=image_tag,
            env_vars=env_vars,
            resume_volume=resume_volume,
            session_id=session_id,
            conversation_id=conversation_id,
            unique_runtime_suffix=_unique_runtime_suffix,
            build_port_bindings=build_port_bindings,
            build_healthcheck_config=build_healthcheck_config,
        )
        container = runtime["container"]
        container_name = runtime["container_name"]
        volume_name = runtime["volume_name"]
        mem_bytes = runtime["mem_bytes"]
        net_info = runtime["net_info"]

        postcheck_warnings = run_post_start_checks(
            blueprint_id=blueprint_id,
            bp=bp,
            package_manifest=package_manifest,
            runtime=runtime,
            derive_readiness_timeout_seconds=derive_readiness_timeout_seconds,
            wait_for_container_health=wait_for_container_health,
            cleanup_failed_container_start=cleanup_failed_container_start,
            emit_ws_activity=emit_ws_activity,
            log_action=log_action,
            logger=logger,
        )

        instance = ContainerInstance(
            container_id=container.id,
            blueprint_id=blueprint_id,
            name=container_name,
            status=ContainerStatus.RUNNING,
            memory_limit_mb=mem_bytes / (1024 * 1024),
            started_at=datetime.utcnow().isoformat(),
            ttl_remaining=resources.timeout_seconds,
            cpu_limit_alloc=float(resources.cpu_limit),
            volume_name=volume_name,
            session_id=session_id or "",
        )

        state = build_refs()
        commit_quota_reservation(instance, reserved_mem_mb, reserved_cpu, state)
        apply_refs(state)
        reservation_active = False

        if resources.timeout_seconds > 0:
            set_ttl_timer(container.id, resources.timeout_seconds)

        instance.network_info = net_info
        instance.deploy_warnings = list(postcheck_warnings or []) + list(deploy_warnings or [])
        instance.hardware_resolution_preview = build_hardware_resolution_preview_payload(hardware_resolution)
        instance.block_apply_handoff_resource_ids_requested = list(block_engine_opt_in.requested_resource_ids or [])
        instance.block_apply_handoff_resource_ids_applied = list(block_engine_opt_in.selected_resource_ids or [])
        log_action(container.id, blueprint_id, "start", f"image={image_tag}, mem={resources.memory_limit}, cpu={resources.cpu_limit}")
        logger.info(f"[Engine] Started: {container_name} ({container.short_id})")
        emit_ws_activity(
            "container_started",
            level="success",
            message=f"Container started: {container.short_id}",
            container_id=container.id,
            blueprint_id=blueprint_id,
            container_name=container_name,
            network_mode=bp.network.value,
        )
        return instance
    finally:
        if reservation_active:
            state = build_refs()
            release_quota_reservation(reserved_mem_mb, reserved_cpu, state)
            apply_refs(state)
