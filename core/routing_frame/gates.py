from typing import Any, Dict

_ORCHESTRATOR_INTENT_KINDS = {
    "capability_question",
    "capability_test",
    "current_state_question",
    "task_loop_request",
    "action_request",
}
_ORCHESTRATOR_EVIDENCE_NEEDS = {
    "self_context",
    "memory_context",
    "file_context",
    "live_runtime",
    "tool_result",
}
_ORCHESTRATOR_EXECUTION_MODES = {
    "retrieve_context",
    "single_tool",
    "multi_tool_plan",
    "loop",
}


def should_run_orchestrator_for_frame(
    raw_tools: Any,
    routing_frame: Dict[str, Any] | None,
) -> bool:
    if isinstance(routing_frame, dict):
        return _frame_requires_orchestrator(routing_frame)
    return bool(raw_tools)


def _frame_requires_orchestrator(routing_frame: Dict[str, Any] | None) -> bool:
    if not isinstance(routing_frame, dict):
        return False
    intent_kind = str(routing_frame.get("intent_kind") or "").strip()
    evidence_need = str(routing_frame.get("evidence_need") or "").strip()
    execution_mode = str(routing_frame.get("execution_mode") or "").strip()
    if intent_kind in _ORCHESTRATOR_INTENT_KINDS:
        return True
    if evidence_need in _ORCHESTRATOR_EVIDENCE_NEEDS:
        return True
    if execution_mode in _ORCHESTRATOR_EXECUTION_MODES:
        return True
    return False


def should_keep_orchestrator_context(
    routing_frame: Dict[str, Any] | None,
    *,
    selected_tool_count: int,
) -> bool:
    if selected_tool_count > 0:
        return True
    return _frame_requires_orchestrator(routing_frame)
