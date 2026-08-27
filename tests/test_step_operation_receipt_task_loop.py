from core.orchestrator.contracts import ToolDescriptor
from core.pipeline.task_loop_stage import build_task_loop_stage
from core.pipeline.plan_contract_validator import issue_initial_step_receipt
from core.routing_frame.contracts import OperationTransition
from core.task_loop.contracts import (
    StepExecutionStatus,
    StepOperationExecution,
    TaskLoopSnapshot,
    TaskLoopState,
)
from core.task_loop.executor import TaskToolResult
from core.task_loop.runner import run_task_loop
from core.task_loop.task_loop import start_task_loop
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
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


def test_task_loop_only_executes_followup_after_validator_receipt_and_eligibility():
    context = _context()
    tools = [_tool("inventory", "list"), _tool("log_reader", "logs")]
    plan = ThinkingPlan(
        intent="run",
        steps=[
            PlanStep(step_id="list-step", title="List", goal="List", tool="inventory"),
            PlanStep(step_id="logs-step", title="Logs", goal="Logs", tool="log_reader"),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="receipt-flow",
    )
    calls = []
    events = []
    result = build_task_loop_stage(
        plan,
        conversation_id="conv",
        objective="objective",
        task_loop_fn=start_task_loop,
        tool_runner=lambda call: calls.append(call.tool_name) or TaskToolResult(success=True, result={}),
        replanner_fn=lambda *_args, **_kwargs: None,
        max_steps=4,
        max_retries_per_step=0,
        max_replans=0,
        event_sink=lambda payload: events.append(dict(payload)),
        available_tools=tools,
        orchestrator_context=context,
    ).result

    assert calls == ["inventory", "log_reader"]
    assert [item.receipt.operation for item in result.snapshot.step_operation_executions] == ["list", "logs"]
    serialized_events = repr(events)
    for sentinel in ("TARGET_SENTINEL", "SCOPE_SENTINEL", "SECRET_SENTINEL"):
        assert sentinel not in serialized_events


def test_task_loop_blocks_followup_when_validator_cannot_issue_receipt():
    context = _context(transition_requirements=())
    tools = [_tool("inventory", "list"), _tool("log_reader", "logs")]
    plan = ThinkingPlan(
        intent="run",
        steps=[PlanStep(step_id="list-step", title="List", goal="List", tool="inventory"),
               PlanStep(step_id="logs-step", title="Logs", goal="Logs", tool="log_reader")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="receipt-block",
    )
    calls = []
    result = build_task_loop_stage(
        plan, conversation_id="conv", objective="objective", task_loop_fn=start_task_loop,
        tool_runner=lambda call: calls.append(call.tool_name) or TaskToolResult(success=True, result={}),
        replanner_fn=lambda *_args, **_kwargs: None, max_steps=4, max_retries_per_step=0,
        max_replans=0, available_tools=tools, orchestrator_context=context,
    ).result

    assert calls == ["inventory"]
    assert result.state is TaskLoopState.BLOCKED


def test_receipt_carrying_resume_blocks_without_validator_issuer():
    initial = issue_initial_step_receipt("list-step", context=_context())
    snapshot = TaskLoopSnapshot(
        "resume", "conv", "objective", TaskLoopState.EXECUTING, 1, 4, 0,
        step_operation_executions=[StepOperationExecution(initial, StepExecutionStatus.SUCCESS)],
    )
    plan = ThinkingPlan(
        intent="run",
        steps=[PlanStep(step_id="list-step", title="List", goal="List", tool="inventory"),
               PlanStep(step_id="logs-step", title="Logs", goal="Logs", tool="log_reader")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        plan_id="resume",
    )

    result = run_task_loop(plan, snapshot, lambda _call: (_ for _ in ()).throw(AssertionError("must not run")))

    assert result.state is TaskLoopState.BLOCKED
    assert result.snapshot.waiting_reason == "step_operation_receipt_missing"
