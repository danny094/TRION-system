from config import (
    OLLAMA_BASE,
    get_control_endpoint_override,
    get_control_llm_check_enable,
    get_control_llm_check_long_document_enable,
    get_control_llm_check_modes,
    get_control_model,
    get_control_model_deep,
    get_control_timeout_deep_s,
    get_control_timeout_interactive_s,
)
from core.thinking.contracts import ThinkingPlan
from core.verifier.input_prepare import VerifierInput


def response_mode(verifier_input: VerifierInput) -> str:
    return "deep" if verifier_input.document_mode == "long_document" else "interactive"


def control_model(verifier_input: VerifierInput) -> str:
    return get_control_model_deep() if response_mode(verifier_input) == "deep" else get_control_model()


def control_timeout_s(verifier_input: VerifierInput) -> int:
    return get_control_timeout_deep_s() if response_mode(verifier_input) == "deep" else get_control_timeout_interactive_s()


def control_ollama_endpoint(verifier_input: VerifierInput) -> str:
    endpoint = str(get_control_endpoint_override(response_mode(verifier_input)) or "").strip()
    return endpoint or str(OLLAMA_BASE or "").strip()


def plan_needs_confirmation(plan: ThinkingPlan) -> bool:
    if plan.risk_level.value == "needs_confirmation":
        return True
    return any(step.risk.value == "needs_confirmation" for step in plan.steps)


def llm_check_enabled(plan: ThinkingPlan, verifier_input: VerifierInput) -> bool:
    raw_modes = set(get_control_llm_check_modes())
    if raw_modes == {"off"}:
        return False
    modes = {mode for mode in raw_modes if mode != "off"}
    if not modes:
        return _legacy_enabled(verifier_input)
    if "all" in modes:
        return True
    if "long_document" in modes and verifier_input.document_mode == "long_document":
        return True
    if "task_loop" in modes and bool(plan.needs_task_loop):
        return True
    if "needs_confirmation" in modes and plan_needs_confirmation(plan):
        return True
    return False


def _legacy_enabled(verifier_input: VerifierInput) -> bool:
    if get_control_llm_check_enable():
        return True
    return verifier_input.document_mode == "long_document" and get_control_llm_check_long_document_enable()
