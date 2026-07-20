"""Entry-Point für core.thinking.analyzer.

Öffentliche API: analyze_request.
Alle Logik liegt in den Submodulen; dieser Entry-Point verdrahtet sie nur.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Iterable, Mapping

from config import (
    get_thinking_analyzer_enable,
    get_thinking_model,
    get_thinking_provider,
    get_thinking_timeout_s,
)
from core.classifier.contracts import ClassifierResult
from core.input_processor.contracts import DocumentContext
from core.llm_provider_client import complete_prompt
from core.thinking.analyzer_io import invoke_prompt, parse_json_object
from core.thinking.analyzer.normalizers import (
    merge_selected_tools,
    normalize_derivable_time_followup,
    normalize_loop_hints,
)
from core.thinking.fallback import fallback_analysis
from core.thinking.prompts import (
    build_thinking_prompt,
    reduce_document_context,
    reduce_orchestrator_context,
)

__all__ = ["analyze_request"]

CompletePromptFn = Callable[..., Awaitable[str]]


def analyze_request(
    user_text: str,
    classifier_result: ClassifierResult | None,
    *,
    available_tools: Iterable[Any] | None = None,
    selected_tools: Iterable[Any] | None = None,
    orchestrator_context: Mapping[str, Any] | None = None,
    document_context: DocumentContext | None = None,
    replan_context: Mapping[str, Any] | None = None,
    complete_prompt_fn: CompletePromptFn = complete_prompt,
    llm_enabled: bool | None = None,
) -> Dict[str, Any]:
    enabled = get_thinking_analyzer_enable() if llm_enabled is None else bool(llm_enabled)
    if not enabled:
        raw = fallback_analysis(
            user_text,
            classifier_result,
            available_tools=available_tools,
            selected_tools=selected_tools,
            orchestrator_context=orchestrator_context,
            document_context=document_context,
            replan_context=replan_context,
        )
        return normalize_loop_hints(
            normalize_derivable_time_followup(raw, user_text, orchestrator_context),
            user_text=user_text,
            orchestrator_context=orchestrator_context,
        )
    # P11 SP3-H: das LLM darf nur aus selected_tools (T_eligible-gegated) waehlen.
    # available_tools ist hoechstens Kontext/Anzeige (Danny-Vorgabe), nicht
    # Vorschlagsquelle — kein Fallback auf available_tools mehr, auch wenn
    # selected_tools leer ist (sonst Schatten-Autoritaet im Prompt-Menue).
    prompt = build_thinking_prompt(
        user_text,
        available_tools=selected_tools,
        context_summary=reduce_orchestrator_context(orchestrator_context),
        document_context_summary=reduce_document_context(document_context),
        replan_context=replan_context,
    )
    try:
        raw = invoke_prompt(
            complete_prompt_fn,
            provider=get_thinking_provider(),
            model=get_thinking_model(),
            prompt=prompt,
            timeout_s=get_thinking_timeout_s(),
            json_mode=True,
        )
        parsed = parse_json_object(raw)
        if isinstance(parsed, dict):
            normalized = normalize_loop_hints(
                normalize_derivable_time_followup(parsed, user_text, orchestrator_context),
                user_text=user_text,
                orchestrator_context=orchestrator_context,
            )
            return merge_selected_tools(
                normalized,
                selected_tools,
                user_text=user_text,
                orchestrator_context=orchestrator_context,
            )
    except Exception:
        pass
    raw = fallback_analysis(
        user_text,
        classifier_result,
        available_tools=available_tools,
        selected_tools=selected_tools,
        orchestrator_context=orchestrator_context,
        document_context=document_context,
        replan_context=replan_context,
    )
    return normalize_loop_hints(
        normalize_derivable_time_followup(raw, user_text, orchestrator_context),
        user_text=user_text,
        orchestrator_context=orchestrator_context,
    )
