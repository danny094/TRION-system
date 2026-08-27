from dataclasses import dataclass
from typing import Any, Dict

from core.models import CoreChatResponse
from core.output.contracts import OutputRequest
from core.output.renderable_evidence import build_renderable_evidence
from core.pipeline.common import contract_dict
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff
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
    output_evidence: OutputEvidenceHandoff,
    document_context: Any,
    stream: bool,
) -> OutputStageResult:
    document_meta = {"document": contract_dict(document_context)} if document_context else {}
    return OutputStageResult(
        output_request=OutputRequest(
            user_text=user_text,
            thinking_plan=thinking_plan,
            output_evidence=output_evidence,
            renderable_evidence=build_renderable_evidence(output_evidence),
            context={
                "verifier": contract_dict(verifier_result),
                **orchestrator_context,
                **document_tools_context,
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
