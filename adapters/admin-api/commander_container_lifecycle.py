from __future__ import annotations

from typing import Any

from commander_api.mcp_runtime import remove_stopped_container_via_mcp
from commander_deploy_orchestrator import start_container as orchestrate_start_container


def start_container(
    blueprint_id: str,
    override_resources: Any = None,
    extra_env: Any = None,
    resume_volume: Any = None,
    *,
    mount_overrides: Any = None,
    storage_scope_override: Any = None,
    device_overrides: Any = None,
    block_apply_handoff_resource_ids: Any = None,
    skip_approval: bool = False,
    session_id: str = "",
    conversation_id: str = "",
):
    return orchestrate_start_container(
        blueprint_id,
        override_resources,
        extra_env,
        resume_volume,
        mount_overrides=mount_overrides,
        storage_scope_override=storage_scope_override,
        device_overrides=device_overrides,
        block_apply_handoff_resource_ids=block_apply_handoff_resource_ids,
        skip_approval=skip_approval,
        session_id=session_id,
        conversation_id=conversation_id,
    )


def remove_stopped_container(container_id: str) -> dict[str, Any]:
    return remove_stopped_container_via_mcp(container_id)
