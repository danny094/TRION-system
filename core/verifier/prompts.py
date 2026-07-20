import json

from config import get_control_prompt_plan_chars
from core.thinking.contracts import ThinkingPlan
from core.verifier.input_prepare import VerifierInput
from intelligence_modules.prompt_manager import load_prompt


def build_verifier_prompt(verifier_input: VerifierInput, plan: ThinkingPlan) -> str:
    parts = [load_prompt("layers", "control")]
    parts.append(
        load_prompt(
            "layers",
            "control_verify_input",
            verifier_input_json=_json_text(_input_payload(verifier_input)),
        )
    )
    parts.append(
        load_prompt(
            "layers",
            "control_verify_plan",
            plan_json=_plan_text(plan),
        )
    )
    return "\n\n".join(part for part in parts if part.strip())


def _input_payload(verifier_input: VerifierInput) -> dict[str, object]:
    return {
        "document_mode": verifier_input.document_mode,
        "user_excerpt": verifier_input.user_excerpt,
        "document_summary": verifier_input.document_summary,
        "document_meta": verifier_input.document_meta,
        "document_retrieval": _document_retrieval_payload(verifier_input),
    }


def _document_retrieval_payload(verifier_input: VerifierInput) -> dict[str, object]:
    if verifier_input.document_mode != "long_document":
        return {}
    meta = verifier_input.document_meta
    return {
        "retrieval_mode": str(meta.get("document_retrieval_mode") or "none"),
        "question_focus": str(meta.get("question_focus") or "semantic"),
        "structure_required": bool(meta.get("structure_required")),
        "known_workspace_entry_ids": list(meta.get("workspace_entry_ids") or [])[:6],
        "preferred_entry_ids": list(meta.get("preferred_entry_ids") or [])[:6],
        "index_like_entry_ids": list(meta.get("index_like_entry_ids") or [])[:6],
        "chapter_candidate_entry_ids": list(meta.get("chapter_candidate_entry_ids") or [])[:6],
        "semantic_keys": [str(item)[:80] for item in list(meta.get("semantic_keys") or [])[:6]],
        "retrieval_plan": dict(meta.get("retrieval_plan") or {}),
    }


def _plan_text(plan: ThinkingPlan) -> str:
    char_cap = get_control_prompt_plan_chars()
    payload = {
        "intent": plan.intent,
        "plan_id": plan.plan_id,
        "needs_task_loop": plan.needs_task_loop,
        "risk_level": plan.risk_level.value,
        "reasoning": plan.reasoning,
        "suggested_tools": plan.suggested_tools,
        "steps": [
            {
                "step_id": step.step_id,
                "title": step.title,
                "goal": step.goal,
                "tool": step.tool,
                "tool_arguments": step.tool_arguments,
                "risk": step.risk.value,
            }
            for step in plan.steps
        ],
    }
    text = _json_text(payload)
    return text if len(text) <= char_cap else f"{text[: max(0, char_cap - 16)].rstrip()}...(truncated)"


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)
