import asyncio

from core.llm.chat import complete_chat
from core.llm.prompts import complete_prompt, stream_prompt
from core.llm.reasoning_sanitizer import StreamingReasoningSanitizer, sanitize_reasoning_text
from core.llm.streaming import stream_chat_events


def test_sanitize_reasoning_text_removes_inline_think_block():
    text = "<think>internal</think>\n\nAntwort."
    assert sanitize_reasoning_text(text) == "Antwort."


def test_streaming_reasoning_sanitizer_removes_split_think_blocks():
    sanitizer = StreamingReasoningSanitizer()
    chunks = []
    chunks.extend(sanitizer.feed("<thi"))
    chunks.extend(sanitizer.feed("nk>secret"))
    chunks.extend(sanitizer.feed("</thi"))
    chunks.extend(sanitizer.feed("nk>Antwort"))
    chunks.extend(sanitizer.flush())
    assert "".join(chunks) == "Antwort"


def test_complete_chat_sanitizes_provider_content(monkeypatch):
    async def fake_complete_chat(**kwargs):
        return {"content": "<think>x</think> Sichtbar.", "tool_calls": []}

    monkeypatch.setattr(
        "core.llm.chat.provider_runtime_module",
        lambda _provider: type("Impl", (), {"complete_chat": staticmethod(fake_complete_chat)})(),
    )
    result = asyncio.run(complete_chat(provider="minimax", model="m", messages=[{"role": "user", "content": "hi"}]))
    assert result["content"] == "Sichtbar."


def test_stream_chat_events_filters_thinking_and_inline_think(monkeypatch):
    async def fake_stream_chat_events(**kwargs):
        yield {"type": "thinking", "chunk": "internal"}
        yield {"type": "content", "chunk": "<think>secret</think>Hallo"}

    monkeypatch.setattr(
        "core.llm.streaming.provider_runtime_module",
        lambda _provider: type("Impl", (), {"stream_chat_events": staticmethod(fake_stream_chat_events)})(),
    )

    async def _collect():
        events = []
        async for event in stream_chat_events(provider="minimax", model="m", messages=[{"role": "user", "content": "hi"}]):
            events.append(event)
        return events

    events = asyncio.run(_collect())
    assert events == [{"type": "content", "chunk": "Hallo"}]


def test_complete_prompt_sanitizes_reasoning_tags(monkeypatch):
    async def fake_complete_prompt(**kwargs):
        return "<think>secret</think>Final."

    monkeypatch.setattr(
        "core.llm.prompts.provider_runtime_module",
        lambda _provider: type("Impl", (), {"complete_prompt": staticmethod(fake_complete_prompt)})(),
    )
    result = asyncio.run(complete_prompt(provider="minimax", model="m", prompt="hi"))
    assert result == "Final."


def test_stream_prompt_sanitizes_split_reasoning_tags(monkeypatch):
    async def fake_stream_prompt(**kwargs):
        for chunk in ("<thi", "nk>x</thi", "nk>Done"):
            yield chunk

    monkeypatch.setattr(
        "core.llm.prompts.provider_runtime_module",
        lambda _provider: type("Impl", (), {"stream_prompt": staticmethod(fake_stream_prompt)})(),
    )

    async def _collect():
        out = []
        async for chunk in stream_prompt(provider="minimax", model="m", prompt="hi"):
            out.append(chunk)
        return "".join(out)

    result = asyncio.run(_collect())
    assert result == "Done"
