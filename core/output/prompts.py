from typing import Any, Dict

from config import (
    get_output_renderable_evidence_max_bullets_per_item,
    get_output_renderable_evidence_max_items,
)
from core.output.claim_classifier import classify_claim
from core.output.evidence_contracts import ClaimType
from intelligence_modules.prompt_manager import load_prompt
from core.output.persona_runtime import get_runtime_persona_prompt
from utils.trion_home_contract import capability_description


def build_output_system_prompt(
    thinking_plan: Any,
    context: Dict[str, Any],
) -> str:
    parts: list[str] = []

    persona = get_runtime_persona_prompt(context)
    if persona:
        parts.append(persona)

    base = load_prompt("layers", "output")
    if base:
        parts.append(base)

    contract_blocks = _contract_blocks(thinking_plan, context)
    if contract_blocks:
        parts.extend(contract_blocks)

    plan_block = _plan_block(thinking_plan)
    if plan_block:
        parts.append(plan_block)

    dialogue_block = _dialogue_block(thinking_plan)
    if dialogue_block:
        parts.append(dialogue_block)

    memory_block = _memory_block(context)
    if memory_block:
        parts.append(memory_block)

    grounded_block = _grounded_tool_block(context)
    if grounded_block:
        parts.append(grounded_block)

    home_block = _home_context_block(context)
    if home_block:
        parts.append(home_block)

    self_context_block = _self_context_block(context)
    if self_context_block:
        parts.append(self_context_block)

    task_block = _task_loop_block(context)
    if task_block:
        parts.append(task_block)

    return "\n\n".join(p for p in parts if p.strip())


def _contract_blocks(thinking_plan: Any, context: Dict[str, Any]) -> list[str]:
    routing_frame = context.get("routing_frame") if isinstance(context, dict) else None
    claim = classify_claim(
        _user_text(thinking_plan),
        dialogue_act=_dialogue_act(thinking_plan),
        routing_frame=routing_frame,
    )
    blocks = [load_prompt("contracts", "output_grounding", hybrid_mode_line="")]
    if claim.claim_type in {ClaimType.CONCEPTUAL_ANALYSIS, ClaimType.RUNTIME_HARDWARE, ClaimType.FILE_CONTENT}:
        blocks.append(load_prompt("contracts", "output_analysis_guard"))
    if _missing_memory_answer_risk(context):
        blocks.append(load_prompt("contracts", "output_anti_hallucination"))
    return [block for block in blocks if str(block or "").strip()]


def _plan_block(thinking_plan: Any) -> str:
    if thinking_plan is None:
        return ""
    intent = str(getattr(thinking_plan, "intent", "") or "").strip()
    reasoning = str(getattr(thinking_plan, "reasoning", "") or "").strip()
    if not intent:
        return ""
    lines = [f"## Dein Plan\nIntent: {intent}"]
    if reasoning:
        lines.append(f"Reasoning: {reasoning[:400]}")
    hints = getattr(thinking_plan, "context_hints", None)
    if isinstance(hints, dict):
        dialogue_act = str(hints.get("dialogue_act") or "").strip()
        response_tone = str(hints.get("response_tone") or "").strip()
        length_hint = str(hints.get("response_length_hint") or "").strip()
        if dialogue_act:
            lines.append(f"DialogueAct: {dialogue_act}")
        if response_tone:
            lines.append(f"ResponseTone: {response_tone}")
        if length_hint:
            lines.append(f"ResponseLengthHint: {length_hint}")
    projection = getattr(thinking_plan, "response_projection", None)
    projection_kind = str(getattr(projection, "kind", "") or "").strip()
    if projection_kind:
        lines.append(f"ResponseProjection: {projection_kind}")
    derivation = getattr(thinking_plan, "response_derivation", None)
    derivation_kind = str(getattr(derivation, "kind", "") or "").strip()
    if derivation_kind:
        lines.append(f"ResponseDerivation: {derivation_kind}")
    evidence_need = getattr(thinking_plan, "additional_evidence_need", None)
    need_reason = str(getattr(evidence_need, "reason", "") or "").strip()
    if need_reason:
        lines.append(f"AdditionalEvidenceNeeded: {need_reason[:240]}")
    return "\n".join(lines)


def _user_text(thinking_plan: Any) -> str:
    hints = getattr(thinking_plan, "context_hints", None)
    if isinstance(hints, dict):
        return str(hints.get("user_text") or "").strip()
    return ""


