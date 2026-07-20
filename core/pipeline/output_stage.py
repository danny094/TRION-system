from dataclasses import dataclass
from typing import Any, Dict

from core.models import CoreChatResponse
from core.output.tool_grounding import collect_grounded_tool_results
from core.output.contracts import OutputRequest
from core.output.renderable_evidence import build_renderable_evidence
from core.pipeline.common import contract_dict
from core.pipeline.public_projection import REJECTION_MESSAGE, public_classifier_fields
from core.verifier.contracts import Verdict


@dataclass(frozen=True)
class OutputStageResult:
    output_request: OutputRequest


def rejected_response(
    *,
    model: str,
    conversation_id: str,
    classifier_result: Any,
    verifier_result: Any,
) -> CoreChatResponse:
    return CoreChatResponse(
        model=model,
        content=REJECTION_MESSAGE,
        conversation_id=conversation_id,
        done=True,
        done_reason=_done_reason_for_verdict(verifier_result.verdict),
        classifier_result=public_classifier_fields(classifier_result),
        validation_passed=False,
    )


def build_output_stage(
    *,
    user_text: str,
    thinking_plan: Any,
    verifier_result: Any,
    orchestrator_context: Dict[str, Any],
    document_tools_context: Dict[str, Any],
    task_loop_context: Dict[str, Any],
    document_context: Any,
    stream: bool,
    grounding_state: Dict[str, Any] | None = None,
) -> OutputStageResult:
    document_meta = {"document": contract_dict(document_context)} if document_context else {}
    grounded_tool_results = collect_grounded_tool_results(task_loop_context)
    grounded_meta = {"grounded_tool_results": grounded_tool_results} if grounded_tool_results else {}
    renderable_evidence = build_renderable_evidence(grounded_tool_results)
    evidence_meta = {"renderable_evidence": renderable_evidence} if renderable_evidence else {}
    grounding_meta = {"grounding_state": grounding_state} if isinstance(grounding_state, dict) and grounding_state else {}
    return OutputStageResult(
        output_request=OutputRequest(
            user_text=user_text,
            thinking_plan=thinking_plan,
            context={
                "verifier": contract_dict(verifier_result),
                **orchestrator_context,
                **document_tools_context,
                **task_loop_context,
                **grounded_meta,
                **evidence_meta,
                **grounding_meta,
                **document_meta,
            },
            stream=stream,
        )
    )


def approved_response(
    *,
    model: str,
    content: str,
    conversation_id: str,
    classifier_result: Any,
) -> CoreChatResponse:
    return CoreChatResponse(
        model=model,
        content=content,
        conversation_id=conversation_id,
        done=True,
        done_reason="stop",
        classifier_result=public_classifier_fields(classifier_result),
        memory_used=False,
        validation_passed=True,
        is_partial=False,
    )


def _done_reason_for_verdict(verdict: Verdict) -> str:
    if verdict == Verdict.HARD_BLOCK:
        return "blocked"
    if verdict == Verdict.REJECTED:
        return "rejected"
    return "stop"
