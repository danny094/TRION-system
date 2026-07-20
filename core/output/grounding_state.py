import threading
import time
from typing import Any

_LOCK = threading.Lock()
_STATE: dict[str, dict[str, Any]] = {}


def remember_grounding_state(
    *,
    conversation_id: str,
    history_len: int,
    grounded_results: list[dict[str, Any]],
    now_ts: float | None = None,
) -> None:
    conv_id = str(conversation_id or "").strip()
    if not conv_id or not isinstance(grounded_results, list) or not grounded_results:
        return
    stored = grounded_results[:4]
    with _LOCK:
        _STATE[conv_id] = {
            "updated_at": float(now_ts if now_ts is not None else time.time()),
            "history_len": max(0, int(history_len or 0)),
            "grounded_results": [dict(item) for item in stored if isinstance(item, dict)],
        }


def get_recent_grounding_state(
    *,
    conversation_id: str,
    history_len: int,
    ttl_s: int,
    ttl_turns: int,
    now_ts: float | None = None,
) -> dict[str, Any] | None:
    conv_id = str(conversation_id or "").strip()
    if not conv_id:
        return None
    now = float(now_ts if now_ts is not None else time.time())
    with _LOCK:
        state = _STATE.get(conv_id)
        if not isinstance(state, dict):
            return None
        updated_at = float(state.get("updated_at") or 0.0)
        previous_history_len = max(0, int(state.get("history_len") or 0))
        age_s = max(0.0, now - updated_at)
        age_turns = max(0, int(history_len or 0) - previous_history_len)
        if age_s > max(1, int(ttl_s or 0)) or age_turns > max(1, int(ttl_turns or 0)):
            _STATE.pop(conv_id, None)
            return None
        grounded_results = state.get("grounded_results")
        if not isinstance(grounded_results, list) or not grounded_results:
            return None
        return {
            "updated_at": updated_at,
            "age_s": age_s,
            "age_turns": age_turns,
            "grounded_results": [dict(item) for item in grounded_results if isinstance(item, dict)],
        }


def clear_grounding_state() -> None:
    with _LOCK:
        _STATE.clear()
