from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from commander_approval_policy import evaluate_deploy_risk
from commander_blueprint_trust import check_digest_policy, verify_image_signature

logger = logging.getLogger(__name__)


def enforce_trust_gates(blueprint_id: str, bp: Any, *, emit_ws_activity: Callable, logger: Any) -> None:
    digest_policy = check_digest_policy(bp)
    if not digest_policy["allowed"]:
        try:
            from mcp.client import call_tool as mcp_call

            mcp_call(
                "workspace_event_save",
                {
                    "conversation_id": "_container_events",
                    "event_type": "trust_blocked",
                    "event_data": {
                        "blueprint_id": blueprint_id,
                        "image": getattr(bp, "image", "") or "",
                        "pinned_digest": getattr(bp, "image_digest", None),
                        "actual_digest": digest_policy.get("actual_digest"),
                        "reason": digest_policy["reason"],
                        "blocked_at": datetime.utcnow().isoformat() + "Z",
                    },
                },
            )
        except Exception:
            pass
        emit_ws_activity(
            "trust_block",
            level="error",
            message=digest_policy["reason"],
            blueprint_id=blueprint_id,
            image=getattr(bp, "image", "") or "",
            pinned_digest=getattr(bp, "image_digest", "") or "",
            actual_digest=digest_policy.get("actual_digest"),
        )
        raise RuntimeError(digest_policy["reason"])
    if digest_policy["mode"] == "unpinned_warn":
        logger.warning(f"[Engine] {digest_policy['reason']}")

    if not getattr(bp, "image", None):
        return

    sig_result = verify_image_signature(bp.image)
    if not sig_result["verified"]:
        try:
            from mcp.client import call_tool as mcp_call

            mcp_call(
                "workspace_event_save",
                {
                    "conversation_id": "_container_events",
                    "event_type": "signature_blocked",
                    "event_data": {
                        "blueprint_id": blueprint_id,
                        "image": bp.image,
                        "mode": sig_result["mode"],
                        "reason": sig_result["reason"],
                        "tool": sig_result.get("tool"),
                        "blocked_at": datetime.utcnow().isoformat() + "Z",
                    },
                },
            )
        except Exception:
            pass
        emit_ws_activity(
            "trust_block",
            level="error",
            message=sig_result["reason"],
            blueprint_id=blueprint_id,
            image=bp.image,
            mode=sig_result.get("mode", ""),
            source="signature",
        )
        raise RuntimeError(f"[Signature-Block] {sig_result['reason']}")
    if sig_result["mode"] != "off":
        logger.info("[Engine] Signature OK: %s", sig_result["reason"])


def request_deploy_approval_if_needed(
    *,
    blueprint_id: str,
    bp: Any,
    skip_approval: bool,
    override_resources: Any,
    extra_env: Optional[Dict[str, str]],
    resume_volume: Optional[str],
    runtime_mount_payloads: List[dict],
    raw_mount_overrides: Optional[List[Dict[str, Any]]],
    effective_scope_name: str,
    runtime_device_overrides: List[str],
    raw_device_overrides: Optional[List[str]],
    block_apply_handoff_resource_ids: Optional[List[str]],
    session_id: str,
    conversation_id: str,
    pending_error_cls: type,
) -> None:
    if skip_approval:
        return
    from commander_approval_workflow import request_approval

    risk = evaluate_deploy_risk(bp)
    if not bool((risk or {}).get("requires_approval")):
        return
    risk_reasons = [str(r).strip() for r in list((risk or {}).get("reasons") or []) if str(r).strip()]
    approval_reason = "; ".join(risk_reasons[:3]) or "Container requests elevated runtime privileges"
    pending = request_approval(
        blueprint_id=blueprint_id,
        reason=approval_reason,
        network_mode=bp.network,
        risk_flags=list((risk or {}).get("risk_flags") or []),
        risk_reasons=risk_reasons,
        requested_cap_add=list((risk or {}).get("cap_add") or []),
        requested_security_opt=list((risk or {}).get("security_opt") or []),
        requested_cap_drop=list((risk or {}).get("cap_drop") or []),
        read_only_rootfs=bool((risk or {}).get("read_only_rootfs", False)),
        override_resources=override_resources,
        extra_env=extra_env,
        resume_volume=resume_volume,
        mount_overrides=runtime_mount_payloads or raw_mount_overrides,
        storage_scope_override=effective_scope_name,
        device_overrides=runtime_device_overrides or raw_device_overrides,
        block_apply_handoff_resource_ids=block_apply_handoff_resource_ids,
        session_id=session_id,
        conversation_id=conversation_id,
    )
    raise pending_error_cls(pending.id, approval_reason)
