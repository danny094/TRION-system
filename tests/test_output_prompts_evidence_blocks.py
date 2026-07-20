from core.output.prompts import build_output_system_prompt
from tests._output_prompts_helpers import plan_answer_user


def test_memory_block_reads_from_orchestrator_inner_context():
    context = {
        "orchestrator": {
            "available_tools": [],
            "selected_tools": [],
            "context": {
                "memory": {
                    "available": True,
                    "items": [
                        {"content": "Dennis bevorzugt knappe Antworten."},
                        {"text": "Projekt heißt TRION."},
                    ],
                },
            },
        },
    }
    prompt = build_output_system_prompt(plan_answer_user(), context)
    assert "## Relevante Erinnerungen" in prompt
    assert "Dennis bevorzugt knappe Antworten." in prompt
    assert "Projekt heißt TRION." in prompt


def test_memory_block_ignores_legacy_top_level_memory_key():
    context = {"memory": {"items": [{"content": "Sollte NICHT erscheinen."}]}}
    prompt = build_output_system_prompt(plan_answer_user(), context)
    assert "## Relevante Erinnerungen" not in prompt
    assert "Sollte NICHT erscheinen." not in prompt


def test_task_loop_block_reads_from_task_loop_artifacts():
    context = {
        "task_loop": {
            "state": "completed",
            "artifacts": [
                {"step_id": "s1", "result": "Container gestartet."},
                {"title": "s2", "output": "Status: healthy."},
            ],
        },
    }
    prompt = build_output_system_prompt(plan_answer_user(), context)
    assert "## Ergebnisse aus ausgeführten Schritten" in prompt
    assert "s1: Container gestartet." in prompt
    assert "s2: Status: healthy." in prompt


def test_grounded_tool_block_reads_structured_tool_facts():
    context = {
        "renderable_evidence": [
            type(
                "RenderableEvidence",
                (),
                {
                    "summary": "Es ist 14:00:46 UTC.",
                    "bullets": ["Datum: 2026-05-12"],
                },
            )()
        ],
        "grounded_tool_results": [
            {
                "tool_name": "time_now",
                "step_id": "tool_1",
                "facts": {
                    "date": "2026-05-12",
                    "time": "14:00:46",
                },
            }
        ]
    }
    prompt = build_output_system_prompt(plan_answer_user(), context)
    assert "## Freigegebene verifizierte Fakten" in prompt
    assert "Es ist 14:00:46 UTC." in prompt
    assert "Datum: 2026-05-12" in prompt


def test_task_loop_block_ignores_legacy_top_level_artifacts_key():
    context = {"artifacts": [{"step_id": "s1", "result": "Sollte NICHT erscheinen."}]}
    prompt = build_output_system_prompt(plan_answer_user(), context)
    assert "## Ergebnisse aus ausgeführten Schritten" not in prompt
    assert "Sollte NICHT erscheinen." not in prompt


def test_memory_and_task_loop_blocks_absent_for_empty_context():
    prompt = build_output_system_prompt(plan_answer_user(), {})
    assert "## Relevante Erinnerungen" not in prompt
    assert "## Ergebnisse aus ausgeführten Schritten" not in prompt
