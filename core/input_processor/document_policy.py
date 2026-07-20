from typing import Iterable

from core.input_processor.contracts import DocumentContext

# PIANO 1.0 B3-Fix: Lookup-Tokens kommen aus intelligence_modules, nicht aus
# hardcodierten Tuples. (2026-06-12)
from intelligence_modules.cim_skill_rag.document_lookup_loader import load_document_lookup_tokens


def select_document_tools(
    user_text: str,
    available_tool_names: Iterable[str],
    document_context: DocumentContext | None,
) -> tuple[list[str], str]:
    if not document_context:
        return [], "none"
    available = [str(name).strip() for name in available_tool_names if str(name).strip()]
    has_workspace = "workspace_get" in available and bool(document_context.workspace_entry_ids)
    has_semantic = "memory_semantic_search" in available and bool(document_context.semantic_keys)
    if not has_workspace and not has_semantic:
        return [], "none"

    lowered = str(user_text or "").lower()
    if _is_structure_lookup(lowered):
        if document_context.preferred_entry_ids and has_workspace:
            return _ordered_tools(has_workspace, has_semantic, workspace_first=True), "structure_first"
        return _ordered_tools(has_workspace, has_semantic, workspace_first=False), "structure_search_first"
    if _is_exact_lookup(lowered):
        return _ordered_tools(has_workspace, has_semantic, workspace_first=True), "workspace_first"
    if _is_semantic_lookup(lowered):
        return _ordered_tools(has_workspace, has_semantic, workspace_first=False), "semantic_first"
    if has_semantic and has_workspace:
        return ["memory_semantic_search", "workspace_get"], "semantic_first"
    if has_semantic:
        return ["memory_semantic_search"], "semantic_only"
    return ["workspace_get"], "workspace_only"


def _ordered_tools(has_workspace: bool, has_semantic: bool, *, workspace_first: bool) -> list[str]:
    ordered = ["workspace_get", "memory_semantic_search"] if workspace_first else ["memory_semantic_search", "workspace_get"]
    allowed = {"workspace_get": has_workspace, "memory_semantic_search": has_semantic}
    return [name for name in ordered if allowed[name]]


def _is_exact_lookup(lowered: str) -> bool:
    tokens = load_document_lookup_tokens().get("exact_lookup", ())
    return any(token in lowered for token in tokens)


def _is_semantic_lookup(lowered: str) -> bool:
    tokens = load_document_lookup_tokens().get("semantic_lookup", ())
    return any(token in lowered for token in tokens)


def _is_structure_lookup(lowered: str) -> bool:
    tokens = load_document_lookup_tokens().get("structure_lookup", ())
    return any(token in lowered for token in tokens)
