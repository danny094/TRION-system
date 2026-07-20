import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.pipeline import runner
from core.thinking.contracts import (
    AdditionalEvidenceNeed, ResponseDerivation, ResponseProjection, RiskLevel, ThinkingPlan,
)
from core.verifier.contracts import Verdict, VerifierResult


class _Request:
    async def json(self):
        return {
            "model": "test-model", "conversation_id": "ENVELOPE_CONVERSATION",
            "messages": [{"role": "user", "content": "USER_TEXT_SENTINEL"}], "stream": True,
        }


def _load_chat_routes():
    root = Path(__file__).resolve().parents[1]
    admin = root / "adapters" / "admin-api"
    if str(admin) not in sys.path:
        sys.path.insert(0, str(admin))
    spec = importlib.util.spec_from_file_location("z8k_chat_routes", admin / "chat_routes.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


async def _lines(response):
    raw = b""
    async for chunk in response.body_iterator:
        raw += chunk if isinstance(chunk, bytes) else chunk.encode()
    return [json.loads(line) for line in raw.decode().splitlines() if line]


def test_real_route_uses_closed_classifier_thinking_and_verifier_projections(monkeypatch):
    classified = ClassifierResult(
        category=Category.INFORMATION, safety_level=SafetyLevel.SAFE,
        needs_orchestrator="BOOLEAN_SENTINEL", is_long_document="BOOLEAN_SENTINEL",
        confidence=0.5, route=Route.DIRECT_TO_THINKING,
        reason="CLASSIFIER_REASON_SENTINEL", matched_pattern="PATTERN_SENTINEL",
    )
    plan = ThinkingPlan(
        intent="INTENT_SENTINEL", steps=[], needs_task_loop=False, risk_level=RiskLevel.SAFE,
        response_projection=ResponseProjection("PROJECTION_SENTINEL"),
        response_derivation=ResponseDerivation("DERIVATION_SENTINEL"),
        additional_evidence_need=AdditionalEvidenceNeed("EVIDENCE_SENTINEL"),
    )
    verified = VerifierResult(
        verdict=Verdict.REJECTED, reason="VERIFIER_REASON_SENTINEL",
        hint="HINT_SENTINEL", warnings=["WARNING_SENTINEL"],
    )
    preprocessed = SimpleNamespace(
        raw_user_text="USER_TEXT_SENTINEL", classifier_result=classified,
        document_context=None, planning_user_text="USER_TEXT_SENTINEL",
    )
    monkeypatch.setattr(runner, "preprocess_request", lambda *_a, **_k: preprocessed)
    monkeypatch.setattr(runner, "build_thinking_stage", lambda *_a, **_k: SimpleNamespace(plan=plan, thinking_context={}))
    monkeypatch.setattr(runner, "verify_plan", lambda *_a, **_k: verified)

    events = asyncio.run(_lines(asyncio.run(_load_chat_routes().chat(_Request()))))
    classifier = next(event for event in events if event["type"] == "classifier_result")
    thinking = next(event for event in events if event["type"] == "thinking_plan")
    verifier = next(event for event in events if event["type"] == "verifier_result")
    serialized = json.dumps(events)

    assert classifier == {
        "type": "classifier_result", "category": "information", "safety_level": "safe",
        "route": "direct_to_thinking", "model": "test-model",
        "conversation_id": "ENVELOPE_CONVERSATION", "created_at": classifier["created_at"], "done": False,
    }
    assert thinking["step_count"] == 0 and thinking["risk_level"] == "safe"
    assert verifier["verdict"] == "rejected"
    assert all(token not in serialized for token in (
        "BOOLEAN_SENTINEL", "CLASSIFIER_REASON_SENTINEL", "PATTERN_SENTINEL",
        "INTENT_SENTINEL", "PROJECTION_SENTINEL", "DERIVATION_SENTINEL",
        "VERIFIER_REASON_SENTINEL", "HINT_SENTINEL", "WARNING_SENTINEL",
    ))
