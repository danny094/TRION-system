import re
import json

from config import get_grounding_no_evidence_fallback_mode
from core.output.claim_classifier import classify_claim
from core.output.contracts import OutputRequest
from core.output.direct_tool_output import render_direct_tool_output
from core.output.evidence_contracts import EvidenceBundle, GuardDecision
from core.output.evidence_requirements import decide_guard
from core.output.truth_renderer import render_truth_projection
from core.output.tool_grounding import render_single_grounded_tool_result
from utils.response_intents import additional_evidence_message, additional_evidence_unresolved, missing_capability_message
from utils.time_followups import derive_time_followup_text


_POSITIVE_EXECUTION_PATTERNS = (
    r"\bich habe\b.*\b(getestet|geprueft|geprüft|probiert|versucht|ausgefuehrt|ausgeführt|gesucht)\b",
    r"\bwir haben\b.*\b(getestet|geprueft|geprüft|probiert|versucht|ausgefuehrt|ausgeführt|gesucht)\b",
    r"\bgetestete[nr]?\b",
    r"\btests?[: ]",
    r"\bergebnisse[: ]",
)
_NEGATED_EXECUTION_PATTERNS = (
    r"\bkonnte\b.*\b(nicht|keine)\b",
    r"\bkonnte ich\b.*\bnicht\b",
    r"\bnicht ausgefuehrt\b",
    r"\bnicht ausgeführt\b",
    r"\bkein passendes tool\b",
    r"\bkeine suchfunktion\b",
    r"\bnicht verifizieren\b",
)


def prefer_direct_grounded_output(output_request: OutputRequest) -> str:
    """
    Prefer a deterministic grounded render when exactly one verified tool result
    is available. This keeps single-tool factual answers out of the free-form
    LLM path.
    """
    context = output_request.context if isinstance(output_request.context, dict) else {}
    grounded = context.get("grounded_tool_results")
    if isinstance(grounded, list) and grounded and _has_missing_capability(output_request):
        return missing_capability_message(output_request.thinking_plan, output_request.user_text, grounded)
    if isinstance(grounded, list) and grounded and additional_evidence_unresolved(output_request.thinking_plan, grounded):
        return additional_evidence_message(output_request.thinking_plan)
    if isinstance(grounded, list) and len(grounded) == 1 and _current_turn_direct_output_allowed(output_request, grounded):
        derived = render_truth_projection(output_request, grounded)
        if derived:
            return derived
        return render_direct_tool_output(output_request)
    state = context.get("grounding_state") if isinstance(context, dict) else None
    carryover = state.get("grounded_results") if isinstance(state, dict) else None
    if not isinstance(carryover, list) or len(carryover) != 1:
        return ""
    if _has_missing_capability(output_request):
        return missing_capability_message(output_request.thinking_plan, output_request.user_text, carryover)
    if additional_evidence_unresolved(output_request.thinking_plan, carryover):
        return additional_evidence_message(output_request.thinking_plan)
    if not _is_carryover_relevant(output_request, carryover) or not _carryover_direct_output_allowed(carryover):
        return ""
    derived = render_truth_projection(output_request, carryover)
    if derived:
        return derived
    derived = _render_time_followup_from_carryover(output_request, carryover)
    if derived:
        return derived
    return render_single_grounded_tool_result(carryover)


def apply_execution_consistency_guard(output_request: OutputRequest, content: str) -> str:
    if not str(content or "").strip():
        return content
    if not _claims_positive_execution(content):
        return content
    if _contains_negated_execution(content):
        return content
    if _has_positive_execution_evidence(output_request):
        return content
    return (
        "Ich kann diese Ausfuehrung gerade nicht als erfolgt bestaetigen. "
        "Es liegen keine positiven Ausfuehrungsbelege fuer einen gestarteten und erfolgreich gelaufenen Schritt vor."
    )


def apply_no_evidence_fallback(output_request: OutputRequest, content: str) -> str:
    """
    If the runtime saw task-loop artifacts but has no verified grounded facts,
    downgrade the output to an explicit unknown instead of allowing free-form
    factual claims.
    """
    if get_grounding_no_evidence_fallback_mode() == "off":
        return content
    if not str(content or "").strip():
        return content
    bundle = _build_evidence_bundle(output_request)
    if _has_missing_capability(output_request):
        return missing_capability_message(output_request.thinking_plan, output_request.user_text, bundle.grounded_tool_results or bundle.relevant_carryover_results)
    if additional_evidence_unresolved(output_request.thinking_plan, bundle.grounded_tool_results):
        return additional_evidence_message(output_request.thinking_plan)
    if bundle.grounded_tool_results:
        return content
    if bundle.relevant_carryover_results:
        return content
    ctx = getattr(output_request, "context", {}) or {}
    routing_frame = ctx.get("routing_frame") if isinstance(ctx, dict) else None
    claim = classify_claim(
        output_request.user_text,
        dialogue_act=_dialogue_act_from_output_request(output_request),
        routing_frame=routing_frame,
    )
    if decide_guard(claim, bundle) == GuardDecision.EXPLICIT_UNKNOWN:
        return "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."
    if not bundle.task_loop_artifacts:
        return content
    return "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."


