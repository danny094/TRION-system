from dataclasses import fields

import pytest

from adapters.task_resume_serialization import plan_from_dict, plan_to_dict
from core.thinking.contracts import (
    AdditionalEvidenceNeed, PlanStep, ResponseDerivation, ResponseProjection,
    RiskLevel, ThinkingPlan,
)


def _full_plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="inspect",
        steps=[PlanStep(
            "step-1", "Inspect", "Inspect runtime", tool="container_inspect",
            tool_arguments={"target": "runtime"}, timeout_s=2.5,
            risk=RiskLevel.NEEDS_CONFIRMATION, done_when="metadata returned",
            required_evidence=["container_metadata"],
        )],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="internal reasoning",
        suggested_tools=["container_inspect"],
        context_hints={"source": "planner"},
        plan_id="plan-1",
        response_projection=ResponseProjection("summary"),
        response_derivation=ResponseDerivation("delayed", seconds=12),
        additional_evidence_need=AdditionalEvidenceNeed(
            "tool", reason="metadata required", candidate_tools=["container_inspect"],
        ),
    )


def test_typed_plan_is_accepted_without_rebuilding_semantics():
    plan = _full_plan()
    assert ThinkingPlan.from_dict(plan) is plan
    assert plan_from_dict(plan) is plan


def test_full_plan_mapping_roundtrip_preserves_every_contract_field_and_type():
    plan = _full_plan()
    serialized = plan_to_dict(plan)
    restored = plan_from_dict(serialized)

    assert set(serialized) == {item.name for item in fields(ThinkingPlan)}
    assert restored == plan
    assert type(restored.response_projection) is ResponseProjection
    assert type(restored.response_derivation) is ResponseDerivation
    assert type(restored.additional_evidence_need) is AdditionalEvidenceNeed
    assert type(restored.steps[0]) is PlanStep


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data.pop("intent"),
        lambda data: data.__setitem__("unknown", "value"),
        lambda data: data.__setitem__("steps", "not-a-list"),
        lambda data: data["steps"][0].__setitem__("step_id", True),
        lambda data: data["response_projection"].__setitem__("kind", True),
        lambda data: data["response_derivation"].__setitem__("seconds", True),
        lambda data: data["additional_evidence_need"].__setitem__("candidate_tools", "tool"),
        lambda data: data.__setitem__("risk_level", True),
    ],
)
def test_malformed_plan_or_nested_contract_is_rejected(mutate):
    serialized = plan_to_dict(_full_plan())
    mutate(serialized)
    with pytest.raises(ValueError):
        plan_from_dict(serialized)


def test_missing_defaulted_legacy_fields_use_contract_defaults_only():
    serialized = plan_to_dict(_full_plan())
    for name in (
        "reasoning", "suggested_tools", "context_hints", "plan_id",
        "response_projection", "response_derivation", "additional_evidence_need",
    ):
        serialized.pop(name)
    restored = plan_from_dict(serialized)
    assert restored.response_projection is None
    assert restored.response_derivation is None
    assert restored.additional_evidence_need is None
