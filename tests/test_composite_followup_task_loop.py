from core.orchestrator.contracts import ToolDescriptor
from core.pipeline import composite_followup
from core.pipeline.output_evidence_contracts import OutputEvidenceItem, OutputEvidenceState
from core.pipeline.task_loop_stage import build_task_loop_stage
from core.classifier.live_claims import detect_live_claim_kind
from core.routing_frame.builder.operation_contract import build_operation_contract
from core.routing_frame.meaning import build_meaning_representation
from core.task_loop.contracts import TaskLoopState
from core.task_loop.contracts import StepExecutionResult, StepExecutionStatus
from core.task_loop.executor import (
    TaskStructuralValidationStatus,
    TaskToolResult,
    TaskToolResultStatus,
)
from core.task_loop.task_loop import start_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.thinking.composite_followup import BoundFollowupTarget
from tests.operation_contract_context import canonical_contract_context


_LIST_RESULT = object()
_LOG_RESULT = object()
_CONTAINER_ID = "d4f8a6c2e1b9473098fedcba76543210d4f8a6c2e1b9473098fedcba76543210"
_RUNTIME_PROMPT = f"Welche Container laufen und zeige mir anschließend die Logzeilen von {_CONTAINER_ID}."


def _tool(name: str, operation: str, evidence, required=()) -> ToolDescriptor:
    return ToolDescriptor(
        name=name,
        capability_domain="container_runtime",
        capability_operation=operation,
        capability_evidence_types=list(evidence) if isinstance(evidence, tuple) else [evidence],
        capability_required_args=list(required),
        capability_target_scopes=["runtime_state"],
        capability_risk="read_only",
    )


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="container_inventory_logs",
        steps=[PlanStep("list-step", "List", "List containers", tool="container_list")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="composite-flow",
    )


def _projector(containers):
    def project(value):
        if value is _LIST_RESULT:
            return OutputEvidenceItem({"containers": containers})
        if value is _LOG_RESULT:
            return OutputEvidenceItem({"container_id": "only-id", "logs": "ok"})
        return None
    return project


def _run(containers, context=None):
    inventory = _tool("container_list", "list", ("runtime_inventory", "runtime_status"))
    log_reader = _tool(
        "container_logs", "logs", "runtime_logs", ("container_id_or_name",),
    )
    calls = []

    def run_tool(call):
        calls.append(call)
        structural = _LIST_RESULT if call.tool_name == "container_list" else _LOG_RESULT
        return TaskToolResult(
            status=TaskToolResultStatus.SUCCESS_VALUE,
            result={"ok": True},
            structural_result=structural,
            structural_validation_status=TaskStructuralValidationStatus.VALID,
        )

    context = context or canonical_contract_context(target="", targets=(), scope_lock="runtime_state")
    stage = build_task_loop_stage(
        _plan(),
        conversation_id="conv",
        objective="Welche Container laufen und zeige mir die Logzeilen.",
        task_loop_fn=start_task_loop,
        tool_runner=run_tool,
        replanner_fn=lambda *_args, **_kwargs: None,
        max_steps=4,
        max_retries_per_step=0,
        max_replans=0,
        available_tools=[inventory],
        receipt_tool_descriptors=[inventory, log_reader],
        orchestrator_context=context,
        project_output_evidence_item=_projector(containers),
    )
    return stage, calls


def test_single_candidate_executes_authorized_logs_followup():
    meaning = build_meaning_representation(_RUNTIME_PROMPT)
    contract = build_operation_contract(
        domain="container_runtime",
        live_claim=detect_live_claim_kind(_RUNTIME_PROMPT),
        intent_kind="action_request",
        evidence_need="live_runtime",
        meaning=meaning,
    )
    context = canonical_contract_context(
        domain=contract.domain, primary_operation=contract.primary_operation,
        target=contract.target, targets=contract.targets,
        detail_fields=contract.detail_fields, mutating_action=contract.mutating_action,
        required_evidence=contract.required_evidence,
        allowed_operations=contract.allowed_operations,
        allowed_transitions=contract.allowed_transitions,
        transition_requirements=contract.transition_requirements,
        scope_lock=contract.scope_lock,
    )
    stage, calls = _run([{"container_id": _CONTAINER_ID, "name": "trion-webui"}], context)

    assert [call.tool_name for call in calls] == ["container_list", "container_logs"]
    assert calls[-1].arguments == {"container_id": _CONTAINER_ID}
    assert [item.receipt.operation for item in stage.result.snapshot.step_operation_executions] == [
        "list", "logs",
    ]
    assert stage.result.state is TaskLoopState.COMPLETED
    assert stage.output_evidence.state is OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE


def test_multiple_candidates_never_start_followup_without_target():
    stage, calls = _run([
        {"container_id": "id-alpha", "name": "alpha"},
        {"container_id": "id-beta", "name": "beta"},
    ])

    assert [call.tool_name for call in calls] == ["container_list"]
    assert len(stage.result.active_plan.steps) == 1
    assert stage.result.state is TaskLoopState.COMPLETED


def test_target_binding_precedes_receipt_and_eligibility(monkeypatch):
    events = []
    tool = _tool("runtime-log-reader", "logs", "runtime_logs", ("container_id_or_name",))

    monkeypatch.setattr(
        composite_followup,
        "bind_followup_target",
        lambda evidence, contract: events.append("target") or BoundFollowupTarget("only-id"),
    )
    monkeypatch.setattr(
        composite_followup,
        "issue_followup_step_receipt",
        lambda *args, **kwargs: events.append("receipt") or object(),
    )
    monkeypatch.setattr(
        composite_followup,
        "authorized_contract_for_receipt",
        lambda *args, **kwargs: events.append("contract") or {
            "primary_operation": "logs", "required_evidence": ["runtime_logs"],
        },
    )
    monkeypatch.setattr(
        composite_followup,
        "eligible_tools_for_contract",
        lambda tools, contract: events.append("eligibility") or [tool],
    )
    monkeypatch.setattr(
        composite_followup,
        "plan_authorized_followup",
        lambda plan, *args: events.append("materialize") or plan,
    )
    planner = composite_followup.build_composite_followup_planner(
        canonical_contract_context(target="", targets=(), scope_lock="runtime_state"),
        [tool],
        lambda value: events.append("project") or OutputEvidenceItem({
            "containers": [{"container_id": "only-id", "name": "only-name"}],
        }),
    )

    result = StepExecutionResult("list-step", StepExecutionStatus.SUCCESS, structural_result=object())
    assert planner is not None
    assert planner(_plan(), _plan().steps[0], result) is not None
    assert events == ["project", "target", "receipt", "contract", "eligibility", "materialize"]