def apply_tool_markup_guard(output_request: OutputRequest, content: str) -> str:
    if "[TOOL_CALL]" not in str(content or ""):
        return content
    summary = _render_task_loop_search_summary(output_request)
    if summary:
        return summary
    return "Die Toolausführung lief, aber die Antwort enthielt unzulässiges Tool-Markup. Bitte formuliere das Ergebnis als normale Antwort."


def _dialogue_act_from_output_request(output_request: OutputRequest) -> str:
    thinking_plan = getattr(output_request, "thinking_plan", None)
    hints = getattr(thinking_plan, "context_hints", None)
    if isinstance(hints, dict):
        return str(hints.get("dialogue_act") or "").strip()
    return ""


def _build_evidence_bundle(output_request: OutputRequest) -> EvidenceBundle:
    context = output_request.context if isinstance(output_request.context, dict) else {}
    grounded = context.get("grounded_tool_results")
    grounded_results = list(grounded) if isinstance(grounded, list) else []
    state = context.get("grounding_state") if isinstance(context, dict) else None
    carryover = state.get("grounded_results") if isinstance(state, dict) else None
    relevant_carryover = (
        list(carryover)
        if isinstance(carryover, list) and carryover and _is_carryover_relevant(output_request, carryover)
        else []
    )
    task_loop = context.get("task_loop") if isinstance(context, dict) else None
    artifacts = task_loop.get("artifacts") if isinstance(task_loop, dict) and isinstance(task_loop.get("artifacts"), list) else []
    orchestrator = context.get("orchestrator") if isinstance(context, dict) else None
    available_tools = (
        [str(item).strip() for item in orchestrator.get("available_tools") if str(item).strip()]
        if isinstance(orchestrator, dict) and isinstance(orchestrator.get("available_tools"), list)
        else []
    )
    selected_tools = (
        [str(item).strip() for item in orchestrator.get("selected_tools") if str(item).strip()]
        if isinstance(orchestrator, dict) and isinstance(orchestrator.get("selected_tools"), list)
        else []
    )
    available_tool_details = (
        [dict(item) for item in orchestrator.get("available_tool_details") if isinstance(item, dict)]
        if isinstance(orchestrator, dict) and isinstance(orchestrator.get("available_tool_details"), list)
        else []
    )
    selected_tool_details = (
        [dict(item) for item in orchestrator.get("selected_tool_details") if isinstance(item, dict)]
        if isinstance(orchestrator, dict) and isinstance(orchestrator.get("selected_tool_details"), list)
        else []
    )
    home_context = (
        dict(inner.get("home_context") or {})
        if isinstance(orchestrator, dict)
        and isinstance((inner := orchestrator.get("context")), dict)
        and isinstance(inner.get("home_context"), dict)
        else {}
    )
    self_context = (
        dict(inner.get("self_context") or {})
        if isinstance(orchestrator, dict)
        and isinstance((inner := orchestrator.get("context")), dict)
        and isinstance(inner.get("self_context"), dict)
        else {}
    )
    return EvidenceBundle(
        grounded_tool_results=grounded_results,
        relevant_carryover_results=relevant_carryover,
        task_loop_artifacts=list(artifacts),
        available_tools=available_tools,
        selected_tools=selected_tools,
        available_tool_details=available_tool_details,
        selected_tool_details=selected_tool_details,
        home_context=home_context,
        self_context=self_context,
    )


def _is_carryover_relevant(output_request: OutputRequest, carryover: list[dict]) -> bool:
    if len(carryover) != 1:
        return False
    result = carryover[0] if isinstance(carryover[0], dict) else {}
    tool_name = str(result.get("tool_name") or "").strip().lower()
    if not tool_name:
        return False
    text = _normalize_text(getattr(output_request, "user_text", ""))
    if not text:
        return False
    tool_keywords = _tool_keywords(tool_name)
    if tool_keywords and any(keyword in text for keyword in tool_keywords):
        return True
    if _contains_conflicting_domain(text):
        return False
    return _is_generic_followup(text)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _contains_conflicting_domain(text: str) -> bool:
    return any(
        token in text
        for token in (
            "/trion-home/",
            ".txt",
            "datei",
            "file",
            "container",
            "ram",
            "vram",
            "gpu",
            "hardware",
            "ressourcen",
            "memory",
        )
    )


def _is_generic_followup(text: str) -> bool:
    if len(text) > 80:
        return False
    return any(
        phrase in text
        for phrase in (
            "und",
            "nochmal",
            "erneut",
            "welche zeitzone",
            "in welcher zeitzone",
            "gib das",
            "zeige das",
            "nur das ergebnis",
        )
    )


def _tool_keywords(tool_name: str) -> tuple[str, ...]:
    if tool_name == "time_now":
        return ("uhr", "uhrzeit", "zeit", "datum", "utc", "zeitzone", "time", "clock")
    if tool_name in {"container_list", "container_inspect", "container_logs"}:
        return ("container", "docker", "logs", "status", "ports", "inspect")
    return ()


