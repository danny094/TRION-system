import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.output import generate_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan

def test_generate_output_fails_closed_for_home_context_capability_claim():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type(
            "Result",
            (),
            {
                "content": "Ich kann den Container inspizieren und seinen Laufzeitstatus lesen, aber aktuell weder Dateien schreiben noch Befehle darin ausführen.",
                "truncated": False,
                "postcheck_applied": False,
            },
        )()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Was kannst du in dem Container alles machen?",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "orchestrator": {
                        "context": {
                            "home_context": {
                                "verified": True,
                                "container_name": "trion-home",
                                "available_capability_classes": ["container_inspect", "container_inventory"],
                                "missing_capability_classes": ["file_write", "local_exec"],
                            }
                        }
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Was kannst du in dem Container alles machen?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."


def test_generate_output_fails_closed_for_self_context_capability_claim():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type(
            "Result",
            (),
            {
                "content": "Ich kann aktuell kuratierten Memory-Kontext lesen, Container inspizieren und Logs lesen. Globales Langzeit-Schreiben ist in diesem Kontext deaktiviert.",
                "truncated": False,
                "postcheck_applied": False,
            },
        )()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Was kannst du gerade insgesamt im System tun?",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "orchestrator": {
                        "context": {
                            "self_context": {
                                "identity": {
                                    "name": "TRION",
                                    "status": "verified",
                                },
                                "capabilities": [
                                    {"name": "memory_read", "status": "verified", "source": "conversation_policy"},
                                    {"name": "container_inspect", "status": "verified", "source": "home_context"},
                                ],
                                "memory_visibility": {
                                    "memory_mode": "conversation_only",
                                    "allow_long_term_write": False,
                                },
                            }
                        }
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Was kannst du gerade insgesamt im System tun?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."
