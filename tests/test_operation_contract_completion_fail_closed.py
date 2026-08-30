"""Completion must distinguish legacy absence from invalid contract provenance."""

import pytest

from core.task_loop.contracts import StopReason
from core.task_loop.outcome_evaluator import OutcomeAction, evaluate
from core.thinking.contracts import INVALID_OPERATION_CONTRACT_CRITERION
from core.thinking.planner import build_plan_from_analysis


def _raw_plan():
    return {
        "intent": "Use the selected tool",
        "suggested_tools": ["demo_tool"],
        "steps": [
            {
                "tool": "demo_tool",
                "done_when": "artifact_type:free_llm_evidence",
                "required_evidence": ["free_llm_evidence"],
            }
        ],
    }


def _context(frame):
    return {
        "routing_frame": frame,
        "selected_tool_details": [
            {
                "name": "demo_tool",
                "capability_evidence_types": ["free_llm_evidence"],
            }
        ],
    }


def test_contractless_legacy_plan_keeps_existing_llm_criteria():
    plan = build_plan_from_analysis(
        _raw_plan(), user_text="legacy", orchestrator_context=_context({})
    )

    assert plan.steps[0].done_when == "artifact_type:free_llm_evidence"
    assert plan.steps[0].required_evidence == ["free_llm_evidence"]


@pytest.mark.parametrize(
    "invalid_contract",
    (
        None,
        {"domain": "files"},
        {
            "domain": "files",
            "primary_operation": "read",
            "allowed_operations": ["inspect"],
        },
    ),
)
def test_partial_or_malformed_contract_blocks_without_llm_fallback(invalid_contract):
    plan = build_plan_from_analysis(
        _raw_plan(),
        user_text="invalid contract",
        orchestrator_context=_context({"operation_contract": invalid_contract}),
    )

    assert plan.steps[0].done_when == INVALID_OPERATION_CONTRACT_CRITERION
    assert plan.steps[0].required_evidence == []
    decision = evaluate(plan, [], replan_budget_remaining=True)
    assert decision.action is OutcomeAction.BLOCK
    assert decision.stop_reason is StopReason.OBJECTIVE_NOT_MET
