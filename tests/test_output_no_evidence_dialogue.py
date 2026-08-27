import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.output import generate_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan

def test_generate_output_keeps_conceptual_analysis_without_runtime_evidence(monkeypatch):
    monkeypatch.setenv("GROUNDING_NO_EVIDENCE_FALLBACK_MODE", "explicit_unknown")

    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "Ich würde das als typisierte Evidence-Firewall im Core bauen.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie würdest du einen Anti-Halluzinationsguard architektonisch aufbauen?",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={},
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Wie würdest du einen Anti-Halluzinationsguard architektonisch aufbauen?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == "Ich würde das als typisierte Evidence-Firewall im Core bauen."


def test_generate_output_keeps_reflective_container_question_when_dialogue_act_is_smalltalk(monkeypatch):
    monkeypatch.setenv("GROUNDING_NO_EVIDENCE_FALLBACK_MODE", "explicit_unknown")

    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "Als Design finde ich einen verifizierten Home-Scope sinnvoll, weil er Grenzen und Capabilities klar macht.", "truncated": False, "postcheck_applied": False})()

    thinking_plan = type(
        "Plan",
        (),
        {"context_hints": {"dialogue_act": "smalltalk"}},
    )()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie ist es für dich, dass wir dir einen Container als Zuhause erstellt haben?",
                thinking_plan=thinking_plan,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={},
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Wie ist es für dich, dass wir dir einen Container als Zuhause erstellt haben?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == "Als Design finde ich einen verifizierten Home-Scope sinnvoll, weil er Grenzen und Capabilities klar macht."


def test_generate_output_keeps_empty_result_when_llm_returns_empty_and_no_guard_applies():
    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie viel Uhr ist es?",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "grounded_tool_results": [
                        {
                            "tool_name": "time_now",
                            "step_id": "tool_1",
                            "facts": {"utc_iso": "2026-05-12T13:58:28Z"},
                        }
                    ]
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Wie viel Uhr ist es?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == ""
