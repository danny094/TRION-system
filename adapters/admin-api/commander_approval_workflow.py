import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional

from commander_audit_store import log_action
from commander_approval_contracts import APPROVAL_TTL, ApprovalStatus, PendingApproval
from commander_approval_store import (
    _callbacks,
    _emit_ws_activity,
    _history,
    _lock,
    _pending,
    approval_event_payload,
    cleanup_expired_unlocked,
    save_unlocked,
)
from commander_container_lifecycle import start_container
from commander_runtime_models import NetworkMode, ResourceLimits

logger = logging.getLogger(__name__)


def request_approval(
    blueprint_id: str,
    reason: str,
    network_mode: NetworkMode,
    risk_flags: Optional[List[str]] = None,
    risk_reasons: Optional[List[str]] = None,
    requested_cap_add: Optional[List[str]] = None,
    requested_security_opt: Optional[List[str]] = None,
    requested_cap_drop: Optional[List[str]] = None,
    read_only_rootfs: bool = False,
    override_resources: Optional[ResourceLimits] = None,
    extra_env: Optional[Dict[str, str]] = None,
    resume_volume: Optional[str] = None,
    mount_overrides: Optional[List[dict]] = None,
    storage_scope_override: Optional[str] = None,
    device_overrides: Optional[List[str]] = None,
    block_apply_handoff_resource_ids: Optional[List[str]] = None,
    session_id: str = "",
    conversation_id: str = "",
) -> PendingApproval:
    with _lock:
        cleanup_expired_unlocked()
        approval = PendingApproval(
            blueprint_id=blueprint_id,
            reason=reason,
            network_mode=network_mode,
            risk_flags=risk_flags,
            risk_reasons=risk_reasons,
            requested_cap_add=requested_cap_add,
            requested_security_opt=requested_security_opt,
            requested_cap_drop=requested_cap_drop,
            read_only_rootfs=read_only_rootfs,
            override_resources=override_resources,
            extra_env=extra_env,
            resume_volume=resume_volume,
            mount_overrides=mount_overrides,
            storage_scope_override=storage_scope_override,
            device_overrides=device_overrides,
            block_apply_handoff_resource_ids=block_apply_handoff_resource_ids,
            session_id=session_id,
            conversation_id=conversation_id,
        )
        _pending[approval.id] = approval
        _callbacks[approval.id] = threading.Event()
        save_unlocked()
    _emit_ws_activity(
        "approval_requested",
        level="warn",
        message=f"Approval requested for {blueprint_id}",
        reason=reason,
        ttl_seconds=APPROVAL_TTL,
        **approval_event_payload(approval),
    )
    log_action("", blueprint_id, "approval_requested", reason)
    return approval


def approve(approval_id: str, approved_by: str = "user") -> Optional[Dict]:
    with _lock:
        approval = _pending.get(approval_id)
        if not approval:
            return None
        if approval.is_expired():
            approval.status = ApprovalStatus.EXPIRED
            approval.resolved_at = datetime.utcnow().isoformat()
            approval.resolved_by = "system_ttl"
            _pending.pop(approval_id, None)
            _history.append(approval)
            _callbacks.pop(approval_id, None)
            save_unlocked()
            _emit_ws_activity(
                "approval_resolved",
                level="warn",
                message=f"Approval expired for {approval.blueprint_id}",
                resolved_by=approval.resolved_by,
                **approval_event_payload(approval),
            )
            return None
        if approval.status != ApprovalStatus.PENDING:
            return None
        approval.status = ApprovalStatus.APPROVED
        approval.resolved_at = datetime.utcnow().isoformat()
        approval.resolved_by = approved_by
    try:
        instance = start_container(
            blueprint_id=approval.blueprint_id,
            override_resources=approval.override_resources,
            extra_env=approval.extra_env,
            resume_volume=approval.resume_volume,
            mount_overrides=approval.mount_overrides,
            storage_scope_override=approval.storage_scope_override,
            device_overrides=approval.device_overrides,
            block_apply_handoff_resource_ids=approval.block_apply_handoff_resource_ids,
            skip_approval=True,
            session_id=approval.session_id,
            conversation_id=approval.conversation_id,
        )
        log_action(instance.container_id, approval.blueprint_id, "approval_approved", f"by {approved_by}")
        evt = _callbacks.pop(approval_id, None)
        if evt:
            evt.set()
        with _lock:
            _pending.pop(approval_id, None)
            _history.append(approval)
            save_unlocked()
        _emit_ws_activity(
            "approval_resolved",
            level="success",
            message=f"Approval approved for {approval.blueprint_id}",
            resolved_by=approved_by,
            container_id=instance.container_id,
            **approval_event_payload(approval),
        )
        return instance.model_dump()
    except Exception as exc:
        logger.error("[Approval] Start after approve failed: %s", exc)
        with _lock:
            approval.status = ApprovalStatus.REJECTED
            approval.resolved_at = datetime.utcnow().isoformat()
            approval.resolved_by = "system_start_failed"
            _pending.pop(approval_id, None)
            _history.append(approval)
            save_unlocked()
        _emit_ws_activity(
            "approval_resolved",
            level="error",
            message=f"Approval failed for {approval.blueprint_id}",
            resolved_by="system_start_failed",
            error=str(exc),
            **approval_event_payload(approval),
        )
        return {"error": str(exc)}


def reject(approval_id: str, rejected_by: str = "user", reason: str = "") -> bool:
    with _lock:
        approval = _pending.get(approval_id)
        if not approval or approval.status != ApprovalStatus.PENDING:
            return False
        approval.status = ApprovalStatus.REJECTED
        approval.resolved_at = datetime.utcnow().isoformat()
        approval.resolved_by = rejected_by
    log_action("", approval.blueprint_id, "approval_rejected", f"by {rejected_by}: {reason}")
    evt = _callbacks.pop(approval_id, None)
    if evt:
        evt.set()
    with _lock:
        _pending.pop(approval_id, None)
        _history.append(approval)
        save_unlocked()
    _emit_ws_activity(
        "approval_resolved",
        level="warn",
        message=f"Approval rejected for {approval.blueprint_id}",
        resolved_by=rejected_by,
        reason=reason or "",
        **approval_event_payload(approval),
    )
    return True
