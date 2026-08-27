from typing import Any, Awaitable, Callable, Optional

from core.models import CoreChatRequest
from core.output.contracts import OutputRequest, OutputResult
from core.output.execution_consistency_guard import apply_execution_consistency_guard
from core.output.no_evidence_fallback import apply_no_evidence_fallback
from core.output.stream import ChunkSink, CompleteChatFn, complete_output
from core.output.tool_markup_guard import apply_tool_markup_guard

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
    if callable(chunk_sink):
        guarded_preflight = apply_no_evidence_fallback(output_request, "", preflight=True)
        if guarded_preflight is not None:
            return OutputResult(content=guarded_preflight)
    kwargs: dict[str, Any] = {}
    if complete_chat_fn is not None:
        kwargs["complete_chat_fn"] = complete_chat_fn
    if chunk_sink is not None:
        kwargs["chunk_sink"] = chunk_sink
    result = await complete_output_fn(output_request, chat_request, **kwargs)
    if str(result.content or "").strip():
        stream_guarded = output_request.stream and callable(chunk_sink)
        guarded = result.content if stream_guarded else apply_execution_consistency_guard(output_request, result.content)
        normalized = apply_tool_markup_guard(output_request, guarded)
        if normalized != guarded:
            return OutputResult(content=normalized, truncated=result.truncated, postcheck_applied=result.postcheck_applied)
        guarded = apply_no_evidence_fallback(output_request, normalized)
        assert guarded is not None
        if guarded == result.content:
            return result
        return OutputResult(content=guarded, truncated=result.truncated, postcheck_applied=result.postcheck_applied)
    return result
def _dialogue_act_from_output_request(output_request: OutputRequest) -> str:
    thinking_plan = getattr(output_request, "thinking_plan", None)
    hints = getattr(thinking_plan, "context_hints", None)
    if isinstance(hints, dict):
        return str(hints.get("dialogue_act") or "").strip()
    return ""
