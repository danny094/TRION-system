"""Late output guards must surface corrected text as final_content."""

import asyncio
import json
import sys
from pathlib import Path

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest, OutputResult
from core.output.output import generate_output
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


def test_late_tool_markup_guard_emits_final_content_replace_event():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    from chat_stream import response_to_ndjson

    streamed_chunks: list[str] = []

    async def fake_complete_output(output_request, chat_request, **kwargs):
        sink = kwargs.get("chunk_sink")
        assert callable(sink), "streaming chunk_sink must be available before the late guard"
        sink("Vorläufige ")
        sink("Antwort.")
        return OutputResult(content="[TOOL_CALL] workspace_get {}")

    result = asyncio.run(
        generate_output(
            _output_request(),
            _chat_request(),
            complete_output_fn=fake_complete_output,
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

    assert [event["type"] for event in events] == ["content", "content", "final_content", "done"]
    assert streamed_events[0]["content"] == "Vorläufige "
    assert "unzulässiges Tool-Markup" in events[2]["content"]
    assert "[TOOL_CALL]" not in events[2]["content"]
    assert events[-1]["done_reason"] == "stop"
