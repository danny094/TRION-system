from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    mode: str = "fts"
    conversation_id: Optional[str] = None
    limit: int = 10


class DeleteBulkRequest(BaseModel):
    ids: List[int]


def _badge_from_policy(meta: Dict[str, Any]) -> str:
    memory_block = meta.get("memory") if isinstance(meta.get("memory"), dict) else {}
    status = meta.get("status") if isinstance(meta.get("status"), dict) else {}
    if bool(status.get("temporary")):
        return "temporary"
    if bool(memory_block.get("do_not_remember")):
        return "do_not_remember"
    mode = str(memory_block.get("mode") or "global_enabled").strip().lower()
    if mode in {"global_enabled", "conversation_only", "disabled"}:
        return mode
    return "global_enabled"


def _policy_response(
    conversation_id: str,
    raw_meta: Optional[Dict[str, Any]],
    build_meta: Callable[..., Dict[str, Any]],
    build_default_meta: Callable[..., Dict[str, Any]],
    build_policy: Callable[..., Any],
) -> Dict[str, Any]:
    meta = build_meta(raw_meta, conversation_id) if isinstance(raw_meta, dict) else build_default_meta(conversation_id)
    policy = build_policy(meta)
    if policy.temporary:
        badge = "temporary"
    elif policy.do_not_remember:
        badge = "do_not_remember"
    else:
        badge = policy.memory_mode.value
    return {
        "conversation_id": conversation_id,
        "memory_mode": policy.memory_mode.value,
        "allow_global_memory_read": policy.allow_global_memory_read,
        "allow_long_term_write": policy.allow_long_term_write,
        "do_not_remember": policy.do_not_remember,
        "temporary": policy.temporary,
        "badge": badge,
    }
