from dataclasses import dataclass

from config import get_control_prompt_user_chars
from core.input_processor.contracts import DocumentContext
from core.thinking.contracts import ThinkingPlan


@dataclass(frozen=True)
class VerifierInput:
    user_text: str
    document_mode: str
    document_summary: str
    document_meta: dict[str, object]
    user_excerpt: str


def build_verifier_input(
    user_text: str,
    plan: ThinkingPlan,
    *,
    document_context: DocumentContext | None = None,
) -> VerifierInput:
    text = str(user_text or "")
    char_cap = get_control_prompt_user_chars()
    if not document_context:
        return VerifierInput(
            user_text=text,
            document_mode="normal",
            document_summary="",
            document_meta={},
            user_excerpt=text[:char_cap],
        )
    summary = str(document_context.summary or "")[:char_cap]
    question_focus = _question_focus(text, str(plan.context_hints.get("document_retrieval_mode") or "none"))
    return VerifierInput(
        user_text=text,
        document_mode="long_document",
        document_summary=summary,
        document_meta={
            "total_chunks": int(document_context.total_chunks or 0),
            "workspace_entry_ids": list(document_context.workspace_entry_ids or [])[:6],
            "preferred_entry_ids": list(document_context.preferred_entry_ids or [])[:6],
            "index_like_entry_ids": list(document_context.index_like_entry_ids or [])[:6],
            "chapter_candidate_entry_ids": list(document_context.chapter_candidate_entry_ids or [])[:6],
            "semantic_keys": list(document_context.semantic_keys or [])[:6],
            "document_retrieval_mode": str(plan.context_hints.get("document_retrieval_mode") or "none"),
            "question_focus": question_focus,
            "structure_required": question_focus == "structure",
            "plan_id": str(plan.plan_id or ""),
            "retrieval_plan": _retrieval_plan(plan),
        },
        user_excerpt=summary or text[:char_cap],
    )


def _retrieval_plan(plan: ThinkingPlan) -> dict[str, object]:
    search_steps = []
    direct_reads = []
    search_reads = []
    unresolved_sources = []
    for step in plan.steps:
        tool = str(step.tool or "").strip()
        if tool == "memory_semantic_search":
            search_steps.append(step.step_id)
            continue
        if tool != "workspace_get":
            continue
        source_step = str(step.tool_arguments.get("document_source_step") or "").strip()
        entry_id = int(step.tool_arguments.get("entry_id") or 0)
        if source_step:
            search_reads.append({"step_id": step.step_id, "entry_id": entry_id, "source_step": source_step})
            continue
        direct_reads.append({"step_id": step.step_id, "entry_id": entry_id})
    known_search_steps = set(search_steps)
    for item in search_reads:
        source_step = str(item.get("source_step") or "").strip()
        if source_step and source_step not in known_search_steps:
            unresolved_sources.append(source_step)
    return {
        "search_step_ids": search_steps[:4],
        "direct_workspace_reads": direct_reads[:4],
        "search_driven_workspace_reads": search_reads[:4],
        "unresolved_source_steps": unresolved_sources[:4],
    }


def _question_focus(user_text: str, retrieval_mode: str) -> str:
    lowered = str(user_text or "").lower()
    if _is_structure_question(lowered):
        return "structure"
    if _is_exact_question(lowered):
        return "exact"
    if retrieval_mode in {"structure_first", "structure_search_first"}:
        return "structure"
    if retrieval_mode in {"workspace_first", "exact_lookup"}:
        return "exact"
    return "semantic"


def _is_structure_question(lowered: str) -> bool:
    return any(
        token in lowered
        for token in (
            "wie viel kapitel",
            "wieviel kapitel",
            "how many chapter",
            "how many chapters",
            "inhaltsverzeichnis",
            "table of contents",
            "welche kapitel",
            "chapter list",
            "list chapters",
            "gliederung",
            "reihenfolge",
            "section order",
        )
    )


def _is_exact_question(lowered: str) -> bool:
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
            "entry id",
            "eintrag",
            "position",
        )
    )
