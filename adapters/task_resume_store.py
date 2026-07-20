import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import get_autonomy_task_resume_max_tasks, get_autonomy_task_resume_store_path
from core.pipeline.plan_contract_validator import operation_contract_fingerprint_from_context
from core.task_loop.contracts import StopReason, TaskLoopResult, TaskLoopSnapshot, TaskLoopState
from core.thinking.contracts import ThinkingPlan

from adapters.task_resume_finalization import prepared_failure_update, prepared_result_update
from adapters.task_resume_serialization import plan_to_dict, snapshot_to_dict

_LOCK = threading.Lock()

def register_waiting_task(
    plan: ThinkingPlan,
    snapshot: TaskLoopSnapshot,
    *,
    orchestrator_context: dict[str, Any] | None = None,
    available_tools: Any = None,
    tool_truth_source: str | None = None,
) -> str:
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    now = _utc_now()
    record = {
        "task_id": task_id,
        "status": TaskLoopState.WAITING.value,
        "created_at": now,
        "updated_at": now,
        "plan_id": snapshot.plan_id,
        "conversation_id": snapshot.conversation_id,
        "objective": snapshot.objective,
        "plan": plan_to_dict(plan),
        "snapshot": snapshot_to_dict(snapshot),
        "orchestrator_context": _dict_value(orchestrator_context),
        "operation_contract_fingerprint": operation_contract_fingerprint_from_context(orchestrator_context) or None,
        "available_tools": _list_value(available_tools),
        "tool_truth_source": str(tool_truth_source) if tool_truth_source else None,
        "result": None,
    }
    with _LOCK:
        payload = _load_store()
        tasks = payload.setdefault("tasks", {})
        tasks[task_id] = record
        _trim_tasks(tasks, max_tasks=get_autonomy_task_resume_max_tasks())
        _save_store(payload)
    return task_id

def get_task_record(task_id: str) -> dict[str, Any] | None:
    key = str(task_id or "").strip()
    if not key:
        return None
    with _LOCK:
        payload = _load_store()
        task = payload.get("tasks", {}).get(key)
    return dict(task) if isinstance(task, dict) else None
def claim_waiting_task(task_id: str, *, expected_updated_at: str | None = None) -> dict[str, Any] | None:
    key = str(task_id or "").strip()
    if not key:
        return None
    with _LOCK:
        payload = _load_store()
        tasks = payload.get("tasks", {})
        task = tasks.get(key)
        if not isinstance(task, dict):
            return None
        if str(task.get("status") or "") != TaskLoopState.WAITING.value:
            raise ValueError(f"task_not_waiting:{key}")
        if expected_updated_at is not None and task.get("updated_at") != expected_updated_at:
            raise ValueError(f"task_changed:{key}")
        snapshot = task.get("snapshot")
        if not isinstance(snapshot, dict) or str(snapshot.get("state") or "") != TaskLoopState.WAITING.value:
            raise ValueError(f"snapshot_not_waiting:{key}")
        task["status"] = TaskLoopState.EXECUTING.value
        task["updated_at"] = _utc_now()
        tasks[key] = task
        _save_store(payload)
        return dict(task)

def cancel_waiting_task(task_id: str) -> dict[str, Any] | None:
    key = str(task_id or "").strip()
    if not key:
        return None
    with _LOCK:
        payload = _load_store()
        tasks = payload.get("tasks", {})
        task = tasks.get(key)
        if not isinstance(task, dict):
            return None
        if str(task.get("status") or "") != TaskLoopState.WAITING.value:
            raise ValueError(f"task_not_waiting:{key}")
        snapshot = task.get("snapshot")
        if not isinstance(snapshot, dict) or str(snapshot.get("state") or "") != TaskLoopState.WAITING.value:
            raise ValueError(f"snapshot_not_waiting:{key}")
        snapshot = {**snapshot, "state": TaskLoopState.CANCELLED.value, "stop_reason": StopReason.USER_CANCELLED.value}
        task["status"] = TaskLoopState.CANCELLED.value
        task["updated_at"] = _utc_now()
        task["snapshot"] = snapshot
        task["result"] = {"state": TaskLoopState.CANCELLED.value, "stop_reason": StopReason.USER_CANCELLED.value}
        tasks[key] = task
        _save_store(payload)
        return dict(task)
def finalize_claimed_task(
    task_id: str, result: TaskLoopResult, *, expected_updated_at: str,
) -> dict[str, Any] | None:
    key = str(task_id or "").strip()
    if not key or type(expected_updated_at) is not str or not expected_updated_at:
        return None
    prepared = prepared_result_update(result, updated_at=_utc_now())
    with _LOCK:
        payload = _load_store()
        tasks = payload.get("tasks", {})
        task = tasks.get(key)
        if (
            not isinstance(task, dict)
            or task.get("status") != TaskLoopState.EXECUTING.value
            or task.get("updated_at") != expected_updated_at
        ):
            return None
        updated = _apply_result(task, prepared)
        _save_store(_payload_with_task(payload, tasks, key, updated))
        return dict(updated)
def finalize_claimed_failure(task_id: str, *, expected_updated_at: str) -> dict[str, Any] | None:
    key = str(task_id or "").strip()
    if not key or type(expected_updated_at) is not str or not expected_updated_at:
        return None
    with _LOCK:
        payload = _load_store()
        tasks = payload.get("tasks", {})
        task = tasks.get(key)
        if (
            type(task) is not dict
            or task.get("status") != TaskLoopState.EXECUTING.value
            or task.get("updated_at") != expected_updated_at
        ):
            return None
        updated = {**task, **prepared_failure_update(task, updated_at=_utc_now())}
        _save_store(_payload_with_task(payload, tasks, key, updated))
        return dict(updated)

def _apply_result(task: dict[str, Any], prepared: dict[str, Any]) -> dict[str, Any]:
    return {**task, **prepared}


def _payload_with_task(
    payload: dict[str, Any], tasks: dict[str, Any], key: str, task: dict[str, Any],
) -> dict[str, Any]:
    return {**payload, "tasks": {**tasks, key: task}}

def _store_path() -> Path:
    return Path(get_autonomy_task_resume_store_path()).expanduser()

def _load_store() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {"tasks": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {"tasks": {}}
        tasks = payload.get("tasks")
        if not isinstance(tasks, dict):
            payload["tasks"] = {}
        return payload
    except Exception:
        return {"tasks": {}}

def _save_store(payload: dict[str, Any]) -> None:
    path = _store_path()
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

def _trim_tasks(tasks: dict[str, Any], *, max_tasks: int) -> None:
    limit = max(10, int(max_tasks or 200))
    if len(tasks) <= limit:
        return
    ordered = sorted(tasks.items(), key=lambda item: str((item[1] or {}).get("updated_at") or ""))
    overflow = len(tasks) - limit
    for task_id, _ in ordered[:overflow]:
        tasks.pop(task_id, None)

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _dict_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}

def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []
