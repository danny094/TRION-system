import asyncio
import importlib.util
import json
from pathlib import Path

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputResult
from core.pipeline import runner
from core.verifier.contracts import Verdict, VerifierResult


def _request(text: str = "Wie viel Uhr ist es?") -> CoreChatRequest:
    return CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content=text)],
        conversation_id="pipeline-events",
        source_adapter="pytest",
    )


def test_run_chat_emits_classifier_thinking_and_verifier_events():
    seen: list[dict] = []

    async def fake_output(output_request, chat_request):
        return OutputResult(content="Antwort")

    response = asyncio.run(
        runner.run_chat(
            _request(),
            output_fn=fake_output,
            pipeline_event_sink=seen.append,
        )
    )

    assert response.content == "Antwort"
    assert [event["type"] for event in seen] == [
        "classifier_result",
        "routing_trace",
        "thinking_plan",
        "verifier_result",
    ]
    assert seen[0]["category"] == "information"
    assert seen[1]["stage"] == "routing"
    assert seen[2]["step_count"] == 1
    assert "steps" not in seen[2]
    assert "plan_id" not in seen[2]
    assert seen[3]["verdict"] == "approved"


def test_pipeline_events_omit_classifier_and_verifier_free_text(monkeypatch):
    sentinels = [
        "PATTERN_SENTINEL", "CLASSIFIER_REASON_SENTINEL", "HINT_SENTINEL",
        "WARNING_SENTINEL", "VERIFIER_REASON_SENTINEL",
    ]
    classified = ClassifierResult(
        category=Category.INFORMATION, safety_level=SafetyLevel.SAFE,
        needs_orchestrator=False, confidence=0.8,
        route=Route.DIRECT_TO_THINKING, matched_pattern=sentinels[0],
        reason=sentinels[1],
    )
    verified = VerifierResult(
        verdict=Verdict.APPROVED, hint=sentinels[2],
        warnings=[sentinels[3]], reason=sentinels[4],
    )
    monkeypatch.setattr(runner, "classify", lambda *_a, **_k: classified)
    monkeypatch.setattr(runner, "verify_plan", lambda *_a, **_k: verified)
    seen = []

    async def fake_output(*_args, **_kwargs):
        return OutputResult(content="Antwort")

    asyncio.run(runner.run_chat(_request(), output_fn=fake_output, pipeline_event_sink=seen.append))
    classifier = next(event for event in seen if event["type"] == "classifier_result")
    verifier = next(event for event in seen if event["type"] == "verifier_result")
    assert classifier == {
        "type": "classifier_result", "needs_orchestrator": False,
        "is_long_document": False, "category": "information",
        "safety_level": "safe", "route": "direct_to_thinking",
    }
    assert verifier == {"type": "verifier_result", "verdict": "approved"}
    stream_path = Path(__file__).resolve().parents[1] / "adapters" / "admin-api" / "chat_stream.py"
    spec = importlib.util.spec_from_file_location("pipeline_event_public_stream", stream_path)
    stream = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(stream)
    ndjson = stream.event_to_ndjson("model", "conversation", classifier)
    ndjson += stream.event_to_ndjson("model", "conversation", verifier)
    assert all(value not in ndjson for value in sentinels)


def test_classifier_projection_omits_non_boolean_runtime_values():
    malformed = ClassifierResult(
        category=Category.INFORMATION, safety_level=SafetyLevel.SAFE,
        needs_orchestrator="BOOLEAN_SENTINEL", confidence=0.8,
        route=Route.DIRECT_TO_THINKING, is_long_document="BOOLEAN_SENTINEL",
    )

    event = runner.classifier_event(malformed)

    assert "needs_orchestrator" not in event
    assert "is_long_document" not in event
    assert "BOOLEAN_SENTINEL" not in json.dumps(event)
