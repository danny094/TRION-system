from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from core.classifier.contracts import ClassifierResult
from core.routing_frame.gates import (
    should_keep_orchestrator_context,
    should_run_orchestrator_for_frame,
)
from core.self_context.builder import build_self_context
from utils.trion_home_contract import capability_classes_from_intents, is_verified_home_scope

OrchestratorFn = Callable[..., Any]

# P11 SP3-F Fund C (Danny-DECIDE: Option 1 - Markieren statt umbenennen).
# Zwei legitime Quellen fuer die Tools-Liste, die Replan/TaskLoop/Observer/
# Resume sehen: entweder vom Orchestrator bereits gefiltert, oder roher
# Fallback, weil kein Orchestrator-Block vorhanden war. Der Name
# "available_tools" allein unterscheidet das nicht - die Provenienz muss
# explizit mitgefuehrt werden.
TOOL_TRUTH_ORCHESTRATOR_FILTERED = "orchestrator_filtered"
TOOL_TRUTH_FALLBACK = "fallback_tools"


@dataclass(frozen=True)
class OrchestratorStageResult:
    context: Dict[str, Any]
    thinking_context: Dict[str, Any] | None


def build_orchestrator_stage(
    user_text: str,
    classifier_result: ClassifierResult,
    *,
    conversation_id: str,
    orchestrator_fn: OrchestratorFn,
    raw_tools: Any = None,
    context_sources: Optional[Dict[str, Any]] = None,
    routing_frame: Optional[Dict[str, Any]] = None,
) -> OrchestratorStageResult:
    if not should_run_orchestrator_for_frame(raw_tools, routing_frame):
        return OrchestratorStageResult(context={}, thinking_context=None)
    orchestrator_package = orchestrator_fn(
        user_text,
        classifier_result,
        raw_tools=raw_tools,
        context_sources=context_sources,
        conversation_id=conversation_id,
        routing_frame=routing_frame,
    )
    if not should_keep_orchestrator_context(
        routing_frame,
        selected_tool_count=len(orchestrator_package.selected_tools),
    ):
        return OrchestratorStageResult(context={}, thinking_context=None)
    orchestrator_context = {
        "orchestrator": {
            "available_tools": [tool.name for tool in orchestrator_package.available_tools],
            "selected_tools": [tool.name for tool in orchestrator_package.selected_tools],
            "available_tool_details": [
                {
                    "name": tool.name,
                    "source": tool.source,
                    "description": tool.description,
                    "intent_description": tool.intent_description,
                    "intent_keywords": list(tool.intent_keywords or []),
                    "capability_domain": tool.capability_domain,
                    "capability_operation": tool.capability_operation,
                    "capability_required_args": list(tool.capability_required_args or []),
                    "capability_evidence_types": list(tool.capability_evidence_types or []),
                    "capability_target_scopes": list(tool.capability_target_scopes or []),
                    "capability_output_schema": str(tool.capability_output_schema or ""),
                    "tool_role": tool.tool_role,
                    "capability_risk": tool.capability_risk,
                }
                for tool in orchestrator_package.available_tools
            ],
            "selected_tool_details": [
                {
                    "name": tool.name,
                    "source": tool.source,
                    "description": tool.description,
                    "intent_description": tool.intent_description,
                    "intent_keywords": list(tool.intent_keywords or []),
                    "capability_domain": tool.capability_domain,
                    "capability_operation": tool.capability_operation,
                    "capability_required_args": list(tool.capability_required_args or []),
                    "capability_evidence_types": list(tool.capability_evidence_types or []),
                    "capability_target_scopes": list(tool.capability_target_scopes or []),
                    "capability_output_schema": str(tool.capability_output_schema or ""),
                    "tool_role": tool.tool_role,
                    "capability_risk": tool.capability_risk,
                }
                for tool in orchestrator_package.selected_tools
            ],
            "context": dict(orchestrator_package.context),
        }
    }
    if isinstance(routing_frame, dict):
        orchestrator_context["orchestrator"]["context"]["routing_frame"] = dict(routing_frame)
    home_context = _build_home_context(orchestrator_context["orchestrator"])
    if home_context:
        orchestrator_context["orchestrator"]["context"]["home_context"] = home_context
    orchestrator_context["orchestrator"]["context"]["self_context"] = build_self_context(
        conversation_id=conversation_id,
        orchestrator_context=orchestrator_context["orchestrator"]["context"],
        available_tool_details=orchestrator_context["orchestrator"]["available_tool_details"],
    )
    return OrchestratorStageResult(
        context=orchestrator_context,
        thinking_context=orchestrator_context["orchestrator"],
    )
