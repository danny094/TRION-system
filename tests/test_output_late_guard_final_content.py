"""Late output guards must surface corrected text as final_content."""

import asyncio
import json
import sys
from pathlib import Path

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.output import generate_output
from core.output.stream import complete_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState
from core.thinking.contracts import RiskLevel, ThinkingPlan


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _output_request() -> OutputRequest:
    return OutputRequest(
        user_text="Sag mir kurz den Status.",
        thinking_plan=ThinkingPlan(
            intent="answer_user",
            steps=[],
            needs_task_loop=False,
            risk_level=RiskLevel.SAFE,
        ),
        output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
        context={},
        stream=True,
    )


def _chat_request() -> CoreChatRequest:
    return CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="Sag mir kurz den Status.")],
        conversation_id="late-guard",
        source_adapter="pytest",
    )


def test_complete_output_blocks_full_tool_marker_before_sink():
    streamed_chunks: list[str] = []

    async def fake_stream(**_kwargs):
        yield "[TOOL_CALL] workspace_get {}"

    result = asyncio.run(
        complete_output(
            _output_request(),
            _chat_request(),
            chunk_sink=streamed_chunks.append,
            stream_chat_fn=fake_stream,
        )
    )

    assert streamed_chunks == []
    assert "unzulässiges Tool-Markup" in result.content
    assert "[TOOL_CALL]" not in result.content


def test_complete_output_blocks_fragmented_tool_marker_before_sink():
    streamed_chunks: list[str] = []

    async def fake_stream(**_kwargs):
        for chunk in ["[TOOL_", "CALL] workspace_get {}"]:
            yield chunk

    result = asyncio.run(
        complete_output(
            _output_request(),
            _chat_request(),
            chunk_sink=streamed_chunks.append,
            stream_chat_fn=fake_stream,
        )
    )

    assert streamed_chunks == []
    assert "unzulässiges Tool-Markup" in result.content
    assert "[TOOL_CALL]" not in result.content


def test_stream_guard_emits_final_content_replace_event_after_safe_prefix():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    from chat_stream import response_to_ndjson

    streamed_chunks: list[str] = []

    async def fake_stream(**_kwargs):
        for chunk in ["Vorläufige Antwort. ", "[TOOL_", "CALL] workspace_get {}"]:
            yield chunk

    async def guarded_complete_output(output_request, chat_request, **kwargs):
        return await complete_output(
            output_request,
            chat_request,
            chunk_sink=kwargs.get("chunk_sink"),
            stream_chat_fn=fake_stream,
        )

    result = asyncio.run(
        generate_output(
            _output_request(),
            _chat_request(),
            complete_output_fn=guarded_complete_output,
            chunk_sink=streamed_chunks.append,
        )
    )

    class _Resp:
        model = "test-model"
        conversation_id = "late-guard"
        content = result.content
        done_reason = "stop"

    streamed_events = [{"type": "content", "content": chunk} for chunk in streamed_chunks]
    tail_events = [
        json.loads(line)
        for line in response_to_ndjson(_Resp(), content_already_streamed=bool(streamed_chunks))
    ]
    events = streamed_events + tail_events

    assert [event["type"] for event in events] == ["content", "final_content", "done"]
    assert events[0]["content"] == "Vorläufige Antwort. "
    assert "unzulässiges Tool-Markup" in events[1]["content"]
    assert "[TOOL_CALL]" not in events[1]["content"]
    assert events[-1]["done_reason"] == "stop"
