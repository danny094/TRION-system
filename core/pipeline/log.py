from typing import Any

from core.classifier.contracts import ClassifierResult
from core.thinking.contracts import ThinkingPlan
from core.verifier.contracts import VerifierResult
from utils.logger import log_info

_TAG = "[Pipeline]"


def log_request_start(conversation_id: str, user_text: str, model: str) -> None:
    log_info(
        f"{_TAG} request conversation_id={conversation_id} model={model} "
        f"chars={len(user_text)}"
    )


def log_classifier(result: ClassifierResult) -> None:
    log_info(
        f"{_TAG} classifier category={result.category.value} "
        f"route={result.route.value} safety={result.safety_level.value} "
        f"needs_orchestrator={result.needs_orchestrator} "
        f"is_long_document={result.is_long_document} "
        f"tokens~{result.estimated_input_tokens}"
    )


def log_orchestrator(thinking_context: Any) -> None:
    if thinking_context is None:
        log_info(f"{_TAG} orchestrator skipped (direct_to_thinking)")
        return
    selected = thinking_context.get("selected_tools") or []
    available = thinking_context.get("available_tools") or []
    log_info(
        f"{_TAG} orchestrator ran available={len(available)} "
        f"selected={len(selected)}"
    )


def log_thinking(plan: ThinkingPlan) -> None:
    log_info(
        f"{_TAG} thinking intent={plan.intent!r} steps={len(plan.steps)} "
        f"needs_task_loop={plan.needs_task_loop} risk={plan.risk_level.value}"
    )


def log_verifier(result: VerifierResult) -> None:
    log_info(
        f"{_TAG} verifier verdict={result.verdict.value} "
        f"warnings={len(result.warnings)}"
    )


def log_task_loop(result: Any) -> None:
    if result is None:
        log_info(f"{_TAG} task_loop skipped")
        return
    state = getattr(result, "state", None)
    state_value = state.value if hasattr(state, "value") else str(state)
    steps = getattr(result, "completed_steps", None)
    if steps is None:
        steps = getattr(result, "step_count", None)
    log_info(f"{_TAG} task_loop state={state_value} steps={steps}")


def log_output(content: str) -> None:
    log_info(f"{_TAG} output chars={len(content or '')}")
