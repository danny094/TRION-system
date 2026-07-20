from dataclasses import dataclass
from typing import Any, Dict

from core.input_processor import select_document_tools
from core.input_processor.contracts import DocumentContext
from core.orchestrator.tools import list_available_tools


@dataclass(frozen=True)
class DocumentToolsStageResult:
    context: Dict[str, Any]
    thinking_context: Dict[str, Any] | None


def build_document_tools_stage(
    raw_tools: Any,
    document_context: DocumentContext | None,
    user_text: str = "",
) -> DocumentToolsStageResult:
    if not document_context:
        return DocumentToolsStageResult(context={}, thinking_context=None)
    available_tools = list_available_tools(raw_tools)
    tool_names = [tool.name for tool in available_tools]
    selected_names, tool_mode = select_document_tools(
        _tool_selection_text(user_text),
        tool_names,
        document_context,
    )
    selected_tools = [tool for tool in available_tools if tool.name in selected_names]
    if not available_tools and not selected_tools:
        return DocumentToolsStageResult(context={}, thinking_context=None)
    return DocumentToolsStageResult(
        context={
            "document_tools": {
                "available_tools": tool_names,
                "selected_tools": selected_names,
                "tool_mode": tool_mode,
            }
        },
        thinking_context={
            "available_tools": tool_names,
            "selected_tools": selected_names,
            "context": {
                "document_context_mode": "chunk_retrieval",
                "document_tool_mode": tool_mode,
            },
        },
    )


def _tool_selection_text(user_text: str) -> str:
    text = str(user_text or "").strip()
    if not text:
        return ""
    head = text.split("\n\n", 1)[0].strip()
    if 0 < len(head) <= 240:
        return head
    return text[:240]
