import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.output import generate_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan

def test_generate_output_fails_closed_for_carryover_grounding_state():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Freier Text.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie viel Uhr ist es?",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "grounding_state": {
                        "updated_at": 100.0,
                        "age_s": 5.0,
                        "age_turns": 0,
                        "grounded_results": [
                            {"tool_name": "time_now", "step_id": "tool_1", "facts": {"utc_iso": "2026-05-12T13:58:28Z"}}
                        ],
                    }
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

    assert seen["called"] is True
    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."


def test_generate_output_does_not_reuse_unrelated_grounding_state_for_new_prompt():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Antwort über eine Datei.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Lies die Datei /trion-home/status.txt. Nutze dafür nur ein Datei-Lese-Tool.",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "grounding_state": {
                        "updated_at": 100.0,
                        "age_s": 5.0,
                        "age_turns": 0,
                        "grounded_results": [
                            {"tool_name": "time_now", "step_id": "tool_1", "facts": {"utc_iso": "2026-05-12T13:58:28Z"}}
                        ],
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Lies die Datei /trion-home/status.txt.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert "Ergebnis von `time_now`:" not in result.content


def test_generate_output_keeps_llm_path_for_time_followup_with_grounding_state():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "In einer Stunde ist es 04:26:51 UTC.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Und in einer Stunde?",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "grounding_state": {
                        "updated_at": 100.0,
                        "age_s": 5.0,
                        "age_turns": 0,
                        "grounded_results": [
                            {"tool_name": "time_now", "step_id": "tool_1", "facts": {"utc_iso": "2026-05-12T03:26:51Z"}}
                        ],
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Und in einer Stunde?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "In einer Stunde ist es 04:26:51 UTC."
