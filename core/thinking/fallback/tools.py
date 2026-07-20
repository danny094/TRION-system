"""Tool-selection helpers for the fallback analyzer.

Decides which tools the fallback path should suggest: reads the routing
frame, applies live-claim/time-followup guards, defers to required or
selected tools, and falls back to keyword-based suggestions only when
nothing more specific is known.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from core.classifier.contracts import ClassifierResult
from core.classifier.live_claims import LiveClaimKind
# C1 Bottleneck-Disziplin: kein Direktaufruf auf live_claims/classifier — immer über Capsule.
from core.orchestrator.frame_signals import live_claim_from_frame
from core.input_processor.contracts import DocumentContext
from utils.time_followups import has_derivable_time_followup

# Tool-Selection-Regeln: intelligence_modules/cim_skill_rag/tool_selection_rules.csv
# (PIANO 1.0 Schritt 3.1, 2026-06-11)
from intelligence_modules.cim_skill_rag.tool_selection_loader import load_tool_selection_rules

# Memory-Block-Signale: intelligence_modules/cim_skill_rag/memory_block_signals.csv
# (PIANO 1.0 B3-Fix, 2026-06-11)
from intelligence_modules.cim_skill_rag.memory_block_loader import load_memory_block_signals

# Dokument-Lookup-Tokens: intelligence_modules/cim_skill_rag/document_lookup_tokens.csv
# (PIANO 1.0 B3-Vollfix, 2026-06-12)
from intelligence_modules.cim_skill_rag.document_lookup_loader import load_document_lookup_tokens

# Fallback-Routing-Regeln: intelligence_modules/cim_skill_rag/fallback_routing_rules.csv
# (PIANO 1.0 B3-Vollfix, 2026-06-12)
from intelligence_modules.cim_skill_rag.fallback_routing_loader import load_fallback_routing_rules


def routing_frame(orchestrator_context: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(orchestrator_context, Mapping):
        return {}
    frame = orchestrator_context.get("routing_frame")
    return frame if isinstance(frame, Mapping) else {}


def tool_names(tools: Iterable[Any] | None) -> list[str]:
    names: list[str] = []
    for tool in tools or []:
        name = str(tool.get("name") if isinstance(tool, Mapping) else tool).strip()
        if name and name not in names:
            names.append(name)
    return names


def should_block_memory_graph_search(lowered: str) -> bool:
    text = str(lowered or "").strip()
    if not text:
        return False
    block_signals = load_memory_block_signals()
    analysis_kw = block_signals.get("analysis_block", ())
    vague_kw = block_signals.get("vague_search_block", ())
    compound_primary = block_signals.get("compound_self_search_primary", ())
    context_check = block_signals.get("context_check", ())
    if any(token in text for token in analysis_kw):
        return True
    if any(p in text for p in compound_primary) and any(s in text for s in vague_kw):
        return True
    if any(c in text for c in context_check) and any(token in text for token in vague_kw):
        return True
    return False


def _apply_fallback_routing_rules(
    frame: Mapping[str, Any],
    classifier_result: ClassifierResult | None,
    available: list[str],
) -> list[str]:
    """Wendet Fallback-Routing-Regeln aus IM an — gibt Tool-Liste zurück oder [].

    Regeln kommen aus fallback_routing_rules.csv (B3-Vollfix, PIANO 1.0, 2026-06-12).
    Keine hardcodierten Frame-Werte oder Classifier-Kategorien im Core.
    """
    if not available:
        return []
    frame_values = {
        "intent_kind": str(frame.get("intent_kind") or "").strip(),
        "execution_mode": str(frame.get("execution_mode") or "").strip(),
        "evidence_need": str(frame.get("evidence_need") or "").strip(),
        "classifier_category": classifier_result.category.value if classifier_result else "",
    }
    for rule in load_fallback_routing_rules():
        if frame_values.get(rule.condition_type, "") != rule.condition_value:
            continue
        if rule.requires_also:
            parts = rule.requires_also.split(":", 1)
            if len(parts) == 2 and frame_values.get(parts[0], "") != parts[1]:
                continue
        if rule.strategy == "first_available":
            return [available[0]]
    return []


def _document_tools_from_im(
    lowered: str,
    available: list[str],
    document_context: DocumentContext | None,
) -> list[str]:
    """Dokument-Tool-Auswahl — liest alle Tokens und Toolnamen aus intelligence_modules.

    Tokens kommen aus document_lookup_tokens.csv (B3-Vollfix, PIANO 1.0, 2026-06-12).
    """
    if not document_context:
        return []
    tokens = load_document_lookup_tokens()
    workspace_tool_names = tokens.get("workspace_tool", ())
    semantic_tool_names = tokens.get("semantic_tool", ())
    workspace_tool = workspace_tool_names[0] if workspace_tool_names else None
    semantic_tool = semantic_tool_names[0] if semantic_tool_names else None
    has_workspace = bool(workspace_tool) and workspace_tool in available and bool(
        getattr(document_context, "workspace_entry_ids", None)
    )
    has_semantic = bool(semantic_tool) and semantic_tool in available and bool(
        getattr(document_context, "semantic_keys", None)
    )
    if not has_workspace and not has_semantic:
        return []
    structure = tokens.get("structure_lookup", ())
    exact = tokens.get("exact_lookup", ())
    semantic_kw = tokens.get("semantic_lookup", ())
    if any(t in lowered for t in structure):
        workspace_first = bool(
            getattr(document_context, "preferred_entry_ids", None) and has_workspace
        )
    elif any(t in lowered for t in exact):
        workspace_first = True
    elif any(t in lowered for t in semantic_kw):
        workspace_first = False
    else:
        workspace_first = not has_semantic
    ordered = (
        [workspace_tool, semantic_tool]
        if workspace_first
        else [semantic_tool, workspace_tool]
    )
    allowed = {workspace_tool: has_workspace, semantic_tool: has_semantic}
    return [n for n in ordered if allowed[n]]


def suggested_tools(
    lowered: str,
    available_tools: Iterable[Any] | None,
    selected_tools: Iterable[Any] | None,
    classifier_result: ClassifierResult | None,
    document_context: DocumentContext | None,
    orchestrator_context: Mapping[str, Any] | None,
    replan_context: Mapping[str, Any] | None,
) -> list[str]:
    available = tool_names(available_tools)
    selected = tool_names(selected_tools)
    frame = routing_frame(orchestrator_context)
    # P11 SP3-H: ein vorhandenes routing_frame heisst, die Orchestrator-/
    # Eligibility-Pipeline ist gelaufen (Doc56 T_eligible). Eine dabei leere
    # selected-Liste ist dann eine gueltige, gegatete Tool-Wahrheit und darf
    # NICHT durch Keyword-/Dokument-Matching auf available ersetzt werden
    # (Schatten-Autoritaet). Fehlt das routing_frame komplett (kein
    # Orchestrator-Pfad ueberhaupt), bleibt der bisherige Keyword-Fallback
    # auf available unveraendert.
    has_routing_frame = isinstance(orchestrator_context, Mapping) and isinstance(
        orchestrator_context.get("routing_frame"), Mapping
    )
    live_claim = live_claim_from_frame(frame, lowered)
    block_signals = load_memory_block_signals()
    graph_search_names = block_signals.get("graph_search_tool", ())
    graph_search_tool = graph_search_names[0] if graph_search_names else None
    if has_derivable_time_followup(lowered, orchestrator_context):
        return []
    if not selected and (has_routing_frame or live_claim != LiveClaimKind.NONE):
        return []
    block_memory_search = should_block_memory_graph_search(lowered)
    if block_memory_search and graph_search_tool and selected == [graph_search_tool]:
        return []
    if selected:
        return selected
    document_tools = _document_tools_from_im(lowered, available, document_context)
    if document_tools:
        return document_tools
    for tool_name, phrases in load_tool_selection_rules():
        if tool_name not in available:
            continue
        if graph_search_tool and tool_name == graph_search_tool and block_memory_search:
            continue
        if any(phrase in lowered for phrase in phrases):
            return [tool_name]
    return _apply_fallback_routing_rules(frame, classifier_result, available)
