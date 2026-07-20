from typing import Any

from core.task_loop.contracts import TaskLoopSnapshot
from core.task_loop.executor import TaskLoopEventSink
from core.task_loop.event_sanitization import public_replan_trigger, public_waiting_fields
from core.task_loop.provenance_trace import task_loop_provenance_event


def emit_task_loop_state(
    event_sink: TaskLoopEventSink | None,
    snapshot: TaskLoopSnapshot,
    *,
    step_id: str = "",
    step_title: str = "",
    total_steps: int = 0,
) -> None:
    if not callable(event_sink):
        return
    step_index = snapshot.current_step_index
    if snapshot.state.value == "completed" and total_steps > 0:
        step_index = min(step_index, max(0, int(total_steps) - 1))
    payload = {
        "type": "task_loop_state",
        "state": snapshot.state.value,
        "step_index": step_index,
        "total_steps": max(0, int(total_steps)),
        "stop_reason": snapshot.stop_reason.value if snapshot.stop_reason else None,
        **public_waiting_fields(snapshot.waiting_reason, snapshot.waiting_source),
        "completed_count": len(snapshot.completed_steps),
        "artifact_count": len(snapshot.artifacts),
        "run_total_steps": snapshot.total_steps,
        "tool_calls": snapshot.tool_calls,
        "max_total_steps": snapshot.max_total_steps,
        "max_tool_calls": snapshot.max_tool_calls,
        "deadline_set": snapshot.deadline_ts is not None,
        "replan_count": snapshot.replan_count,
        "max_replans": snapshot.max_replans,
        "max_steps": snapshot.max_steps,
        "no_progress_count": snapshot.no_progress_count,
    }
    try:
        event_sink(payload)
    except Exception:
        return
    _try_emit_provenance(event_sink, task_loop_provenance_event(snapshot))
    _try_emit_progress(event_sink, payload)


def emit_replan_trace(event_sink: TaskLoopEventSink | None, plan: Any, snapshot: TaskLoopSnapshot, failure: Any) -> None:
    """Emit sanitized replan decisions without artifact contents or argument values."""
    if not callable(event_sink):
        return
    need = getattr(plan, "additional_evidence_need", None)
    payload = {
        "type": "replan_trace",
        "stage": "thinking",
        "phase": "replan",
        "replan_count": snapshot.replan_count,
        "trigger": public_replan_trigger(failure),
        "failure_status": str(getattr(getattr(failure, "status", None), "value", "") or ""),
        "step_count": len(list(getattr(plan, "steps", []) or [])),
        "additional_evidence_present": need is not None,
        "artifact_count": len(snapshot.artifacts),
    }
    try:
        event_sink(payload)
    except Exception:
        return
    _try_emit_provenance(
        event_sink,
        task_loop_provenance_event(snapshot, phase="replan", plan=plan, failure=failure, validator_decision="approved"),
    )


def _try_emit_progress(event_sink: TaskLoopEventSink, payload: dict) -> None:
    """Emittiert progress_utterance für WAITING/REPLANNING/BLOCKED-Zustände.

    EXECUTING und COMPLETED erzeugen kein progress_utterance (kommt via tool_start
    bzw. final content). Der Builder gibt für diese Zustände None zurück.
    """
    from core.task_loop.progress_utterance_builder import build_progress_utterance
    try:
        progress = build_progress_utterance(payload)
        if progress is not None:
            event_sink(progress)
    except Exception:
        return


def _try_emit_provenance(event_sink: TaskLoopEventSink, payload: dict) -> None:
    try:
        event_sink(payload)
    except Exception:
        return
