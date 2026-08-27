from core.output.contracts import RenderableEvidence
from core.output.prompts import build_output_system_prompt
from tests._output_prompts_helpers import plan_answer_user


def test_raw_memory_context_is_not_projected() -> None:
    context = {
        "orchestrator": {
            "context": {
                "memory": {"items": [{"content": "RAW_MEMORY_SENTINEL"}]},
            }
        }
    }

    prompt = build_output_system_prompt(plan_answer_user(), context)

    assert "RAW_MEMORY_SENTINEL" not in prompt
    assert "## Relevante Erinnerungen" not in prompt


def test_raw_task_loop_artifacts_are_not_projected() -> None:
    context = {
        "task_loop": {
            "artifacts": [{"step_id": "s1", "result": "RAW_TASK_SENTINEL"}],
        }
    }

    prompt = build_output_system_prompt(plan_answer_user(), context)

    assert "RAW_TASK_SENTINEL" not in prompt
    assert "## Ergebnisse aus ausgeführten Schritten" not in prompt


def test_typed_renderable_evidence_is_projected() -> None:
    evidence = (
        RenderableEvidence(
            summary="Es ist 14:00:46 UTC.",
            bullets=("Datum: 2026-05-12",),
        ),
    )

    prompt = build_output_system_prompt(
        plan_answer_user(),
        {"grounded_tool_results": ["RAW_TOOL_SENTINEL"]},
        renderable_evidence=evidence,
    )

    assert "## Freigegebene verifizierte Fakten" in prompt
    assert "Es ist 14:00:46 UTC." in prompt
    assert "Datum: 2026-05-12" in prompt
    assert "RAW_TOOL_SENTINEL" not in prompt


def test_empty_typed_evidence_adds_no_evidence_block() -> None:
    prompt = build_output_system_prompt(plan_answer_user(), {}, renderable_evidence=())

    assert "## Freigegebene verifizierte Fakten" not in prompt
