from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Optional

from config import get_output_provider
from core.llm_provider_client import complete_chat, stream_chat
from core.models import CoreChatRequest
from core.output.contracts import OutputRequest, OutputResult
from core.output.execution_consistency_guard import (
    apply_execution_consistency_guard,
    execution_claim_pending_start,
)
from core.output.messages import build_output_messages
from core.output.tool_markup_guard import TOOL_MARKUP_MARKER, TOOL_MARKUP_REJECTION

CompleteChatFn = Callable[..., Awaitable[Dict[str, Any]]]
StreamChatFn = Callable[..., AsyncIterator[str]]
ChunkSink = Callable[[str], None]

_HOLLOW_PREFIXES = (
    "Natürlich! ", "Natürlich, ", "Gerne! ", "Gerne, ",
    "Of course! ", "Of course, ", "Sure! ", "Sure, ",
    "Certainly! ", "Certainly, ",
)


def _provider_from_request(request: CoreChatRequest) -> str:
    raw = request.raw_request if isinstance(request.raw_request, dict) else {}
    return str(raw.get("provider") or raw.get("selected_provider") or get_output_provider() or "ollama")


def _ollama_endpoint_from_request(request: CoreChatRequest) -> str:
    raw = request.raw_request if isinstance(request.raw_request, dict) else {}
    return str(raw.get("ollama_endpoint") or raw.get("endpoint") or "")


async def complete_output(
    output_request: OutputRequest,
    chat_request: CoreChatRequest,
    complete_chat_fn: CompleteChatFn = complete_chat,
    *,
    chunk_sink: Optional[ChunkSink] = None,
    stream_chat_fn: StreamChatFn = stream_chat,
) -> OutputResult:
    messages = build_output_messages(output_request, chat_request)
    if output_request.stream and callable(chunk_sink):
        return await _stream_output(
            output_request, chat_request, messages, chunk_sink, stream_chat_fn
        )
    provider = _provider_from_request(chat_request)
    ollama_endpoint = _ollama_endpoint_from_request(chat_request)
    result = await complete_chat_fn(
        provider=provider,
        model=chat_request.model,
        messages=messages,
        ollama_endpoint=ollama_endpoint,
    )
    content = str(result.get("content") or "")
    postcheck_applied, content = _postcheck_full(content)
    return OutputResult(content=content, truncated=False, postcheck_applied=postcheck_applied)


async def _stream_output(
    output_request: OutputRequest,
    chat_request: CoreChatRequest,
    messages: list,
    chunk_sink: ChunkSink,
    stream_chat_fn: StreamChatFn,
) -> OutputResult:
    provider = _provider_from_request(chat_request)
    ollama_endpoint = _ollama_endpoint_from_request(chat_request)
    chunks: list[str] = []
    pending = ""
    blocked = False
    emitted_length = 0
    postcheck_applied = False
    first_chunk_seen = False
    async for chunk in stream_chat_fn(
        provider=provider,
        model=chat_request.model,
        messages=messages,
        ollama_endpoint=ollama_endpoint,
    ):
        text = str(chunk or "")
        if not text:
            continue
        if not first_chunk_seen:
            first_chunk_seen = True
            postcheck_applied, text = _strip_hollow_prefix(text)
            if not text:
                continue
        candidate = pending + text
        if TOOL_MARKUP_MARKER in candidate:
            safe_prefix = candidate.split(TOOL_MARKUP_MARKER, 1)[0]
            if safe_prefix:
                prospective_content = "".join(chunks) + safe_prefix
                guarded_content = apply_execution_consistency_guard(output_request, prospective_content)
                if guarded_content != prospective_content:
                    return OutputResult(content=guarded_content, truncated=False, postcheck_applied=True)
                chunks.append(safe_prefix)
                pending_start = execution_claim_pending_start(output_request, prospective_content)
                emit_end = len(prospective_content) if pending_start is None else pending_start
                if emit_end > emitted_length:
                    chunk_sink(prospective_content[emitted_length:emit_end])
                    emitted_length = emit_end
            pending = ""
            blocked = True
            break
        pending_size = 0
        for size in range(min(len(candidate), len(TOOL_MARKUP_MARKER) - 1), 0, -1):
            if TOOL_MARKUP_MARKER.startswith(candidate[-size:]):
                pending_size = size
                break
        safe_text = candidate[:-pending_size] if pending_size else candidate
        pending = candidate[-pending_size:] if pending_size else ""
        if safe_text:
            prospective_content = "".join(chunks) + safe_text
            guarded_content = apply_execution_consistency_guard(output_request, prospective_content)
            if guarded_content != prospective_content:
                return OutputResult(
                    content=guarded_content,
                    truncated=False,
                    postcheck_applied=True,
                )
            chunks.append(safe_text)
            pending_start = execution_claim_pending_start(output_request, prospective_content)
            emit_end = len(prospective_content) if pending_start is None else pending_start
            if emit_end > emitted_length:
                chunk_sink(prospective_content[emitted_length:emit_end])
                emitted_length = emit_end
    if pending:
        blocked = True
    if blocked:
        return OutputResult(
            content=TOOL_MARKUP_REJECTION,
            truncated=False,
            postcheck_applied=True,
        )
    content = "".join(chunks)
    if emitted_length < len(content):
        chunk_sink(content[emitted_length:])
    return OutputResult(
        content=content,
        truncated=False,
        postcheck_applied=postcheck_applied,
    )


def _postcheck_full(content: str) -> tuple[bool, str]:
    stripped = content.strip()
    return _strip_hollow_prefix(stripped)


def _strip_hollow_prefix(text: str) -> tuple[bool, str]:
    leading = text.lstrip()
    for prefix in _HOLLOW_PREFIXES:
        if leading.startswith(prefix):
            return True, leading[len(prefix):].lstrip()
    return False, text
