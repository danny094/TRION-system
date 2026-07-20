from typing import Any, Dict, Iterable, List, Optional

from core.classifier.contracts import Category, ClassifierResult
from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility import eligible_tools_for_contract
from core.orchestrator.tool_candidates.service import select_top_k_tools
from core.orchestrator.tool_candidates.scoring import score_tool_breakdown
from core.orchestrator.tool_descriptor_projection import descriptor_from_raw


def list_available_tools(raw_tools: Optional[Iterable[Any]] = None) -> List[ToolDescriptor]:
    """P11.0 SP4: Projektion von roh -> ToolDescriptor liegt in
    core/orchestrator/tool_descriptor_projection.py::descriptor_from_raw().
    Eligibility entsteht primaer in get_available_tools()
    (adapters/tool_runner_bridge.py); descriptor_from_raw() bleibt
    zusaetzlicher Fail-closed-Guard - siehe dortiger Modul-Docstring.
    """
    tools = [descriptor_from_raw(item) for item in (raw_tools or [])]
    return [tool for tool in tools if tool is not None]


def select_relevant_tools(
    user_text: str,
    classifier_result: ClassifierResult,
    available_tools: List[ToolDescriptor],
    rules: Optional[List[Dict[str, str]]] = None,
    routing_frame: Optional[Dict[str, Any]] = None,
) -> List[ToolDescriptor]:
    del rules
    frame_requires_tools = _frame_requires_tool_routing(routing_frame)
    if frame_requires_tools is False:
        return []
    if frame_requires_tools is None and classifier_result.category not in {Category.INFORMATION, Category.TOOL, Category.PLANNING}:
        return []
    # P11 SP3 Mini-Savepoint B (Doc56 "Tool-Contract und Eligibility";
    # Ersetzungskarte "RequiredCapabilitySpec und Constraint -> Contract-
    # basierte Eligibility"): wenn der RoutingFrame einen OperationContract
    # mitfuehrt, entscheidet ausschliesslich eligible_tools_for_contract()
    # (T_eligible: Domain/Operation/Evidence/Scope/Risiko) ueber Toolfreigabe.
    # Kein Rohtext-Resolver (resolve_required_capability_spec/_constraint,
    # is_active_container_capability_question) wird in diesem Fall noch
    # aufgerufen - das waere genau die per Plan verbotene Doppelautoritaet.
    # SP3-P DECIDE B: operation_contract ist Pflichtgrenze fuer jede
    # Toolauswahl. Fehlt der Schluessel, bleibt select_relevant_tools()
    # fail-closed; kein Rohtext-/Legacy-Fallback.
    if not isinstance(routing_frame, dict) or "operation_contract" not in routing_frame:
        return []
    contract = routing_frame.get("operation_contract")
    eligible = eligible_tools_for_contract(
        available_tools, contract if isinstance(contract, dict) else {}
    )
    if not eligible:
        return []
    if len(eligible) == 1:
        return eligible
    return _select_constrained_tools(user_text, eligible)


def _frame_requires_tool_routing(routing_frame: Optional[Dict[str, Any]]) -> Optional[bool]:
    if not isinstance(routing_frame, dict):
        return None
    intent_kind = str(routing_frame.get("intent_kind") or "").strip()
    execution_mode = str(routing_frame.get("execution_mode") or "").strip()
    evidence_need = str(routing_frame.get("evidence_need") or "").strip()
    if intent_kind in {"smalltalk", "feedback", "meta_analysis"}:
        return False
    if execution_mode in {"single_tool", "multi_tool_plan", "loop", "retrieve_context"}:
        return True
    if evidence_need in {"memory_context", "file_context", "live_runtime", "tool_result"}:
        return True
    if intent_kind in {"capability_test", "task_loop_request", "action_request", "current_state_question"}:
        return True
    if intent_kind in {"conceptual_question", "capability_question"} and execution_mode == "direct_answer":
        return False
    return None


def _select_constrained_tools(user_text: str, constrained: List[ToolDescriptor]) -> List[ToolDescriptor]:
    ranked = select_top_k_tools(user_text, constrained)
    if ranked:
        return ranked
    fallback = sorted(
        constrained,
        key=lambda tool: (-score_tool_breakdown(user_text, tool).total, tool.name),
    )
    return fallback[:1]
