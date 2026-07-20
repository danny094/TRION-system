from typing import Any, Dict, Iterable, Optional

from config import get_autonomy_tool_allowlist, get_autonomy_tool_blocklist
from core.classifier.contracts import ClassifierResult
from core.orchestrator.context import ContextSource, build_context
from core.orchestrator.contracts import OrchestratorPackage
from core.orchestrator.tool_filter import filter_tools
from core.orchestrator.tools import list_available_tools, select_relevant_tools


def resolve(
    user_text: str,
    classifier_result: ClassifierResult,
    raw_tools: Optional[Iterable[Any]] = None,
    context_sources: Optional[Dict[str, ContextSource]] = None,
    conversation_id: str = "",
    routing_frame: Optional[Dict[str, Any]] = None,
) -> OrchestratorPackage:
    discovered = list_available_tools(raw_tools)
    available_tools = filter_tools(
        discovered,
        get_autonomy_tool_allowlist(),
        get_autonomy_tool_blocklist(),
    )
    selected_tools = select_relevant_tools(user_text, classifier_result, available_tools, routing_frame=routing_frame)
    context = build_context(user_text, conversation_id, context_sources)
    return OrchestratorPackage(
        available_tools=available_tools,
        selected_tools=selected_tools,
        context=context,
        classifier_result=classifier_result,
    )
