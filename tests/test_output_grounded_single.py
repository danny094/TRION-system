import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.output import generate_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan

def test_generate_output_fails_closed_for_raw_grounded_tool_output():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Es ist 13:58:28 UTC.", "truncated": False, "postcheck_applied": False})()

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
                    ],
                    "task_loop": {
                        "artifacts": [
                            {
                                "artifact_type": "tool_result",
                                "tool": "time_now",
                                "result": '{"utc_iso":"2026-05-12T13:58:28Z"}',
                            }
                        ]
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


def test_generate_output_fails_closed_for_incomplete_task_loop():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Verifizierte Home-Metadaten.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Prüfe den Container trion-home und zeige mir nur verifizierte Home-Metadaten.",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "grounded_tool_results": [
                        {
                            "tool_name": "container_inspect",
                            "step_id": "tool_1",
                            "facts": {"home_scope": {"is_home": True, "home_root": "/home/trion"}},
                        }
                    ],
                    "task_loop": {
                        "completion_status": "needs_more_evidence",
                        "artifacts": [
                            {
                                "artifact_type": "tool_result",
                                "tool": "container_inspect",
                                "result": '{"home_scope":{"is_home":true,"home_root":"/home/trion"}}',
                            }
                        ],
                    },
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Prüfe den Container trion-home und zeige mir nur verifizierte Home-Metadaten.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."