def replan_tools_with_provenance(orchestrator_context: Any, fallback_tools: Any) -> tuple[Any, str]:
    """Tool-Wahrheit fuer Replan/TaskLoop/Observer/Resume MIT Provenienz.

    orchestrator/tool_filter.py hat forbidden_direct hier schon entfernt.
    Kein erneutes Filtern hier — sonst Schatten-Autoritaet (Doc 36 Regel 2+3).
    Fallback auf fallback_tools nur, wenn der Orchestrator-Kontext (oder der
    Key darin) wirklich fehlt — eine leere Liste ist eine gueltige, gefilterte
    Tool-Wahrheit (z.B. alles war forbidden_direct) und darf NICHT durch die
    rohen, ungefilterten Tools ersetzt werden.

    P11 SP3-F Fund C (Danny-DECIDE: Option 1): liefert zusaetzlich zur Liste
    die Quelle (TOOL_TRUTH_ORCHESTRATOR_FILTERED / TOOL_TRUTH_FALLBACK), damit
    Aufrufer den Fallback-Fall nicht mehr mit gefilterter Wahrheit verwechseln
    koennen.
    """
    block = orchestrator_context.get("orchestrator") if isinstance(orchestrator_context, dict) else None
    if not isinstance(block, dict) or "available_tool_details" not in block:
        return fallback_tools, TOOL_TRUTH_FALLBACK
    return block.get("available_tool_details"), TOOL_TRUTH_ORCHESTRATOR_FILTERED


def replan_tools_from_context(orchestrator_context: Any, fallback_tools: Any) -> Any:
    """Kompatibilitaets-Wrapper um replan_tools_with_provenance() ohne Provenienz.

    Bestehende Aufrufer (z.B. Resume/Approve) bleiben unveraendert; Verhalten
    ist bit-identisch zur alten Implementierung. Wer die Quelle braucht, ruft
    replan_tools_with_provenance() direkt auf.
    """
    tools, _source = replan_tools_with_provenance(orchestrator_context, fallback_tools)
    return tools


def _build_home_context(orchestrator: Dict[str, Any]) -> Dict[str, Any]:
    context = orchestrator.get("context")
    if not isinstance(context, dict):
        return {}
    active = ((context.get("active_containers") or {}).get("active_home") or {}) if isinstance(context.get("active_containers"), dict) else {}
    scope = active.get("home_scope") if isinstance(active, dict) else {}
    if not is_verified_home_scope(scope if isinstance(scope, dict) else {}):
        return {}
    available, missing = capability_classes_from_intents(orchestrator.get("available_tool_details") or [])
    verification_sources = list(dict.fromkeys(list(scope.get("verification_sources") or []) + ["active_containers"]))
    return {
        "verified": True,
        "verification_sources": verification_sources,
        "container_id": str(active.get("container_id") or ""),
        "container_name": str(active.get("name") or ""),
        "blueprint_id": str(scope.get("blueprint_id") or ""),
        "owner_agent": str(scope.get("owner_agent") or ""),
        "runtime_profile": str(scope.get("runtime_profile") or ""),
        "home_root": str(scope.get("home_root") or ""),
        "allowed_write_roots": list(scope.get("allowed_write_roots") or []),
        "available_capability_classes": available,
        "missing_capability_classes": missing,
    }
