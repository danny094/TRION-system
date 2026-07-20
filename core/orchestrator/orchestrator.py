from typing import Any, Dict, Iterable, Optional

from core.classifier.contracts import ClassifierResult
from core.orchestrator.context import ContextSource
from core.orchestrator.contracts import OrchestratorPackage
from core.orchestrator.resolver import resolve


def orchestrate(
    user_text: str,
    classifier_result: ClassifierResult,
    raw_tools: Optional[Iterable[Any]] = None,
    context_sources: Optional[Dict[str, ContextSource]] = None,
    conversation_id: str = "",
    routing_frame: Optional[Dict[str, Any]] = None,
) -> OrchestratorPackage:
    return resolve(
        user_text,
        classifier_result,
        raw_tools,
        context_sources,
        conversation_id,
        routing_frame=routing_frame,
    )
