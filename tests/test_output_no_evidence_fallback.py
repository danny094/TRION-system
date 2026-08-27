import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.output import generate_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan

def test_generate_output_downgrades_to_unknown_when_artifacts_exist_without_grounded_evidence(monkeypatch):
    monkeypatch.setenv("GROUNDING_NO_EVIDENCE_FALLBACK_MODE", "explicit_unknown")

    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "Die VRAM-Nutzung beträgt 75%.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Prüfe die aktuelle VRAM-Nutzung.",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "task_loop": {
                        "artifacts": [
                            {
                                "artifact_type": "tool_result",
                                "tool": "container_inspect",
                                "result": "placeholder text without structured evidence",
                            }
                        ]
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Prüfe die aktuelle VRAM-Nutzung.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."
def test_generate_output_downgrades_to_unknown_when_carryover_is_unrelated(monkeypatch):
    monkeypatch.setenv("GROUNDING_NO_EVIDENCE_FALLBACK_MODE", "explicit_unknown")

    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "Erfundene Dateiausgabe.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Lies die Datei /trion-home/status.txt.",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "grounding_state": {
                        "updated_at": 100.0,
                        "age_s": 2.0,
                        "age_turns": 0,
                        "grounded_results": [
                            {"tool_name": "time_now", "step_id": "tool_1", "facts": {"utc_iso": "2026-05-12T13:58:28Z"}}
                        ],
                    },
                    "task_loop": {
                        "artifacts": [
                            {
                                "artifact_type": "tool_result",
                                "tool": "container_inspect",
                                "result": "placeholder text without structured evidence",
                            }
                        ]
                    },
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

    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."


def test_generate_output_downgrades_runtime_hardware_claim_without_hardware_evidence(monkeypatch):
    monkeypatch.setenv("GROUNDING_NO_EVIDENCE_FALLBACK_MODE", "explicit_unknown")

    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "RAM: 12 GB, VRAM: 16 GB.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie viel RAM oder VRAM hast du gerade?",
                thinking_plan=None,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={},
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Wie viel RAM oder VRAM hast du gerade?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."
