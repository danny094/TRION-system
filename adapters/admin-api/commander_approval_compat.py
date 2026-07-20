from __future__ import annotations

from typing import Any

from commander_approval_workflow import request_approval
from commander_runtime_models import NetworkMode, ResourceLimits


def request_legacy_approval(action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = dict(payload or {})
    blueprint_id = str(data.get("blueprint_id") or data.get("id") or "").strip()
    if not blueprint_id:
        return {"error": "blueprint_id is required"}

    network_raw = data.get("network_mode") or data.get("network") or NetworkMode.INTERNAL.value
    try:
        network_mode = network_raw if isinstance(network_raw, NetworkMode) else NetworkMode(str(network_raw))
    except Exception:
        network_mode = NetworkMode.INTERNAL

    override_resources = data.get("override_resources")
    if isinstance(override_resources, dict):
        override_resources = ResourceLimits(**override_resources)
    else:
        override_resources = None

    pending = request_approval(
        blueprint_id=blueprint_id,
        reason=str(data.get("reason") or action or "approval_required").strip(),
        network_mode=network_mode,
        risk_flags=data.get("risk_flags") if isinstance(data.get("risk_flags"), list) else None,
        risk_reasons=data.get("risk_reasons") if isinstance(data.get("risk_reasons"), list) else None,
        requested_cap_add=data.get("requested_cap_add") if isinstance(data.get("requested_cap_add"), list) else None,
        requested_security_opt=data.get("requested_security_opt") if isinstance(data.get("requested_security_opt"), list) else None,
        requested_cap_drop=data.get("requested_cap_drop") if isinstance(data.get("requested_cap_drop"), list) else None,
        read_only_rootfs=bool(data.get("read_only_rootfs", False)),
        override_resources=override_resources,
        extra_env=data.get("extra_env") if isinstance(data.get("extra_env"), dict) else None,
        resume_volume=str(data.get("resume_volume") or "").strip() or None,
        mount_overrides=data.get("mount_overrides") if isinstance(data.get("mount_overrides"), list) else None,
        storage_scope_override=str(data.get("storage_scope_override") or "").strip() or None,
        device_overrides=data.get("device_overrides") if isinstance(data.get("device_overrides"), list) else None,
        block_apply_handoff_resource_ids=(
            data.get("block_apply_handoff_resource_ids")
            if isinstance(data.get("block_apply_handoff_resource_ids"), list)
            else None
        ),
        session_id=str(data.get("session_id") or ""),
        conversation_id=str(data.get("conversation_id") or ""),
    )
    return pending.to_dict()
