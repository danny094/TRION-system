"""Evidence-need and execution-mode resolution for the routing frame.

`evidence_need` decides what kind of context must be fetched before the
thinking layer can answer (memory_context / file_context / live_runtime /
self_context / none).

`execution_mode` decides how the orchestrator and task loop should run
(refuse / loop / multi_tool_plan / single_tool / retrieve_context /
direct_answer).
"""

from __future__ import annotations

from core.classifier.contracts import ClassifierResult, Route
from core.classifier.live_claims import LiveClaimKind


def evidence_need(live_claim: LiveClaimKind, *, domain: str, intent_kind: str) -> str:
    if intent_kind == "meta_analysis":
        return "none"
    if domain == "memory":
        return "memory_context" if intent_kind in {"capability_test", "task_loop_request"} else "self_context"
    if live_claim == LiveClaimKind.FILE_CONTENT:
        return "file_context"
    if live_claim in {LiveClaimKind.TIME, LiveClaimKind.HARDWARE, LiveClaimKind.CONTAINER_RUNTIME}:
        return "live_runtime"
    if live_claim == LiveClaimKind.SKILL_INVENTORY:
        return "self_context"
    return "none"


def execution_mode(
    classifier_result: ClassifierResult,
    *,
    selected_count: int,
    has_loop_markers: bool,
    domain: str,
    intent_kind: str,
    evidence_need_value: str,
) -> str:
    if classifier_result.route == Route.BLOCK:
        return "refuse"
    if has_loop_markers:
        return "loop"
    if selected_count > 1:
        return "multi_tool_plan"
    if selected_count == 1:
        return "single_tool"
    if intent_kind in {"capability_test", "task_loop_request", "action_request", "current_state_question"}:
        return "retrieve_context"
    if domain in {"memory", "container_runtime", "files", "hardware", "time"} and evidence_need_value in {
        "memory_context",
        "file_context",
        "live_runtime",
        "tool_result",
    }:
        return "retrieve_context"
    return "direct_answer"
