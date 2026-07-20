from typing import Any, Awaitable, Callable, Optional

from core.models import CoreChatRequest
from core.output.claim_classifier import classify_claim
from core.output.contracts import OutputRequest, OutputResult
from core.output.evidence_contracts import ClaimType
from core.output.evidence_guard import apply_execution_consistency_guard, apply_no_evidence_fallback, apply_tool_markup_guard
from core.output.stream import ChunkSink, CompleteChatFn, complete_output

CompleteOutputFn = Callable[..., Awaitable[OutputResult]]


async def generate_output(
    output_request: OutputRequest,
    chat_request: CoreChatRequest,
    complete_output_fn: CompleteOutputFn = complete_output,
    complete_chat_fn: CompleteChatFn | None = None,
    *,
    chunk_sink: Optional[ChunkSink] = None,
) -> OutputResult:
    """Wire output generation to the streaming layer."""
    kwargs: dict[str, Any] = {}
    if complete_chat_fn is not None:
        kwargs["complete_chat_fn"] = complete_chat_fn
    if chunk_sink is not None and not _should_defer_streaming(output_request):
        kwargs["chunk_sink"] = chunk_sink
    result = await complete_output_fn(output_request, chat_request, **kwargs)
    if str(result.content or "").strip():
        guarded = (
            apply_execution_consistency_guard(output_request, result.content)
            if _should_apply_execution_consistency_guard(output_request)
            else result.content
        )
        normalized = apply_tool_markup_guard(output_request, guarded)
        if normalized != guarded:
            return OutputResult(content=normalized, truncated=result.truncated, postcheck_applied=result.postcheck_applied)
        guarded = apply_no_evidence_fallback(output_request, normalized)
        if guarded == result.content:
            return result
        return OutputResult(content=guarded, truncated=result.truncated, postcheck_applied=result.postcheck_applied)
    return result


def _should_defer_streaming(output_request: OutputRequest) -> bool:
    ctx = getattr(output_request, "context", {}) or {}
    routing_frame = ctx.get("routing_frame") if isinstance(ctx, dict) else None
    claim = classify_claim(
        getattr(output_request, "user_text", ""),
        dialogue_act=_dialogue_act_from_output_request(output_request),
        routing_frame=routing_frame,
    )
    return claim.claim_type in {
        ClaimType.RUNTIME_TIME,
        ClaimType.RUNTIME_HARDWARE,
        ClaimType.FILE_CONTENT,
        ClaimType.CONTAINER_RUNTIME,
        ClaimType.SKILL_INVENTORY,
    }


def _should_apply_execution_consistency_guard(output_request: OutputRequest) -> bool:
    ctx = getattr(output_request, "context", {}) or {}
    if isinstance(ctx, dict) and isinstance(ctx.get("task_loop"), dict):
        return True
    plan = getattr(output_request, "thinking_plan", None)
    if plan is None:
        return True
    if bool(getattr(plan, "needs_task_loop", False)):
        return True
    steps = getattr(plan, "steps", None)
    if isinstance(steps, list):
        return any(str(getattr(step, "tool", "") or "").strip() for step in steps)
    return False


def _dialogue_act_from_output_request(output_request: OutputRequest) -> str:
    thinking_plan = getattr(output_request, "thinking_plan", None)
    hints = getattr(thinking_plan, "context_hints", None)
    if isinstance(hints, dict):
        return str(hints.get("dialogue_act") or "").strip()
    return ""
