import os
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from commander_runtime_models import NetworkMode, ResourceLimits

APPROVAL_TTL = int(os.environ.get("APPROVAL_TTL", "300"))
APPROVAL_STORE_PATH = os.environ.get("APPROVAL_STORE_PATH", "/tmp/trion_approvals_store.json")


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PendingApproval:
    """Container deploy request waiting for user approval."""

    def __init__(
        self,
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
    ):
        self.id = str(uuid.uuid4())[:8]
        self.blueprint_id = blueprint_id
        self.reason = reason
        self.network_mode = network_mode
        self.risk_flags = [str(f).strip() for f in list(risk_flags or []) if str(f or "").strip()]
        self.risk_reasons = [str(r).strip() for r in list(risk_reasons or []) if str(r or "").strip()]
        self.requested_cap_add = [str(c).strip() for c in list(requested_cap_add or []) if str(c or "").strip()]
        self.requested_security_opt = [str(o).strip() for o in list(requested_security_opt or []) if str(o or "").strip()]
        self.requested_cap_drop = [str(c).strip() for c in list(requested_cap_drop or []) if str(c or "").strip()]
        self.read_only_rootfs = bool(read_only_rootfs)
        self.override_resources = override_resources
        self.extra_env = extra_env
        self.resume_volume = resume_volume
        self.mount_overrides = list(mount_overrides or [])
        self.storage_scope_override = str(storage_scope_override or "").strip()
        self.device_overrides = list(device_overrides or [])
        self.block_apply_handoff_resource_ids = [
            str(item or "").strip()
            for item in list(block_apply_handoff_resource_ids or [])
            if str(item or "").strip()
        ]
        self.session_id = session_id
        self.conversation_id = conversation_id
        self.status = ApprovalStatus.PENDING
        self.created_at = datetime.utcnow().isoformat()
        self.expires_at = time.time() + APPROVAL_TTL
        self.resolved_at = None
        self.resolved_by = None

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "blueprint_id": self.blueprint_id,
            "reason": self.reason,
            "network_mode": self.network_mode.value,
            "risk_flags": list(self.risk_flags),
            "risk_reasons": list(self.risk_reasons),
            "requested_cap_add": list(self.requested_cap_add),
            "requested_security_opt": list(self.requested_security_opt),
            "requested_cap_drop": list(self.requested_cap_drop),
            "read_only_rootfs": self.read_only_rootfs,
            "status": self.status.value,
            "created_at": self.created_at,
            "ttl_remaining": max(0, int(self.expires_at - time.time())),
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "mount_overrides": list(self.mount_overrides or []),
            "storage_scope_override": self.storage_scope_override or "",
            "device_overrides": list(self.device_overrides or []),
            "block_apply_handoff_resource_ids": list(self.block_apply_handoff_resource_ids or []),
        }

    def to_persist_dict(self) -> dict:
        payload = self.to_dict()
        payload.update(
            {
                "expires_at": self.expires_at,
                "override_resources": self.override_resources.model_dump() if self.override_resources else None,
                "extra_env": dict(self.extra_env or {}),
                "resume_volume": self.resume_volume,
                "session_id": self.session_id,
                "conversation_id": self.conversation_id,
            }
        )
        return payload

    @classmethod
    def from_persist_dict(cls, data: dict) -> "PendingApproval":
        raw = dict(data or {})
        override_raw = raw.get("override_resources")
        item = cls(
            blueprint_id=str(raw.get("blueprint_id", "")),
            reason=str(raw.get("reason", "")),
            network_mode=NetworkMode(str(raw.get("network_mode", NetworkMode.FULL.value))),
            risk_flags=raw.get("risk_flags") if isinstance(raw.get("risk_flags"), list) else None,
            risk_reasons=raw.get("risk_reasons") if isinstance(raw.get("risk_reasons"), list) else None,
            requested_cap_add=raw.get("requested_cap_add") if isinstance(raw.get("requested_cap_add"), list) else None,
            requested_security_opt=raw.get("requested_security_opt")
            if isinstance(raw.get("requested_security_opt"), list)
            else None,
            requested_cap_drop=raw.get("requested_cap_drop") if isinstance(raw.get("requested_cap_drop"), list) else None,
            read_only_rootfs=bool(raw.get("read_only_rootfs", False)),
            override_resources=ResourceLimits(**override_raw) if isinstance(override_raw, dict) else None,
            extra_env=raw.get("extra_env") if isinstance(raw.get("extra_env"), dict) else None,
            resume_volume=raw.get("resume_volume"),
            mount_overrides=raw.get("mount_overrides") if isinstance(raw.get("mount_overrides"), list) else None,
            storage_scope_override=str(raw.get("storage_scope_override", "") or "").strip(),
            device_overrides=raw.get("device_overrides") if isinstance(raw.get("device_overrides"), list) else None,
            block_apply_handoff_resource_ids=raw.get("block_apply_handoff_resource_ids")
            if isinstance(raw.get("block_apply_handoff_resource_ids"), list)
            else None,
            session_id=str(raw.get("session_id", "")),
            conversation_id=str(raw.get("conversation_id", "")),
        )
        if raw.get("id"):
            item.id = str(raw["id"])
        status_raw = str(raw.get("status", ApprovalStatus.PENDING.value))
        item.status = ApprovalStatus(status_raw) if status_raw in ApprovalStatus._value2member_map_ else ApprovalStatus.PENDING
        if raw.get("created_at"):
            item.created_at = str(raw["created_at"])
        if raw.get("expires_at") is not None:
            try:
                item.expires_at = float(raw["expires_at"])
            except Exception:
                pass
        item.resolved_at = raw.get("resolved_at")
        item.resolved_by = raw.get("resolved_by")
        return item
