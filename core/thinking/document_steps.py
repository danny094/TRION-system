from typing import Any, Dict

from core.input_processor.contracts import DocumentContext
from core.thinking.contracts import PlanStep, RiskLevel

_SEARCH_FIRST_MODES = {"semantic_first", "structure_search_first"}


def build_document_steps(
    raw_plan: Dict[str, Any],
    user_text: str,
    suggested_tools: list[str],
    document_context: DocumentContext | None,
    risk: RiskLevel,
) -> list[PlanStep]:
    if not document_context or not suggested_tools:
        return []
    query = str(raw_plan.get("intent") or user_text or document_context.summary or "document query").strip()
    query_mode = _query_mode(query)
    mode = str(raw_plan.get("document_retrieval_mode") or "none")
    workspace_ids = _workspace_targets(document_context, mode, suggested_tools, query_mode=query_mode)
    if _search_first(mode, document_context, suggested_tools, query_mode=query_mode):
        return _semantic_steps(query, risk, document_context) + _workspace_steps(query, risk, workspace_ids)
    return _workspace_steps(query, risk, workspace_ids, search_driven=False) + _semantic_steps(query, risk, document_context)


def _search_first(
    mode: str,
    document_context: DocumentContext,
    suggested_tools: list[str],
    *,
    query_mode: str,
) -> bool:
    if "memory_semantic_search" not in suggested_tools or not document_context.semantic_keys:
        return False
    if mode in _SEARCH_FIRST_MODES:
        return True
    return not _workspace_targets(document_context, mode, suggested_tools, query_mode=query_mode)


def _workspace_targets(
    document_context: DocumentContext,
    mode: str,
    suggested_tools: list[str],
    *,
    query_mode: str,
) -> list[int]:
    if "workspace_get" not in suggested_tools:
        return []
    limit = _workspace_limit(mode, query_mode)
    for candidate_ids in _workspace_target_sets(document_context, mode, query_mode):
        targets = _limit_unique(candidate_ids, limit=limit)
        if targets:
            return targets
    return _limit_unique(document_context.workspace_entry_ids, limit=min(2, limit))


def _workspace_target_sets(document_context: DocumentContext, mode: str, query_mode: str) -> list[list[int]]:
    if mode == "structure_first":
        if query_mode == "chapter_specific":
            return [
                list(document_context.chapter_candidate_entry_ids),
                list(document_context.index_like_entry_ids),
                list(document_context.preferred_entry_ids),
            ]
        return [
            list(document_context.index_like_entry_ids),
            list(document_context.chapter_candidate_entry_ids),
            list(document_context.preferred_entry_ids),
        ]
    if mode == "workspace_first":
        if query_mode == "structure_overview":
            return [
                list(document_context.index_like_entry_ids),
                list(document_context.preferred_entry_ids),
                list(document_context.chapter_candidate_entry_ids),
            ]
        return [
            list(document_context.preferred_entry_ids),
            list(document_context.chapter_candidate_entry_ids),
            list(document_context.index_like_entry_ids),
        ]
    if mode in _SEARCH_FIRST_MODES:
        if query_mode == "structure_overview":
            return [
                list(document_context.index_like_entry_ids),
                list(document_context.chapter_candidate_entry_ids),
                list(document_context.preferred_entry_ids),
            ]
        return [
            list(document_context.chapter_candidate_entry_ids),
            list(document_context.preferred_entry_ids),
            list(document_context.index_like_entry_ids),
        ]
    return [
        list(document_context.preferred_entry_ids),
        list(document_context.chapter_candidate_entry_ids),
        list(document_context.index_like_entry_ids),
    ]


def _workspace_limit(mode: str, query_mode: str) -> int:
    if query_mode in {"structure_overview", "exact_lookup"}:
        return 2
    if mode == "workspace_first":
        return 2
    return 3


def _query_mode(query: str) -> str:
    lowered = str(query or "").lower()
    if any(
        token in lowered
        for token in (
            "how many chapter",
            "how many chapters",
            "wie viel kapitel",
            "wieviel kapitel",
            "list chapters",
            "chapter list",
            "inhaltsverzeichnis",
            "table of contents",
            "gliederung",
        )
    ):
        return "structure_overview"
    if any(token in lowered for token in ("chapter ", "kapitel ", "abschnitt ", "section ")) and any(char.isdigit() for char in lowered):
        return "chapter_specific"
    if any(token in lowered for token in ("quote", "zitat", "exact", "genau", "wo steht", "passage")):
        return "exact_lookup"
    return "generic"


def _limit_unique(values: list[int], *, limit: int) -> list[int]:
    unique: list[int] = []
    for value in values:
        entry_id = int(value or 0)
        if entry_id <= 0 or entry_id in unique:
            continue
        unique.append(entry_id)
        if len(unique) >= limit:
            break
    return unique


def _semantic_steps(
    query: str,
    risk: RiskLevel,
    document_context: DocumentContext,
) -> list[PlanStep]:
    if not document_context.semantic_keys:
        return []
    return [
        PlanStep(
            step_id="semantic_search_1",
            title="Search relevant document chunks",
            goal=query,
            tool="memory_semantic_search",
            tool_arguments={
                "query": query,
                "conversation_id": str(document_context.conversation_id or "global"),
                "content_type": "document_chunk",
            },
            risk=risk,
        )
    ]


def _workspace_steps(query: str, risk: RiskLevel, workspace_ids: list[int], *, search_driven: bool = True) -> list[PlanStep]:
    if not workspace_ids:
        return []
    steps: list[PlanStep] = []
    for index, entry_id in enumerate(workspace_ids, start=1):
        tool_arguments = {
            "entry_id": entry_id,
            "document_fallback_entry_id": entry_id,
        }
        if search_driven:
            tool_arguments.update(
                {
                    "document_source_step": "semantic_search_1",
                    "document_result_rank": index - 1,
                }
            )
        steps.append(
            PlanStep(
                step_id=f"workspace_{entry_id}",
                title=f"Read document chunk {index}",
                goal=query,
                tool="workspace_get",
                tool_arguments=tool_arguments,
                risk=risk,
            )
        )
    return steps
