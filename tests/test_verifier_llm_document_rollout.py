from core.task_loop.executor import build_tool_call
from core.thinking.planner import build_plan_from_analysis
from core.verifier.contracts import Verdict
from core.verifier.document_checks import run_document_retrieval_check
from core.verifier.input_prepare import build_verifier_input
from core.verifier.llm_check import run_llm_check
from tests.verifier_document_fixture_support import document_context, entry_id_for_phrase


def test_tax_document_structure_plan_reads_real_toc_chunk_first():
    question = "Welche Kapitel enthaelt das Inhaltsverzeichnis?"
    document = document_context("WAS STEUERN SIND UND.md")
    expected_entry = entry_id_for_phrase("WAS STEUERN SIND UND.md", "Inhaltsverzeichnis")
    plan = build_plan_from_analysis(
        {
            "intent": question,
            "suggested_tools": ["workspace_get", "memory_semantic_search"],
            "document_retrieval_mode": "structure_first",
        },
        user_text=question,
        document_context=document,
    )

    verifier_input = build_verifier_input(question, plan, document_context=document)

    assert plan.steps[0].tool == "workspace_get"
    assert plan.steps[0].tool_arguments["entry_id"] == expected_entry
    assert run_document_retrieval_check(plan, verifier_input) is None


def test_story_semantic_plan_resolves_police_chunk_from_search_hits():
    question = "Warum ruft die Frau die Polizei?"
    document = document_context("Das Fenstertheater.md")
    expected_entry = entry_id_for_phrase("Das Fenstertheater.md", "hatte sie schon die Polizei verständigt")
    plan = build_plan_from_analysis(
        {
            "intent": question,
            "suggested_tools": ["memory_semantic_search", "workspace_get"],
            "document_retrieval_mode": "semantic_first",
        },
        user_text=question,
        document_context=document,
    )

    first_read = next(step for step in plan.steps if step.tool == "workspace_get")
    resolved = build_tool_call(
        first_read,
        artifacts=[
            {
                "artifact_type": "semantic_search_result",
                "source_step_id": "semantic_search_1",
                "rank": 0,
                "workspace_entry_id": expected_entry,
            }
        ],
    )

    assert plan.steps[0].tool == "memory_semantic_search"
    assert first_read.tool_arguments["document_source_step"] == "semantic_search_1"
    assert resolved.arguments["entry_id"] == expected_entry


def test_ai_semantic_plan_resolves_risk_chunk_from_search_hits():
    question = "Welche Risiken generativer KI beschreibt der Text?"
    document = document_context("Künstliche Intelligenz.md")
    expected_entry = entry_id_for_phrase("Künstliche Intelligenz.md", "generative KI-Tools neue Anwen")
    plan = build_plan_from_analysis(
        {
            "intent": question,
            "suggested_tools": ["memory_semantic_search", "workspace_get"],
            "document_retrieval_mode": "semantic_first",
        },
        user_text=question,
        document_context=document,
    )

    first_read = next(step for step in plan.steps if step.tool == "workspace_get")
    resolved = build_tool_call(
        first_read,
        artifacts=[
            {
                "artifact_type": "semantic_search_result",
                "source_step_id": "semantic_search_1",
                "rank": 0,
                "workspace_entry_id": expected_entry,
            }
        ],
    )

    assert expected_entry > 0
    assert plan.steps[0].tool == "memory_semantic_search"
    assert resolved.arguments["entry_id"] == expected_entry


def test_story_exact_question_reads_real_house_loss_chunk_and_hits_rollout_gate(monkeypatch):
    question = "An welcher Stelle wird klar, dass das Haus nicht mehr existiert?"
    document = document_context("Zeitenwende.md")
    expected_entry = entry_id_for_phrase("Zeitenwende.md", "Toter nach Gasexplosion")
    seen = {}
    plan = build_plan_from_analysis(
        {
            "intent": question,
            "suggested_tools": ["workspace_get", "memory_semantic_search"],
            "document_retrieval_mode": "workspace_first",
        },
        user_text=question,
        document_context=document,
    )

    async def fake_complete_prompt(**kwargs):
        seen["prompt"] = kwargs.get("prompt")
        return '{"approved": true, "hard_block": false, "warnings": [], "final_instruction": "ok"}'

    monkeypatch.setattr("core.verifier.llm_check.get_control_llm_check_modes", lambda: ["long_document"])
    verifier_input = build_verifier_input(question, plan, document_context=document)
    result = run_llm_check(plan, verifier_input, complete_prompt_fn=fake_complete_prompt)

    assert plan.steps[0].tool == "workspace_get"
    assert plan.steps[0].tool_arguments["entry_id"] == expected_entry
    assert result.verdict == Verdict.APPROVED
    assert '"question_focus": "exact"' in seen["prompt"]
