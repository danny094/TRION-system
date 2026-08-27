import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.output import generate_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan

def test_generate_output_fails_closed_for_raw_completed_container_result():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Der Container ist als verifiziertes Home markiert.", "truncated": False, "postcheck_applied": False})()

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
                        "completion_status": "complete",
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


def test_generate_output_keeps_llm_path_for_multiple_grounded_results():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Zusammenfassung.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Fasse beide Ergebnisse zusammen.",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "grounded_tool_results": [
                        {"tool_name": "time_now", "step_id": "tool_1", "facts": {"time": "13:58:28"}},
                        {"tool_name": "home_read", "step_id": "tool_2", "facts": {"value": "Systemstatus: OK"}},
                    ]
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Fasse beide Ergebnisse zusammen.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "Zusammenfassung."


def test_generate_output_does_not_use_multi_tool_direct_fallback_when_llm_returns_empty():
    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Prüfe Uhrzeit und Container.",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "grounded_tool_results": [
                        {"tool_name": "time_now", "step_id": "tool_1", "facts": {"time": "13:58:28", "timezone": "UTC"}},
                        {
                            "tool_name": "container_list",
                            "step_id": "tool_2",
                            "facts": {"containers": [{"name": "trion-webui", "status": "running"}]},
                        },
                    ],
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Prüfe Uhrzeit und Container.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == ""