def _dialogue_act(thinking_plan: Any) -> str:
    hints = getattr(thinking_plan, "context_hints", None)
    if isinstance(hints, dict):
        return str(hints.get("dialogue_act") or "").strip()
    return ""


def _dialogue_block(thinking_plan: Any) -> str:
    # Regeltext: intelligence_modules/prompts/contracts/output_dialogue_rule.md
    # (PIANO 1.0 Schritt 1.2, 2026-06-11)
    dialogue_act = _dialogue_act(thinking_plan).lower()
    if dialogue_act not in {"smalltalk", "feedback", "ack"}:
        return ""
    return load_prompt("contracts", "output_dialogue_rule")


def _memory_block(context: Dict[str, Any]) -> str:
    orchestrator = context.get("orchestrator") or {}
    inner = orchestrator.get("context") if isinstance(orchestrator, dict) else None
    memory = inner.get("memory") if isinstance(inner, dict) else None
    if not isinstance(memory, dict):
        return ""
    items = memory.get("items") or memory.get("results") or []
    if not isinstance(items, list) or not items:
        return ""
    lines = ["## Relevante Erinnerungen"]
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or item.get("text") or "").strip()
        if content:
            lines.append(f"- {content[:200]}")
    return "\n".join(lines) if len(lines) > 1 else ""


def _missing_memory_answer_risk(context: Dict[str, Any]) -> bool:
    orchestrator = context.get("orchestrator") or {}
    inner = orchestrator.get("context") if isinstance(orchestrator, dict) else None
    memory = inner.get("memory") if isinstance(inner, dict) else None
    if not isinstance(memory, dict):
        return False
    if memory.get("available") is False:
        return False
    items = memory.get("items") or memory.get("results") or []
    if isinstance(items, list) and items:
        return False
    return bool(memory)


def _task_loop_block(context: Dict[str, Any]) -> str:
    task_loop = context.get("task_loop") or {}
    if not isinstance(task_loop, dict):
        return ""
    artifacts = task_loop.get("artifacts") or []
    if not isinstance(artifacts, list) or not artifacts:
        return ""
    lines = ["## Ergebnisse aus ausgeführten Schritten"]
    for artifact in artifacts[:6]:
        if not isinstance(artifact, dict):
            continue
        step = str(artifact.get("step_id") or artifact.get("title") or "").strip()
        result = str(artifact.get("result") or artifact.get("output") or "").strip()
        if step and result:
            lines.append(f"- {step}: {result[:300]}")
    return "\n".join(lines) if len(lines) > 1 else ""


def _grounded_tool_block(context: Dict[str, Any]) -> str:
    # Regeltext: intelligence_modules/prompts/contracts/output_evidence_header.md
    #            intelligence_modules/prompts/contracts/output_tool_facts_header.md
    # (PIANO 1.0 Schritt 1.2, 2026-06-11)
    evidence = context.get("renderable_evidence") or []
    if isinstance(evidence, list) and evidence:
        max_items = get_output_renderable_evidence_max_items()
        max_bullets = get_output_renderable_evidence_max_bullets_per_item()
        lines = load_prompt("contracts", "output_evidence_header").splitlines()
        for item in evidence[:max_items]:
            summary = str(getattr(item, "summary", "") or "").strip()
            bullets = getattr(item, "bullets", []) if isinstance(getattr(item, "bullets", []), list) else []
            if summary:
                lines.append(f"- {summary}")
            for bullet in bullets[:max_bullets]:
                text = str(bullet or "").strip()
                if text:
                    lines.append(f"  {text}")
        return "\n".join(lines) if len(lines) > 2 else ""
    grounded = context.get("grounded_tool_results") or []
    if not isinstance(grounded, list) or not grounded:
        return ""
    lines = load_prompt("contracts", "output_tool_facts_header").splitlines()
    for item in grounded[:4]:
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get("tool_name") or "").strip()
        step_id = str(item.get("step_id") or "").strip()
        facts = item.get("facts") if isinstance(item.get("facts"), dict) else {}
        if not tool_name or not facts:
            continue
        header = f"- Tool `{tool_name}`"
        if step_id:
            header += f" (step `{step_id}`)"
        lines.append(header)
        for key, value in list(facts.items())[:12]:
            lines.append(f"  {key}: {value}")
    return "\n".join(lines) if len(lines) > 2 else ""


