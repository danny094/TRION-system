from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Optional

from config import get_output_provider
from core.llm_provider_client import complete_chat, stream_chat
from core.models import CoreChatRequest
from core.output.contracts import OutputRequest, OutputResult
from core.output.messages import build_output_messages

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
    provider = _provider_from_request(chat_request)
    ollama_endpoint = _ollama_endpoint_from_request(chat_request)
    if output_request.stream and callable(chunk_sink):
        return await _stream_output(
            chat_request, messages, provider, ollama_endpoint, chunk_sink, stream_chat_fn
        )
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
    chat_request: CoreChatRequest,
    messages: list,
    provider: str,
    ollama_endpoint: str,
    chunk_sink: ChunkSink,
    stream_chat_fn: StreamChatFn,
) -> OutputResult:
    chunks: list[str] = []
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
        chunks.append(text)
        chunk_sink(text)
    return OutputResult(
        content="".join(chunks),
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
