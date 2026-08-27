from core.orchestrator.contracts import ToolDescriptor
from core.pipeline.composite_followup import build_composite_followup_planner
from core.pipeline.output_evidence_contracts import OutputEvidenceItem
from core.pipeline.plan_contract_validator import issue_initial_step_receipt
from core.routing_frame.contracts import OperationTransition
from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus
from core.thinking.composite_followup import (
    BoundFollowupTarget,
    ValidatedFollowupEvidence,
    bind_followup_target,
    followup_step_id,
    plan_authorized_followup,
)
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from tests.operation_contract_context import canonical_contract_context


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="container_inventory_logs",
        steps=[PlanStep("list-step", "List", "List containers", tool="inventory")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="composite-plan",
    )


_LIST_TO_LOGS = (OperationTransition("list", "logs", ("runtime_logs",)),)


def _logs_tool(evidence=("runtime_logs",)) -> ToolDescriptor:
    return ToolDescriptor(
        name="runtime-log-reader",
        capability_domain="container_runtime",
        capability_operation="logs",
        capability_evidence_types=list(evidence),
        capability_required_args=["container_id_or_name"],
        capability_target_scopes=["runtime_state"],
        capability_risk="read_only",
    )


def _contract(*, target: str = "") -> dict:
    context = canonical_contract_context(
        target=target,
        targets=(target,) if target else (),
        scope_lock="runtime_state",
        transition_requirements=_LIST_TO_LOGS,
    )
    contract = context["routing_frame"]["operation_contract"]
    return {**contract, "primary_operation": "logs", "allowed_operations": ["logs"]}


def _evidence(containers) -> ValidatedFollowupEvidence:
    return ValidatedFollowupEvidence({"containers": containers})


def test_explicit_contract_target_binds_exact_matching_candidate():
    target = bind_followup_target(
        _evidence([
            {"container_id": "id-alpha", "name": "alpha"},
            {"container_id": "id-beta", "name": "beta"},
        ]),
        _contract(target="beta"),
    )

    expanded = plan_authorized_followup(
        _plan(), "list-step", _logs_tool(), target, ("runtime_logs",),
    )

    assert target == BoundFollowupTarget("id-beta")
    assert expanded is not None
    assert [step.tool for step in expanded.steps] == ["inventory", "runtime-log-reader"]
    assert expanded.steps[-1].tool_arguments == {"container_id": "id-beta"}


def test_single_typed_candidate_binds_without_contract_target():
    target = bind_followup_target(
        _evidence([{"container_id": "only-id", "name": "only-name"}]),
        _contract(),
    )

    expanded = plan_authorized_followup(
        _plan(), "list-step", _logs_tool(), target, ("runtime_logs",),
    )

    assert target == BoundFollowupTarget("only-id")
    assert expanded is not None
    assert expanded.steps[-1].tool == "runtime-log-reader"
    assert expanded.steps[-1].tool_arguments == {"container_id": "only-id"}


def test_ambiguous_or_nonmatching_candidates_remain_fail_closed():
    cases = (
        _evidence([]),
        _evidence([
            {"container_id": "id-alpha", "name": "alpha"},
            {"container_id": "id-beta", "name": "beta"},
        ]),
        _evidence([
            {"container_id": "duplicate", "name": "alpha"},
            {"container_id": "duplicate", "name": "beta"},
        ]),
        _evidence([{"container_id": "", "name": "broken"}]),
    )
    for evidence in cases:
        assert bind_followup_target(evidence, _contract()) is None
    assert bind_followup_target(
        _evidence([{"container_id": "id-alpha", "name": "alpha"}]),
        _contract(target="missing"),
    ) is None


def test_planner_rejects_untyped_target():
    assert plan_authorized_followup(
        _plan(), "list-step", _logs_tool(), {"container_id": "id-alpha"}, ("runtime_logs",),
    ) is None


def test_multiple_contract_targets_never_collapse_to_absent_target():
    ambiguous_contract = {
        **_contract(),
        "target": "alpha",
        "targets": ["alpha", "beta"],
    }

    assert bind_followup_target(
        _evidence([{"container_id": "only-id", "name": "only-name"}]),
        ambiguous_contract,
    ) is None


def test_followup_step_id_is_operation_neutral():
    assert followup_step_id("list-step") == "list-step-followup"


def _pipeline_followup(tool: ToolDescriptor, transitions=_LIST_TO_LOGS):
    context = canonical_contract_context(
        target="", targets=(), scope_lock="runtime_state",
        transition_requirements=transitions,
    )
    initial = issue_initial_step_receipt("list-step", context=context)
    result = StepExecutionResult(
        "list-step", StepExecutionStatus.SUCCESS, receipt=initial, structural_result=object(),
    )
    planner = build_composite_followup_planner(
        context, [tool], lambda _value: OutputEvidenceItem({
            "containers": [{"container_id": "only-id", "name": "only-name"}],
        }),
    )
    return planner(_plan(), _plan().steps[0], result)


def test_empty_descriptor_cannot_materialize_authorized_followup():
    assert _pipeline_followup(_logs_tool(())) is None


def test_superset_descriptor_materializes_only_contract_owned_evidence():
    expanded = _pipeline_followup(_logs_tool(("runtime_logs", "runtime_status")))
    assert expanded is not None
    assert expanded.steps[-1].required_evidence == ["runtime_logs"]


def test_empty_authorized_transition_evidence_fails_closed():
    empty = (OperationTransition("list", "logs", ()),)
    assert _pipeline_followup(_logs_tool(), empty) is None
