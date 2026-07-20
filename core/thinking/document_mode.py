from typing import Mapping

from core.input_processor.contracts import DocumentContext


def resolve_document_retrieval_mode(
    tools: list[str],
    document_context: DocumentContext | None,
    orchestrator_context: Mapping[str, object] | None,
    *,
    user_text: str = "",
) -> str:
    if not document_context:
        return "none"
    context_mode = str((orchestrator_context or {}).get("document_tool_mode") or "").strip()
    if context_mode:
        return context_mode
    lowered = str(user_text or "").lower()
    if "workspace_get" in tools and "memory_semantic_search" in tools:
        if _looks_structure_lookup(lowered):
            return "structure_first"
        if _looks_exact_lookup(lowered):
            return "workspace_first"
        return "semantic_first"
    if tools[:2] == ["workspace_get", "memory_semantic_search"]:
        return "workspace_first"
    if tools[:2] == ["memory_semantic_search", "workspace_get"]:
        return "semantic_first"
    if "workspace_get" in tools and getattr(document_context, "workspace_entry_ids", None):
        if _looks_exact_lookup(lowered):
            return "exact_lookup"
        return "workspace_only"
    if "memory_semantic_search" in tools and getattr(document_context, "semantic_keys", None):
        return "semantic_only"
    return "none"


def _looks_exact_lookup(lowered: str) -> bool:
    return any(
        token in lowered
        for token in (
            "quote",
            "zitat",
            "exact",
            "genau",
            "wo steht",
            "passage",
            "abschnitt",
            "chunk",
            "lies",
            "read",
        )
    )


def _looks_structure_lookup(lowered: str) -> bool:
    return any(
        token in lowered
        for token in (
            "wie viel kapitel",
            "wie viele kapitel",
            "wieviel kapitel",
            "how many chapter",
            "how many chapters",
            "inhaltsverzeichnis",
            "table of contents",
            "welche kapitel",
            "list chapters",
            "chapter list",
            "gliederung",
        )
    )
