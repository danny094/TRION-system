from typing import Awaitable, Callable

from config import (
    OLLAMA_BASE,
    get_control_endpoint_override,
    get_control_llm_check_enable,
    get_control_llm_check_long_document_enable,
    get_control_llm_check_modes,
    get_control_model,
    get_control_model_deep,
    get_control_provider,
    get_control_timeout_deep_s,
    get_control_timeout_interactive_s,
)
from core.llm_provider_client import complete_prompt
from core.thinking.analyzer_io import invoke_prompt, parse_json_object
from core.thinking.contracts import ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult
from core.verifier.input_prepare import VerifierInput
from core.verifier.llm_result import _invalid, result_from_payload
from utils.logger import log_info

CompletePromptFn = Callable[..., Awaitable[str]]


def run_llm_check(
    plan: ThinkingPlan,
    verifier_input: VerifierInput,
    *,
    complete_prompt_fn: CompletePromptFn = complete_prompt,
    llm_enabled: bool | None = None,
    extra_modes: set[str] | None = None,
) -> VerifierResult:
    enabled = (
        llm_check_enabled(plan, verifier_input, extra_modes=extra_modes)
        if llm_enabled is None
        else bool(llm_enabled)
    )
    if not enabled:
        return VerifierResult(
            verdict=Verdict.APPROVED,
            reason=f"Control LLM check disabled. modes={','.join(get_control_llm_check_modes())}",
        )

    log_info(
        f"[Verifier] LLM check running "
        f"document_mode={verifier_input.document_mode} "
        f"needs_task_loop={plan.needs_task_loop} "
        f"risk={plan.risk_level.value}"
    )
    prompt = build_verifier_prompt(verifier_input, plan)
    try:
        raw = invoke_prompt(
            complete_prompt_fn,
            provider=get_control_provider(),
            model=control_model(verifier_input),
            prompt=prompt,
            timeout_s=control_timeout_s(verifier_input),
            ollama_endpoint=control_ollama_endpoint(verifier_input),
            json_mode=True,
        )
        parsed = parse_json_object(raw)
        if isinstance(parsed, dict):
            result = result_from_payload(parsed, verifier_input)
            if result:
                log_info(f"[Verifier] LLM check verdict={result.verdict.value}")
                return result
    except Exception as exc:
        return VerifierResult(
            verdict=Verdict.APPROVED,
            reason=f"Control LLM check failed open: {exc.__class__.__name__}.",
            warnings=["control_llm_check_failed"],
        )
    return _invalid(
        "control_llm_invalid_json",
        "Der Verifier-LLM-Check lieferte keine valide JSON-Entscheidung. Plane konservativer und halte das Ausgabeformat strikt ein.",
    )


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


def llm_check_enabled(
    plan: ThinkingPlan,
    verifier_input: VerifierInput,
    *,
    extra_modes: set[str] | None = None,
) -> bool:
    raw_modes = set(get_control_llm_check_modes())
    if extra_modes:
        raw_modes |= {mode for mode in extra_modes if mode in {"all", "long_document", "task_loop", "needs_confirmation"}}
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


from core.verifier.prompts import build_verifier_prompt