def _render_task_loop_search_summary(output_request: OutputRequest) -> str:
    thinking_plan = getattr(output_request, "thinking_plan", None)
    steps = getattr(thinking_plan, "steps", None)
    if not isinstance(steps, list) or not steps:
        return ""
    task_loop = output_request.context.get("task_loop") if isinstance(output_request.context, dict) else None
    artifacts = task_loop.get("artifacts") if isinstance(task_loop, dict) and isinstance(task_loop.get("artifacts"), list) else []
    results_by_step = _tool_result_outputs_by_step(artifacts)
    if len(steps) == 1:
        step = steps[0]
        tool_name = str(getattr(step, "tool", "") or "").strip()
        result = results_by_step.get(str(getattr(step, "step_id", "") or "").strip(), {})
        if tool_name == "memory_graph_search" and isinstance(result, dict) and result:
            rendered = render_single_grounded_tool_result(
                [
                    {
                        "tool_name": tool_name,
                        "step_id": str(getattr(step, "step_id", "") or "").strip(),
                        "facts": result,
                    }
                ]
            )
            if rendered:
                return rendered
    lines = []
    for step in steps:
        tool_name = str(getattr(step, "tool", "") or "").strip()
        tool_arguments = getattr(step, "tool_arguments", None)
        if tool_name != "memory_graph_search" or not isinstance(tool_arguments, dict):
            return ""
        query = str(tool_arguments.get("query") or "").strip()
        if not query:
            return ""
        result = results_by_step.get(str(getattr(step, "step_id", "") or "").strip(), {})
        count = int(result.get("count") or 0) if isinstance(result, dict) else 0
        lines.append(f'- "{query}" -> {count} Treffer')
    if not lines:
        return ""
    return "**Ausgeführte Suchen:**\n" + "\n".join(lines)


def _tool_result_outputs_by_step(artifacts: list[dict]) -> dict[str, dict]:
    outputs: dict[str, dict] = {}
    for artifact in artifacts:
        if str(artifact.get("artifact_type") or "") != "tool_result":
            continue
        step_id = str(artifact.get("source_step_id") or "").strip()
        raw = artifact.get("output")
        if not step_id or not isinstance(raw, str):
            continue
        try:
            parsed = json.loads(raw)
        except Exception:
            continue
        if isinstance(parsed, dict):
            outputs[step_id] = parsed
    return outputs


def _render_time_followup_from_carryover(output_request: OutputRequest, carryover: list[dict]) -> str:
    if len(carryover) != 1:
        return ""
    result = carryover[0] if isinstance(carryover[0], dict) else {}
    if str(result.get("tool_name") or "").strip() != "time_now":
        return ""
    facts = result.get("facts") if isinstance(result.get("facts"), dict) else {}
    return derive_time_followup_text(getattr(output_request, "user_text", ""), facts)


def _has_missing_capability(output_request: OutputRequest) -> bool:
    need = getattr(getattr(output_request, "thinking_plan", None), "additional_evidence_need", None)
    return need is not None and not list(getattr(need, "candidate_tools", []) or [])


def _claims_positive_execution(content: str) -> bool:
    text = _normalize_text(content)
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in _POSITIVE_EXECUTION_PATTERNS)


def _contains_negated_execution(content: str) -> bool:
    text = _normalize_text(content)
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in _NEGATED_EXECUTION_PATTERNS)


def _has_positive_execution_evidence(output_request: OutputRequest) -> bool:
    context = output_request.context if isinstance(output_request.context, dict) else {}
    grounded = context.get("grounded_tool_results")
    if isinstance(grounded, list) and grounded:
        return True
    task_loop = context.get("task_loop")
    snapshot = task_loop.get("snapshot") if isinstance(task_loop, dict) and isinstance(task_loop.get("snapshot"), dict) else {}
    completed_steps = snapshot.get("completed_steps")
    if isinstance(completed_steps, list) and completed_steps:
        return True
    artifacts = task_loop.get("artifacts") if isinstance(task_loop, dict) and isinstance(task_loop.get("artifacts"), list) else []
    return bool(artifacts)


def _current_turn_direct_output_allowed(output_request: OutputRequest, grounded: list[dict]) -> bool:
    if not _supports_natural_direct_render(grounded):
        return False
    task_loop = output_request.context.get("task_loop") if isinstance(output_request.context, dict) else None
    if not isinstance(task_loop, dict):
        return True
    status = str(task_loop.get("completion_status") or "").strip().lower()
    if not status:
        return True
    return status == "complete"


def _carryover_direct_output_allowed(carryover: list[dict]) -> bool:
    return _supports_natural_direct_render(carryover)


def _supports_natural_direct_render(results: list[dict]) -> bool:
    if len(results) != 1:
        return False
    item = results[0] if isinstance(results[0], dict) else {}
    tool_name = str(item.get("tool_name") or "").strip()
    return tool_name in {"time_now", "container_list"}
