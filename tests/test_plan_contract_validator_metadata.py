from core.orchestrator.contracts import ToolDescriptor
from core.pipeline.plan_contract_validator import validate_plan_contract
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


def _plan(tool: str = "tool_a") -> ThinkingPlan:
    return ThinkingPlan(
        intent="run_tools",
        steps=[PlanStep(step_id="s1", title="Step", goal="Run", tool=tool)],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="plan-metadata",
    )


def _context() -> dict:
    return {"context": {"routing_frame": {"operation_contract_fingerprint": "fp-meta"}}}


def _detail(**overrides):
    data = {
        "name": "tool_a",
        "capability_domain": "memory",
        "capability_operation": "search",
        "capability_evidence_types": ["memory_context"],
        "capability_required_args": [],
        "capability_target_scopes": ["assistant_identity"],
        "capability_risk": "read_only",
    }
    data.update(overrides)
    return data


def test_string_only_tool_truth_blocks():
    decision = validate_plan_contract(_plan(), ["tool_a"], context=_context())

    assert decision.allowed is False
    assert decision.reason == "plan_contract_missing_tool_detail:tool_a"


def test_missing_domain_blocks():
    decision = validate_plan_contract(_plan(), [_detail(capability_domain="")], context=_context())

    assert decision.allowed is False
    assert decision.reason == "plan_contract_missing_tool_metadata:tool_a:capability_domain"


def test_missing_operation_blocks():
    decision = validate_plan_contract(_plan(), [_detail(capability_operation="")], context=_context())

    assert decision.allowed is False
    assert decision.reason == "plan_contract_missing_tool_metadata:tool_a:capability_operation"


def test_missing_target_scopes_blocks():
    decision = validate_plan_contract(_plan(), [_detail(capability_target_scopes=[])], context=_context())

    assert decision.allowed is False
    assert decision.reason == "plan_contract_missing_tool_metadata:tool_a:capability_target_scopes"


def test_missing_risk_blocks():
    decision = validate_plan_contract(_plan(), [_detail(capability_risk="")], context=_context())

    assert decision.allowed is False
    assert decision.reason == "plan_contract_missing_tool_metadata:tool_a:capability_risk"


def test_empty_required_args_is_allowed():
    decision = validate_plan_contract(_plan(), [_detail(capability_required_args=[])], context=_context())

    assert decision.allowed is True


def test_mismatching_complete_values_are_not_re_evaluated():
    tool = ToolDescriptor(
        name="tool_a",
        capability_domain="container_runtime",
        capability_operation="delete",
        capability_evidence_types=["runtime_logs"],
        capability_required_args=[],
        capability_target_scopes=["runtime_state"],
        capability_risk="mutating",
    )

    decision = validate_plan_contract(_plan(), [tool], context=_context())

    assert decision.allowed is True
