from dataclasses import asdict, replace

from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tool_eligibility import eligible_tools_for_contract
from core.pipeline.plan_contract_validator import (
    authorized_contract_for_receipt,
    issue_followup_step_receipt,
    issue_initial_step_receipt,
)
from core.pipeline.task_loop_stage import build_step_receipt_validator
from core.task_loop.contracts import (
    StepExecutionResult,
    StepExecutionStatus,
    StepOperationExecution,
    TaskLoopSnapshot,
    TaskLoopState,
)
from core.task_loop.executor import TaskToolResult
from core.task_loop.runner import run_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.routing_frame.contracts import OperationTransition
from tests.operation_contract_context import canonical_contract_context


_LIST_TO_LOGS = (OperationTransition("list", "logs", ("runtime_logs",)),)


def _context(**updates):
    normalized = {
        key: tuple(value)
        if key in {"allowed_operations", "required_evidence", "detail_fields", "transition_requirements"}
        else value
        for key, value in updates.items()
    }
    normalized.setdefault("transition_requirements", _LIST_TO_LOGS)
    return canonical_contract_context(
        target="TARGET_SENTINEL",
        scope_lock="SCOPE_SENTINEL",
        **normalized,
    )
def _tool(name, operation):
    return ToolDescriptor(
        name=name,
        capability_domain="container_runtime",
        capability_operation=operation,
        capability_evidence_types=["runtime_status" if operation == "list" else "runtime_logs"],
        capability_target_scopes=["runtime_state"],
        capability_risk="read_only",
    )


def _success(receipt):
    return StepExecutionResult("list-step", StepExecutionStatus.SUCCESS, receipt=receipt)


def test_validator_issues_initial_and_followup_receipts_from_contract_only():
    context = _context()
    initial = issue_initial_step_receipt("list-step", context=context)
    followup = issue_followup_step_receipt("logs-step", _success(initial), context=context)

    assert initial and initial.operation == "list"
    assert followup and followup.operation == "logs"
    assert followup.operation_contract_fingerprint == initial.operation_contract_fingerprint
    assert followup.scope_preserved is True


def test_followup_receipt_is_fail_closed_for_invalid_predecessor_or_contract():
    context = _context()
    initial = issue_initial_step_receipt("list-step", context=context)
    assert initial is not None

    assert issue_followup_step_receipt("logs-step", None, context=context) is None
    for status in (StepExecutionStatus.FAILED, StepExecutionStatus.TIMEOUT, StepExecutionStatus.SKIPPED):
        assert issue_followup_step_receipt(
            "logs-step", StepExecutionResult("list-step", status, receipt=initial), context=context
        ) is None
    assert issue_followup_step_receipt("logs-step", _success(replace(initial, scope_preserved=False)), context=context) is None
    assert issue_followup_step_receipt("logs-step", _success(replace(initial, operation="inspect")), context=context) is None
    assert issue_followup_step_receipt(
        "logs-step", _success(initial), context=_context(transition_requirements=())
    ) is None
    assert issue_followup_step_receipt("logs-step", _success(initial), context=_context()) is not None
    mismatch = canonical_contract_context(target="TARGET_SENTINEL", scope_lock="SCOPE_SENTINEL", fingerprint="other-fp")
    assert issue_followup_step_receipt("logs-step", _success(initial), context=mismatch) is None


def test_followup_contract_projection_only_unlocks_validator_authorized_operation():
    context = _context()
    initial = issue_initial_step_receipt("list-step", context=context)
    followup = issue_followup_step_receipt("logs-step", _success(initial), context=context)
    initial_contract = _context()["routing_frame"]["operation_contract"]
    predecessor = _success(initial)
    authorized = authorized_contract_for_receipt(followup, context=context, predecessor=predecessor)
    tools = [_tool("inventory", "list"), _tool("log_reader", "logs")]

    assert authorized["required_evidence"] == ["runtime_logs"]
    assert [tool.name for tool in eligible_tools_for_contract(tools, initial_contract)] == ["inventory"]
    assert [tool.name for tool in eligible_tools_for_contract(tools, authorized)] == ["log_reader"]


def test_receipt_serialization_excludes_contract_and_tool_sentinels():
    context = _context()
    receipt = issue_initial_step_receipt("step-id", context=context)

    assert receipt is not None
    serialized = repr(asdict(receipt))
    for sentinel in ("TARGET_SENTINEL", "SCOPE_SENTINEL", "TOOL_SENTINEL", "ARG_SENTINEL", "SECRET_SENTINEL"):
        assert sentinel not in serialized


def test_executor_and_snapshot_preserve_receipt_with_actual_status():
    receipt = issue_initial_step_receipt("list-step", context=_context())
    plan = ThinkingPlan(
        intent="run",
        steps=[PlanStep(step_id="list-step", title="List", goal="List", tool="inventory")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="receipt-plan",
    )
    snapshot = TaskLoopSnapshot("receipt-plan", "conv", "objective", TaskLoopState.EXECUTING, 0, 3, 0)

    result = run_task_loop(
        plan,
        snapshot,
        lambda _call: TaskToolResult(success=True, result={}),
        step_receipts={"list-step": receipt},
        receipt_validator=build_step_receipt_validator(_context(), [_tool("inventory", "list")], plan),
        receipt_mode=True,
    )

    execution = result.snapshot.step_operation_executions[0]
    assert execution.receipt == receipt
    assert execution.status is StepExecutionStatus.SUCCESS
    followup = issue_followup_step_receipt("logs-step", execution, context=_context())
    assert followup and followup.operation == "logs"