def _home_context_block(context: Dict[str, Any]) -> str:
    # Regeltext: intelligence_modules/prompts/contracts/output_home_scope_rule.md
    # (PIANO 1.0 Schritt 1.2, 2026-06-11)
    orchestrator = context.get("orchestrator") or {}
    inner = orchestrator.get("context") if isinstance(orchestrator, dict) else None
    home = inner.get("home_context") if isinstance(inner, dict) else None
    if not isinstance(home, dict) or home.get("verified") is not True:
        return ""
    lines = load_prompt("contracts", "output_home_scope_rule").splitlines()
    container_name = str(home.get("container_name") or "").strip()
    runtime_profile = str(home.get("runtime_profile") or "").strip()
    home_root = str(home.get("home_root") or "").strip()
    if container_name:
        lines.append(f"- container_name: {container_name}")
    if runtime_profile:
        lines.append(f"- runtime_profile: {runtime_profile}")
    if home_root:
        lines.append(f"- home_root: {home_root}")
    available = home.get("available_capability_classes")
    if isinstance(available, list) and available:
        lines.append(f"- available_capability_classes: {', '.join(str(item).strip() for item in available if str(item).strip())}")
        for item in available[:8]:
            name = str(item).strip()
            description = capability_description(name)
            if name and description:
                lines.append(f"  {name}: {description}")
    missing = home.get("missing_capability_classes")
    if isinstance(missing, list) and missing:
        lines.append(f"- missing_capability_classes: {', '.join(str(item).strip() for item in missing if str(item).strip())}")
        for item in missing[:8]:
            name = str(item).strip()
            description = capability_description(name)
            if name and description:
                lines.append(f"  {name}: {description}")
    roots = home.get("allowed_write_roots")
    if isinstance(roots, list) and roots:
        lines.append(f"- allowed_write_roots: {', '.join(str(item).strip() for item in roots if str(item).strip())}")
    return "\n".join(lines) if len(lines) > 2 else ""


def _self_context_block(context: Dict[str, Any]) -> str:
    # Regeltext: intelligence_modules/prompts/contracts/output_self_context_rule.md
    # (PIANO 1.0 Schritt 1.2, 2026-06-11)
    orchestrator = context.get("orchestrator") or {}
    inner = orchestrator.get("context") if isinstance(orchestrator, dict) else None
    self_context = inner.get("self_context") if isinstance(inner, dict) else None
    if not isinstance(self_context, dict):
        return ""
    identity = self_context.get("identity") if isinstance(self_context.get("identity"), dict) else {}
    current_scope = self_context.get("current_scope") if isinstance(self_context.get("current_scope"), dict) else {}
    memory_visibility = self_context.get("memory_visibility") if isinstance(self_context.get("memory_visibility"), dict) else {}
    capabilities = self_context.get("capabilities") if isinstance(self_context.get("capabilities"), list) else []
    uncertainties = self_context.get("uncertainties") if isinstance(self_context.get("uncertainties"), list) else []
    lines = load_prompt("contracts", "output_self_context_rule").splitlines()
    if identity:
        lines.append(f"- identity: {str(identity.get('name') or '').strip()} ({str(identity.get('role') or '').strip()})")
    if current_scope:
        runtime_profile = str(current_scope.get("runtime_profile") or "").strip()
        home_name = str(current_scope.get("home_container_name") or "").strip()
        if runtime_profile:
            lines.append(f"- current_runtime_profile: {runtime_profile}")
        if home_name:
            lines.append(f"- current_home_container: {home_name}")
    if memory_visibility:
        lines.append(
            "- memory_visibility: "
            f"mode={str(memory_visibility.get('memory_mode') or '').strip()}, "
            f"global_read={bool(memory_visibility.get('allow_global_memory_read'))}, "
            f"long_term_write={bool(memory_visibility.get('allow_long_term_write'))}, "
            f"max_hits={int(memory_visibility.get('max_memory_hits') or 0)}"
        )
    if capabilities:
        lines.append("- capability_classes (abstrakt, keine Tool-Namen):")
        for item in capabilities[:12]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            status = str(item.get("status") or "").strip()
            description = str(item.get("description") or "").strip()
            source = str(item.get("source") or "").strip()
            if name and status:
                tail = f" - {description}" if description else ""
                lines.append(f"  class:{name} [{status} via {source}]{tail}")
    if uncertainties:
        lines.append("- uncertainties:")
        for item in uncertainties[:6]:
            if not isinstance(item, dict):
                continue
            subject = str(item.get("subject") or "").strip()
            status = str(item.get("status") or "").strip()
            message = str(item.get("message") or "").strip()
            if subject and status:
                lines.append(f"  {subject} [{status}]: {message}")
    return "\n".join(lines) if len(lines) > 3 else ""
