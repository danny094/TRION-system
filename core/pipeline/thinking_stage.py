import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict

from core.classifier.contracts import ClassifierResult
from core.input_processor.contracts import DocumentContext
from core.pipeline.common import merge_thinking_contexts


@dataclass(frozen=True)
class ThinkingStageResult:
    plan: Any
    thinking_context: Dict[str, Any] | None


def build_thinking_stage(
    user_text: str,
    classifier_result: ClassifierResult,
    *,
    build_plan_fn: Callable[..., Any],
    orchestrator_thinking_context: Dict[str, Any] | None,
    routing_frame_thinking_context: Dict[str, Any] | None,
    document_tools_thinking_context: Dict[str, Any] | None,
    document_context: DocumentContext | None,
) -> ThinkingStageResult:
    thinking_context = merge_thinking_contexts(
        orchestrator_thinking_context,
        routing_frame_thinking_context,
        document_tools_thinking_context,
    )
    build_plan_kwargs = {}
    if _accepts_kwarg(build_plan_fn, "orchestrator_context"):
        build_plan_kwargs["orchestrator_context"] = thinking_context
    if _accepts_kwarg(build_plan_fn, "document_context"):
        build_plan_kwargs["document_context"] = document_context
    return ThinkingStageResult(
        plan=build_plan_fn(user_text, classifier_result, **build_plan_kwargs),
        thinking_context=thinking_context,
    )


def _accepts_kwarg(fn: Any, name: str) -> bool:
    params = inspect.signature(fn).parameters.values()
    if name in inspect.signature(fn).parameters:
        return True
    return any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params)
