from core.output.prompts import build_output_system_prompt
from core.pipeline.output_stage import build_output_stage
from core.thinking.contracts import RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict, VerifierResult


def _plan(user_text: str = "hi") -> ThinkingPlan:
    return ThinkingPlan(
        intent="answer_user",
        steps=[],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        reasoning="test",
        context_hints={"user_text": user_text},
    )


def _verifier_ok() -> VerifierResult:
    return VerifierResult(verdict=Verdict.APPROVED, reason="ok")


def test_output_prompt_includes_grounding_and_analysis_contracts_for_runtime_file_claim():
    prompt = build_output_system_prompt(_plan("Was steht in /trion-home/status.txt?"), {})
    assert "### OUTPUT-GROUNDING:" in prompt
    assert "### ANALYSE-GUARD:" in prompt


def test_output_prompt_includes_memory_anti_hallucination_when_memory_is_empty():
    context = {
        "orchestrator": {
            "context": {
                "memory": {"available": True, "items": []},
            }
        }
    }
    prompt = build_output_system_prompt(_plan("Was weißt du über meinen Lieblingsfilm?"), context)
    assert "### ANTI-HALLUZINATION:" in prompt


def test_output_stage_shape_feeds_prompt_blocks_end_to_end():
    orchestrator_context = {
        "orchestrator": {
            "available_tools": [],
            "selected_tools": [],
            "context": {
                "memory": {"items": [{"content": "Erinnerung A"}]},
            },
        },
    }
    task_loop_context = {
        "task_loop": {
            "state": "completed",
            "artifacts": [
                {"step_id": "alpha", "result": "fertig"},
                {
                    "artifact_type": "tool_result",
                    "tool": "time_now",
                    "source_step_id": "tool_1",
                    "result": '{"time":"14:00:46","timezone":"UTC"}',
                },
            ],
        },
    }
    stage = build_output_stage(
        user_text="hi",
        thinking_plan=_plan(),
        verifier_result=_verifier_ok(),
        orchestrator_context=orchestrator_context,
        document_tools_context={},
        task_loop_context=task_loop_context,
        document_context=None,
        stream=False,
    )
    assert stage.output_request.context["renderable_evidence"]
    prompt = build_output_system_prompt(_plan(), stage.output_request.context)
    assert "Erinnerung A" in prompt
    assert "alpha: fertig" in prompt
    assert "## Freigegebene verifizierte Fakten" in prompt
    assert "Es ist 14:00:46 UTC." in prompt


def test_output_stage_can_carry_grounding_state_without_changing_prompt_blocks():
    stage = build_output_stage(
        user_text="hi",
        thinking_plan=_plan(),
        verifier_result=_verifier_ok(),
        orchestrator_context={},
        document_tools_context={},
        task_loop_context={},
        document_context=None,
        stream=False,
        grounding_state={
            "updated_at": 100.0,
            "age_s": 4.0,
            "age_turns": 0,
            "grounded_results": [{"tool_name": "time_now", "facts": {"time": "14:00:46"}}],
        },
    )
    assert stage.output_request.context["grounding_state"]["age_s"] == 4.0
    prompt = build_output_system_prompt(_plan(), stage.output_request.context)
    assert "## Verifizierte Tool-Fakten" not in prompt
