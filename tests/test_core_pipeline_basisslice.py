import asyncio

from core.output.contracts import OutputResult
from core.pipeline import runner
from core.verifier.contracts import Verdict, VerifierResult
from tests._core_pipeline_request_helpers import core_pipeline_request


def test_core_vertical_slice_returns_response_with_injected_output():
    seen = {}

    async def fake_output(output_request, chat_request):
        seen["user_text"] = output_request.user_text
        seen["plan_intent"] = output_request.thinking_plan.intent
        seen["stream"] = output_request.stream
        seen["model"] = chat_request.model
        return OutputResult(content="fake answer")

    response = asyncio.run(runner.run_chat(core_pipeline_request("Hallo TRION"), output_fn=fake_output))

    assert response.model == "test-model"
    assert response.content == "fake answer"
    assert response.conversation_id == "p0-test"
    assert response.done is True
    assert response.done_reason == "stop"
    assert response.validation_passed is True
    assert response.memory_used is False
    assert response.is_partial is False
    assert response.classifier_result["category"] == "information"
    assert response.classifier_result["route"] == "direct_to_thinking"
    assert seen == {
        "user_text": "Hallo TRION",
        "plan_intent": "answer_user",
        "stream": False,
        "model": "test-model",
    }
    assert response.classifier_result["is_long_document"] is False
    assert "estimated_input_tokens" not in response.classifier_result


def test_core_rejected_path_returns_clean_response_without_output(monkeypatch):
    async def fail_output(*args, **kwargs):
        raise AssertionError("output must not be called for rejected plans")

    def reject_plan(plan, user_text="", **kwargs):
        return VerifierResult(
            verdict=Verdict.REJECTED,
            hint="Bitte genauer formulieren.",
            reason="plan needs clarification",
        )

    monkeypatch.setattr(runner, "verify_plan", reject_plan)

    response = asyncio.run(runner.run_chat(core_pipeline_request(), output_fn=fail_output))

    assert response.content == "Die Anfrage konnte nicht freigegeben werden."
    assert response.done is True
    assert response.done_reason == "rejected"
    assert response.validation_passed is False
    assert response.classifier_result["route"] == "direct_to_thinking"


def test_core_hard_block_path_returns_clean_response_without_output(monkeypatch):
    async def fail_output(*args, **kwargs):
        raise AssertionError("output must not be called for hard-blocked plans")

    def hard_block_plan(plan, user_text="", **kwargs):
        return VerifierResult(
            verdict=Verdict.HARD_BLOCK,
            reason="blocked by deterministic safety policy",
        )

    monkeypatch.setattr(runner, "verify_plan", hard_block_plan)

    response = asyncio.run(runner.run_chat(core_pipeline_request(), output_fn=fail_output))

    assert response.content == "Die Anfrage konnte nicht freigegeben werden."
    assert response.done is True
    assert response.done_reason == "blocked"
    assert response.validation_passed is False
    assert response.classifier_result["safety_level"] == "safe"
