import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from commander_approval_contracts import APPROVAL_STORE_PATH, ApprovalStatus, PendingApproval
from commander_ws_activity import emit_activity

logger = logging.getLogger(__name__)

_pending: Dict[str, PendingApproval] = {}
_history: List[PendingApproval] = []
_lock = threading.Lock()
_callbacks: Dict[str, threading.Event] = {}
_last_store_mtime: float = 0.0


def _emit_ws_activity(event: str, level: str = "info", message: str = "", **data):
    try:
        emit_activity(event, level=level, message=message, **data)
    except Exception as exc:
        logger.debug("[Approval] WS emit failed (%s): %s", event, exc)


def approval_event_payload(approval: PendingApproval) -> dict:
    return {
        "approval_id": approval.id,
        "blueprint_id": approval.blueprint_id,
        "approval_reason": approval.reason,
        "network_mode": approval.network_mode.value,
        "risk_flags": list(approval.risk_flags),
        "risk_reasons": list(approval.risk_reasons),
        "requested_cap_add": list(approval.requested_cap_add),
        "requested_security_opt": list(approval.requested_security_opt),
        "requested_cap_drop": list(approval.requested_cap_drop),
        "read_only_rootfs": approval.read_only_rootfs,
        "mount_overrides": list(approval.mount_overrides or []),
        "storage_scope_override": approval.storage_scope_override or "",
        "device_overrides": list(approval.device_overrides or []),
        "status": approval.status.value,
    }


def save_unlocked() -> None:
    try:
        payload = {
            "pending": [item.to_persist_dict() for item in _pending.values()],
            "history": [item.to_persist_dict() for item in _history],
        }
        os.makedirs(os.path.dirname(APPROVAL_STORE_PATH), exist_ok=True)
        tmp_path = f"{APPROVAL_STORE_PATH}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2)
        os.replace(tmp_path, APPROVAL_STORE_PATH)
    except Exception as exc:
        logger.warning("[Approval] Failed to persist store: %s", exc)


def cleanup_expired_unlocked() -> None:
    now = time.time()
    expired = [
        item for item in _pending.values() if item.status == ApprovalStatus.PENDING and now > item.expires_at
    ]
    for item in expired:
        item.status = ApprovalStatus.EXPIRED
        item.resolved_at = datetime.utcnow().isoformat()
        item.resolved_by = "system_ttl"
        _pending.pop(item.id, None)
        _history.append(item)
        _emit_ws_activity(
            "approval_resolved",
            level="warn",
            message=f"Approval expired for {item.blueprint_id}",
            resolved_by=item.resolved_by,
            **approval_event_payload(item),
        )
    if expired:
        save_unlocked()


def load_store() -> None:
    global _last_store_mtime
    if not os.path.exists(APPROVAL_STORE_PATH):
        return
    try:
        mtime = os.path.getmtime(APPROVAL_STORE_PATH)
        with open(APPROVAL_STORE_PATH, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except Exception as exc:
        logger.warning("[Approval] Failed to load store: %s", exc)
        return
    with _lock:
        _pending.clear()
        _history.clear()
        _callbacks.clear()
        for row in raw.get("pending", []) if isinstance(raw, dict) else []:
            try:
                item = PendingApproval.from_persist_dict(row)
                if item.status == ApprovalStatus.PENDING:
                    _pending[item.id] = item
                    _callbacks[item.id] = threading.Event()
                else:
                    _history.append(item)
            except Exception:
                continue
        for row in raw.get("history", []) if isinstance(raw, dict) else []:
            try:
                _history.append(PendingApproval.from_persist_dict(row))
            except Exception:
                continue
        cleanup_expired_unlocked()
        save_unlocked()
        _last_store_mtime = mtime


def sync_from_disk_if_stale() -> None:
    global _last_store_mtime
    if not os.path.exists(APPROVAL_STORE_PATH):
        return
    try:
        mtime = os.path.getmtime(APPROVAL_STORE_PATH)
    except Exception:
        return
    if mtime <= _last_store_mtime:
        return
    try:
        with open(APPROVAL_STORE_PATH, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except Exception as exc:
        logger.warning("[Approval] Failed to sync store: %s", exc)
        return
    with _lock:
        for row in raw.get("pending", []) if isinstance(raw, dict) else []:
            try:
                item = PendingApproval.from_persist_dict(row)
                if item.status == ApprovalStatus.PENDING and item.id not in _pending:
                    _pending[item.id] = item
                    _callbacks[item.id] = threading.Event()
            except Exception:
                continue
        _last_store_mtime = mtime


def get_pending() -> List[dict]:
    sync_from_disk_if_stale()
    with _lock:
        cleanup_expired_unlocked()
        return [item.to_dict() for item in _pending.values() if item.status == ApprovalStatus.PENDING]


def get_approval(approval_id: str) -> Optional[dict]:
    sync_from_disk_if_stale()
    with _lock:
        item = _pending.get(approval_id)
        if item:
            if item.is_expired() and item.status == ApprovalStatus.PENDING:
                item.status = ApprovalStatus.EXPIRED
            return item.to_dict()
    return None


def get_history(limit: int = 20) -> List[dict]:
    with _lock:
        items = sorted(
            list(_history) + [item for item in _pending.values() if item.status != ApprovalStatus.PENDING],
            key=lambda item: item.created_at,
            reverse=True,
        )
        return [item.to_dict() for item in items[:limit]]


load_store()
