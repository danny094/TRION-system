from typing import Any

from core.thinking.contracts import ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from core.verifier.input_prepare import VerifierInput


def run_document_retrieval_check(plan: ThinkingPlan, verifier_input: VerifierInput) -> VerifierResult | None:
    if verifier_input.document_mode != "long_document":
        return None
    meta = verifier_input.document_meta
    workspace_ids = {int(item) for item in meta.get("workspace_entry_ids") or [] if int(item or 0) > 0}
    retrieval_mode = str(meta.get("document_retrieval_mode") or "none")
    retrieval_plan = dict(meta.get("retrieval_plan") or {})
    semantic_step_positions = {
        step.step_id: index
        for index, step in enumerate(plan.steps)
        if str(step.tool or "").strip() == "memory_semantic_search"
    }
    retrieval_plan_result = _retrieval_plan_consistency_check(retrieval_mode, retrieval_plan, meta)
    if retrieval_plan_result:
        return retrieval_plan_result
    for index, step in enumerate(plan.steps):
        if str(step.tool or "").strip() != "workspace_get":
            continue
        entry_id = int(step.tool_arguments.get("entry_id") or 0)
        if entry_id > 0 and entry_id not in workspace_ids:
            return VerifierResult(
                verdict=Verdict.REJECTED,
                hint="Nutze nur bekannte workspace_entry_ids aus dem DocumentContext oder leite Reads aus Suchtreffern ab.",
                reason="document_workspace_entry_out_of_scope",
                warnings=[f"entry_id={entry_id}"],
            )
        source_step = str(step.tool_arguments.get("document_source_step") or "").strip()
        if source_step and source_step not in semantic_step_positions:
            return VerifierResult(
                verdict=Verdict.REJECTED,
                hint="Fuege vor dynamischen Dokument-Reads einen passenden memory_semantic_search-Schritt ein.",
                reason="document_missing_semantic_source_step",
                warnings=[f"missing_source_step={source_step}"],
            )
        if source_step and semantic_step_positions.get(source_step, -1) >= index:
            return VerifierResult(
                verdict=Verdict.REJECTED,
                hint="Dynamische Dokument-Reads duerfen nur Suchschritte referenzieren, die vorher im Plan liegen.",
                reason="document_semantic_source_step_not_before_read",
                warnings=[f"source_step={source_step}", f"step_id={step.step_id}"],
            )
        if retrieval_mode in {"semantic_first", "structure_search_first"} and not source_step:
            return VerifierResult(
                verdict=Verdict.REJECTED,
                hint="Leite workspace_get im semantischen Dokumentpfad aus einem memory_semantic_search-Treffer ab.",
                reason="document_missing_search_driven_read",
                warnings=[f"step_id={step.step_id}"],
            )
    if retrieval_mode in {"semantic_first", "structure_search_first"} and not semantic_step_positions:
        return VerifierResult(
            verdict=Verdict.REJECTED,
            hint="Der semantische Dokumentpfad braucht zuerst einen memory_semantic_search-Schritt.",
            reason="document_missing_semantic_step",
        )
    return None


def _retrieval_plan_consistency_check(
    retrieval_mode: str,
    retrieval_plan: dict[str, Any],
    document_meta: dict[str, object],
) -> VerifierResult | None:
    unresolved_sources = [str(item).strip() for item in list(retrieval_plan.get("unresolved_source_steps") or []) if str(item).strip()]
    if unresolved_sources:
        return VerifierResult(
            verdict=Verdict.REJECTED,
            hint="Jeder document_source_step muss auf einen echten vorherigen memory_semantic_search-Schritt zeigen.",
            reason="document_unresolved_source_steps",
            warnings=unresolved_sources[:3],
        )
    direct_reads = list(retrieval_plan.get("direct_workspace_reads") or [])
    search_reads = list(retrieval_plan.get("search_driven_workspace_reads") or [])
    search_steps = list(retrieval_plan.get("search_step_ids") or [])
    has_index_candidates = bool(document_meta.get("index_like_entry_ids") or [])
    if retrieval_mode == "structure_first" and has_index_candidates and search_reads and not direct_reads:
        return VerifierResult(
            verdict=Verdict.REJECTED,
            hint="Fuer structure_first lies zuerst einen bekannten Index- oder Overview-Chunk direkt, bevor du nur search-driven Reads nutzt.",
            reason="document_structure_missing_direct_overview_read",
        )
    if retrieval_mode == "workspace_first" and not direct_reads:
        return VerifierResult(
            verdict=Verdict.REJECTED,
            hint="Fuer workspace_first braucht der Plan mindestens einen direkten workspace_get-Read auf einen bekannten Dokument-Chunk.",
            reason="document_exact_missing_direct_read",
        )
    if retrieval_mode == "workspace_only" and search_steps:
        return VerifierResult(
            verdict=Verdict.REJECTED,
            hint="workspace_only darf keinen memory_semantic_search-Schritt enthalten. Nutze sonst workspace_first oder semantic_first.",
            reason="document_workspace_only_contains_search",
        )
    if retrieval_mode == "semantic_first" and len(direct_reads) > 1:
        return VerifierResult(
            verdict=Verdict.REJECTED,
            hint="Im semantic_first-Pfad sollen direkte workspace_get-Reads die Ausnahme bleiben. Nutze zuerst Search-Treffer und lies danach gezielt wenige Chunks.",
            reason="document_semantic_too_many_direct_reads",
            warnings=[f"direct_reads={len(direct_reads)}"],
        )
    return None
