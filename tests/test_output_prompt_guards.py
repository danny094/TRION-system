from core.output.prompts import build_output_system_prompt
from core.pipeline.output_evidence_contracts import (
    OutputEvidenceHandoff,
    OutputEvidenceItem,
    OutputEvidenceState,
)
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


def _verified_handoff() -> OutputEvidenceHandoff:
    return OutputEvidenceHandoff(
        OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE,
        (OutputEvidenceItem({"time": "14:00:46 UTC"}),),
    )


def test_output_prompt_includes_grounding_and_analysis_contracts_for_runtime_file_claim():
    prompt = build_output_system_prompt(_plan("Was steht in /trion-home/status.txt?"), {})

    assert "### OUTPUT-GROUNDING:" in prompt
    assert "### ANALYSE-GUARD:" in prompt
    assert "Tools wurden bereits ausgeführt" not in prompt


def test_output_prompt_does_not_claim_memory_search_from_raw_context():
    context = {
        "orchestrator": {
            "context": {"memory": {"available": True, "items": ["RAW_MEMORY_SENTINEL"]}}
        }
    }

    prompt = build_output_system_prompt(_plan("Was weißt du über meinen Lieblingsfilm?"), context)

    assert "RAW_MEMORY_SENTINEL" not in prompt
    assert "explizit im Gedächtnis gesucht" not in prompt


def test_output_stage_feeds_only_typed_evidence_to_prompt():
    stage = build_output_stage(
        user_text="Wie spaet ist es?",
        thinking_plan=_plan("Wie spaet ist es?"),
        verifier_result=_verifier_ok(),
        orchestrator_context={"task_loop": {"artifacts": ["RAW_TASK_SENTINEL"]}},
        document_tools_context={},
        output_evidence=_verified_handoff(),
        document_context=None,
        stream=False,
    )

    prompt = build_output_system_prompt(
        stage.output_request.thinking_plan,
        stage.output_request.context,
        renderable_evidence=stage.output_request.renderable_evidence,
    )

    assert "renderable_evidence" not in stage.output_request.context
    assert "14:00:46 UTC" in prompt
    assert "RAW_TASK_SENTINEL" not in prompt


def test_raw_grounding_state_does_not_change_prompt_contract():
    stage = build_output_stage(
        user_text="hi",
        thinking_plan=_plan(),
        verifier_result=_verifier_ok(),
        orchestrator_context={
            "grounding_state": {"grounded_results": ["RAW_GROUNDING_SENTINEL"]}
        },
        document_tools_context={},
        output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
        document_context=None,
        stream=False,
    )

    prompt = build_output_system_prompt(
        stage.output_request.thinking_plan,
        stage.output_request.context,
        renderable_evidence=stage.output_request.renderable_evidence,
    )

    assert "RAW_GROUNDING_SENTINEL" not in prompt
    assert "## Freigegebene verifizierte Fakten" not in prompt
