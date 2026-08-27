import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.output import generate_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan

def test_generate_output_blocks_positive_execution_claims_without_execution_evidence():
    async def fake_complete_output(output_request, chat_request, **kwargs):
        return type(
            "Result",
            (),
            {
                "content": 'Ich habe 5 Stichwoerter getestet. Ergebnisse: 1. "Name" 2. "Deutsch" 3. "Interesse" 4. "Hobby" 5. "Arbeit".',
                "truncated": False,
                "postcheck_applied": False,
            },
        )()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Pruef mal die Stichwortsuche 5x.",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={},
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Pruef mal die Stichwortsuche 5x.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert "keine positiven Ausfuehrungsbelege" in result.content


def test_generate_output_allows_honest_non_execution_message_without_step_evidence():
    async def fake_complete_output(output_request, chat_request, **kwargs):
        return type(
            "Result",
            (),
            {
                "content": "Ich konnte die Stichwortsuche nicht ausfuehren, weil mir dafuer aktuell kein passendes Tool vorliegt.",
                "truncated": False,
                "postcheck_applied": False,
            },
        )()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Pruef mal die Stichwortsuche.",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={},
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Pruef mal die Stichwortsuche.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert "kein passendes Tool" in result.content
