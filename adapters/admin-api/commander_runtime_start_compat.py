"""
Shared runtime start compatibility wrapper.

This module is the local truth for the remaining legacy engine.start entry
signature used by repo compatibility paths.
"""

from __future__ import annotations

from typing import Any

from commander_deploy_orchestrator import start_container as orchestrate_start_container
from commander_runtime_errors import PendingApprovalError


def start_container(
    blueprint_id: str,
    override_resources: Any = None,
    extra_env: Any = None,
    resume_volume: Any = None,
    mount_overrides: Any = None,
    storage_scope_override: Any = None,
    device_overrides: Any = None,
    block_apply_handoff_resource_ids: Any = None,
    _skip_approval: bool = False,
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
        skip_approval=_skip_approval,
        session_id=session_id,
        conversation_id=conversation_id,
    )
