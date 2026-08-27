"""Streaming-path tests for core/output/stream.py + adapter chat_stream helper."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest, OutputResult
from core.output.output import generate_output
from core.output.stream import complete_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState
from core.thinking.contracts import RiskLevel, ThinkingPlan


def _request(stream: bool) -> OutputRequest:
    plan = ThinkingPlan(
        intent="answer_user",
        steps=[],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
    )
    return OutputRequest(
        user_text="Hi",
        thinking_plan=plan,
        output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
        stream=stream,
    )


def _chat_request() -> CoreChatRequest:
    return CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="Hi")],
        conversation_id="stream-test",
        source_adapter="pytest",
    )


async def _async_chunks(chunks: list[str]):
    for chunk in chunks:
        yield chunk


def test_complete_output_streams_chunks_through_sink_when_stream_true():
    sink_calls: list[str] = []

    def fake_stream(**_kwargs):
        return _async_chunks(["Hello", " ", "World"])

    async def fail_complete_chat(**_kwargs):
        raise AssertionError("complete_chat must not be called when streaming")

    result: OutputResult = asyncio.run(
        complete_output(
            _request(stream=True),
            _chat_request(),
            complete_chat_fn=fail_complete_chat,
            chunk_sink=sink_calls.append,
            stream_chat_fn=fake_stream,
        )
    )
    assert sink_calls == ["Hello", " ", "World"]
    assert result.content == "Hello World"
    assert result.postcheck_applied is False


def test_complete_output_strips_hollow_prefix_on_first_chunk_before_sink():
    sink_calls: list[str] = []

    def fake_stream(**_kwargs):
        return _async_chunks(["Natürlich! Hier kommt", " die Antwort."])

    async def fail_complete_chat(**_kwargs):
        raise AssertionError("complete_chat must not be called when streaming")

    result = asyncio.run(
        complete_output(
            _request(stream=True),
            _chat_request(),
            complete_chat_fn=fail_complete_chat,
            chunk_sink=sink_calls.append,
            stream_chat_fn=fake_stream,
        )
    )
    assert sink_calls == ["Hier kommt", " die Antwort."]
    assert result.content == "Hier kommt die Antwort."
    assert result.postcheck_applied is True


def test_complete_output_without_sink_falls_back_to_non_streaming():
    sink_should_not_be_called: list[str] = []

    async def fake_complete_chat(**_kwargs):
        return {"content": "Antwort am Stück."}

    def fail_stream(**_kwargs):
        raise AssertionError("stream_chat must not be called without sink")

    result = asyncio.run(
        complete_output(
            _request(stream=True),
            _chat_request(),
            complete_chat_fn=fake_complete_chat,
            chunk_sink=None,
            stream_chat_fn=fail_stream,
        )
    )
    assert sink_should_not_be_called == []
    assert result.content == "Antwort am Stück."


def test_complete_output_skips_streaming_when_request_stream_false():
    """stream=False darf nie streamen, auch wenn ein chunk_sink durchgereicht wird."""

    async def fake_complete_chat(**_kwargs):
        return {"content": "non-stream"}

    def fail_stream(**_kwargs):
        raise AssertionError("stream_chat must not be called when stream=False")

    result = asyncio.run(
        complete_output(
            _request(stream=False),
            _chat_request(),
            complete_chat_fn=fake_complete_chat,
            chunk_sink=lambda _: None,
            stream_chat_fn=fail_stream,
        )
    )
    assert result.content == "non-stream"


def test_response_to_ndjson_skips_content_event_when_already_streamed():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters" / "admin-api"))
    from chat_stream import response_to_ndjson

    class _Resp:
        model = "m"
        conversation_id = "c"
        content = "this should not be re-emitted"
        done_reason = "stop"

    lines_streamed = list(response_to_ndjson(_Resp(), content_already_streamed=True))
    payloads_streamed = [json.loads(line) for line in lines_streamed]
    assert [event["type"] for event in payloads_streamed] == ["final_content", "done"]
    assert payloads_streamed[0]["content"] == "this should not be re-emitted"

    lines_non_streamed = list(response_to_ndjson(_Resp(), content_already_streamed=False))
    payloads_non_streamed = [json.loads(line) for line in lines_non_streamed]
    assert [event["type"] for event in payloads_non_streamed] == ["content", "done"]
    assert payloads_non_streamed[0]["content"] == "this should not be re-emitted"


def test_generate_output_blocks_unverified_stream_before_sink():
    seen = {"complete_called": False}
    chunks = []

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["complete_called"] = True
        kwargs["chunk_sink"]("leaked runtime claim")
        return OutputResult(content="Unbekannt. Es liegen keine verifizierten Tool-Fakten vor.")

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie viel RAM oder VRAM hast du gerade?",
                thinking_plan=_request(stream=True).thinking_plan,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={},
                stream=True,
            ),
            _chat_request(),
            complete_output_fn=fake_complete_output,
            chunk_sink=chunks.append,
        )
    )

    assert seen["complete_called"] is False
    assert chunks == []
    assert "Unbekannt" in result.content
