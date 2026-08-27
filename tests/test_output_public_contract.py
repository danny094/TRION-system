import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest, OutputResult
from core.output.messages import build_output_messages
from core.output.output import generate_output
from core.output.renderable_evidence import build_renderable_evidence
from core.pipeline.output_evidence_contracts import (
    OutputEvidenceHandoff,
    OutputEvidenceItem,
    OutputEvidenceState,
)
from core.thinking.contracts import RiskLevel, ThinkingPlan


def _plan() -> ThinkingPlan:
    return ThinkingPlan("answer", [], False, RiskLevel.SAFE)


def _chat_request() -> CoreChatRequest:
    return CoreChatRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="Wie ist der Status?")],
        conversation_id="public-contract",
    )


def _verified_request(*, context=None, renderable=True) -> OutputRequest:
    handoff = OutputEvidenceHandoff(
        OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE,
        (OutputEvidenceItem({"status": "VERIFIED_SENTINEL"}),),
    )
    return OutputRequest(
        user_text="Wie viel VRAM ist gerade verfuegbar?",
        thinking_plan=_plan(),
        output_evidence=handoff,
        renderable_evidence=build_renderable_evidence(handoff) if renderable else (),
        context=context or {},
        stream=True,
    )


def test_verified_evidence_reaches_provider_and_prompt() -> None:
    seen = {"called": False, "prompt": ""}

    async def fake_complete_output(output_request, chat_request, **_kwargs):
        seen["called"] = True
        seen["prompt"] = build_output_messages(output_request, chat_request)[0]["content"]
        return OutputResult(content="Verifizierter Status.")

    result = asyncio.run(
        generate_output(
            _verified_request(),
            _chat_request(),
            complete_output_fn=fake_complete_output,
            chunk_sink=lambda _chunk: None,
        )
    )

    assert seen["called"] is True
    assert "VERIFIED_SENTINEL" in seen["prompt"]
    assert result.content == "Verifizierter Status."


def test_verified_state_without_renderable_evidence_fails_before_provider() -> None:
    seen = {"called": False}

    async def fake_complete_output(*_args, **_kwargs):
        seen["called"] = True
        return OutputResult(content="must not run")

    result = asyncio.run(
        generate_output(
            _verified_request(renderable=False),
            _chat_request(),
            complete_output_fn=fake_complete_output,
            chunk_sink=lambda _chunk: None,
        )
    )

    assert seen["called"] is False
    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."


def test_prompt_ignores_raw_context_projection_sources() -> None:
    request = _verified_request(
        context={
            "task_loop": {"artifacts": [{"result": "RAW_TASK_SENTINEL"}]},
            "grounded_tool_results": [{"facts": {"value": "RAW_TOOL_SENTINEL"}}],
            "orchestrator": {
                "context": {
                    "memory": {"items": [{"content": "RAW_MEMORY_SENTINEL"}]},
                    "home_context": {"verified": True, "home_root": "RAW_HOME_SENTINEL"},
                    "self_context": {"identity": {"name": "RAW_SELF_SENTINEL"}},
                }
            },
        }
    )

    prompt = build_output_messages(request, _chat_request())[0]["content"]

    assert "VERIFIED_SENTINEL" in prompt
    for sentinel in (
        "RAW_TASK_SENTINEL",
        "RAW_TOOL_SENTINEL",
        "RAW_MEMORY_SENTINEL",
        "RAW_HOME_SENTINEL",
        "RAW_SELF_SENTINEL",
    ):
        assert sentinel not in prompt
