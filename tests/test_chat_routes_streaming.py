"""Verify the admin-api chat route streams content chunks via chunk_sink."""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

from core.models import CoreChatResponse
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


ROOT = Path(__file__).resolve().parents[1]
ADMIN_API_DIR = ROOT / "adapters" / "admin-api"


def _load_chat_routes():
    if str(ADMIN_API_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_API_DIR))
    spec = importlib.util.spec_from_file_location(
        "trion_chat_routes_for_streaming_test",
        ADMIN_API_DIR / "chat_routes.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Request:
    async def json(self):
        return {
            "model": "test-model",
            "conversation_id": "conv-stream",
            "messages": [{"role": "user", "content": "Stream please"}],
            "stream": True,
        }


async def _read_ndjson_lines(response):
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode("utf-8"))
    payload = "".join(chunks)
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


def test_chat_route_emits_streamed_chunks_then_done(monkeypatch):
    chat_routes = _load_chat_routes()

    async def fake_run_chat(core_request, **kwargs):
        sink = kwargs.get("chunk_sink")
        assert callable(sink), "chunk_sink must be passed to run_chat"
        for chunk in ["Hallo ", "Welt", "!"]:
            sink(chunk)
        return CoreChatResponse(
            model="test-model",
            content="Hallo Welt!",
            conversation_id="conv-stream",
            done=True,
            done_reason="stop",
        )

    monkeypatch.setattr("core.pipeline.runner.run_chat", fake_run_chat)
    response = asyncio.run(chat_routes.chat(_Request()))
    lines = asyncio.run(_read_ndjson_lines(response))

    types = [event["type"] for event in lines]
    assert types == ["content", "content", "content", "final_content", "done"]
    assert [event["content"] for event in lines if event["type"] == "content"] == ["Hallo ", "Welt", "!"]
    assert [event["content"] for event in lines if event["type"] == "final_content"] == ["Hallo Welt!"]
    assert lines[-1]["done_reason"] == "stop"


def test_chat_route_emits_single_content_event_when_no_streaming_chunks(monkeypatch):
    """Wenn run_chat keinen Chunk emittiert (z.B. fehlerfreier Fallback ohne Streaming),
    muss response_to_ndjson trotzdem genau ein content event vor done senden."""
    chat_routes = _load_chat_routes()

    async def fake_run_chat(core_request, **kwargs):
        return CoreChatResponse(
            model="test-model",
            content="Komplette Antwort am Stück.",
            conversation_id="conv-stream",
            done=True,
            done_reason="stop",
        )

    monkeypatch.setattr("core.pipeline.runner.run_chat", fake_run_chat)
    response = asyncio.run(chat_routes.chat(_Request()))
    lines = asyncio.run(_read_ndjson_lines(response))

    types = [event["type"] for event in lines]
    assert types == ["content", "done"]
    assert lines[0]["content"] == "Komplette Antwort am Stück."


def test_chat_route_forwards_pipeline_events_before_content(monkeypatch):
    chat_routes = _load_chat_routes()

    async def fake_run_chat(core_request, **kwargs):
        event_sink = kwargs.get("pipeline_event_sink")
        assert callable(event_sink), "pipeline_event_sink must be passed to run_chat"
        event_sink({"type": "classifier_result", "category": "information", "route": "direct_to_thinking"})
        event_sink({"type": "thinking_plan", "step_count": 0, "needs_task_loop": False})
        event_sink({"type": "verifier_result", "verdict": "approved"})
        return CoreChatResponse(
            model="test-model",
            content="Antwort mit sichtbarem Thinking.",
            conversation_id="conv-stream",
            done=True,
            done_reason="stop",
        )

    monkeypatch.setattr("core.pipeline.runner.run_chat", fake_run_chat)
    response = asyncio.run(chat_routes.chat(_Request()))
    lines = asyncio.run(_read_ndjson_lines(response))

    assert [event["type"] for event in lines] == [
        "classifier_result",
        "thinking_plan",
        "verifier_result",
        "content",
        "done",
    ]
    assert lines[0]["category"] == "information"
    assert lines[1]["step_count"] == 0
    assert lines[2]["verdict"] == "approved"


def test_chat_route_sanitizes_unhandled_pipeline_exception(monkeypatch):
    chat_routes = _load_chat_routes()
    sentinels = (
        "SECRET_SENTINEL", "PRIVATE_TOOL_SENTINEL", "TARGET_SENTINEL",
        "SCOPE_SENTINEL", "ARGUMENT_SENTINEL", "OUTPUT_SENTINEL",
        "PROVIDER_RESPONSE_SENTINEL", "USER_TEXT_SENTINEL",
        "PAYLOAD_CONVERSATION_SENTINEL",
    )

    async def fake_run_chat(core_request, **kwargs):
        raise RuntimeError(" ".join(sentinels))

    monkeypatch.setattr("core.pipeline.runner.run_chat", fake_run_chat)
    response = asyncio.run(chat_routes.chat(_Request()))
    chunks = []
    async def _read_chunks():
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode("utf-8"))
    asyncio.run(_read_chunks())
    raw_lines = [line for line in "".join(chunks).splitlines() if line.strip()]
    lines = [json.loads(line) for line in raw_lines]

    assert [event["type"] for event in lines] == ["error", "done"]
    error = lines[0]
    assert error["content"] == "Ein interner Fehler ist aufgetreten."
    assert error["error_code"] == "internal_error"
    assert error["conversation_id"] == "conv-stream"
    assert raw_lines[0].count('"conversation_id"') == 1
    serialized = json.dumps(lines, ensure_ascii=False)
    assert all(sentinel not in serialized for sentinel in sentinels)


def test_chat_route_sanitizes_plan_contract_rejection(monkeypatch):
    chat_routes = _load_chat_routes()
    from core.pipeline import runner

    plan = ThinkingPlan(
        intent="run", steps=[PlanStep(
            step_id="STEP_SENTINEL", title="Step", goal="TARGET_SENTINEL",
            tool="PRIVATE_TOOL_SENTINEL",
        )], needs_task_loop=True, risk_level=RiskLevel.SAFE,
        plan_id="PLAN_SENTINEL",
    )
    monkeypatch.setattr(runner, "build_plan", lambda *_a, **_k: plan)
    monkeypatch.setattr(chat_routes, "get_available_tools", lambda: [])
    monkeypatch.setattr(chat_routes, "build_context_sources", lambda: {})

    response = asyncio.run(chat_routes.chat(_Request()))
    lines = asyncio.run(_read_ndjson_lines(response))
    rejected = next(event for event in lines if event["type"] == "rejected")
    assert rejected["content"] == "Die Anfrage konnte nicht freigegeben werden."
    assert rejected["error_code"] == "request_rejected"
    assert lines[-1]["done_reason"] == "rejected"
    serialized = json.dumps(lines)
    assert "SENTINEL" not in serialized
