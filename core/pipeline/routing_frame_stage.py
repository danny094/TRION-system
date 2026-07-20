from dataclasses import dataclass
from typing import Any, Dict

from core.classifier.contracts import ClassifierResult
from core.pipeline.common import contract_dict
from core.routing_frame.builder import build_routing_frame


@dataclass(frozen=True)
class RoutingFrameStageResult:
    context: Dict[str, Any]
    thinking_context: Dict[str, Any]


def build_routing_frame_stage(
    user_text: str,
    classifier_result: ClassifierResult,
    *,
    orchestrator_thinking_context: Dict[str, Any] | None,
) -> RoutingFrameStageResult:
    orchestrator = orchestrator_thinking_context if isinstance(orchestrator_thinking_context, dict) else {}
    available_tool_details = orchestrator.get("available_tool_details") if isinstance(orchestrator.get("available_tool_details"), list) else []
    selected_tool_details = orchestrator.get("selected_tool_details") if isinstance(orchestrator.get("selected_tool_details"), list) else []
    inner_context = orchestrator.get("context") if isinstance(orchestrator.get("context"), dict) else {}
    frame = build_routing_frame(
        user_text,
        classifier_result,
        available_tool_details=available_tool_details,
        selected_tool_details=selected_tool_details,
        context=inner_context,
    )
    return RoutingFrameStageResult(
        context={"routing_frame": frame},
        thinking_context={"context": {"routing_frame": frame}},
    )
